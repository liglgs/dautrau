"""Lớp lưu trữ cho lát cắt DI (WorkItem/Response/FollowUp) trên kho ELT.

Quy ước chống mất dữ liệu:

* Mọi lần sửa ``work_items`` phải kèm ``expected_version`` (khoá lạc quan) và được ghi
  bằng một câu ``UPDATE ... WHERE version = :expected`` có kiểm ``rowcount`` — hai
  người cùng sửa một phiên bản thì đúng một người thắng, người kia nhận
  ``VERSION_CONFLICT`` và không ghi gì.
* Mọi lần tạo/sửa đều ghi thêm một dòng ``version_refs`` giữ ảnh chụp của thực thể,
  nên lịch sử luôn đọc lại được.
* Chỉ nhận các trường trong danh sách trắng; khoá lạ thì báo ``INVALID_REQUEST``
  thay vì bỏ qua im lặng.
* ``professional_responses`` là append-only theo phiên bản: bản cũ chuyển sang
  ``superseded`` nhưng vẫn nằm trong bảng, và ràng buộc duy nhất
  ``(work_item_id, version)`` chặn hai bản "hiện hành" cùng lúc.

Mã lỗi dùng envelope chung của MVP (``src/services/errors.py``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, inspect, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.services.casework.models import (
    EvidenceBundle,
    FollowUp,
    InvestigationLink,
    ProfessionalResponse,
    ReviewRef,
    VersionRef,
    WorkItem,
)
from src.services.errors import (
    MvpError,
    idempotency_conflict,
    invalid_request,
    invalid_state,
    not_found,
    version_conflict,
)
from src.services.warehouse.db import session_scope
from src.services.warehouse.models import WarehouseBase, now

# Bản đồ trường nghiệp vụ -> cột, dùng chung cho danh sách trắng và vòng lặp gán giá trị.
WORK_ITEM_COLUMNS = {
    "context": "context_json",
    "question": "question",
    "scope": "scope_json",
    "unknowns": "unknowns_json",
    "priority": "priority",
    "owner": "owner_json",
    "work_status": "work_status",
    "run_status": "run_status",
    "review_status": "review_status",
    "labels": "labels_json",
    "revision_of": "revision_of",
    "revision_reason": "revision_reason",
}
ALLOWED_WORK_ITEM_PATCH_FIELDS = frozenset(WORK_ITEM_COLUMNS)

CASEWORK_TABLES = (
    "work_items",
    "investigation_links",
    "evidence_bundles",
    "professional_responses",
    "follow_ups",
    "version_refs",
    "review_refs",
)

WORK_STATUSES = frozenset(
    {"draft", "accepted", "in_progress", "awaiting_information", "awaiting_review", "completed", "cancelled"}
)
RUN_STATUSES = frozenset(
    {"not_started", "queued", "running", "waiting_for_review", "completed", "cancelled", "interrupted", "failed"}
)
REVIEW_STATUSES = frozenset({"not_required", "pending", "approved", "rejected", "changes_requested"})
RESPONSE_CREATE_STATUSES = frozenset({"draft", "in_review"})
ASSESSMENT_STATUSES = frozenset(
    {
        "supported_for_scope",
        "contradicted_for_scope",
        "insufficient_evidence",
        "scope_mismatch",
        "out_of_scope",
        "requires_human_review",
    }
)
PRIORITIES = frozenset({"routine", "urgent", "stat"})
LINK_PURPOSES = frozenset({"initial", "additional", "recheck", "reproduce"})
# Trạng thái liên kết điều tra dùng đúng tập của ``RunStatusRef`` trong hợp đồng.
LINK_STATES = RUN_STATUSES
REVIEW_ENTITIES = frozenset({"work_item", "response", "evidence_bundle"})
REVIEW_ACTIONS = frozenset(
    {"approve", "reject", "request_changes", "edit_claim", "edit_evidence", "exclude_evidence", "request_more"}
)
FOLLOW_UP_KINDS = frozenset({"request_information", "recheck_source", "monitor_case", "handover", "close"})
FOLLOW_UP_STATUSES = frozenset({"open", "in_progress", "done", "cancelled"})
ACTOR_ROLES = frozenset({"doctor", "pharmacist", "nurse", "reviewer", "admin", "service"})

# Độ rộng cột trong `models.py`; kiểm ở đây để đầu vào quá dài trả 422 thay vì DataError.
ID_MAX_LENGTH = 80
INVESTIGATION_ID_MAX_LENGTH = 120
REVISION_REASON_MAX_LENGTH = 300
REVIEW_REASON_MAX_LENGTH = 1000

WORK_ITEM_REVIEW_TARGET = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "changes_requested",
    "edit_claim": "changes_requested",
    "edit_evidence": "changes_requested",
    "exclude_evidence": "changes_requested",
    "request_more": "changes_requested",
}
RESPONSE_REVIEW_TARGET = {
    "approve": "approved",
    "reject": "rejected",
    "request_changes": "draft",
    "edit_claim": "draft",
    "edit_evidence": "draft",
    "exclude_evidence": "draft",
    "request_more": "draft",
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def etag_for(entity: str, entity_id: str, version: int) -> str:
    return hashlib.sha256(f"{entity}:{entity_id}:{version}".encode()).hexdigest()[:32]


def _iso(value: datetime | None) -> str | None:
    """RFC 3339 kèm múi giờ; SQLite trả về thời gian không múi giờ nên gắn UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _as_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise invalid_request(f"{field} phải là số nguyên.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise invalid_request(f"{field} phải là số nguyên.") from exc


def _text(value: Any, field: str, *, max_length: int | None = None) -> str:
    """Chuỗi bắt buộc, đã cắt khoảng trắng; quá dài thì 422 (không để cơ sở dữ liệu nổ)."""
    if not isinstance(value, str) or not value.strip():
        raise invalid_request(f"{field} không được để trống.")
    text = value.strip()
    if max_length is not None and len(text) > max_length:
        raise invalid_request(
            f"{field} dài quá {max_length} ký tự.",
            {"field": field, "max_length": max_length, "actual_length": len(text)},
        )
    return text


def _optional_text(value: Any, field: str, *, max_length: int | None = None) -> str | None:
    return None if value is None else _text(value, field, max_length=max_length)


def _json_object(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise invalid_request(f"{field} phải là đối tượng.")
    return value


def _json_list(value: Any, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise invalid_request(f"{field} phải là danh sách.")
    return value


def _optional_object(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise invalid_request(f"{field} phải là đối tượng hoặc null.")
    return value


def _actor(value: Any, field: str = "actor") -> dict[str, Any] | None:
    """Chuẩn hoá người dùng về dạng ``Actor`` của hợp đồng: ``{id, role?, unit?}``."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise invalid_request(f"{field} phải là đối tượng.")
    raw_id = value.get("id", value.get("actor_id"))
    actor: dict[str, Any] = {"id": _text(raw_id, f"{field}.id")}
    role = value.get("role")
    if role is not None:
        if role not in ACTOR_ROLES:
            raise invalid_request(f"Vai trò không hợp lệ trong {field}.role: {role!r}.", {"allowed": sorted(ACTOR_ROLES)})
        actor["role"] = role
    unit = value.get("unit")
    if unit is not None:
        if not isinstance(unit, str):
            raise invalid_request(f"{field}.unit phải là chuỗi.")
        actor["unit"] = unit
    return actor


def _response_save_conflicts(work_item_id: str, version: int) -> dict[str, MvpError]:
    """Lỗi trả khi hai lần lưu phiếu trả lời đua nhau, cho *cả hai* ràng buộc duy nhất.

    Bên thua có thể bị chặn bởi ràng buộc số phiên bản hoặc bởi ràng buộc "một bản hiện
    hành"; dùng chung một lỗi để mã lỗi không phụ thuộc vào việc ràng buộc nào bắt được.
    """
    error = invalid_state(
        "Có phiếu trả lời khác vừa được lưu; đọc lại yêu cầu rồi gửi lại.",
        {"work_item_id": work_item_id, "attempted_version": version},
    )
    return dict.fromkeys(("uq_response_version", "uq_response_current"), error)


def _constraint_name(exc: IntegrityError) -> str | None:
    """Tên ràng buộc/chỉ mục mà cơ sở dữ liệu nêu trong lỗi, nếu đọc được.

    PostgreSQL đưa tên qua ``diag.constraint_name``; SQLite chỉ có trong thông báo lỗi.
    """
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    name = getattr(diag, "constraint_name", None)
    if name:
        return str(name)
    return str(getattr(exc, "orig", exc))


def _require(value: Any, allowed: Iterable[str], field: str) -> None:
    if value is None:
        raise invalid_request(f"Thiếu trường bắt buộc: {field}.")
    if not isinstance(value, str) or value not in allowed:
        raise invalid_request(f"Giá trị không hợp lệ cho {field}: {value!r}.", {"allowed": sorted(allowed)})


def visible_to_expression(user_id: str):
    """Biểu thức phạm vi của một người: chủ sở hữu nếu đã gán, ngược lại người gửi yêu cầu.

    Cùng quy tắc với ``_is_owner`` ở tầng API, nhưng viết bằng SQL để lọc được **trước** khi
    phân trang. ``as_string()`` sinh cú pháp JSON phù hợp với từng hệ quản trị (``json_extract``
    trên SQLite, ``->>`` trên PostgreSQL).
    """
    owner_id = WorkItem.owner_json["id"].as_string()
    requester_id = WorkItem.context_json["requester"]["id"].as_string()
    return func.coalesce(owner_id, requester_id) == user_id


def ensure_casework_schema(engine: Engine) -> list[str]:
    """Tạo các bảng còn thiếu của lát cắt DI (chỉ thêm, không sửa bảng cũ)."""
    existing = set(inspect(engine).get_table_names())
    missing = [name for name in CASEWORK_TABLES if name not in existing]
    if not missing:
        return []
    WarehouseBase.metadata.create_all(
        engine, tables=[WarehouseBase.metadata.tables[name] for name in missing]
    )
    return sorted(missing)


def _ensure_row(session, model, identifier: str, what: str):
    """Đọc một dòng theo khoá chính; mã sai kiểu thì 422, không có thì 404."""
    identifier = _text(identifier, model.__mapper__.primary_key[0].name, max_length=ID_MAX_LENGTH)
    row = session.get(model, identifier)
    if row is None:
        raise not_found(what, identifier)
    return row


def _ensure_work_item(session, work_item_id: str) -> WorkItem:
    return _ensure_row(session, WorkItem, work_item_id, "yêu cầu")


def _related_ids(session, work_item_id: str) -> dict[str, list[str]]:
    return {
        "investigation_ids": [
            value
            for value in session.execute(
                select(InvestigationLink.link_id).where(InvestigationLink.work_item_id == work_item_id)
            ).scalars()
        ],
        "response_ids": [
            value
            for value in session.execute(
                select(ProfessionalResponse.response_id).where(ProfessionalResponse.work_item_id == work_item_id)
            ).scalars()
        ],
        "follow_up_ids": [
            value
            for value in session.execute(
                select(FollowUp.follow_up_id).where(FollowUp.work_item_id == work_item_id)
            ).scalars()
        ],
    }


def work_item_document(row: WorkItem, related: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Chuyển bản ghi ORM sang hình dạng ``WorkItem`` của hợp đồng hospital-v2."""
    ids = related or {}
    return {
        "work_item_id": row.work_item_id,
        "version": row.version,
        "etag": row.etag,
        "context": row.context_json or {},
        "question": row.question,
        "scope": row.scope_json or {},
        "unknowns": row.unknowns_json or [],
        "priority": row.priority,
        "owner": row.owner_json,
        "work_status": row.work_status,
        "run_status": row.run_status,
        "review_status": row.review_status,
        "investigation_ids": ids.get("investigation_ids", []),
        "response_ids": ids.get("response_ids", []),
        "follow_up_ids": ids.get("follow_up_ids", []),
        "labels": row.labels_json or {},
        "revision_of": row.revision_of,
        "revision_reason": row.revision_reason,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _link_document(row: InvestigationLink) -> dict[str, Any]:
    return {
        "link_id": row.link_id,
        "work_item_id": row.work_item_id,
        "investigation_id": row.investigation_id,
        "purpose": row.purpose,
        "state": row.state,
        "run_summary": row.run_summary_json,
        "error": row.error_json,
        "created_by": row.created_by_json,
        "created_at": _iso(row.created_at),
    }


def _bundle_document(row: EvidenceBundle) -> dict[str, Any]:
    return {
        "bundle_id": row.bundle_id,
        "work_item_id": row.work_item_id,
        "investigation_id": row.investigation_id,
        "created_at": _iso(row.created_at),
        "claim": row.claim_json,
        "items": row.items_json or [],
        "gaps": row.gaps_json or [],
        "coverage": row.coverage_json or {},
        "assessment_status": row.assessment_status,
        "source_errors": row.source_errors_json or [],
        "limitations": row.limitations_json or [],
    }


def _latest_response_reviews(session: Session, response_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Quyết định duyệt **mới nhất** của từng phiếu, đọc từ ``review_refs``.

    ``review_refs`` là sổ append-only và là nguồn sự thật; ``ProfessionalResponse.review_json`` chỉ
    được ghi ``None`` lúc tạo và **không** nơi nào cập nhật. Trả về ``review_json`` trần thì mọi phiếu
    đã duyệt vẫn đọc ra ``review: null`` — giao diện đọc lớp bọc sẽ nói "chưa duyệt" về một phiếu đã
    duyệt, tức là nói sai về thực tế.
    """
    if not response_ids:
        return {}
    rows = (
        session.execute(
            select(ReviewRef)
            .where(ReviewRef.entity == "response", ReviewRef.entity_id.in_(response_ids))
            # ``entity_version`` là số phiên bản của đối tượng bị duyệt tại lúc ra quyết định, và mỗi
            # quyết định đều tăng số đó lên đúng một (``_apply_response_review`` ghi ``expected + 1``
            # và chặn nếu ``expected`` không khớp bản đang có), nên trong một đối tượng nó chính là
            # thứ tự ghi. Vì vậy nó phải đứng TRƯỚC ``decided_at``: ``decided_at`` là giờ tường, giờ
            # này có thể lùi (NTP, máy lệch giờ, đồng hồ chậm), và khi đó bản ghi sau lại mang dấu cũ
            # rồi bị bản cũ đè về mặt thứ tự. ``decided_at`` xuống làm khoá phụ, ``review_id`` là chốt
            # cuối cho trường hợp hoà hoàn toàn — mã đó ngẫu nhiên nên không phản ánh thứ tự ghi.
            .order_by(ReviewRef.entity_version, ReviewRef.decided_at, ReviewRef.review_id)
        )
        .scalars()
        .all()
    )
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest[row.entity_id] = _review_document(row)
    return latest


def _response_document(row: ProfessionalResponse, review: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "response_id": row.response_id,
        "work_item_id": row.work_item_id,
        "version": row.version,
        "etag": row.etag,
        "status": row.status,
        "sections": row.sections_json or [],
        "assessment_status": row.assessment_status,
        "coverage": row.coverage_json or {},
        "drafted_by": row.drafted_by_json,
        "review": review,
        "approval": row.approval_json,
        "supersedes": row.supersedes,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _follow_up_document(row: FollowUp) -> dict[str, Any]:
    return {
        "follow_up_id": row.follow_up_id,
        "work_item_id": row.work_item_id,
        "kind": row.kind,
        "status": row.status,
        "note": row.note,
        "due_at": _iso(row.due_at),
        "assignee": row.assignee_json,
        "created_by": row.created_by_json,
        "created_at": _iso(row.created_at),
        "closed_at": _iso(row.closed_at),
        "resolution": row.resolution,
    }


def _review_document(row: ReviewRef) -> dict[str, Any]:
    return {
        "review_id": row.review_id,
        "entity": row.entity,
        "entity_id": row.entity_id,
        "entity_version": row.entity_version,
        "action": row.action,
        "reviewer": row.reviewer_json or {},
        "reason": row.reason,
        "decided_at": _iso(row.decided_at),
        "previous_status": row.previous_status,
        "new_status": row.new_status,
    }


def version_ref_document(row: VersionRef) -> dict[str, Any]:
    """Hình dạng ``VersionRef`` của hợp đồng (bản chiếu của một dòng ``version_refs``)."""
    return {
        "entity": row.entity,
        "id": row.entity_id,
        "version": row.entity_version,
        "etag": row.etag,
        "updated_at": _iso(row.updated_at),
        "updated_by": row.updated_by_json,
    }


def _version_document(row: VersionRef) -> dict[str, Any]:
    """Bản đầy đủ trong kho: gồm cả hình dạng hợp đồng lẫn phần thêm của nhật ký."""
    return {
        **version_ref_document(row),
        "revision": row.revision,
        "change_kind": row.change_kind,
        "changed_fields": row.changed_fields_json or [],
        "snapshot": row.snapshot_json or {},
    }


class CaseWorkStore:
    """Đọc/ghi yêu cầu, liên kết điều tra, gói bằng chứng, phiếu trả lời và theo dõi."""

    def __init__(self, engine: Engine, *, ensure_schema: bool = True):
        """``ensure_schema=False`` cho đường chỉ đọc hoặc khi lược đồ đã do nơi khác dựng."""
        self.engine = engine
        if ensure_schema:
            ensure_casework_schema(engine)

    # ------------------------------------------------------------------ tiện ích

    def _record_version(
        self,
        session,
        *,
        entity: str,
        entity_id: str,
        version: int,
        change_kind: str,
        changed_fields: list[str],
        snapshot: dict[str, Any],
        actor: dict[str, Any] | None,
    ) -> None:
        """Ghi một dòng nhật ký append-only; ``revision`` đếm riêng cho từng thực thể."""
        current = session.execute(
            select(func.max(VersionRef.revision)).where(
                VersionRef.entity == entity, VersionRef.entity_id == entity_id
            )
        ).scalar_one()
        session.add(
            VersionRef(
                entity=entity,
                entity_id=entity_id,
                revision=int(current or 0) + 1,
                entity_version=version,
                etag=etag_for(entity, entity_id, version),
                change_kind=change_kind,
                changed_fields_json=changed_fields,
                snapshot_json=snapshot,
                updated_by_json=actor,
                updated_at=now(),
            )
        )

    def _insert(
        self,
        session,
        row,
        *,
        key: str,
        conflicts: dict[str, MvpError] | None = None,
    ) -> None:
        """Chèn bản ghi mới; vi phạm ràng buộc trả 409 thay vì lỗi hệ thống.

        ``conflicts`` ánh xạ *tên ràng buộc* sang lỗi muốn trả (ví dụ số phiên bản phiếu
        trả lời). Mọi ràng buộc khác — kể cả khoá chính trùng — trả ``IDEMPOTENCY_CONFLICT``,
        để mã trùng luôn được báo đúng là mã trùng.
        """
        model = type(row)
        primary_key = model.__mapper__.primary_key[0].name
        if session.get(model, getattr(row, primary_key)) is not None:
            # Kiểm trước để lỗi xác định trên mọi hệ quản trị, không phụ thuộc thông báo của cơ sở dữ liệu.
            raise idempotency_conflict(key)
        session.add(row)
        try:
            session.flush()
        except IntegrityError as exc:
            name = _constraint_name(exc)
            for constraint, error in (conflicts or {}).items():
                if name is not None and constraint in name:
                    raise error from exc
            raise idempotency_conflict(key) from exc

    def _apply_work_item_change(
        self,
        session,
        work_item_id: str,
        *,
        expected: int,
        changes: dict[str, Any],
        actor: dict[str, Any] | None,
        change_kind: str = "updated",
        changed_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Cập nhật có khoá lạc quan: chỉ một người thắng mỗi phiên bản."""
        values = {WORK_ITEM_COLUMNS[field]: changes[field] for field in changes}
        values.update(
            version=expected + 1,
            etag=etag_for("work_item", work_item_id, expected + 1),
            updated_at=now(),
        )
        result = session.execute(
            update(WorkItem)
            .where(WorkItem.work_item_id == work_item_id, WorkItem.version == expected)
            .values(**values)
        )
        session.expire_all()
        if result.rowcount != 1:
            current = session.get(WorkItem, work_item_id)
            if current is None:
                raise not_found("yêu cầu", work_item_id)
            raise version_conflict(expected, current.version)
        row = _ensure_work_item(session, work_item_id)
        document = work_item_document(row, _related_ids(session, work_item_id))
        self._record_version(
            session,
            entity="work_item",
            entity_id=work_item_id,
            version=row.version,
            change_kind=change_kind,
            changed_fields=sorted(changed_fields if changed_fields is not None else changes),
            snapshot=document,
            actor=actor,
        )
        return document

    # ------------------------------------------------------------- work items

    def create_work_item(
        self,
        *,
        question: str,
        context: dict[str, Any] | None = None,
        scope: dict[str, Any] | None = None,
        unknowns: list[dict[str, Any]] | None = None,
        priority: str = "routine",
        owner: dict[str, Any] | None = None,
        labels: dict[str, Any] | None = None,
        actor: dict[str, Any] | None = None,
        work_item_id: str | None = None,
        revision_of: str | None = None,
        revision_reason: str | None = None,
    ) -> dict[str, Any]:
        question = _text(question, "question")
        _require(priority, PRIORITIES, "priority")
        context = _json_object(context, "context")
        scope = _json_object(scope, "scope")
        unknowns = _json_list(unknowns, "unknowns")
        labels = _json_object(labels, "labels")
        owner = _actor(owner, "owner")
        actor = _actor(actor)
        work_item_id = (
            new_id("wi") if work_item_id is None else _text(work_item_id, "work_item_id", max_length=ID_MAX_LENGTH)
        )
        revision_of = _optional_text(revision_of, "revision_of", max_length=ID_MAX_LENGTH)
        revision_reason = _optional_text(
            revision_reason, "revision_reason", max_length=REVISION_REASON_MAX_LENGTH
        )

        work_item_id = work_item_id or new_id("wi")
        stamp = now()
        row = WorkItem(
            work_item_id=work_item_id,
            version=1,
            etag=etag_for("work_item", work_item_id, 1),
            context_json=context,
            question=question,
            scope_json=scope,
            unknowns_json=unknowns,
            priority=priority,
            owner_json=owner,
            work_status="draft",
            run_status="not_started",
            review_status="not_required",
            revision_of=revision_of,
            revision_reason=revision_reason,
            labels_json=labels,
            created_at=stamp,
            updated_at=stamp,
            created_by_json=actor,
        )
        with session_scope(self.engine) as session:
            self._insert(session, row, key=work_item_id)
            document = work_item_document(row, _related_ids(session, work_item_id))
            self._record_version(
                session,
                entity="work_item",
                entity_id=work_item_id,
                version=1,
                change_kind="created",
                changed_fields=sorted(ALLOWED_WORK_ITEM_PATCH_FIELDS),
                snapshot=document,
                actor=actor,
            )
        return document

    def count_work_items(
        self,
        *,
        work_status: str | None = None,
        run_status: str | None = None,
        visible_to: str | None = None,
    ) -> int:
        """Tổng số yêu cầu khớp bộ lọc, **trước** khi cắt trang.

        Cần hàm này vì ``total`` lấy bằng ``len(trang)`` là số của một trang, không phải số của hàng
        đợi: giao diện đọc nó để vẽ "còn bao nhiêu ca" sẽ báo thiếu. Và khi đã biết tổng thì con trỏ
        trang sau suy được từ ``offset + len(trang) < total``, không phải lấy dư một dòng — chỗ đó
        vỡ đúng ở ``limit`` bằng trần (``limit + 1`` bị kẹp về trần nên không bao giờ thấy dòng dư).
        """
        if work_status is not None:
            _require(work_status, WORK_STATUSES, "work_status")
        if run_status is not None:
            _require(run_status, RUN_STATUSES, "run_status")
        query = select(func.count()).select_from(WorkItem)
        if work_status:
            query = query.where(WorkItem.work_status == work_status)
        if run_status:
            query = query.where(WorkItem.run_status == run_status)
        if visible_to:
            query = query.where(visible_to_expression(visible_to))
        with session_scope(self.engine) as session:
            return int(session.execute(query).scalar_one())

    def get_work_item(self, work_item_id: str) -> dict[str, Any]:
        work_item_id = _text(work_item_id, "work_item_id")
        with session_scope(self.engine) as session:
            row = _ensure_work_item(session, work_item_id)
            return work_item_document(row, _related_ids(session, work_item_id))

    def list_work_items(
        self,
        *,
        work_status: str | None = None,
        run_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        visible_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Hàng đợi theo thứ tự mới nhất trước.

        ``visible_to`` lọc phạm vi **trong câu truy vấn**, trước ``LIMIT``/``OFFSET``. Cắt trang
        trước rồi mới lọc trong Python sẽ chôn mất ca của chính người gọi khi hàng đợi có nhiều ca
        của người khác nằm trên, và không trang nào chạm tới chúng nữa.
        """
        limit = max(1, min(_as_int(limit, "limit"), 200))
        offset = max(0, _as_int(offset, "offset"))
        if work_status is not None:
            _require(work_status, WORK_STATUSES, "work_status")
        if run_status is not None:
            _require(run_status, RUN_STATUSES, "run_status")
        with session_scope(self.engine) as session:
            query = select(WorkItem).order_by(WorkItem.created_at.desc(), WorkItem.work_item_id)
            if work_status:
                query = query.where(WorkItem.work_status == work_status)
            if run_status:
                query = query.where(WorkItem.run_status == run_status)
            if visible_to:
                query = query.where(visible_to_expression(visible_to))
            rows = session.execute(query.limit(limit).offset(offset)).scalars().all()
            return [work_item_document(row) for row in rows]

    def update_work_item(
        self,
        work_item_id: str,
        *,
        changes: dict[str, Any],
        expected_version: int | None,
        actor: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Sửa yêu cầu với khoá lạc quan; trả bản ghi mới kèm ``version`` tăng một."""
        work_item_id = _text(work_item_id, "work_item_id")
        if not isinstance(changes, dict) or not changes:
            raise invalid_request("Không có trường nào để cập nhật.")
        unknown = sorted(set(changes) - ALLOWED_WORK_ITEM_PATCH_FIELDS)
        if unknown:
            raise invalid_request(
                "Trường không được phép cập nhật: " + ", ".join(unknown),
                {"allowed": sorted(ALLOWED_WORK_ITEM_PATCH_FIELDS)},
            )
        if expected_version is None:
            raise invalid_request("Thiếu expected_version; đọc lại yêu cầu rồi gửi kèm phiên bản.")
        expected = _as_int(expected_version, "expected_version")
        actor = _actor(actor)

        checks: tuple[tuple[str, Iterable[str]], ...] = (
            ("work_status", WORK_STATUSES),
            ("run_status", RUN_STATUSES),
            ("review_status", REVIEW_STATUSES),
            ("priority", PRIORITIES),
        )
        for field, allowed in checks:
            if field in changes:
                _require(changes[field], allowed, field)
        validators: dict[str, Any] = {
            "question": _text,
            "context": _json_object,
            "scope": _json_object,
            "unknowns": _json_list,
            "labels": _json_object,
            "owner": _actor,
            "revision_of": lambda value, field: _optional_text(value, field, max_length=ID_MAX_LENGTH),
            "revision_reason": lambda value, field: _optional_text(
                value, field, max_length=REVISION_REASON_MAX_LENGTH
            ),
        }
        changes = {
            **changes,
            **{field: validators[field](changes[field], field) for field in changes if field in validators},
        }
        if reason is not None:
            changes = {
                **changes,
                "revision_reason": _text(reason, "reason", max_length=REVISION_REASON_MAX_LENGTH),
            }

        with session_scope(self.engine) as session:
            return self._apply_work_item_change(
                session,
                work_item_id,
                expected=expected,
                changes=changes,
                actor=actor,
            )

    # ------------------------------------------------------- liên kết điều tra

    def add_investigation_link(
        self,
        work_item_id: str,
        *,
        investigation_id: str,
        purpose: str = "initial",
        state: str = "queued",
        run_summary: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        actor: dict[str, Any] | None = None,
        link_id: str | None = None,
    ) -> dict[str, Any]:
        _require(purpose, LINK_PURPOSES, "purpose")
        _require(state, LINK_STATES, "state")
        investigation_id = _text(investigation_id, "investigation_id", max_length=INVESTIGATION_ID_MAX_LENGTH)
        run_summary = _optional_object(run_summary, "run_summary")
        error = _optional_object(error, "error")
        actor = _actor(actor)
        link_id = new_id("il") if link_id is None else _text(link_id, "link_id", max_length=ID_MAX_LENGTH)
        row = InvestigationLink(
            link_id=link_id,
            work_item_id=work_item_id,
            investigation_id=investigation_id,
            purpose=purpose,
            state=state,
            run_summary_json=run_summary,
            error_json=error,
            created_at=now(),
            created_by_json=actor,
        )
        with session_scope(self.engine) as session:
            _ensure_work_item(session, work_item_id)
            self._insert(session, row, key=link_id)
            document = _link_document(row)
            self._record_version(
                session,
                entity="investigation_link",
                entity_id=link_id,
                version=1,
                change_kind="created",
                changed_fields=["investigation_id", "purpose", "state"],
                snapshot=document,
                actor=actor,
            )
        return document

    def update_investigation_link(
        self,
        link_id: str,
        *,
        state: str | None = None,
        run_summary: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
        actor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if state is not None:
            _require(state, LINK_STATES, "state")
        run_summary = _optional_object(run_summary, "run_summary")
        error = _optional_object(error, "error")
        actor = _actor(actor)
        with session_scope(self.engine) as session:
            row = _ensure_row(session, InvestigationLink, link_id, "liên kết điều tra")
            changed: list[str] = []
            if state is not None:
                row.state = state
                changed.append("state")
            if run_summary is not None:
                row.run_summary_json = run_summary
                changed.append("run_summary")
            if error is not None:
                row.error_json = error
                changed.append("error")
            document = _link_document(row)
            if changed:
                self._record_version(
                    session,
                    entity="investigation_link",
                    entity_id=link_id,
                    version=1,
                    change_kind="updated",
                    changed_fields=changed,
                    snapshot=document,
                    actor=actor,
                )
            return document

    def list_investigation_links(self, work_item_id: str) -> list[dict[str, Any]]:
        work_item_id = _text(work_item_id, "work_item_id")
        with session_scope(self.engine) as session:
            rows = (
                session.execute(
                    select(InvestigationLink)
                    .where(InvestigationLink.work_item_id == work_item_id)
                    .order_by(InvestigationLink.created_at)
                )
                .scalars()
                .all()
            )
            return [_link_document(row) for row in rows]

    # --------------------------------------------------------- gói bằng chứng

    def add_evidence_bundle(
        self,
        work_item_id: str,
        *,
        investigation_id: str,
        items: list[dict[str, Any]],
        gaps: list[dict[str, Any]],
        coverage: dict[str, Any],
        assessment_status: str,
        claim: dict[str, Any] | None = None,
        source_errors: list[dict[str, Any]] | None = None,
        limitations: list[str] | None = None,
        bundle_id: str | None = None,
    ) -> dict[str, Any]:
        _require(assessment_status, ASSESSMENT_STATUSES, "assessment_status")
        investigation_id = _text(investigation_id, "investigation_id")
        items = _json_list(items, "items")
        gaps = _json_list(gaps, "gaps")
        source_errors = _json_list(source_errors, "source_errors")
        limitations = _json_list(limitations, "limitations")
        if not isinstance(coverage, dict):
            raise invalid_request("coverage phải là đối tượng.")
        claim = _optional_object(claim, "claim")
        bundle_id = (
            new_id("eb") if bundle_id is None else _text(bundle_id, "bundle_id", max_length=ID_MAX_LENGTH)
        )
        row = EvidenceBundle(
            bundle_id=bundle_id,
            work_item_id=work_item_id,
            investigation_id=investigation_id,
            created_at=now(),
            claim_json=claim,
            items_json=items,
            gaps_json=gaps,
            coverage_json=coverage,
            assessment_status=assessment_status,
            source_errors_json=source_errors,
            limitations_json=limitations,
        )
        with session_scope(self.engine) as session:
            _ensure_work_item(session, work_item_id)
            self._insert(session, row, key=bundle_id)
            document = _bundle_document(row)
            self._record_version(
                session,
                entity="evidence_bundle",
                entity_id=bundle_id,
                version=1,
                change_kind="created",
                changed_fields=["items", "gaps", "coverage", "assessment_status"],
                snapshot=document,
                actor=None,
            )
        return document

    def get_evidence_bundle(self, bundle_id: str) -> dict[str, Any]:
        bundle_id = _text(bundle_id, "bundle_id")
        with session_scope(self.engine) as session:
            return _bundle_document(_ensure_row(session, EvidenceBundle, bundle_id, "gói bằng chứng"))

    def list_evidence_bundles(self, work_item_id: str) -> list[dict[str, Any]]:
        work_item_id = _text(work_item_id, "work_item_id")
        with session_scope(self.engine) as session:
            rows = (
                session.execute(
                    select(EvidenceBundle)
                    .where(EvidenceBundle.work_item_id == work_item_id)
                    .order_by(EvidenceBundle.created_at)
                )
                .scalars()
                .all()
            )
            return [_bundle_document(row) for row in rows]

    # -------------------------------------------------------- phiếu trả lời

    def save_response(
        self,
        work_item_id: str,
        *,
        sections: list[dict[str, Any]],
        status: str = "draft",
        assessment_status: str = "insufficient_evidence",
        coverage: dict[str, Any] | None = None,
        drafted_by: dict[str, Any] | None = None,
        response_id: str | None = None,
        actor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ghi một phiên bản phiếu trả lời mới; bản trước đó chuyển sang ``superseded``."""
        _require(status, RESPONSE_CREATE_STATUSES, "status")
        _require(assessment_status, ASSESSMENT_STATUSES, "assessment_status")
        sections = _json_list(sections, "sections")
        if not sections:
            raise invalid_request("Phiếu trả lời phải có ít nhất một mục.")
        coverage = _json_object(coverage, "coverage")
        drafted_by = _actor(drafted_by, "drafted_by")
        actor = _actor(actor)
        response_id = (
            new_id("resp") if response_id is None else _text(response_id, "response_id", max_length=ID_MAX_LENGTH)
        )

        with session_scope(self.engine) as session:
            # Khoá dòng yêu cầu để hai lần lưu song song không tạo hai bản "hiện hành".
            _ensure_work_item(session, work_item_id)
            session.execute(
                select(WorkItem.work_item_id).where(WorkItem.work_item_id == work_item_id).with_for_update()
            ).scalar_one()
            previous = (
                session.execute(
                    select(ProfessionalResponse)
                    .where(
                        ProfessionalResponse.work_item_id == work_item_id,
                        ProfessionalResponse.status != "superseded",
                    )
                    .order_by(ProfessionalResponse.version.desc())
                )
                .scalars()
                .first()
            )
            version = 1
            supersedes: str | None = None
            if previous is not None:
                version = previous.version + 1
                supersedes = previous.response_id
                previous.status = "superseded"
                previous.updated_at = now()
                # Ghi ngay: SQLAlchemy xếp INSERT trước UPDATE, mà ràng buộc
                # "một bản hiện hành" kiểm ở cuối câu lệnh, nên phải hạ bản cũ xuống trước.
                session.flush()
                self._record_version(
                    session,
                    entity="response",
                    entity_id=previous.response_id,
                    version=previous.version,
                    change_kind="superseded",
                    changed_fields=["status"],
                    snapshot=_response_document(previous),
                    actor=actor,
                )
            stamp = now()
            row = ProfessionalResponse(
                response_id=response_id,
                work_item_id=work_item_id,
                version=version,
                etag=etag_for("response", response_id, version),
                status=status,
                sections_json=sections,
                assessment_status=assessment_status,
                coverage_json=coverage,
                drafted_by_json=drafted_by,
                review_json=None,
                approval_json=None,
                supersedes=supersedes,
                created_at=stamp,
                updated_at=stamp,
            )
            self._insert(
                session,
                row,
                key=response_id,
                # Lưới an toàn: nếu vì lý do nào đó hai lần lưu lọt qua khoá dòng, một trong
                # hai ràng buộc duy nhất chặn lại — báo cùng một lỗi dù bị chặn bởi ràng buộc
                # số phiên bản hay ràng buộc "một bản hiện hành", để mã lỗi không gây hiểu nhầm.
                # Mã phiếu trùng vẫn rơi về IDEMPOTENCY_CONFLICT như các bảng khác.
                conflicts=_response_save_conflicts(work_item_id, version),
            )
            document = _response_document(row)
            self._record_version(
                session,
                entity="response",
                entity_id=response_id,
                version=version,
                change_kind="created",
                changed_fields=["sections", "status", "assessment_status", "coverage"],
                snapshot=document,
                actor=actor,
            )
            return document

    def get_response(self, response_id: str) -> dict[str, Any]:
        response_id = _text(response_id, "response_id")
        with session_scope(self.engine) as session:
            row = _ensure_row(session, ProfessionalResponse, response_id, "phiếu trả lời")
            return _response_document(row, _latest_response_reviews(session, [response_id]).get(response_id))

    def list_responses(self, work_item_id: str, *, include_superseded: bool = True) -> list[dict[str, Any]]:
        work_item_id = _text(work_item_id, "work_item_id")
        with session_scope(self.engine) as session:
            query = select(ProfessionalResponse).where(ProfessionalResponse.work_item_id == work_item_id)
            if not include_superseded:
                query = query.where(ProfessionalResponse.status != "superseded")
            rows = session.execute(query.order_by(ProfessionalResponse.version)).scalars().all()
            reviews = _latest_response_reviews(session, [row.response_id for row in rows])
            return [_response_document(row, reviews.get(row.response_id)) for row in rows]

    # --------------------------------------------------------------- duyệt

    def add_review(
        self,
        *,
        entity: str,
        entity_id: str,
        action: str,
        reviewer: dict[str, Any],
        reason: str | None = None,
        review_id: str | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        _require(entity, REVIEW_ENTITIES, "entity")
        _require(action, REVIEW_ACTIONS, "action")
        entity_id = _text(entity_id, "entity_id", max_length=ID_MAX_LENGTH)
        reviewer = _actor(reviewer, "reviewer")
        if reviewer is None:
            raise invalid_request("reviewer không được để trống.")
        reason = _optional_text(reason, "reason", max_length=REVIEW_REASON_MAX_LENGTH)
        if reason is not None and len(reason) > 1000:
            raise invalid_request("reason tối đa 1000 ký tự.")
        review_id = (
            new_id("rev") if review_id is None else _text(review_id, "review_id", max_length=ID_MAX_LENGTH)
        )
        expected = _as_int(expected_version, "expected_version") if expected_version is not None else None

        with session_scope(self.engine) as session:
            previous_status = ""
            new_status = ""
            entity_version = 0
            snapshot: dict[str, Any]
            snapshot_version: int
            # Nhánh tự ghi nhật ký phiên bản thì đặt cờ, để cuối hàm không ghi lần thứ hai.
            logged = False
            if entity == "work_item":
                row = _ensure_work_item(session, entity_id)
                entity_version = row.version
                previous_status = row.review_status
                new_status = WORK_ITEM_REVIEW_TARGET[action]
                if expected is not None and expected != row.version:
                    raise version_conflict(expected, row.version)
                snapshot = self._apply_work_item_change(
                    session,
                    entity_id,
                    expected=entity_version,
                    changes={"review_status": new_status},
                    actor=reviewer,
                    change_kind="reviewed",
                    changed_fields=["review_status"],
                )
                snapshot_version = snapshot["version"]
                logged = True
            elif entity == "response":
                response = _ensure_row(session, ProfessionalResponse, entity_id, "phiếu trả lời")
                if response.status == "superseded":
                    raise invalid_state(
                        "Không duyệt được phiếu trả lời đã bị thay thế.",
                        {"response_id": entity_id, "status": response.status},
                    )
                if expected is None:
                    raise invalid_request("Thiếu expected_version; đọc lại phiếu rồi gửi kèm phiên bản.")
                if expected != response.version:
                    raise version_conflict(expected, response.version)
                entity_version = response.version
                previous_status = response.status
                new_status = RESPONSE_REVIEW_TARGET[action]
                snapshot, snapshot_version = self._apply_response_review(
                    session, entity_id, expected=entity_version, new_status=new_status
                )
            else:
                bundle = _ensure_row(session, EvidenceBundle, entity_id, "gói bằng chứng")
                previous_status = "created"
                # Gói bằng chứng không có cột phiên bản, nên đếm số quyết định đã có để giữ đúng
                # bất biến mà thứ tự sắp xếp dựa vào: ``entity_version`` tăng một mỗi quyết định.
                # Gán cứng 1 thì hai quyết định hoà nhau và thứ tự rơi xuống ``review_id`` ngẫu nhiên.
                highest = session.execute(
                    select(func.max(ReviewRef.entity_version)).where(
                        ReviewRef.entity == "evidence_bundle", ReviewRef.entity_id == entity_id
                    )
                ).scalar()
                entity_version = (highest or 0) + 1
                new_status = "reviewed"
                snapshot = _bundle_document(bundle)
                snapshot_version = 1

            row_review = ReviewRef(
                review_id=review_id,
                entity=entity,
                entity_id=entity_id,
                entity_version=entity_version,
                action=action,
                reviewer_json=reviewer,
                reason=reason,
                decided_at=now(),
                previous_status=previous_status,
                new_status=new_status,
            )
            # Mã quyết định trùng là mã trùng, không phải xung đột trạng thái.
            self._insert(session, row_review, key=review_id)
            if not logged:
                self._record_version(
                    session,
                    entity=entity,
                    entity_id=entity_id,
                    version=snapshot_version,
                    change_kind="reviewed",
                    changed_fields=["status"],
                    snapshot=snapshot,
                    actor=reviewer,
                )
            return _review_document(row_review)

    def _apply_response_review(
        self, session, response_id: str, *, expected: int, new_status: str
    ) -> tuple[dict[str, Any], int]:
        """Duyệt phiếu trả lời bằng so-sánh-rồi-ghi, không đọc-rồi-ghi.

        Không có bước này thì hai người duyệt cùng lúc đều thấy thành công, quyết định
        sau đè quyết định trước, và nhật ký có hai dòng cùng một số phiên bản.
        Điều kiện ``status != 'superseded'`` chặn luôn trường hợp một lần lưu khác vừa
        thay thế phiếu này trong lúc ta đọc.
        """
        new_version = expected + 1
        try:
            result = session.execute(
                update(ProfessionalResponse)
                .where(
                    ProfessionalResponse.response_id == response_id,
                    ProfessionalResponse.version == expected,
                    ProfessionalResponse.status != "superseded",
                )
                .values(
                    status=new_status,
                    version=new_version,
                    etag=etag_for("response", response_id, new_version),
                    updated_at=now(),
                )
            )
        except IntegrityError as exc:
            # Ràng buộc duy nhất (work_item_id, version) chặn: một phiếu khác vừa chiếm số này.
            raise invalid_state(
                "Có phiếu trả lời khác vừa được lưu cùng lúc; đọc lại rồi gửi lại.",
                {"response_id": response_id, "attempted_version": new_version},
            ) from exc
        session.expire_all()
        if result.rowcount != 1:
            current = session.get(ProfessionalResponse, response_id)
            if current is not None and current.status == "superseded":
                raise invalid_state(
                    "Không duyệt được phiếu trả lời đã bị thay thế.",
                    {"response_id": response_id, "status": current.status},
                )
            raise version_conflict(expected, current.version if current is not None else expected)
        response = _ensure_row(session, ProfessionalResponse, response_id, "phiếu trả lời")
        return _response_document(response), response.version

    def list_reviews(self, *, entity: str, entity_id: str) -> list[dict[str, Any]]:
        with session_scope(self.engine) as session:
            rows = (
                session.execute(
                    select(ReviewRef)
                    .where(ReviewRef.entity == entity, ReviewRef.entity_id == entity_id)
                    # ``entity_version`` là số phiên bản của đối tượng bị duyệt tại lúc ra quyết định, và mỗi
            # quyết định đều tăng số đó lên đúng một (``_apply_response_review`` ghi ``expected + 1``
            # và chặn nếu ``expected`` không khớp bản đang có), nên trong một đối tượng nó chính là
            # thứ tự ghi. Vì vậy nó phải đứng TRƯỚC ``decided_at``: ``decided_at`` là giờ tường, giờ
            # này có thể lùi (NTP, máy lệch giờ, đồng hồ chậm), và khi đó bản ghi sau lại mang dấu cũ
            # rồi bị bản cũ đè về mặt thứ tự. ``decided_at`` xuống làm khoá phụ, ``review_id`` là chốt
            # cuối cho trường hợp hoà hoàn toàn — mã đó ngẫu nhiên nên không phản ánh thứ tự ghi.
            .order_by(ReviewRef.entity_version, ReviewRef.decided_at, ReviewRef.review_id)
                )
                .scalars()
                .all()
            )
            return [_review_document(row) for row in rows]

    # -------------------------------------------------------------- theo dõi

    def add_follow_up(
        self,
        work_item_id: str,
        *,
        kind: str,
        note: str,
        due_at: datetime | None = None,
        assignee: dict[str, Any] | None = None,
        actor: dict[str, Any] | None = None,
        follow_up_id: str | None = None,
    ) -> dict[str, Any]:
        _require(kind, FOLLOW_UP_KINDS, "kind")
        note = _text(note, "note")
        if due_at is not None and not isinstance(due_at, datetime):
            raise invalid_request("due_at phải là thời điểm.")
        assignee = _actor(assignee, "assignee")
        actor = _actor(actor)
        follow_up_id = (
            new_id("fu") if follow_up_id is None else _text(follow_up_id, "follow_up_id", max_length=ID_MAX_LENGTH)
        )
        row = FollowUp(
            follow_up_id=follow_up_id,
            work_item_id=work_item_id,
            kind=kind,
            status="open",
            note=note,
            due_at=due_at,
            assignee_json=assignee,
            created_by_json=actor,
            created_at=now(),
        )
        with session_scope(self.engine) as session:
            _ensure_work_item(session, work_item_id)
            self._insert(session, row, key=follow_up_id)
            document = _follow_up_document(row)
            self._record_version(
                session,
                entity="follow_up",
                entity_id=follow_up_id,
                version=1,
                change_kind="created",
                changed_fields=["kind", "status", "note"],
                snapshot=document,
                actor=actor,
            )
        return document

    def update_follow_up(
        self,
        follow_up_id: str,
        *,
        status: str | None = None,
        note: str | None = None,
        resolution: str | None = None,
        actor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if status is not None:
            _require(status, FOLLOW_UP_STATUSES, "status")
        if note is not None:
            note = _text(note, "note")
        if resolution is not None:
            resolution = _text(resolution, "resolution")
        actor = _actor(actor)
        with session_scope(self.engine) as session:
            row = _ensure_row(session, FollowUp, follow_up_id, "việc theo dõi")
            changed: list[str] = []
            if status is not None:
                row.status = status
                changed.append("status")
                if status in {"done", "cancelled"}:
                    row.closed_at = now()
                    changed.append("closed_at")
            if note is not None:
                row.note = note
                changed.append("note")
            if resolution is not None:
                row.resolution = resolution
                changed.append("resolution")
            document = _follow_up_document(row)
            if changed:
                self._record_version(
                    session,
                    entity="follow_up",
                    entity_id=follow_up_id,
                    version=1,
                    change_kind="updated",
                    changed_fields=changed,
                    snapshot=document,
                    actor=actor,
                )
            return document

    def list_follow_ups(self, work_item_id: str) -> list[dict[str, Any]]:
        work_item_id = _text(work_item_id, "work_item_id")
        with session_scope(self.engine) as session:
            rows = (
                session.execute(
                    select(FollowUp).where(FollowUp.work_item_id == work_item_id).order_by(FollowUp.created_at)
                )
                .scalars()
                .all()
            )
            return [_follow_up_document(row) for row in rows]

    # ------------------------------------------------------------- lịch sử

    def history(self, *, entity: str, entity_id: str) -> list[dict[str, Any]]:
        """Toàn bộ ảnh chụp phiên bản của một thực thể, cũ nhất trước."""
        with session_scope(self.engine) as session:
            rows = (
                session.execute(
                    select(VersionRef)
                    .where(VersionRef.entity == entity, VersionRef.entity_id == entity_id)
                    .order_by(VersionRef.revision, VersionRef.id)
                )
                .scalars()
                .all()
            )
            return [_version_document(row) for row in rows]

    def work_item_bundle(self, work_item_id: str) -> dict[str, Any]:
        """Yêu cầu kèm mọi thứ thuộc về nó, đọc trong một phiên để không bị cắt khúc."""
        with session_scope(self.engine) as session:
            row = _ensure_work_item(session, work_item_id)
            links = (
                session.execute(
                    select(InvestigationLink)
                    .where(InvestigationLink.work_item_id == work_item_id)
                    .order_by(InvestigationLink.created_at)
                )
                .scalars()
                .all()
            )
            bundles = (
                session.execute(
                    select(EvidenceBundle)
                    .where(EvidenceBundle.work_item_id == work_item_id)
                    .order_by(EvidenceBundle.created_at)
                )
                .scalars()
                .all()
            )
            responses = (
                session.execute(
                    select(ProfessionalResponse)
                    .where(ProfessionalResponse.work_item_id == work_item_id)
                    .order_by(ProfessionalResponse.version)
                )
                .scalars()
                .all()
            )
            response_reviews = _latest_response_reviews(session, [item.response_id for item in responses])
            follow_ups = (
                session.execute(
                    select(FollowUp).where(FollowUp.work_item_id == work_item_id).order_by(FollowUp.created_at)
                )
                .scalars()
                .all()
            )
            return {
                "work_item": work_item_document(
                    row,
                    {
                        "investigation_ids": [item.link_id for item in links],
                        "response_ids": [item.response_id for item in responses],
                        "follow_up_ids": [item.follow_up_id for item in follow_ups],
                    },
                ),
                "investigation_links": [_link_document(item) for item in links],
                "evidence_bundles": [_bundle_document(item) for item in bundles],
                "responses": [
                    _response_document(item, response_reviews.get(item.response_id)) for item in responses
                ],
                "follow_ups": [_follow_up_document(item) for item in follow_ups],
            }

    def counts(self) -> dict[str, int]:
        with session_scope(self.engine) as session:
            return {
                name: int(
                    session.execute(select(func.count()).select_from(WarehouseBase.metadata.tables[name])).scalar_one()
                )
                for name in CASEWORK_TABLES
            }
