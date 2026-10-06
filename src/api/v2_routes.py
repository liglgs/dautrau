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
* **Danh tính lấy từ phiên đăng nhập, không lấy từ thân yêu cầu.** Ai duyệt và ai soạn phiếu đều
  do máy chủ điền từ danh tính đã xác thực; không có trường nào trong thân yêu cầu ghi đè được, vì
  như vậy bất kỳ ai cũng ký được quyết định dưới tên đồng nghiệp. Ba chỗ còn lại **được** nêu tên
  người khác — ``owner``, ``assignee``, ``context.requester`` — nhưng đều đòi quyền ``queue:assign``,
  vì cả ba đều là giao việc hoặc cấp quyền đọc cho người khác. ``role``/``unit`` đi kèm những cái
  tên đó là dữ liệu ghi lại, **không** cấp quyền gì.

Chỗ tệp này cố ý khác hợp đồng ``docs/spec/hospital-v2`` (ghi ra để người đọc không tưởng là sót):

* Thân yêu cầu của ``POST /work-items`` **không** nhận ``WorkItem`` nguyên bản. Hợp đồng mô tả thân
  đó bằng chính ``WorkItem``, tức là đòi cả ``work_item_id``/``version``/``created_at`` — những
  trường máy chủ sinh. Tệp này nhận một tập con và tự sinh phần còn lại.
* Yêu cầu mới **luôn** ở ``draft``; không có đường nào tạo thẳng một yêu cầu đã duyệt hay đã huỷ.
* ``GET /work-items/{id}`` trả cả gói (yêu cầu + liên kết + gói bằng chứng + phiếu + việc theo dõi)
  trong một lần đọc, thay vì chỉ ``WorkItem``.
* ``ETag`` trả ở dạng ``W/"..."``; các tuyến đọc không gửi ``ETag``.
* Chưa đọc ``If-Match`` và ``Idempotency-Key`` mà hợp đồng có khai báo; khoá lạc quan đi qua
  ``expected_version`` trong thân yêu cầu.
* ``GET /work-items/{id}/evidence-bundle`` đối chiếu gói với ``schemas.json`` rồi mới trả; gói sai
  lược đồ nhận **500** kèm đường dẫn từng chỗ sai, vì hình dạng gói do bên ghi quyết định chứ không
  qua một mô hình nào của tầng này.
* ``POST /responses`` **cố ý** không đòi ``expected_version``: đây là đường chỉ-thêm, bản trước
  chuyển sang ``superseded`` chứ không bị đè, nên hai lần lưu đua nhau không làm mất dữ liệu. Đổi
  lại, một người soạn có thể vô hiệu hoá phiên bản mà người duyệt đang chuẩn bị quyết — chấp nhận
  vì quyết định duyệt vẫn có khoá riêng của nó.

Các hàm xử lý cố ý viết dạng ``def`` (không ``async``) vì chúng gọi SQLAlchemy đồng bộ; FastAPI chạy
chúng trong threadpool nên một truy vấn chậm không chặn vòng lặp sự kiện.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Engine

from src.api.auth import Principal, require_permission
from src.models.schemas import ErrorCode
from src.services.casework.store import CaseWorkStore
from src.services.errors import MvpError, forbidden, invalid_request, not_found
from src.services.identity import Permission
from src.services.request_context import current_request_id
from src.services.warehouse import db as wh_db

router = APIRouter(tags=["v2"])

#: Trần số dòng một trang hàng chờ; chặn ``limit`` lớn làm nghẽn kho.
MAX_PAGE = 200

#: Lược đồ đóng băng của hợp đồng ``hospital-v2``. Đọc một lần lúc nạp mô-đun: tệp này là hợp đồng,
#: không phải cấu hình, nên thiếu nó là lỗi dựng chương trình chứ không phải lỗi chạy.
_CONTRACT_SCHEMAS = json.loads(
    (Path(__file__).resolve().parents[2] / "docs" / "spec" / "hospital-v2" / "schemas.json").read_text(
        encoding="utf-8"
    )
)


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

ProfessionalRole = Literal["doctor", "pharmacist", "nurse", "reviewer", "admin", "service"]
Resolution = Literal["confirmed", "candidate", "unknown"]
ScopeSource = Literal["requester", "dictionary", "agent", "reviewer", "unknown"]
AttachmentKind = Literal["file", "url", "text"]
WorkStatus = Literal[
    "draft", "accepted", "in_progress", "awaiting_information", "awaiting_review", "completed", "cancelled"
]
RunStatusRef = Literal[
    "not_started", "queued", "running", "waiting_for_review", "completed", "cancelled", "interrupted", "failed"
]
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
    role: ProfessionalRole | None = None
    unit: str | None = Field(default=None, max_length=120)


class ScopeField(BaseModel):
    """Một trường phạm vi theo ``ScopeField`` của hợp đồng.

    ``resolution="unknown"`` là giá trị **hợp lệ**, không phải chỗ trống: câu hỏi chưa nêu rõ thì
    ghi là chưa rõ, không tự suy diễn thành một giá trị cụ thể.
    """

    model_config = ConfigDict(extra="forbid")

    value: str | None = Field(default=None, max_length=300)
    resolution: Resolution
    source: ScopeSource | None = None
    evidence_ref: str | None = Field(default=None, max_length=200)


#: Sáu trường phạm vi **tuỳ chọn** của hợp đồng. Khai đủ chứ không chỉ ``drug``/``event``: bỏ sót
#: chúng thì một yêu cầu hợp lệ có nêu dân số hay đường dùng sẽ bị trả 422, và B4.3 sẽ phải nhét
#: chúng vào chỗ khác.
_OPTIONAL_SCOPE_FIELDS = ("population", "route", "dose", "time_window", "indication", "comparator")


class Scope(BaseModel):
    """Phạm vi của yêu cầu: ``drug`` và ``event`` bắt buộc, sáu trường còn lại tuỳ chọn."""

    model_config = ConfigDict(extra="forbid")

    drug: ScopeField
    event: ScopeField
    population: ScopeField | None = None
    route: ScopeField | None = None
    dose: ScopeField | None = None
    time_window: ScopeField | None = None
    indication: ScopeField | None = None
    comparator: ScopeField | None = None


def _unknown_scope() -> Scope:
    return Scope(drug=ScopeField(resolution="unknown"), event=ScopeField(resolution="unknown"))


def _scope_field_payload(field: ScopeField) -> dict[str, Any]:
    """Một trường phạm vi theo đúng ``ScopeField`` của hợp đồng.

    ``value`` **luôn có mặt** kể cả khi là ``null`` (hợp đồng bắt buộc trường này), còn ``source`` và
    ``evidence_ref`` **bỏ hẳn** khi chưa biết — hợp đồng cho phép vắng, nhưng không cho ``null``.
    """
    payload: dict[str, Any] = {"value": field.value, "resolution": field.resolution}
    if field.source is not None:
        payload["source"] = field.source
    if field.evidence_ref is not None:
        payload["evidence_ref"] = field.evidence_ref
    return payload


def _scope_payload(scope: Scope) -> dict[str, Any]:
    """Phạm vi ở dạng ghi xuống kho, đúng hợp đồng: đủ hai khóa bắt buộc, không có khóa ``null``."""
    payload: dict[str, Any] = {
        "drug": _scope_field_payload(scope.drug),
        "event": _scope_field_payload(scope.event),
    }
    for name in _OPTIONAL_SCOPE_FIELDS:
        field = getattr(scope, name)
        if field is not None:
            payload[name] = _scope_field_payload(field)
    return payload


class CoverageReport(BaseModel):
    """``CoverageReport`` của hợp đồng: bằng chứng đã chạm tới đâu.

    ``sources_error`` khác ``sources_empty``: lỗi truy hồi không phải bằng chứng vắng mặt.
    """

    model_config = ConfigDict(extra="forbid")

    documents_retrieved: int = Field(ge=0, strict=True)
    sources_ok: list[str]
    sources_empty: list[str]
    sources_error: list[str]
    abstract_only: bool
    full_text_sources: list[str] | None = None
    note: str | None = Field(default=None, max_length=400)


class SourceSystem(BaseModel):
    """Hệ thống gửi yêu cầu sang. ``deidentified`` là trường **bắt buộc** của hợp đồng, không phải tuỳ chọn.

    Bắt buộc là có lý do: nó là lời khai rằng yêu cầu đã được tách thông tin nhận dạng. Bỏ trống được
    thì hệ thống không phân biệt nổi một yêu cầu đã tách thông tin với một yêu cầu chưa ai kiểm.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    record_id: str | None = Field(default=None, max_length=120)
    #: Chặt kiểu: ``"yes"`` không được âm thầm thành ``true``. Đây là lời khai đã tách thông tin nhận
    #: dạng, nên nhận một giá trị gần đúng là nhận một lời khai khác hẳn ý người gửi.
    deidentified: bool = Field(strict=True)


class Attachment(BaseModel):
    """Tệp hoặc liên kết đính kèm. ``sha256`` theo hợp đồng phải đủ 64 ký tự thập lục phân."""

    model_config = ConfigDict(extra="forbid")

    kind: AttachmentKind
    ref: str = Field(min_length=1, max_length=500)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RequestContext(BaseModel):
    """Bối cảnh tiếp nhận. ``request_id`` và ``received_at`` do máy chủ sinh, không nhận từ người gọi."""

    model_config = ConfigDict(extra="forbid")

    requester: Actor
    channel: Channel = "api"
    raw_text: str = Field(min_length=1, max_length=4000)
    language: Language = "vi"
    source_system: SourceSystem | None = None
    attachments: list[Attachment] = Field(default_factory=list, max_length=20)


class UnknownField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=300)
    needs_confirmation: bool = True


class WorkItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    context: RequestContext
    #: Không gửi thì mặc định là "chưa rõ" ở cả hai trường — vẫn là một phạm vi hợp lệ, không phải
    #: một phạm vi rỗng mà hợp đồng không cho phép.
    scope: Scope = Field(default_factory=_unknown_scope)
    unknowns: list[UnknownField] = Field(default_factory=list)
    priority: Priority = "routine"
    owner: Actor | None = None
    labels: dict[str, Annotated[str, Field(max_length=80)]] = Field(default_factory=dict)
    revision_of: str | None = Field(default=None, max_length=120)
    revision_reason: str | None = Field(default=None, max_length=300)


class WorkItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    question: str | None = Field(default=None, min_length=1, max_length=4000)
    scope: Scope | None = None
    unknowns: list[UnknownField] | None = None
    priority: Priority | None = None
    owner: Actor | None = None
    labels: dict[str, Annotated[str, Field(max_length=80)]] | None = None
    work_status: WorkStatus | None = None
    reason: str | None = Field(default=None, max_length=500)


class RunSummary(BaseModel):
    """Số đo của một lần chạy. Mọi trường đều tuỳ chọn; cái nào chưa đo được thì vắng, không ghi ``0``."""

    model_config = ConfigDict(extra="forbid")

    steps_used: int | None = Field(default=None, ge=0, strict=True)
    documents_used: int | None = Field(default=None, ge=0, strict=True)
    source_requests_used: int | None = Field(default=None, ge=0, strict=True)
    stop_reason: str | None = Field(default=None, max_length=60)
    assessment_status: str | None = Field(default=None, max_length=60)


class InvestigationLinkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investigation_id: str = Field(min_length=1, max_length=120)
    purpose: Purpose = "initial"
    state: RunStatusRef = "queued"
    run_summary: RunSummary | None = None


class ResponseSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Literal["summary", "evidence", "limits", "recommendation", "follow_up"]
    title: str = Field(min_length=1, max_length=200)
    #: Trần 8000 theo hợp đồng ``ResponseSection``, không phải 20000.
    text: str = Field(min_length=1, max_length=8000)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class ResponseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[ResponseSectionIn] = Field(min_length=1)
    assessment_status: AssessmentStatus
    #: Bắt buộc theo hợp đồng: một phiếu nói "đã đối chiếu bằng chứng" mà không nói đã truy hồi được
    #: bao nhiêu tài liệu thì người đọc không kiểm được mức bao phủ.
    coverage: CoverageReport


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    reason: str | None = Field(default=None, max_length=2000)
    #: Bắt buộc: duyệt một bản mà không nói rõ đang duyệt phiên bản nào là duyệt mù.
    expected_version: int = Field(ge=1)


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: FollowUpKind
    note: str = Field(min_length=1, max_length=1000)
    due_at: str | None = None
    #: Giao cho người khác là việc của hàng đợi: nêu tên người khác đòi quyền ``queue:assign``.
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
    """Danh tính cho hợp đồng: mã người, và vai chuyên môn khi biết chắc.

    Không kèm ``display_name``: ``Actor`` của hợp đồng đặt ``additionalProperties: false`` và không
    có trường đó, nên gửi thêm là làm hỏng chính tài liệu mình trả về.
    """
    actor: dict[str, Any] = {"id": principal.user_id}
    role = _PROFESSIONAL_ROLE.get(str(principal.role))
    if role:
        actor["role"] = role
    return actor


def _require_assign_permission(principal: Principal, target: dict[str, Any] | None) -> None:
    """Nêu tên **người khác** trong ``owner``/``assignee`` thì phải có quyền giao việc.

    Không có phép kiểm này, một người điều tra tự gán ca cho người khác (rồi mất quyền đọc chính ca
    đó) hoặc đẩy việc sang hàng đợi của người không liên quan, mà nhật ký vẫn ghi như một thao tác
    bình thường. Tự nhận việc cho mình thì không cần quyền gì thêm.
    """
    if not target or target.get("id") == principal.user_id:
        return
    if not principal.has(Permission.QUEUE_ASSIGN):
        raise forbidden(f"Vai {principal.role} không có quyền queue:assign để giao việc cho người khác.")


def _contract_violations(name: str, document: Any) -> list[str]:
    """Đường dẫn JSON của những chỗ tài liệu sai ``schemas.json``, rỗng nếu khớp.

    ``docs/contracts-hospital-v2.md`` giao cho tầng này việc bảo đảm tài liệu trả ra đúng lược đồ.
    Gói bằng chứng là chỗ duy nhất tài liệu đi thẳng từ kho ra mà **không** qua một mô hình Pydantic
    nào, vì hình dạng của nó do bên ghi quyết định — nên đây là chỗ phải soi bằng chính tệp lược đồ.
    """
    schema = {"$ref": f"#/$defs/{name}", "$defs": _CONTRACT_SCHEMAS["$defs"]}
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(part) for part in error.path) or '<gốc>'}: {error.message}"
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    ]


def _require_contract_shaped_bundles(work_item_id: str, bundles: list[dict[str, Any]]) -> None:
    """Chặn không cho gói sai lược đồ ra khỏi hệ thống, dù đi qua đường nào.

    Không chuẩn hoá: ``stance`` và ``retrieval`` mà kho không có thì không suy ra được, và bịa ra
    đúng là loại dữ liệu giả mà hợp đồng này sinh ra để chặn.
    """
    for bundle in bundles:
        violations = _contract_violations("EvidenceBundle", bundle)
        if violations:
            raise MvpError(
                500,
                ErrorCode.UNAVAILABLE,
                "Gói bằng chứng trong kho không khớp hợp đồng nên không trả ra được.",
                {
                    "work_item_id": work_item_id,
                    "bundle_id": bundle.get("bundle_id"),
                    "violations": violations,
                },
            )


def _etag_header(document: dict[str, Any]) -> str:
    """``ETag`` đúng cú pháp HTTP: giá trị phải nằm trong dấu ngoặc kép.

    Kho trả một chuỗi hex trần; gửi nguyên như vậy thì ``If-Match`` của khách hàng chuẩn không bao
    giờ khớp, vì thẻ yếu phải viết ``W/"..."``.
    """
    value = str(document.get("etag") or "")
    return f'W/"{value}"' if value else ""


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


def _require_writable(document: dict[str, Any], principal: Principal) -> None:
    """Sửa được khi là chủ ca, hoặc khi có quyền chạy mọi ca."""
    if principal.has(Permission.INVESTIGATION_RUN_ANY):
        return
    identifier = str(document.get("work_item_id") or "")
    if not _is_owner(document, principal) or not principal.has(Permission.INVESTIGATION_RUN_OWN):
        raise not_found("yêu cầu", identifier)


# --------------------------------------------------------------------------------------
# Yêu cầu tiếp nhận
# --------------------------------------------------------------------------------------


@router.post("/work-items", status_code=201)
def create_work_item(
    payload: WorkItemCreate,
    response: Response,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_CREATE))],
) -> dict[str, Any]:
    """Tiếp nhận một yêu cầu mới.

    Yêu cầu mới **luôn** ở ``draft``: tiếp nhận không đồng nghĩa với bắt đầu điều tra, và cũng
    không có đường tắt tạo thẳng một ca "đã duyệt" hay "đã huỷ". ``request_id`` và ``received_at``
    do máy chủ sinh — người gọi không được tự đặt, vì nhật ký truy vết dựa vào chúng.
    """
    # ``exclude_none`` để các trường tuỳ chọn chưa biết **vắng mặt** thay vì bằng ``null``:
    # hợp đồng cho phép vắng, nhưng ``null`` thì không (``Actor.role``, ``source_system``...).
    context = payload.context.model_dump(exclude_none=True)
    context["request_id"] = _request_id()
    context["received_at"] = _now_iso()
    actor = _actor_of(principal)
    _require_assign_permission(principal, payload.owner.model_dump() if payload.owner else None)
    # ``context.requester`` cũng là một chỗ nêu tên người khác, và nó **cấp quyền đọc** qua đường dự
    # phòng của ``_is_owner`` khi ca chưa có chủ. Không kiểm thì quyền ``queue:assign`` bị lách.
    _require_assign_permission(principal, payload.context.requester.model_dump())
    document = store.create_work_item(
        question=payload.question,
        context=context,
        scope=_scope_payload(payload.scope),
        unknowns=[item.model_dump(exclude_none=True) for item in payload.unknowns],
        priority=payload.priority,
        owner=payload.owner.model_dump() if payload.owner else actor,
        labels=payload.labels,
        actor=actor,
        revision_of=payload.revision_of,
        revision_reason=payload.revision_reason,
    )
    response.headers["ETag"] = _etag_header(document)
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

    ``total`` là **tổng số ca khớp bộ lọc**, không phải số dòng của trang này — giao diện đọc nó để
    vẽ "còn bao nhiêu ca", nên trả số của một trang là báo thiếu. Con trỏ trang sau suy từ chính
    tổng đó, nhờ vậy trang cuối vẫn đi hết được kể cả khi ``limit`` chạm trần.
    """
    offset = _offset_from_cursor(cursor)
    visible_to = None if principal.has(Permission.INVESTIGATION_READ_ANY) else principal.user_id
    page = store.list_work_items(
        work_status=work_status,
        run_status=run_status,
        limit=limit,
        offset=offset,
        visible_to=visible_to,
    )
    total = store.count_work_items(work_status=work_status, run_status=run_status, visible_to=visible_to)
    next_offset = offset + len(page)
    return {"items": page, "next_cursor": str(next_offset) if next_offset < total else None, "total": total}


@router.get("/work-items/{work_item_id}")
def read_work_item(
    work_item_id: str,
    store: StoreDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.INVESTIGATION_READ_OWN))],
) -> dict[str, Any]:
    """Đọc một yêu cầu kèm mọi thứ thuộc về nó, trong một phiên đọc.

    Gói bằng chứng trong lớp bọc cũng được đối chiếu ``schemas.json`` như ở đường đọc gói riêng:
    cùng một tài liệu thì phải cùng một luật, nếu không thì chỗ dễ lách nhất lại là chỗ ít ai nhìn.
    """
    document = _read_work_item(store, work_item_id, principal)
    bundle = store.work_item_bundle(document["work_item_id"])
    _require_contract_shaped_bundles(document["work_item_id"], bundle.get("evidence_bundles") or [])
    return bundle


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

    Hai phép kiểm chạy **độc lập**: đổi chủ sở hữu cần ``queue:assign``, còn sửa bất kỳ nội dung nào
    (kể cả khi đi kèm đổi chủ) vẫn cần quyền sửa ca. Gộp chúng thành "hoặc" sẽ cho người phân công
    viết được nội dung của ca mà chính họ không được sửa.
    """
    current = _read_work_item(store, work_item_id, principal)
    changes: dict[str, Any] = {}
    for field in ("question", "priority", "labels", "work_status"):
        value = getattr(payload, field)
        if value is not None:
            changes[field] = value
    if payload.scope is not None:
        changes["scope"] = _scope_payload(payload.scope)
    if payload.unknowns is not None:
        changes["unknowns"] = [item.model_dump() for item in payload.unknowns]
    if "owner" in payload.model_fields_set:
        # ``owner: null`` là xoá chủ sở hữu (ca quay về cho người gửi), khác hẳn với không gửi gì.
        # Xoá cũng là một thao tác của hàng đợi: không đòi quyền thì người điều tra tự đẩy ca vào
        # hàng đợi của người khác bằng cách tạo ca với ``requester.id`` của người đó rồi xoá chủ.
        if not principal.has(Permission.QUEUE_ASSIGN):
            raise forbidden(f"Vai {principal.role} không có quyền queue:assign để đổi chủ sở hữu.")
        changes["owner"] = payload.owner.model_dump() if payload.owner else None
    if not changes:
        raise invalid_request("Không có trường nào để sửa.")
    if any(field != "owner" for field in changes):
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
        run_summary=payload.run_summary.model_dump(exclude_none=True) if payload.run_summary else None,
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

    Gói là tài liệu duy nhất đi thẳng từ kho ra mà không qua một mô hình Pydantic nào — hình dạng
    của nó do bên ghi quyết định. Nên trước khi trả, gói được đối chiếu với ``schemas.json``. Sai
    lược đồ thì trả **500** kèm đường dẫn từng chỗ sai, chứ **không** trả tài liệu hỏng: một khách
    hàng sinh kiểu từ hợp đồng sẽ đọc sai trường mà không có lỗi nào để lần theo. Đây là lỗi của máy
    chủ (đã ghi một thứ không phục vụ được), không phải lỗi của người gọi.
    """
    _read_work_item(store, work_item_id, principal)
    bundles = store.list_evidence_bundles(work_item_id)
    if not bundles:
        raise MvpError(
            404,
            ErrorCode.NOT_FOUND,
            "Yêu cầu chưa có gói bằng chứng nào.",
            {"work_item_id": work_item_id, "remedy": "Liên kết một lần chạy điều tra trước."},
        )
    # Chỉ soi gói **mình sắp trả**. Gói cũ hỏng không làm đường này đổ oan: mỗi tuyến chịu trách
    # nhiệm cho đúng những tài liệu nó phát ra, và lớp bọc của ``GET /work-items/{id}`` mới là chỗ
    # phát ra cả danh sách.
    bundle = bundles[-1]
    _require_contract_shaped_bundles(work_item_id, [bundle])
    return bundle


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
        coverage=payload.coverage.model_dump(exclude_none=True),
        drafted_by=_actor_of(principal),
        actor=_actor_of(principal),
    )
    response.headers["ETag"] = _etag_header(document)
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

    Người duyệt **luôn** là người đang gọi: không có trường nào trong thân yêu cầu ghi đè được, nên
    không ai ký được quyết định dưới tên đồng nghiệp. Quyết định vừa ghi được trả kèm trong ``review``
    để giao diện vẽ được dấu duyệt ngay, khỏi phải gọi thêm một vòng.
    """
    review = store.add_review(
        entity="response",
        entity_id=response_id,
        action=payload.action,
        reviewer=_actor_of(principal),
        reason=payload.reason,
        expected_version=payload.expected_version,
    )
    document = store.get_response(response_id)
    document["review"] = review
    response.headers["ETag"] = _etag_header(document)
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
    hệ thống không biết hạn nào áp dụng cho cơ sở nào. Giao cho người khác đòi quyền ``queue:assign``.
    """
    current = _read_work_item(store, work_item_id, principal)
    _require_writable(current, principal)
    _require_assign_permission(principal, payload.assignee.model_dump() if payload.assignee else None)
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


def _request_id() -> str:
    """Mã yêu cầu **dùng chung** với envelope lỗi và nhật ký kiểm toán.

    Đọc từ ``ContextVar`` mà middleware đã đặt, không tự sinh mã mới: một mã riêng ở đây sẽ làm
    ``context.request_id`` không tra ngược được sang sự kiện kiểm toán nào.
    """
    return current_request_id() or ""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_due_at(value: str | None) -> datetime | None:
    if value is None:
        return None
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
