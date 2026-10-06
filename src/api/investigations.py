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

from src.api.auth import (
    Principal,
    current_principal,
    require_investigation_access,
)
from src.models.schemas import (
    CancelResponse,
    ClaimInput,
    ContinueResponse,
    CreateInvestigationResponse,
    DocumentResponse,
    Dossier,
    DossierResponse,
    EventListResponse,
    EvidenceListResponse,
    InvestigationDetailResponse,
    InvestigationListResponse,
    InvestigationState,
    ReviewDecision,
    RunStatus,
    SourceDocument,
    TraceResponse,
)
from src.services.dossier import export_markdown, validate_dossier
from src.services.errors import forbidden, invalid_state, runner_busy, version_conflict
from src.services.identity import Permission
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
UserDep = Annotated[Principal, Depends(current_principal)]


def _require(principal: Principal, permission: Permission) -> None:
    """Đòi một quyền; thiếu thì 403 kèm tên quyền để người vận hành biết đường sửa vai."""
    if not principal.has(permission):
        raise forbidden(f"Vai {principal.role} không có quyền {permission}.")


class ContinueRequest(BaseModel):
    """Body của ``/continue``. ``expected_version`` là **bắt buộc** (RV-06).

    Trước đây bỏ trống được, nên hai lần bấm chạy tiếp cùng lúc đều qua. Nay thiếu trường này
    trả 422; gửi sai phiên bản trả 409 ``version_conflict``.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


# --------------------------------------------------------------------------------------
# Tạo & đọc cuộc điều tra
# --------------------------------------------------------------------------------------


@router.post("", status_code=202, response_model=CreateInvestigationResponse)
async def create_investigation(
    claim: ClaimInput,
    request: Request,
    store: StoreDep,
    user: UserDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> CreateInvestigationResponse:
    """Tạo cuộc điều tra mới và chạy nền; trả 202 + ID."""
    _require(user, Permission.INVESTIGATION_CREATE)
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


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    store: StoreDep,
    user: UserDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    mine_only: bool = Query(default=False),
) -> InvestigationListResponse:
    """Danh sách cuộc điều tra (mới nhất trước).

    AUTH-02: vai chỉ có quyền ``:own`` **luôn** bị giới hạn vào ca của mình, và bộ lọc nằm trong
    câu truy vấn (trước ``LIMIT``) nên không còn chuyện ca cũ biến mất khỏi danh sách. Trả thêm
    ``total``/``has_more`` để giao diện phân trang mà không đếm bằng độ dài trang đầu.
    """
    created_by = user.user_id if (mine_only or not user.has(Permission.INVESTIGATION_READ_ANY)) else None
    items = store.list_investigations(limit=limit, created_by=created_by, offset=offset)
    total = store.count_investigations(created_by=created_by)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
        "scope": "own" if created_by is not None else "any",
    }


@router.get("/{investigation_id}", response_model=InvestigationDetailResponse)
async def get_investigation(
    investigation_id: str, store: StoreDep, user: UserDep
) -> InvestigationDetailResponse:
    """Trạng thái đầy đủ để frontend polling (counters, gaps, checkpoint)."""
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "read")
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


@router.get("/{investigation_id}/events", response_model=EventListResponse)
async def list_events(
    investigation_id: str,
    store: StoreDep,
    user: UserDep,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> EventListResponse:
    """Timeline tiến trình cho polling (``after_id`` để chỉ lấy phần mới)."""
    require_investigation_access(user, _state(store, investigation_id), "read")
    events = store.list_events(investigation_id, after_id=after_id, limit=limit)
    return {"items": events, "last_id": events[-1]["id"] if events else after_id}


@router.get("/{investigation_id}/evidence", response_model=EvidenceListResponse)
async def list_evidence(investigation_id: str, store: StoreDep, user: UserDep) -> EvidenceListResponse:
    """Bằng chứng kèm trích dẫn và tài liệu nguồn tương ứng."""
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "read")
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


@router.get("/{investigation_id}/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    investigation_id: str, doc_id: str, store: StoreDep, user: UserDep
) -> DocumentResponse:
    """Nội dung tài liệu gốc + locator để đối chiếu trích dẫn."""
    require_investigation_access(user, _state(store, investigation_id), "read")
    document = store.get_document(investigation_id, doc_id)
    locators = [
        {"evidence_id": item.evidence_id, "locator": item.locator.model_dump(), "quote": item.quote}
        for item in store.list_evidence(investigation_id)
        if item.doc_id == doc_id
    ]
    return {"document": document.model_dump(), "locators": locators}


@router.get("/{investigation_id}/dossier", response_model=DossierResponse)
async def get_dossier(investigation_id: str, store: StoreDep, user: UserDep) -> DossierResponse:
    """Hồ sơ nháp hoặc đã duyệt gần nhất, kèm báo cáo kiểm tra."""
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "read")
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

    Chỉ người có quyền chạy ca (``investigation:run:own``/``:any``) mới hủy được.
    """
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "run")
    runner = get_runner()
    cancelled_state = runner.cancel(investigation_id)
    return CancelResponse(
        investigation_id=cancelled_state.investigation_id,
        run_status=cancelled_state.run_status,
        cancelled=True,
        message="Cuộc điều tra đã được hủy thành công.",
    )


@router.post("/{investigation_id}/continue", status_code=202, response_model=ContinueResponse)
async def continue_investigation(
    investigation_id: str,
    store: StoreDep,
    user: UserDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    payload: ContinueRequest = Body(...),
) -> ContinueResponse:
    """Chạy tiếp sau checkpoint review (giữ nguyên ngân sách đã dùng).

    RV-06: ``expected_version`` là bắt buộc — thiếu thì 422, sai thì 409. Double-click vẫn được
    chặn thêm bằng ``Idempotency-Key``.
    """
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "run")
    if state.checkpoint is not None:
        raise invalid_state(
            "Còn checkpoint review chưa xử lý; hãy gửi quyết định review trước.",
            {"checkpoint": str(state.checkpoint)},
        )
    if state.run_status is RunStatus.COMPLETED:
        raise invalid_state("Cuộc điều tra đã hoàn tất; không chạy tiếp.", {"run_status": str(state.run_status)})
    # RT-04: ca đã hủy không được hồi sinh. Trước đây chỉ chặn checkpoint/COMPLETED/RUNNING, nên
    # một ca đã hủy vẫn chạy tiếp được và kết thúc ở trạng thái "hoàn tất".
    if state.run_status is RunStatus.CANCELLED:
        raise invalid_state(
            "Cuộc điều tra đã bị hủy; không chạy tiếp.",
            {"run_status": str(state.run_status)},
        )
    runner = get_runner()
    # Kiểm tra runner rảnh TRƯỚC khi tiêu thụ Idempotency-Key: 429 là lỗi tạm thời
    # (retryable) nên client sẽ gọi lại cùng key — key không được bị "khoá" bởi lần bị từ chối.
    if runner.is_busy and runner.current != investigation_id:
        raise runner_busy(runner.current)
    token = _resume_token(idempotency_key, store.list_review_decisions(investigation_id))
    # RV-06: nhận ra cú bấm trùng TRƯỚC khi kiểm phiên bản. Lượt chạy nền do cú bấm đầu khởi động
    # làm phiên bản nhảy liên tục, nên kiểm phiên bản trước sẽ biến cú bấm thứ hai thành 409 —
    # đúng thứ mà khoá chống lặp sinh ra để tránh.
    if token is not None and store.has_resume_request(investigation_id, token):
        return ContinueResponse(
            investigation_id=investigation_id,
            run_status=str(state.run_status),
            resumed=False,
            detail="Yêu cầu chạy tiếp trùng (cùng Idempotency-Key và quyết định review) đã được xử lý.",
        )
    if payload.expected_version != state.version:
        # Chưa tiêu thụ khoá: client đọc lại phiên bản rồi gửi lại **cùng** key vẫn phải chạy được.
        raise version_conflict(payload.expected_version, state.version)
    if not runner.register_resume(investigation_id, token):
        return ContinueResponse(
            investigation_id=investigation_id,
            run_status=str(state.run_status),
            resumed=False,
            detail="Yêu cầu chạy tiếp trùng (cùng Idempotency-Key và quyết định review) đã được xử lý.",
        )
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
    return ContinueResponse(
        investigation_id=investigation_id, run_status=str(state.run_status), resumed=True
    )


@router.get("/{investigation_id}/trace", response_model=TraceResponse)
async def get_investigation_trace(
    investigation_id: str,
    store: StoreDep,
    user: UserDep,
) -> TraceResponse:
    """Lấy toàn bộ vết suy luận, các bước chạy LLM và tình trạng ngân sách."""
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "read")
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
async def export_dossier(investigation_id: str, store: StoreDep, user: UserDep) -> Response:
    """Tải Markdown hồ sơ chính thức — chỉ khi có phiên bản đã duyệt."""
    state = _state(store, investigation_id)
    require_investigation_access(user, state, "export")
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
    """Tóm tắt tài liệu cho giao diện.

    API-02: phải kèm ``metadata`` — giao diện đang đọc ``document.metadata.coverage`` để hiện
    phần báo phủ, mà trước đây trường này không bao giờ tới nơi.
    """
    return {
        "doc_id": document.doc_id,
        "source": str(document.source),
        "source_id": document.source_id,
        "version": document.version,
        "title": document.title,
        "source_url": str(document.source_url),
        "hash": document.hash,
        "retrieved_at": document.retrieved_at.isoformat(),
        "metadata": document.metadata,
    }
