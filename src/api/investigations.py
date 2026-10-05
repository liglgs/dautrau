"""Endpoint nghiệp vụ MVP điều tra an toàn thuốc (M07).

Quyết định của reviewer nằm ở ``src/api/reviews.py`` (yêu cầu role reviewer).

Luồng: tạo cuộc điều tra (202, chạy nền) → frontend polling ``/events`` và ``/{id}`` →
reviewer gửi quyết định tại ``/reviews`` → ``/continue`` chạy tiếp → ``/export`` khi hồ sơ đã duyệt.

Mọi thao tác ghi đều đi qua runner trong tiến trình và store SQLite, không có đường tắt
nào bỏ qua budget/review.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, Query, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from src.api.auth import Role, UserSession, check_ownership, current_role, current_user
from src.models.schemas import (
    CancelResponse,
    ClaimInput,
    Dossier,
    InvestigationState,
    ReviewDecision,
    RunStatus,
    SourceDocument,
)
from src.services.dossier import export_markdown, validate_dossier
from src.services.errors import invalid_state, runner_busy, version_conflict
from src.services.runner import get_runner
from src.services.store import MvpStore

router = APIRouter(prefix="/investigations", tags=["mvp"])


class MarkdownResponse(PlainTextResponse):
    """Hồ sơ export dưới dạng Markdown (để OpenAPI ghi đúng kiểu nội dung)."""

    media_type = "text/markdown"


# --------------------------------------------------------------------------------------
# Phụ thuộc dùng chung
# --------------------------------------------------------------------------------------


def get_store() -> MvpStore:
    """Store của app; đặt một lần ở ``main`` qua ``configure_mvp``."""
    from src.api.mvp_runtime import get_mvp_store

    return get_mvp_store()


StoreDep = Annotated[MvpStore, Depends(get_store)]
RoleDep = Annotated[Role, Depends(current_role)]
UserDep = Annotated[UserSession, Depends(current_user)]


class ContinueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int | None = Field(default=None, ge=1)


# --------------------------------------------------------------------------------------
# Tạo & đọc cuộc điều tra
# --------------------------------------------------------------------------------------


@router.post("", status_code=202)
async def create_investigation(
    claim: ClaimInput,
    request: Request,
    store: StoreDep,
    role: RoleDep,
    user: UserDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    """Tạo cuộc điều tra mới và chạy nền; trả 202 + ID."""
    runner = get_runner()
    state, created = store.create_investigation(claim, idempotency_key=idempotency_key, created_by=user.user_id)
    started = False
    if created or state.run_status is RunStatus.QUEUED:
        # ``created``: tạo mới. ``queued`` + không tạo mới: lần gọi trước đã bị 429 nên job còn
        # nằm chờ — gọi lại cùng Idempotency-Key phải chạy nốt, không để job "treo" vĩnh viễn.
        if runner.is_busy and runner.current != state.investigation_id:
            # Cuộc điều tra đã được ghi lại; client có thể gọi /continue khi runner rảnh.
            error = runner_busy(runner.current)
            error.details["investigation_id"] = state.investigation_id
            raise error
        runner.start_background(state.investigation_id)
        started = True
    return {
        "investigation_id": state.investigation_id,
        "created": created,
        "started": started,
        "run_status": str(state.run_status),
        "version": state.version,
        "events_url": str(request.url_for("list_events", investigation_id=state.investigation_id)),
    }


@router.get("")
async def list_investigations(
    store: StoreDep,
    role: RoleDep,
    user: UserDep,
    limit: int = Query(default=50, ge=1, le=200),
    mine_only: bool = Query(default=False),
):
    """Danh sách cuộc điều tra đã lưu (mới nhất trước). Hỗ trợ lọc theo mine_only."""
    items = store.list_investigations(limit=limit)
    if mine_only:
        items = [item for item in items if item.get("created_by") == user.user_id]
    return {"items": items}


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str, store: StoreDep, role: RoleDep) -> dict[str, Any]:
    """Trạng thái đầy đủ để frontend polling (counters, gaps, checkpoint)."""
    state = _state(store, investigation_id)
    timestamps = store.timestamps(state.investigation_id)
    return {
        "investigation_id": state.investigation_id,
        "created_at": timestamps["created_at"],
        "updated_at": timestamps["updated_at"],
        "claim": state.claim.model_dump(),
        "normalized_claim": state.normalized_claim.model_dump() if state.normalized_claim else None,
        "run_status": str(state.run_status),
        "assessment_status": str(state.assessment_status) if state.assessment_status else None,
        "assessment": state.assessment.model_dump() if state.assessment else None,
        "stop_reason": str(state.stop_reason) if state.stop_reason else None,
        "checkpoint": str(state.checkpoint) if state.checkpoint else None,
        "next_stage": state.next_stage,
        "review_status": store.review_status(state.investigation_id),
        "last_review": store.last_review(state.investigation_id),
        "version": state.version,
        "budget": state.budget.model_dump(),
        "step_index": state.step_index,
        "searched_sources": state.searched_sources,
        "source_status": {key: str(value) for key, value in state.source_status.items()},
        "counters": {
            "evidence": len(state.active_evidence()),
            "documents": len(state.documents),
            "queries": len(state.queries),
            "gaps": len(state.gaps),
        },
        "gaps": [gap.model_dump() for gap in state.gaps],
    }


@router.get("/{investigation_id}/events")
async def list_events(
    investigation_id: str,
    store: StoreDep,
    role: RoleDep,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, Any]:
    """Timeline tiến trình cho polling (``after_id`` để chỉ lấy phần mới)."""
    _state(store, investigation_id)
    events = store.list_events(investigation_id, after_id=after_id, limit=limit)
    return {"items": events, "last_id": events[-1]["id"] if events else after_id}


@router.get("/{investigation_id}/evidence")
async def list_evidence(investigation_id: str, store: StoreDep, role: RoleDep) -> dict[str, Any]:
    """Bằng chứng kèm trích dẫn và tài liệu nguồn tương ứng."""
    state = _state(store, investigation_id)
    documents = {document.doc_id: document for document in store.list_documents(investigation_id)}
    items = []
    for evidence in store.list_evidence(investigation_id):
        document = documents.get(evidence.doc_id)
        scope_result = None
        if state.normalized_claim and not evidence.excluded:
            from src.services.evidence.contracts import read_annotation
            from src.services.evidence.scope import ScopeMatcher

            if read_annotation(evidence.notes) is not None:
                scope_result = ScopeMatcher().assess_one(evidence, state.normalized_claim)
        items.append(
            {
                **evidence.model_dump(),
                "document": _document_summary(document) if document else None,
                "scope_match": str(scope_result.outcome) if scope_result else None,
            }
        )
    return {"items": items, "active_count": len(state.active_evidence())}


@router.get("/{investigation_id}/documents/{doc_id}")
async def get_document(investigation_id: str, doc_id: str, store: StoreDep, role: RoleDep) -> dict[str, Any]:
    """Nội dung tài liệu gốc + locator để đối chiếu trích dẫn."""
    _state(store, investigation_id)
    document = store.get_document(investigation_id, doc_id)
    locators = [
        {"evidence_id": item.evidence_id, "locator": item.locator.model_dump(), "quote": item.quote}
        for item in store.list_evidence(investigation_id)
        if item.doc_id == doc_id
    ]
    return {"document": document.model_dump(), "locators": locators}


@router.get("/{investigation_id}/dossier")
async def get_dossier(investigation_id: str, store: StoreDep, role: RoleDep) -> dict[str, Any]:
    """Hồ sơ nháp hoặc đã duyệt gần nhất, kèm báo cáo kiểm tra."""
    state = _state(store, investigation_id)
    dossier: Dossier | None = store.latest_dossier(investigation_id)
    if dossier is None:
        return {"dossier": None, "approved": None, "validation": None}
    report = validate_dossier(dossier, state)
    approved = store.approved_dossier(investigation_id)
    return {
        "dossier": dossier.model_dump(),
        "approved": approved.model_dump() if approved else None,
        "validation": report.model_dump(),
    }


# --------------------------------------------------------------------------------------
# Review / continue / export
# --------------------------------------------------------------------------------------


@router.post("/{investigation_id}/cancel", response_model=CancelResponse)
async def cancel_investigation(
    investigation_id: str,
    store: StoreDep,
    user: UserDep,
) -> CancelResponse:
    """Hủy cuộc điều tra đang chạy, đang chờ hoặc chờ reviewer.

    Chỉ người tạo cuộc điều tra hoặc reviewer mới có quyền hủy.
    """
    state = _state(store, investigation_id)
    check_ownership(state, user)
    runner = get_runner()
    cancelled_state = runner.cancel(investigation_id)
    return CancelResponse(
        investigation_id=cancelled_state.investigation_id,
        run_status=cancelled_state.run_status,
        cancelled=True,
        message="Cuộc điều tra đã được hủy thành công.",
    )


@router.post("/{investigation_id}/continue", status_code=202)
async def continue_investigation(
    investigation_id: str,
    store: StoreDep,
    role: RoleDep,
    user: UserDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    payload: ContinueRequest | None = Body(default=None),
) -> dict[str, Any]:
    """Chạy tiếp sau checkpoint review (giữ nguyên ngân sách đã dùng).

    Double-click được chặn bằng ``Idempotency-Key``: cùng key + cùng version ⇒ không chạy thêm lần nữa.
    """
    state = _state(store, investigation_id)
    check_ownership(state, user)
    if payload and payload.expected_version is not None and payload.expected_version != state.version:
        raise version_conflict(payload.expected_version, state.version)
    if state.checkpoint is not None:
        raise invalid_state(
            "Còn checkpoint review chưa xử lý; hãy gửi quyết định review trước.",
            {"checkpoint": str(state.checkpoint)},
        )
    if state.run_status is RunStatus.COMPLETED:
        raise invalid_state("Cuộc điều tra đã hoàn tất; không chạy tiếp.", {"run_status": str(state.run_status)})
    runner = get_runner()
    # Kiểm tra runner rảnh TRƯỚC khi tiêu thụ Idempotency-Key: 429 là lỗi tạm thời
    # (retryable) nên client sẽ gọi lại cùng key — key không được bị "khoá" bởi lần bị từ chối.
    if runner.is_busy and runner.current != investigation_id:
        raise runner_busy(runner.current)
    token = _resume_token(idempotency_key, store.list_review_decisions(investigation_id))
    if not runner.register_resume(investigation_id, token):
        # Double-click: cùng key + cùng quyết định review ⇒ không chạy thêm lần nữa.
        return {
            "investigation_id": investigation_id,
            "run_status": str(state.run_status),
            "resumed": False,
            "detail": "Yêu cầu chạy tiếp trùng (cùng Idempotency-Key và version) đã được xử lý.",
        }
    if state.run_status is RunStatus.RUNNING:
        # Yêu cầu MỚI trong khi cuộc điều tra này đang chạy: từ chối rõ ràng thay vì 202 sai sự thật.
        runner.forget_resume(investigation_id, token)
        raise invalid_state(
            "Cuộc điều tra đang chạy; chờ chạy xong rồi thử lại.",
            {"run_status": str(state.run_status)},
        )
    try:
        runner.start_background(investigation_id, resume=True)
    except Exception:
        runner.forget_resume(investigation_id, token)
        raise
    return {"investigation_id": investigation_id, "run_status": str(state.run_status), "resumed": True}


@router.get("/{investigation_id}/trace")
async def get_investigation_trace(
    investigation_id: str,
    store: StoreDep,
    role: RoleDep,
) -> dict[str, Any]:
    """Lấy toàn bộ vết suy luận, các bước chạy LLM và tình trạng ngân sách."""
    state = _state(store, investigation_id)
    events = store.list_events(investigation_id, limit=500)
    llm_events = [e for e in events if e.get("kind") in ("llm", "step", "checkpoint", "cancelled", "running", "completed")]
    return {
        "investigation_id": state.investigation_id,
        "run_status": str(state.run_status),
        "step_index": state.step_index,
        "budget": state.budget.model_dump(),
        "counters": {
            "steps": state.step_index,
            "documents": len(state.documents),
            "evidence": len(state.active_evidence()),
            "queries": len(state.queries),
        },
        "traces": llm_events,
    }


@router.get("/{investigation_id}/export", response_class=MarkdownResponse)
async def export_dossier(investigation_id: str, store: StoreDep, role: RoleDep) -> Response:
    """Tải Markdown hồ sơ chính thức — chỉ khi có phiên bản đã duyệt."""
    _state(store, investigation_id)
    markdown = export_markdown(store, investigation_id)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{investigation_id}-dossier.md"'},
    )


# --------------------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------------------


def _resume_token(idempotency_key: str | None, decisions: list[ReviewDecision]) -> str | None:
    """Khoá idempotency của ``/continue``.

    Token gắn với **quyết định review mới nhất**: bấm lặp cùng một nút bị chặn, nhưng sau khi
    reviewer ra quyết định mới thì một lần chạy tiếp mới là hợp lệ.
    """
    if not idempotency_key:
        return None
    latest = decisions[-1].decision_id if decisions else "no-decision"
    return f"{idempotency_key}@{latest}"


def _state(store: MvpStore, investigation_id: str) -> InvestigationState:
    """Đọc state; store đã ném ``not_found`` (404) cho ID lạ, còn lại để lỗi thật nổi lên."""
    return store.get_state(investigation_id)


def _document_summary(document: SourceDocument) -> dict[str, Any]:
    return {
        "doc_id": document.doc_id,
        "source": str(document.source),
        "source_id": document.source_id,
        "version": document.version,
        "title": document.title,
        "source_url": str(document.source_url),
        "hash": document.hash,
        "retrieved_at": document.retrieved_at.isoformat(),
    }
