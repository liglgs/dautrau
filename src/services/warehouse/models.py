"""Kho dữ liệu ELT (PostgreSQL) phục vụ RAG và tra cứu có cấu trúc.

Nguyên tắc:
  * ``documents`` là bản ghi chuẩn bất biến theo ``(source, source_id, version)``;
    mọi trường dẫn xuất nằm ở bảng riêng hoặc trong ``metadata_json``.
  * Mọi lần chạy ELT đều để lại dấu vết trong ``elt_runs``/``elt_artifacts``/``quality_findings``.
  * Không lưu nhãn chuyên môn ở đây: gói hiện tại là ``candidate_not_gold``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now(UTC)


class WarehouseBase(DeclarativeBase):
    pass


class EltRun(WarehouseBase):
    __tablename__ = "elt_runs"
    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    profile: Mapped[str] = mapped_column(String(30))
    git_sha: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EltArtifact(WarehouseBase):
    __tablename__ = "elt_artifacts"
    artifact_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("elt_runs.run_id"), index=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    url: Mapped[str] = mapped_column(Text, default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    local_path: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Drug(WarehouseBase):
    __tablename__ = "drugs"
    drug_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    ingredient: Mapped[str] = mapped_column(String(200), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(40), default="elt")
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DrugEventPair(WarehouseBase):
    __tablename__ = "drug_event_pairs"
    pair_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    drug_id: Mapped[str] = mapped_column(ForeignKey("drugs.drug_id"), index=True)
    drug_name: Mapped[str] = mapped_column(String(200))
    event_term: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(40), default="candidate_not_gold")
    source: Mapped[str] = mapped_column(String(40), default="bundle")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Document(WarehouseBase):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source", "source_id", "version", name="uq_document_identity"),)
    doc_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source: Mapped[str] = mapped_column(String(30), index=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(Text, default="")
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    content_level: Mapped[str] = mapped_column(String(40), default="")
    pair_id: Mapped[str | None] = mapped_column(
        ForeignKey("drug_event_pairs.pair_id", ondelete="SET NULL"), nullable=True, index=True
    )
    run_id: Mapped[str] = mapped_column(String(80), default="")
    quality_status: Mapped[str] = mapped_column(String(20), default="keep", index=True)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    sections: Mapped[list[DocumentSection]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentSection(WarehouseBase):
    __tablename__ = "document_sections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(300), default="")
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    document: Mapped[Document] = relationship(back_populates="sections")


class PubmedRecord(WarehouseBase):
    __tablename__ = "pubmed_records"
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True)
    pmid: Mapped[str] = mapped_column(String(40), index=True)
    journal: Mapped[str] = mapped_column(String(300), default="")
    publication_date: Mapped[str] = mapped_column(String(120), default="")
    publication_types: Mapped[list] = mapped_column(JSON, default=list)
    doi: Mapped[list] = mapped_column(JSON, default=list)
    authors: Mapped[list] = mapped_column(JSON, default=list)
    has_abstract: Mapped[bool] = mapped_column(Boolean, default=False)


class DailymedLabel(WarehouseBase):
    __tablename__ = "dailymed_labels"
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True)
    setid: Mapped[str] = mapped_column(String(80), index=True)
    effective_time: Mapped[str | None] = mapped_column(String(40), nullable=True)
    published_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    routes: Mapped[list] = mapped_column(JSON, default=list)
    ingredients: Mapped[list] = mapped_column(JSON, default=list)
    n_sections: Mapped[int] = mapped_column(Integer, default=0)
    single_ingredient: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class FaersReport(WarehouseBase):
    __tablename__ = "faers_reports"
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id", ondelete="CASCADE"), primary_key=True)
    safetyreportid: Mapped[str] = mapped_column(String(40), index=True)
    report_version: Mapped[int] = mapped_column(Integer, default=1)
    receivedate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    occurcountry: Mapped[str | None] = mapped_column(String(40), nullable=True)
    serious: Mapped[str | None] = mapped_column(String(20), nullable=True)
    patient_sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    patient_age: Mapped[float | None] = mapped_column(Float, nullable=True)
    patient_age_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reporter_country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    n_drugs: Mapped[int] = mapped_column(Integer, default=0)
    n_reactions: Mapped[int] = mapped_column(Integer, default=0)
    total_hits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    matched_drugs: Mapped[list] = mapped_column(JSON, default=list)
    reactions: Mapped[list] = mapped_column(JSON, default=list)
    drugs: Mapped[list[FaersReportDrug]] = relationship(back_populates="report", cascade="all, delete-orphan")
    reaction_rows: Mapped[list[FaersReportReaction]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class FaersReportDrug(WarehouseBase):
    __tablename__ = "faers_report_drugs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("faers_reports.doc_id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    medicinalproduct: Mapped[str] = mapped_column(String(400), default="")
    generic_name: Mapped[str] = mapped_column(String(400), default="")
    brand_name: Mapped[str] = mapped_column(String(400), default="")
    substance_name: Mapped[str] = mapped_column(String(400), default="")
    route: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dose_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    characterization: Mapped[str | None] = mapped_column(String(20), nullable=True)
    indication: Mapped[str | None] = mapped_column(String(400), nullable=True)
    report: Mapped[FaersReport] = relationship(back_populates="drugs")


class FaersReportReaction(WarehouseBase):
    __tablename__ = "faers_report_reactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("faers_reports.doc_id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    term: Mapped[str] = mapped_column(String(400), index=True)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    report: Mapped[FaersReport] = relationship(back_populates="reaction_rows")


class QualityFinding(WarehouseBase):
    __tablename__ = "quality_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(80), index=True)
    doc_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    pair_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="")
    check_name: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(10), default="info")
    decision: Mapped[str] = mapped_column(String(20), default="note")
    detail: Mapped[str] = mapped_column(Text, default="")


class DocumentChunk(WarehouseBase):
    __tablename__ = "document_chunks"
    chunk_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    text_sha256: Mapped[str] = mapped_column(String(64))
    n_chars: Mapped[int] = mapped_column(Integer)
    embedding_model: Mapped[str] = mapped_column(String(120), default="")
    chroma_collection: Mapped[str] = mapped_column(String(120), default="")
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class IngestionEvent(WarehouseBase):
    """Nhật ký thao tác nạp tài liệu (upload thủ công hoặc chạy ELT) cho trang admin."""

    __tablename__ = "ingestion_events"
    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    title: Mapped[str] = mapped_column(String(300), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
