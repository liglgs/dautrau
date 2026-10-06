"""R2-2-02: chín điểm cuối ``/api/v2`` trên lát cắt DI (hợp đồng ``hospital-v2``).

Vì sao có tệp này: hợp đồng ``docs/spec/hospital-v2`` và bảy bảng lưu trữ đã xong từ trước, nhưng
chưa có điểm cuối HTTP nào — hợp đồng ở trạng thái ``proposed_not_implemented``, nên Người 2 và
Người 3 không có gì để nối vào. Tệp này là tầng HTTP đó.

Bốn quy tắc chi phối toàn bộ tệp:

* **Ba trạng thái tách rời.** ``work_status`` (nghiệp vụ), ``run_status`` (agent đang chạy) và
  ``review_status`` (duyệt chuyên môn) không suy ra nhau. "Đã nhận" khác "đang chạy" khác "đã duyệt",
  và gộp chúng lại chính là chỗ dễ sinh báo cáo sai nhất.
* **Không dò được sự tồn tại của ca.** Ca ngoài phạm vi trả **404**, không phải 403 — giống quy ước
  đã dùng ở ``/api/v1/investigations``.
* **Ghi thì phải khoá.** Mọi thao tác sửa đều đòi ``expected_version``; thua trong cuộc đua nhận
  **409** kèm trạng thái hiện tại để giao diện vẽ lại, chứ không âm thầm ghi đè.
* **Phiếu trả lời luôn sinh ra ở dạng nháp.** ``POST /responses`` không có tham số nào để tạo bản
  đã duyệt; chỉ ``POST /responses/{id}/review`` với quyền ``review:decide`` mới đổi được trạng thái.
  "Xuất" và "gửi" cũng là hai việc khác nhau — tệp này không gửi đi đâu cả.

Các hàm xử lý cố ý viết dạng ``def`` (không ``async``) vì chúng gọi SQLAlchemy đồng bộ; FastAPI chạy
chúng trong threadpool nên một truy vấn chậm không chặn vòng lặp sự kiện.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine

from src.api.auth import Principal, require_permission
from src.models.schemas import ErrorCode
from src.services.casework.store import CaseWorkStore
from src.services.errors import MvpError, forbidden, invalid_request, not_found
from src.services.identity import Permission
from src.services.request_context import current_request_id
from src.services.warehouse import db as wh_db

_log = logging.getLogger(__name__)

router = APIRouter(tags=["v2"])

#: Trần số dòng một trang hàng chờ; chặn ``limit`` lớn làm nghẽn kho.
MAX_PAGE = 200


# --------------------------------------------------------------------------------------
# Engine và kho
# --------------------------------------------------------------------------------------


@lru_cache(maxsize=4)
def _store_for(url: str) -> CaseWorkStore:
    engine: Engine = wh_db.get_warehouse_engine(url)
    return CaseWorkStore(engine)


def get_casework_store() -> CaseWorkStore:
    """Kho lát cắt DI trên chính cơ sở dữ liệu kho ELT (bảy bảng chỉ-thêm).

    Tách thành dependency để phép kiểm thử thay được bằng ``app.dependency_overrides`` mà không
    cần dựng PostgreSQL thật.
    """
    return _store_for(wh_db.elt_database_url())


StoreDep = Annotated[CaseWorkStore, Depends(get_casework_store)]


# --------------------------------------------------------------------------------------
# Mô hình vào/ra (khớp ``docs/spec/hospital-v2/schemas.json``)
# --------------------------------------------------------------------------------------

WorkStatus = Literal[
    "draft", "accepted", "in_progress", "awaiting_information", "awaiting_review", "completed", "cancelled"
]
RunStatusRef = Literal[
    "not_started", "queued", "running", "waiting_for_review", "completed", "cancelled", "interrupted", "failed"
]
ReviewStatusRef = Literal["not_required", "pending", "approved", "rejected", "changes_requested"]
AssessmentStatus = Literal[
    "supported_for_scope",
    "contradicted_for_scope",
    "insufficient_evidence",
    "scope_mismatch",
    "out_of_scope",
    "requires_human_review",
]
Priority = Literal["routine", "urgent", "stat"]
Channel = Literal["web", "api", "import", "email"]
Language = Literal["vi", "en"]
Purpose = Literal["initial", "additional", "recheck", "reproduce"]
ReviewAction = Literal[
    "approve", "reject", "request_changes", "edit_claim", "edit_evidence", "exclude_evidence", "request_more"
]
FollowUpKind = Literal["request_information", "recheck_source", "monitor_case", "handover", "close"]


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=120)
    display_name: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=60)


class RequestContext(BaseModel):
    """Bối cảnh tiếp nhận. ``request_id`` và ``received_at`` do máy chủ sinh, không nhận từ người gọi."""

    model_config = ConfigDict(extra="forbid")

    requester: Actor
    channel: Channel = "api"
    raw_text: str = Field(min_length=1, max_length=20000)
    language: Language = "vi"
    source_system: dict[str, Any] | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class UnknownField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=500)
    needs_confirmation: bool = True


class WorkItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    context: RequestContext
    scope: dict[str, Any] = Field(default_factory=dict)
    unknowns: list[UnknownField] = Field(default_factory=list)
    priority: Priority = "routine"
    owner: Actor | None = None
    labels: dict[str, Any] = Field(default_factory=dict)
    work_status: WorkStatus | None = None
    revision_of: str | None = Field(default=None, max_length=120)
    revision_reason: str | None = Field(default=None, max_length=500)


class WorkItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    question: str | None = Field(default=None, min_length=1, max_length=4000)
    scope: dict[str, Any] | None = None
    unknowns: list[UnknownField] | None = None
    priority: Priority | None = None
    owner: Actor | None = None
    labels: dict[str, Any] | None = None
    work_status: WorkStatus | None = None
    reason: str | None = Field(default=None, max_length=500)


class InvestigationLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investigation_id: str = Field(min_length=1, max_length=120)
    purpose: Purpose = "initial"
    state: RunStatusRef = "queued"
    run_summary: dict[str, Any] | None = None


class ResponseSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Literal["summary", "evidence", "limits", "recommendation", "follow_up"]
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20000)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class ResponseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[ResponseSectionIn] = Field(min_length=1)
    assessment_status: AssessmentStatus
    coverage: dict[str, Any] | None = None
    drafted_by: Actor | None = None


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    reviewer: Actor | None = None
    reason: str | None = Field(default=None, max_length=2000)
    #: Bắt buộc: duyệt một bản mà không nói rõ đang duyệt phiên bản nào là duyệt mù.
    expected_version: int = Field(ge=1)


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: FollowUpKind
    note: str = Field(min_length=1, max_length=4000)
    due_at: str | None = None
    assignee: Actor | None = None


# --------------------------------------------------------------------------------------
# Phạm vi nhìn thấy
# --------------------------------------------------------------------------------------


#: Vai trò trong hệ thống quyền → vai trò **chuyên môn** mà hợp đồng ``Actor.role`` nói tới
#: (``ACTOR_ROLES`` trong ``src/services/casework/store.py``). Chỉ ánh xạ khi hai thứ trùng nghĩa
#: thật; "điều tra viên" và "người kiểm toán" **không** nói người đó là bác sĩ hay dược sĩ, nên hai
#: vai đó để trống trường ``role`` thay vì gán bừa một chức danh chuyên môn.
_PROFESSIONAL_ROLE = {
    "reviewer": "reviewer",
    "admin": "admin",
    "service": "service",
}


def _actor_of(principal: Principal) -> dict[str, Any]:
    """Danh tính cho hợp đồng: mã người, tên hiển thị, và vai chuyên môn khi biết chắc."""
    actor: dict[str, Any] = {"id": principal.user_id}
    if principal.display_name:
        actor["display_name"] = principal.display_name
    role = _PROFESSIONAL_ROLE.get(str(principal.role))
    if role:
        actor["role"] = role
    return actor


def _is_owner(document: dict[str, Any], principal: Principal) -> bool:
    """Yêu cầu này có thuộc về người đang gọi không.

    Chưa gán chủ sở hữu thì người **gửi yêu cầu** được coi là chủ, để ca mới tạo vẫn đọc lại được
    trước khi hàng đợi phân công.
    """
    owner = document.get("owner") or {}
    if owner.get("id"):
        return owner["id"] == principal.user_id
    requester = (document.get("context") or {}).get("requester") or {}
    return requester.get("id") == principal.user_id


def _require_visible(document: dict[str, Any], principal: Principal) -> dict[str, Any]:
    """Ca ngoài phạm vi trả 404 để không dò được sự tồn tại của ca."""
    if principal.has(Permission.INVESTIGATION_READ_ANY):
        return document
    if _is_owner(document, principal):
        return document
    raise not_found("yêu cầu", str(document.get("work_item_id") or ""))


def _read_work_item(store: CaseWorkStore, work_item_id: str, principal: Principal) -> dict[str, Any]:
    return _require_visible(store.get_work_item(work_item_id), principal)


def _require_writable(document: dict[str, Any], principal: Principal) -> dict[str, Any]:
    """Sửa được khi là chủ ca, hoặc khi có quyền chạy mọi ca."""
    if principal.has(Permission.INVESTIGATION_RUN_ANY):
        return document
    identifier = str(document.get("work_item_id") or "")
    if not _is_owner(document, principal) or not principal.has(Permission.INVESTIGATION_RUN_OWN):
        raise not_found("yêu cầu", identifier)
    return document


# --------------------------------------------------------------------------------------
# Yêu cầu tiếp nhận
# --------------------------------------------------------------------------------------


@router.post("/work-items", status_code=201)
def create_work_item(
    payload: WorkItemCreate,
    request: Request,
    response: Response,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_CREATE))],
) -> dict[str, Any]:
    """Tiếp nhận một yêu cầu mới.

    ``work_status`` mặc định là ``draft``: tiếp nhận **không** đồng nghĩa với bắt đầu điều tra.
    ``request_id`` và ``received_at`` do máy chủ sinh — người gọi không được tự đặt, vì nhật ký
    truy vết dựa vào chúng.
    """
    context = payload.context.model_dump()
    context["request_id"] = _request_id(request)
    context["received_at"] = _now_iso()
    document = store.create_work_item(
        question=payload.question,
        context=context,
        scope=payload.scope,
        unknowns=[item.model_dump() for item in payload.unknowns],
        priority=payload.priority,
        owner=payload.owner.model_dump() if payload.owner else _actor_of(principal),
        labels=payload.labels,
        actor=_actor_of(principal),
        revision_of=payload.revision_of,
        revision_reason=payload.revision_reason,
    )
    if payload.work_status is not None and payload.work_status != "draft":
        document = store.update_work_item(
            document["work_item_id"],
            changes={"work_status": payload.work_status},
            expected_version=document["version"],
            actor=_actor_of(principal),
            reason="Trạng thái ban đầu do người gửi đặt.",
        )
    response.headers["ETag"] = str(document.get("etag") or "")
    return document


@router.get("/work-items")
def list_work_items(
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_READ_OWN))],
    work_status: Annotated[WorkStatus | None, Query()] = None,
    run_status: Annotated[RunStatusRef | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE)] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """Hàng chờ yêu cầu, mới nhất trước.

    Người chỉ có quyền đọc ca của mình **không** thấy ca người khác trong danh sách; lọc theo phạm vi
    nằm trong câu truy vấn chứ không cắt sau ``LIMIT``, nên số trang không bị hụt.
    """
    offset = _offset_from_cursor(cursor)
    # Lấy dư một dòng để biết còn trang sau hay không, thay vì đoán theo ``limit``.
    rows = store.list_work_items(
        work_status=work_status, run_status=run_status, limit=limit + 1, offset=offset
    )
    visible = [row for row in rows if principal.has(Permission.INVESTIGATION_READ_ANY) or _is_owner(row, principal)]
    page = visible[:limit]
    next_cursor = str(offset + len(page)) if len(visible) > limit else None
    return {"items": page, "next_cursor": next_cursor, "total": len(page)}


@router.get("/work-items/{work_item_id}")
def read_work_item(
    work_item_id: str,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_READ_OWN))],
) -> dict[str, Any]:
    """Đọc một yêu cầu kèm mọi thứ thuộc về nó, trong một phiên đọc."""
    document = _read_work_item(store, work_item_id, principal)
    return store.work_item_bundle(document["work_item_id"])


@router.patch("/work-items/{work_item_id}")
def update_work_item(
    work_item_id: str,
    payload: WorkItemPatch,
    response: Response,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_READ_OWN))],
) -> dict[str, Any]:
    """Sửa câu hỏi/phạm vi hoặc gán chủ sở hữu.

    Gán chủ sở hữu là việc của hàng đợi, không phải của người điều tra: đổi ``owner`` đòi quyền
    ``queue:assign``. Khoá lạc quan nằm ở ``expected_version``; thiếu thì nhận 422 chứ không được
    hiểu ngầm là "ghi đè bản mới nhất".
    """
    current = _read_work_item(store, work_item_id, principal)
    changes: dict[str, Any] = {}
    for field in ("question", "scope", "priority", "labels", "work_status"):
        value = getattr(payload, field)
        if value is not None:
            changes[field] = value
    if payload.unknowns is not None:
        changes["unknowns"] = [item.model_dump() for item in payload.unknowns]
    if payload.owner is not None:
        if not principal.has(Permission.QUEUE_ASSIGN):
            raise forbidden(f"Vai {principal.role} không có quyền queue:assign.")
        changes["owner"] = payload.owner.model_dump()
    if not changes:
        raise invalid_request("Không có trường nào để sửa.")
    if "owner" not in changes:
        _require_writable(current, principal)
    document = store.update_work_item(
        work_item_id,
        changes=changes,
        expected_version=payload.expected_version,
        actor=_actor_of(principal),
        reason=payload.reason,
    )
    response.headers["ETag"] = str(document.get("etag") or "")
    return document


@router.post("/work-items/{work_item_id}/investigations", status_code=201)
def link_investigation(
    work_item_id: str,
    payload: InvestigationLinkCreate,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_RUN_OWN))],
) -> dict[str, Any]:
    """Liên kết một lần chạy điều tra với yêu cầu.

    Đây là **liên kết**, không phải lệnh chạy: tệp này không khởi động agent. Nhờ vậy một yêu cầu có
    thể có nhiều lần chạy (``initial``/``additional``/``recheck``/``reproduce``) mà không lẫn chúng.
    """
    current = _read_work_item(store, work_item_id, principal)
    _require_writable(current, principal)
    return store.add_investigation_link(
        work_item_id=work_item_id,
        investigation_id=payload.investigation_id,
        purpose=payload.purpose,
        state=payload.state,
        run_summary=payload.run_summary,
        actor=_actor_of(principal),
    )


@router.get("/work-items/{work_item_id}/evidence-bundle")
def read_evidence_bundle(
    work_item_id: str,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_READ_OWN))],
) -> dict[str, Any]:
    """Gói bằng chứng của lần chạy gần nhất.

    Chưa có gói nào trả **404** kèm lý do, không trả một gói rỗng — gói rỗng trông y hệt "đã tìm mà
    không thấy gì", và đó là hai chuyện khác nhau.
    """
    _read_work_item(store, work_item_id, principal)
    bundles = store.list_evidence_bundles(work_item_id)
    if not bundles:
        # 404 chứ không trả gói rỗng: gói rỗng trông y hệt "đã tìm mà không thấy gì".
        raise MvpError(
            404,
            ErrorCode.NOT_FOUND,
            "Yêu cầu chưa có gói bằng chứng nào.",
            {"work_item_id": work_item_id, "remedy": "Liên kết một lần chạy điều tra trước."},
        )
    return bundles[-1]


@router.post("/work-items/{work_item_id}/responses", status_code=201)
def create_response(
    work_item_id: str,
    payload: ResponseCreate,
    response: Response,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_RUN_OWN))],
) -> dict[str, Any]:
    """Tạo phiếu trả lời. Luôn là **bản nháp**.

    Không có tham số nào để tạo bản đã duyệt. Bản nháp trước đó của cùng yêu cầu chuyển sang
    ``superseded`` chứ không bị xoá, để còn đối chiếu được đã đổi cái gì.
    """
    current = _read_work_item(store, work_item_id, principal)
    _require_writable(current, principal)
    document = store.save_response(
        work_item_id=work_item_id,
        sections=[section.model_dump() for section in payload.sections],
        status="draft",
        assessment_status=payload.assessment_status,
        coverage=payload.coverage,
        drafted_by=payload.drafted_by.model_dump() if payload.drafted_by else _actor_of(principal),
        actor=_actor_of(principal),
    )
    response.headers["ETag"] = str(document.get("etag") or "")
    return document


@router.post("/responses/{response_id}/review")
def review_response(
    response_id: str,
    payload: ReviewCreate,
    response: Response,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.REVIEW_DECIDE))],
) -> dict[str, Any]:
    """Duyệt phiếu trả lời. Chỉ vai có ``review:decide`` gọi được.

    Quyết định lưu **trước**, trạng thái phiếu đổi **sau**, trong cùng giao dịch — nên không có cửa
    sổ nào để một phiếu vừa "đã duyệt" vừa không có vết quyết định.
    """
    store.get_response(response_id)  # 404 nếu không có
    store.add_review(
        entity="response",
        entity_id=response_id,
        action=payload.action,
        reviewer=payload.reviewer.model_dump() if payload.reviewer else _actor_of(principal),
        reason=payload.reason,
        expected_version=payload.expected_version,
    )
    document = store.get_response(response_id)
    response.headers["ETag"] = str(document.get("etag") or "")
    return document


@router.post("/work-items/{work_item_id}/follow-ups", status_code=201)
def create_follow_up(
    work_item_id: str,
    payload: FollowUpCreate,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_RUN_OWN))],
) -> dict[str, Any]:
    """Tạo việc theo dõi/chuyển giao.

    ``due_at`` chỉ được đặt khi người gọi nêu tường minh. Không suy ra hạn luật định từ loại việc:
    hệ thống không biết hạn nào áp dụng cho cơ sở nào.
    """
    current = _read_work_item(store, work_item_id, principal)
    _require_writable(current, principal)
    return store.add_follow_up(
        work_item_id=work_item_id,
        kind=payload.kind,
        note=payload.note,
        due_at=_parse_due_at(payload.due_at),
        assignee=payload.assignee.model_dump() if payload.assignee else None,
        actor=_actor_of(principal),
    )


# --------------------------------------------------------------------------------------
# Tiện ích
# --------------------------------------------------------------------------------------


def _request_id(request: Request) -> str:
    """Mã yêu cầu **dùng chung** với envelope lỗi và nhật ký kiểm toán.

    Đọc từ ``ContextVar`` mà middleware đã đặt, không tự sinh mã mới: một mã riêng ở đây sẽ làm
    ``context.request_id`` không tra ngược được sang sự kiện kiểm toán nào.
    """
    value = current_request_id()
    if value:
        return str(value)
    return str(request.headers.get("X-Request-Id") or "").strip()[:128]


def _now_iso() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def _parse_due_at(value: str | None):
    if value is None:
        return None
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise invalid_request(f"due_at không phải mốc thời gian RFC 3339: {value}") from exc
    if parsed.tzinfo is None:
        raise invalid_request("due_at phải kèm múi giờ.")
    return parsed


def _offset_from_cursor(cursor: str | None) -> int:
    if cursor is None or cursor == "":
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise invalid_request(f"cursor không hợp lệ: {cursor}") from exc
    if offset < 0:
        raise invalid_request("cursor không được âm.")
    return offset


__all__ = ["router", "get_casework_store"]
