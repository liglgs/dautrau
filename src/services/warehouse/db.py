"""Kết nối PostgreSQL cho kho ELT.

Không dùng chung engine với ``src.db`` (di sản VMEC) để tránh trộn hai lược đồ.
Địa chỉ mặc định: ``postgresql+psycopg://medreview:medreview@localhost:5432/vigilens_elt``.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.services.warehouse.models import WarehouseBase

ELT_DB_NAME = "vigilens_elt"


def derive_elt_url(base_url: str) -> str:
    """Đổi tên cơ sở dữ liệu trong URL sang ``vigilens_elt`` (giữ driver và thông tin đăng nhập)."""
    parts = urlsplit(base_url)
    if not parts.scheme.startswith("postgresql"):
        return base_url
    return urlunsplit(parts._replace(path=f"/{ELT_DB_NAME}"))


def elt_database_url() -> str:
    settings = get_settings()
    configured = (getattr(settings, "elt_database_url", "") or "").strip()
    if configured:
        return configured
    return derive_elt_url(settings.database_url)


@lru_cache(maxsize=4)
def get_warehouse_engine(url: str | None = None) -> Engine:
    return create_engine(url or elt_database_url(), pool_pre_ping=True, future=True)


def create_schema(engine: Engine) -> None:
    WarehouseBase.metadata.create_all(engine)


def table_counts(engine: Engine) -> dict[str, int]:
    names = [
        "documents",
        "document_sections",
        "pubmed_records",
        "dailymed_labels",
        "faers_reports",
        "faers_report_drugs",
        "faers_report_reactions",
        "quality_findings",
        "document_chunks",
        "drugs",
        "drug_event_pairs",
        "ingestion_events",
    ]
    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for name in names:
            counts[name] = int(conn.execute(text(f"SELECT count(*) FROM {name}")).scalar_one())
    return counts


@contextmanager
def read_session(engine: Engine):
    """Phiên ORM chỉ đọc: bắt buộc để nhận đối tượng ORM thay vì hàng cột thô."""
    with Session(engine) as session:
        yield session


@contextmanager
def session_scope(engine: Engine):
    factory = sessionmaker(engine, expire_on_commit=False)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
