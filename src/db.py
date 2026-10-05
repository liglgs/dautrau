"""Persistent VMEC-03 records.  Every workflow mutation locks its case row."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from src.config import get_settings


def uid(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CaseRecord(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    patient_id: Mapped[str] = mapped_column(String(80))
    encounter_id: Mapped[str] = mapped_column(String(80))
    reconciliation_at: Mapped[str] = mapped_column(String(40))
    visible_at: Mapped[str] = mapped_column(String(40))
    lifecycle: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    input_revision: Mapped[int] = mapped_column(Integer, default=1)
    extraction_pending: Mapped[bool] = mapped_column(Boolean, default=True)
    scenario: Mapped[str | None] = mapped_column(String(30), nullable=True)
    assigned: Mapped[list] = mapped_column(JSON, default=list)
    assertions: Mapped[list] = mapped_column(JSON, default=list)
    issues: Mapped[list] = mapped_column(JSON, default=list)
    audit: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[list["SourceRecord"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    evidence: Mapped[list["EvidenceRecord"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class SourceRecord(Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("case_id", "source_id", "version"),)
    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: uid("SRC"))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(160))
    author_role: Mapped[str] = mapped_column(String(40))
    event_time: Mapped[str | None] = mapped_column(String(40))
    recorded_at: Mapped[str | None] = mapped_column(String(40))
    available_at: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64))
    case: Mapped[CaseRecord] = relationship(back_populates="sources")


class EvidenceRecord(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer)
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text)
    case: Mapped[CaseRecord] = relationship(back_populates="evidence")


class TaskRecord(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    issue_id: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    assignee: Mapped[str] = mapped_column(ForeignKey("users.id"))
    question: Mapped[str] = mapped_column(Text)
    missing_fields: Mapped[list] = mapped_column(JSON, default=list)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="open")
    response: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(255), index=True)


class HandoffRecord(Base):
    __tablename__ = "handoffs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    issue_id: Mapped[str] = mapped_column(String(80))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    recipient: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)


class ReviewRecord(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    case_revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    approved_by: Mapped[str | None] = mapped_column(String(160))
    approved_at: Mapped[str | None] = mapped_column(String(40))
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(25), default="queued")
    input_revision: Mapped[int] = mapped_column(Integer)
    parent_run_id: Mapped[str | None] = mapped_column(String(80))
    trigger_event_id: Mapped[str | None] = mapped_column(String(80))
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ReceiptRecord(Base):
    __tablename__ = "receipts"
    __table_args__ = (UniqueConstraint("actor", "method", "path", "key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(80))
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(255))
    key: Mapped[str] = mapped_column(String(160))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int] = mapped_column(Integer)
    response: Mapped[dict] = mapped_column(JSON)


class ReleaseEvent(Base):
    __tablename__ = "release_events"
    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    payload_hash: Mapped[str] = mapped_column(String(64))
    receipt: Mapped[dict] = mapped_column(JSON)


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
