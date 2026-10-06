"""Lớp lưu trữ cho lát cắt DI (WorkItem/Response/FollowUp) trên kho ELT.

Quy ước chống mất dữ liệu:

* Mọi lần sửa ``work_items`` phải kèm ``expected_version`` (khoá lạc quan). Sai phiên
  bản thì trả ``VERSION_CONFLICT`` và **không** ghi gì.
* Mọi lần tạo/sửa đều ghi thêm một dòng ``version_refs`` giữ ảnh chụp của thực thể
  sau khi ghi, nên lịch sử luôn đọc lại được.
* Chỉ nhận các trường trong danh sách trắng; khoá lạ thì báo ``INVALID_REQUEST``
  thay vì bỏ qua im lặng.
* ``professional_responses`` là append-only theo phiên bản: bản cũ chuyển sang
  ``superseded`` nhưng vẫn nằm trong bảng.

Mã lỗi dùng envelope chung của MVP (``src/services/errors.py``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from src.services.casework.models import (
    EvidenceBundle,
    FollowUp,
    InvestigationLink,
    ProfessionalResponse,
    ReviewRef,
    VersionRef,
    WorkItem,
)
from src.services.errors import invalid_request, not_found, version_conflict
from src.services.warehouse.db import session_scope
from src.services.warehouse.models import WarehouseBase

ALLOWED_WORK_ITEM_PATCH_FIELDS = frozenset(
    {
        "context",
        "question",
        "scope",
        "unknowns",
        "priority",
        "owner",
        "work_status",
        "run_status",
        "review_status",
        "labels",
        "revision_of",
        "revision_reason",
    }
)

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
RESPONSE_STATUSES = frozenset({"draft", "in_review", "approved", "rejected", "superseded"})
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
LINK_STATES = frozenset({"queued", "running", "completed", "failed", "cancelled"})
REVIEW_ENTITIES = frozenset({"work_item", "response", "evidence_bundle"})
REVIEW_ACTIONS = frozenset(
    {"approve", "reject", "request_changes", "edit_claim", "edit_evidence", "exclude_evidence", "request_more"}
)
FOLLOW_UP_KINDS = frozenset({"request_information", "recheck_source", "monitor_case", "handover", "close"})
FOLLOW_UP_STATUSES = frozenset({"open", "in_progress", "done", "cancelled"})

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


def utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _require(value: Any, allowed: Iterable[str], field: str) -> str:
    if value is None:
        raise invalid_request(f"Thiếu trường bắt buộc: {field}.")
    if value not in allowed:
        raise invalid_request(f"Giá trị không hợp lệ cho {field}: {value!r}.", {"allowed": sorted(allowed)})
    return str(value)


def ensure_casework_schema(engine: Engine) -> list[str]:
    """Tạo các bảng còn thiếu của lát cắt DI (chỉ thêm, không sửa bảng cũ)."""
    tables = [WarehouseBase.metadata.tables[name] for name in CASEWORK_TABLES]
    before = set(_table_names(engine))
    WarehouseBase.metadata.create_all(engine, tables=tables)
    return sorted(set(_table_names(engine)) - before)


def _table_names(engine: Engine) -> list[str]:
    from sqlalchemy import inspect

    return list(inspect(engine).get_table_names())


def work_item_document(row: WorkItem) -> dict[str, Any]:
    """Chuyển bản ghi ORM sang hình dạng ``WorkItem`` của hợp đồng hospital-v2."""
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
        "labels": row.labels_json or {},
        "revision_of": row.revision_of,
        "revision_reason": row.revision_reason,
        "created_by": row.created_by_json,
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


def _response_document(row: ProfessionalResponse) -> dict[str, Any]:
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
        "review": row.review_json,
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


def _version_document(row: VersionRef) -> dict[str, Any]:
    return {
        "entity": row.entity,
        "entity_id": row.entity_id,
        "revision": row.revision,
        "entity_version": row.entity_version,
        "etag": row.etag,
        "change_kind": row.change_kind,
        "changed_fields": row.changed_fields_json or [],
        "snapshot": row.snapshot_json or {},
        "updated_by": row.updated_by_json,
        "updated_at": _iso(row.updated_at),
    }


class CaseWorkStore:
    """Đọc/ghi yêu cầu, liên kết điều tra, gói bằng chứng, phiếu trả lời và theo dõi."""

    def __init__(self, engine: Engine, *, ensure_schema: bool = True):
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
                updated_at=utcnow(),
            )
        )

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
        if not (question or "").strip():
            raise invalid_request("Câu hỏi không được để trống.")
        _require(priority, PRIORITIES, "priority")
        if scope is not None and not isinstance(scope, dict):
            raise invalid_request("scope phải là đối tượng.")
        if unknowns is not None and not isinstance(unknowns, list):
            raise invalid_request("unknowns phải là danh sách.")

        work_item_id = work_item_id or new_id("wi")
        stamp = utcnow()
        row = WorkItem(
            work_item_id=work_item_id,
            version=1,
            etag=etag_for("work_item", work_item_id, 1),
            context_json=context or {},
            question=question,
            scope_json=scope or {},
            unknowns_json=unknowns or [],
            priority=priority,
            owner_json=owner,
            work_status="draft",
            run_status="not_started",
            review_status="not_required",
            revision_of=revision_of,
            revision_reason=revision_reason,
            labels_json=labels or {},
            created_at=stamp,
            updated_at=stamp,
            created_by_json=actor,
        )
        document = work_item_document(row)
        with session_scope(self.engine) as session:
            session.add(row)
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

    def get_work_item(self, work_item_id: str) -> dict[str, Any]:
        with session_scope(self.engine) as session:
            row = session.get(WorkItem, work_item_id)
            if row is None:
                raise not_found("yêu cầu", work_item_id)
            return work_item_document(row)

    def list_work_items(
        self,
        *,
        work_status: str | None = None,
        run_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        with session_scope(self.engine) as session:
            query = select(WorkItem).order_by(WorkItem.created_at.desc(), WorkItem.work_item_id)
            if work_status:
                query = query.where(WorkItem.work_status == work_status)
            if run_status:
                query = query.where(WorkItem.run_status == run_status)
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
        force: bool = False,
    ) -> dict[str, Any]:
        """Sửa yêu cầu với khoá lạc quan; trả bản ghi mới kèm ``version`` tăng một."""
        if not isinstance(changes, dict) or not changes:
            raise invalid_request("Không có trường nào để cập nhật.")
        unknown = sorted(set(changes) - ALLOWED_WORK_ITEM_PATCH_FIELDS)
        if unknown:
            raise invalid_request(
                "Trường không được phép cập nhật: " + ", ".join(unknown),
                {"allowed": sorted(ALLOWED_WORK_ITEM_PATCH_FIELDS)},
            )
        if not force and expected_version is None:
            raise invalid_request("Thiếu expected_version; đọc lại yêu cầu rồi gửi kèm phiên bản.")

        if "work_status" in changes:
            _require(changes["work_status"], WORK_STATUSES, "work_status")
        if "run_status" in changes:
            _require(changes["run_status"], RUN_STATUSES, "run_status")
        if "review_status" in changes:
            _require(changes["review_status"], REVIEW_STATUSES, "review_status")
        if "priority" in changes:
            _require(changes["priority"], PRIORITIES, "priority")
        if "question" in changes and not str(changes["question"] or "").strip():
            raise invalid_request("Câu hỏi không được để trống.")

        columns = {
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

        with session_scope(self.engine) as session:
            row = session.get(WorkItem, work_item_id)
            if row is None:
                raise not_found("yêu cầu", work_item_id)
            if not force and int(expected_version) != row.version:
                raise version_conflict(int(expected_version), row.version)
            if reason is not None:
                changes = {**changes, "revision_reason": reason}
            for field, column in columns.items():
                if field in changes:
                    setattr(row, column, changes[field])
            row.version = row.version + 1
            row.etag = etag_for("work_item", work_item_id, row.version)
            row.updated_at = utcnow()
            document = work_item_document(row)
            self._record_version(
                session,
                entity="work_item",
                entity_id=work_item_id,
                version=row.version,
                change_kind="updated",
                changed_fields=sorted(changes),
                snapshot=document,
                actor=actor,
            )
            return document

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
        if not investigation_id:
            raise invalid_request("Thiếu investigation_id.")
        link_id = link_id or new_id("il")
        row = InvestigationLink(
            link_id=link_id,
            work_item_id=work_item_id,
            investigation_id=investigation_id,
            purpose=purpose,
            state=state,
            run_summary_json=run_summary,
            error_json=error,
            created_at=utcnow(),
            created_by_json=actor,
        )
        with session_scope(self.engine) as session:
            if session.get(WorkItem, work_item_id) is None:
                raise not_found("yêu cầu", work_item_id)
            session.add(row)
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
        with session_scope(self.engine) as session:
            row = session.get(InvestigationLink, link_id)
            if row is None:
                raise not_found("liên kết điều tra", link_id)
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
        if not investigation_id:
            raise invalid_request("Thiếu investigation_id.")
        for name, value in (("items", items), ("gaps", gaps), ("coverage", coverage)):
            if not isinstance(value, (list if name != "coverage" else dict)):
                raise invalid_request(f"{name} sai kiểu dữ liệu.")
        bundle_id = bundle_id or new_id("eb")
        row = EvidenceBundle(
            bundle_id=bundle_id,
            work_item_id=work_item_id,
            investigation_id=investigation_id,
            created_at=utcnow(),
            claim_json=claim,
            items_json=items,
            gaps_json=gaps,
            coverage_json=coverage,
            assessment_status=assessment_status,
            source_errors_json=source_errors or [],
            limitations_json=limitations or [],
        )
        with session_scope(self.engine) as session:
            if session.get(WorkItem, work_item_id) is None:
                raise not_found("yêu cầu", work_item_id)
            session.add(row)
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
        with session_scope(self.engine) as session:
            row = session.get(EvidenceBundle, bundle_id)
            if row is None:
                raise not_found("gói bằng chứng", bundle_id)
            return _bundle_document(row)

    def list_evidence_bundles(self, work_item_id: str) -> list[dict[str, Any]]:
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
        if not isinstance(sections, list):
            raise invalid_request("sections phải là danh sách.")

        with session_scope(self.engine) as session:
            if session.get(WorkItem, work_item_id) is None:
                raise not_found("yêu cầu", work_item_id)
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
                previous.updated_at = utcnow()
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
            response_id = response_id or new_id("resp")
            stamp = utcnow()
            row = ProfessionalResponse(
                response_id=response_id,
                work_item_id=work_item_id,
                version=version,
                etag=etag_for("response", response_id, version),
                status=status,
                sections_json=sections,
                assessment_status=assessment_status,
                coverage_json=coverage or {},
                drafted_by_json=drafted_by,
                review_json=None,
                approval_json=None,
                supersedes=supersedes,
                created_at=stamp,
                updated_at=stamp,
            )
            session.add(row)
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
        with session_scope(self.engine) as session:
            row = session.get(ProfessionalResponse, response_id)
            if row is None:
                raise not_found("phiếu trả lời", response_id)
            return _response_document(row)

    def list_responses(self, work_item_id: str, *, include_superseded: bool = True) -> list[dict[str, Any]]:
        with session_scope(self.engine) as session:
            query = select(ProfessionalResponse).where(ProfessionalResponse.work_item_id == work_item_id)
            if not include_superseded:
                query = query.where(ProfessionalResponse.status != "superseded")
            rows = session.execute(query.order_by(ProfessionalResponse.version)).scalars().all()
            return [_response_document(row) for row in rows]

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
    ) -> dict[str, Any]:
        _require(entity, REVIEW_ENTITIES, "entity")
        _require(action, REVIEW_ACTIONS, "action")
        if not isinstance(reviewer, dict) or not reviewer.get("actor_id"):
            raise invalid_request("reviewer cần có actor_id.")

        with session_scope(self.engine) as session:
            previous_status = ""
            new_status = ""
            entity_version = 0
            if entity == "work_item":
                row = session.get(WorkItem, entity_id)
                if row is None:
                    raise not_found("yêu cầu", entity_id)
                previous_status, entity_version = row.review_status, row.version
                new_status = WORK_ITEM_REVIEW_TARGET[action]
                row.review_status = new_status
                row.updated_at = utcnow()
                row.version += 1
                row.etag = etag_for("work_item", entity_id, row.version)
                snapshot, snapshot_version = work_item_document(row), row.version
            elif entity == "response":
                response = session.get(ProfessionalResponse, entity_id)
                if response is None:
                    raise not_found("phiếu trả lời", entity_id)
                previous_status, entity_version = response.status, response.version
                new_status = RESPONSE_REVIEW_TARGET[action]
                response.status = new_status
                response.updated_at = utcnow()
                snapshot, snapshot_version = _response_document(response), response.version
            else:
                bundle = session.get(EvidenceBundle, entity_id)
                if bundle is None:
                    raise not_found("gói bằng chứng", entity_id)
                previous_status, entity_version = "created", 1
                new_status = "reviewed"
                snapshot, snapshot_version = _bundle_document(bundle), 1

            review_id = review_id or new_id("rev")
            row_review = ReviewRef(
                review_id=review_id,
                entity=entity,
                entity_id=entity_id,
                entity_version=entity_version,
                action=action,
                reviewer_json=reviewer,
                reason=reason,
                decided_at=utcnow(),
                previous_status=previous_status,
                new_status=new_status,
            )
            session.add(row_review)
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

    def list_reviews(self, *, entity: str, entity_id: str) -> list[dict[str, Any]]:
        with session_scope(self.engine) as session:
            rows = (
                session.execute(
                    select(ReviewRef)
                    .where(ReviewRef.entity == entity, ReviewRef.entity_id == entity_id)
                    .order_by(ReviewRef.decided_at, ReviewRef.review_id)
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
        if not (note or "").strip():
            raise invalid_request("Ghi chú theo dõi không được để trống.")
        follow_up_id = follow_up_id or new_id("fu")
        row = FollowUp(
            follow_up_id=follow_up_id,
            work_item_id=work_item_id,
            kind=kind,
            status="open",
            note=note,
            due_at=due_at,
            assignee_json=assignee,
            created_by_json=actor,
            created_at=utcnow(),
        )
        with session_scope(self.engine) as session:
            if session.get(WorkItem, work_item_id) is None:
                raise not_found("yêu cầu", work_item_id)
            session.add(row)
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
        with session_scope(self.engine) as session:
            row = session.get(FollowUp, follow_up_id)
            if row is None:
                raise not_found("việc theo dõi", follow_up_id)
            changed: list[str] = []
            if status is not None:
                row.status = status
                changed.append("status")
                if status in {"done", "cancelled"}:
                    row.closed_at = utcnow()
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
        """Yêu cầu kèm mọi thứ thuộc về nó (dùng cho API và kiểm thử khôi phục)."""
        return {
            "work_item": self.get_work_item(work_item_id),
            "investigation_links": self.list_investigation_links(work_item_id),
            "evidence_bundles": self.list_evidence_bundles(work_item_id),
            "responses": self.list_responses(work_item_id),
            "follow_ups": self.list_follow_ups(work_item_id),
        }

    def counts(self) -> dict[str, int]:
        with session_scope(self.engine) as session:
            return {
                name: int(session.execute(select(func.count()).select_from(WarehouseBase.metadata.tables[name])).scalar_one())
                for name in CASEWORK_TABLES
            }
