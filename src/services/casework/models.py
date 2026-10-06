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
