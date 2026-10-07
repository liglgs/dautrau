"""Bảng lưu trữ cho lát cắt DI: yêu cầu, liên kết điều tra, gói bằng chứng, phiếu trả lời, theo dõi.

Các bảng ở đây nằm cùng ``WarehouseBase`` với kho ELT (một cơ sở dữ liệu, một lần
``create_all``) nhưng tách mô-đun để ranh giới nghiệp vụ rõ ràng:

  * ``work_items`` — yêu cầu tra cứu của bác sĩ, có ``version`` làm khoá lạc quan;
  * ``investigation_links`` — nối yêu cầu với một lần chạy điều tra và trạng thái của nó;
  * ``evidence_bundles`` — gói bằng chứng bất biến (mỗi lần chạy một bản);
  * ``professional_responses`` — phiếu trả lời theo phiên bản, có ``supersedes``;
  * ``follow_ups`` — việc theo dõi sau khi trả lời;
  * ``version_refs`` — nhật ký phiên bản append-only (ảnh chụp từng lần ghi);
  * ``review_refs`` — quyết định duyệt append-only.

Nguyên tắc chống mất dữ liệu: mọi lần cập nhật đều đi qua ``version`` đã đọc, ghi thêm
một dòng ``version_refs`` giữ nguyên ảnh chụp trước khi sửa, và chỉ nhận các trường
nằm trong danh sách trắng. Hai lần cập nhật liên tiếp vì thế không thể ghi đè im lặng.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.services.warehouse.models import WarehouseBase, now

__all__ = [
    "EvidenceBundle",
    "FollowUp",
    "InvestigationLink",
    "ProfessionalResponse",
    "ReviewRef",
    "VersionRef",
    "WorkItem",
    "CaseworkWorkflow",
    "InputRevision",
    "Clarification",
    "CaseworkRun",
    "CaseworkCommand",
    "OutputBasis",
    "ReviewBasis",
    "IdempotencyRecord",
    "EditorDraft",
]


class WorkItem(WarehouseBase):
    """Yêu cầu tra cứu của bác sĩ (contract ``WorkItem``)."""

    __tablename__ = "work_items"
    work_item_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    etag: Mapped[str] = mapped_column(String(120), default="")
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    question: Mapped[str] = mapped_column(Text)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict)
    unknowns_json: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[str] = mapped_column(String(20), default="routine")
    owner_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    work_status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    run_status: Mapped[str] = mapped_column(String(30), default="not_started")
    review_status: Mapped[str] = mapped_column(String(30), default="not_required")
    revision_of: Mapped[str | None] = mapped_column(String(80), nullable=True)
    revision_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    labels_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class InvestigationLink(WarehouseBase):
    """Nối yêu cầu với một lần chạy điều tra (contract ``InvestigationLink``)."""

    __tablename__ = "investigation_links"
    link_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    investigation_id: Mapped[str] = mapped_column(String(120), index=True)
    purpose: Mapped[str] = mapped_column(String(20), default="initial")
    state: Mapped[str] = mapped_column(String(30), default="queued")
    run_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EvidenceBundle(WarehouseBase):
    """Gói bằng chứng bất biến của một lần điều tra (contract ``EvidenceBundle``)."""

    __tablename__ = "evidence_bundles"
    bundle_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    investigation_id: Mapped[str] = mapped_column(String(120), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    claim_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    items_json: Mapped[list] = mapped_column(JSON, default=list)
    gaps_json: Mapped[list] = mapped_column(JSON, default=list)
    coverage_json: Mapped[dict] = mapped_column(JSON, default=dict)
    assessment_status: Mapped[str] = mapped_column(String(40), default="insufficient_evidence")
    source_errors_json: Mapped[list] = mapped_column(JSON, default=list)
    limitations_json: Mapped[list] = mapped_column(JSON, default=list)


class ProfessionalResponse(WarehouseBase):
    """Phiếu trả lời theo phiên bản (contract ``ProfessionalResponse``)."""

    __tablename__ = "professional_responses"
    # Hai ràng buộc duy nhất giữ chuỗi phiên bản lành mạnh:
    #   * (work_item_id, version) — không hai bản cùng số phiên bản (đua nhau khi lưu);
    #   * (work_item_id) WHERE status <> 'superseded' — mỗi yêu cầu chỉ một bản "hiện hành".
    # Ràng buộc thứ hai là chỉ mục duy nhất một phần; PostgreSQL và SQLite đều hỗ trợ.
    __table_args__ = (
        Index("uq_response_version", "work_item_id", "version", unique=True),
        Index(
            "uq_response_current",
            "work_item_id",
            unique=True,
            postgresql_where=text("status <> 'superseded'"),
            sqlite_where=text("status <> 'superseded'"),
        ),
    )
    response_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    etag: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    sections_json: Mapped[list] = mapped_column(JSON, default=list)
    assessment_status: Mapped[str] = mapped_column(String(40), default="insufficient_evidence")
    coverage_json: Mapped[dict] = mapped_column(JSON, default=dict)
    drafted_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    review_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supersedes: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FollowUp(WarehouseBase):
    """Việc theo dõi sau khi trả lời (contract ``FollowUp``)."""

    __tablename__ = "follow_ups"
    follow_up_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="request_information")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    note: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignee_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)


class VersionRef(WarehouseBase):
    """Nhật ký phiên bản append-only: một dòng cho mỗi lần tạo/sửa thực thể."""

    __tablename__ = "version_refs"
    __table_args__ = (Index("uq_version_ref", "entity", "entity_id", "revision", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    entity_version: Mapped[int] = mapped_column(Integer)
    etag: Mapped[str] = mapped_column(String(120), default="")
    change_kind: Mapped[str] = mapped_column(String(20), default="created")
    changed_fields_json: Mapped[list] = mapped_column(JSON, default=list)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ReviewRef(WarehouseBase):
    """Quyết định duyệt append-only (contract ``ReviewRef``)."""

    __tablename__ = "review_refs"
    review_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    entity: Mapped[str] = mapped_column(String(30), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    entity_version: Mapped[int] = mapped_column(Integer, default=0)
    action: Mapped[str] = mapped_column(String(30))
    reviewer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    previous_status: Mapped[str] = mapped_column(String(40), default="")
    new_status: Mapped[str] = mapped_column(String(40), default="")


# Các bảng dưới đây là sidecar của WorkItem v1. Chúng không thêm cột vào bảng v1,
# nhờ đó database đang chạy phiên bản cũ vẫn nâng cấp theo hướng chỉ thêm bảng.
class CaseworkWorkflow(WarehouseBase):
    __tablename__ = "casework_workflows"
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    input_revision: Mapped[int] = mapped_column(Integer, default=1)
    current_run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    current_response_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    readiness_json: Mapped[dict] = mapped_column(JSON, default=dict)
    adr_intake_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class InputRevision(WarehouseBase):
    __tablename__ = "casework_input_revisions"
    __table_args__ = (Index("uq_casework_input_revision", "work_item_id", "revision", unique=True),)
    input_revision_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    sources_json: Mapped[list] = mapped_column(JSON, default=list)
    assertions_json: Mapped[list] = mapped_column(JSON, default=list)
    adr_facts_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Clarification(WarehouseBase):
    __tablename__ = "casework_clarifications"
    __table_args__ = (
        Index(
            "uq_casework_open_clarification",
            "work_item_id",
            "semantic_key",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
    )
    clarification_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    field_key: Mapped[str] = mapped_column(String(80), index=True)
    question: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(40))
    blocked_step: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    input_revision: Mapped[int] = mapped_column(Integer)
    semantic_key: Mapped[str] = mapped_column(String(128), index=True)
    answer_source_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answered_by_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supersedes: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseworkRun(WarehouseBase):
    __tablename__ = "casework_runs"
    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    purpose: Mapped[str] = mapped_column(String(40))
    input_revision: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64))
    runtime_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    progress_revision: Mapped[int] = mapped_column(Integer, default=1)
    source_results_json: Mapped[list] = mapped_column(JSON, default=list)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CaseworkCommand(WarehouseBase):
    __tablename__ = "casework_commands"
    __table_args__ = (Index("uq_casework_operation", "work_item_id", "operation_key", unique=True),)
    command_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    command_type: Mapped[str] = mapped_column(String(50), index=True)
    operation_key: Mapped[str] = mapped_column(String(160))
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cursor_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OutputBasis(WarehouseBase):
    __tablename__ = "casework_output_basis"
    __table_args__ = (Index("uq_casework_current_output_basis", "response_id", "response_version", unique=True),)
    basis_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    response_id: Mapped[str] = mapped_column(String(80), index=True)
    response_version: Mapped[int] = mapped_column(Integer)
    basis_hash: Mapped[str] = mapped_column(String(64), unique=True)
    input_revision: Mapped[int] = mapped_column(Integer)
    basis_json: Mapped[dict] = mapped_column(JSON, default=dict)
    author_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    valid: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    invalidated_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReviewBasis(WarehouseBase):
    __tablename__ = "casework_review_basis"
    review_basis_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    basis_id: Mapped[str] = mapped_column(ForeignKey("casework_output_basis.basis_id"), index=True)
    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.work_item_id"), index=True)
    reviewer_json: Mapped[dict] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(30))
    stale_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IdempotencyRecord(WarehouseBase):
    __tablename__ = "casework_idempotency"
    __table_args__ = (Index("uq_casework_idempotency", "actor_id", "route", "idempotency_key", unique=True),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    route: Mapped[str] = mapped_column(String(160))
    idempotency_key: Mapped[str] = mapped_column(String(160))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EditorDraft(WarehouseBase):
    __tablename__ = "casework_editor_drafts"
    __table_args__ = (Index("uq_casework_editor_draft", "actor_id", "entity", "entity_id", unique=True),)
    draft_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(120), index=True)
    entity: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    base_versions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    saved_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
