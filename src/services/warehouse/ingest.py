"""Nạp tài liệu thủ công vào kho ELT (dùng cho trang quản trị).

Luồng: kiểm tra đầu vào -> băm nội dung -> kiểm trùng theo ``(source, source_id, version)``
-> ghi ``documents`` + ``document_sections`` -> lập chỉ mục Chroma -> ghi nhật ký ``ingestion_events``.

Cổng chất lượng ở đây là bản rút gọn (định danh, độ dài, trùng lặp, nguồn hợp lệ) vì tài liệu
nạp tay không đi qua bộ phân tích nguồn; pipeline ELT vẫn dùng cổng đầy đủ trong ``scripts/elt``.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine

from src.config import Settings
from src.services.warehouse.db import read_session, session_scope
from src.services.warehouse.models import (
    DailymedLabel,
    Document,
    DocumentChunk,
    DocumentSection,
    FaersReport,
    FaersReportDrug,
    FaersReportReaction,
    IngestionEvent,
    PubmedRecord,
    QualityFinding,
)
from src.vmec import DomainError

_log = logging.getLogger(__name__)

ALLOWED_SOURCES = {"pubmed", "dailymed", "faers", "reference", "manual"}
#: Ba nguồn ELT chính — nạp tay bằng nhãn này được đánh dấu là chưa đối chiếu với API gốc.
PRIMARY_SOURCES = {"pubmed", "dailymed", "faers"}
MIN_TEXT_CHARS = 40
MAX_TEXT_CHARS = 200_000


def _ingest_event_pattern(doc_id: str) -> str:
    """Mẫu LIKE cho sự kiện nạp của một tài liệu, đã thoát ký tự đại diện."""
    escaped = doc_id.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"ingest-{escaped}-%"


def delete_document(engine: Engine, doc_id: str) -> bool:
    """Xoá một tài liệu và mọi bản ghi con (thứ tự an toàn cho khoá ngoại).

    Trả ``True`` nếu tài liệu tồn tại và đã bị xoá.
    """
    child_tables = (
        DocumentSection, PubmedRecord, DailymedLabel,
        FaersReportDrug, FaersReportReaction, FaersReport, DocumentChunk,
    )
    with session_scope(engine) as session:
        row = session.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one_or_none()
        if row is None:
            return False
        for table in child_tables:
            session.execute(table.__table__.delete().where(table.doc_id == doc_id))
        session.execute(QualityFinding.__table__.delete().where(QualityFinding.doc_id == doc_id))
        # Sự kiện nạp của chính tài liệu này (mã dạng ``ingest-{doc_id}-{digest}``).
        # `doc_id` có thể chứa `_` hoặc `%` — ký tự đại diện của LIKE — nên phải thoát
        # để không xoá nhầm sự kiện của tài liệu khác.
        session.execute(
            IngestionEvent.__table__.delete().where(
                IngestionEvent.event_id.like(_ingest_event_pattern(doc_id), escape="\\")
            )
        )
        session.execute(Document.__table__.delete().where(Document.doc_id == doc_id))
    return True


def purge_document(engine: Engine, doc_id: str, settings: Settings | None = None) -> dict:
    """Xoá tài liệu khỏi PostgreSQL và chỉ mục vector (dùng cho dọn dẹp/kiểm thử)."""
    rag_removed = 0
    try:
        from src.services.rag.store import delete_document as chroma_delete
        from src.services.rag.store import get_collection

        collection = get_collection(settings)
        existing = collection.get(where={"doc_id": doc_id})
        rag_removed = len(existing.get("ids") or [])
        chroma_delete(collection, doc_id)
    except Exception as exc:  # noqa: BLE001 - thiếu chỉ mục không chặn việc xoá kho
        _log.warning("Không xoá được đoạn Chroma của %s: %s: %s", doc_id, exc.__class__.__name__, exc)
        rag_removed = 0
    return {"doc_id": doc_id, "postgres_removed": delete_document(engine, doc_id), "chunks_removed": rag_removed}


def ingest_document(
    engine: Engine,
    *,
    source: str,
    source_id: str,
    version: int,
    title: str,
    text: str,
    source_url: str = "",
    metadata: dict | None = None,
    event_id: str | None = None,
    settings: "Settings | None" = None,
) -> dict:
    source = (source or "").strip().lower()
    source_id = (source_id or "").strip()
    title = (title or "").strip()
    body = (text or "").strip()
    if source not in ALLOWED_SOURCES:
        raise DomainError(422, "INGEST_SOURCE_INVALID",
                          f"Nguồn không hợp lệ. Chọn một trong: {', '.join(sorted(ALLOWED_SOURCES))}.")
    if not source_id or len(source_id) > 200:
        raise DomainError(422, "INGEST_SOURCE_ID_INVALID", "Thiếu mã nguồn (source_id) hoặc mã quá dài.")
    if not isinstance(version, int) or version < 1:
        raise DomainError(422, "INGEST_VERSION_INVALID", "Phiên bản phải là số nguyên >= 1.")
    if len(body) < MIN_TEXT_CHARS:
        raise DomainError(422, "INGEST_TEXT_TOO_SHORT",
                          f"Văn bản quá ngắn ({len(body)} ký tự, cần tối thiểu {MIN_TEXT_CHARS}).")
    if len(body) > MAX_TEXT_CHARS:
        raise DomainError(422, "INGEST_TEXT_TOO_LONG",
                          f"Văn bản vượt giới hạn {MAX_TEXT_CHARS} ký tự.")
    doc_id = f"{source}:{source_id}:{version}"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)

    with read_session(engine) as session:
        existing = session.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one_or_none()
        existing_hash = existing.text_sha256 if existing else None
    if existing_hash is not None and existing_hash != digest:
        raise DomainError(409, "INGEST_CONFLICT",
                          f"Tài liệu {doc_id} đã tồn tại với nội dung khác. Tạo phiên bản mới thay vì ghi đè.")

    flags = ["manual_ingest"]
    if source in PRIMARY_SOURCES:
        # Nạp tay không đi qua bộ tải/đối chiếu bản thô của ELT: ghi rõ để người đọc biết
        # nội dung này không được xác minh với API gốc.
        flags.append("manual_entry_not_verified_with_source")
    values = {
        "doc_id": doc_id, "source": source, "source_id": source_id, "version": version,
        "title": title[:500] or source_id, "text": body, "text_sha256": digest,
        "source_url": source_url[:1000], "retrieved_at": now, "content_level": "manual_entry",
        "pair_id": None, "run_id": f"ingest-{now.strftime('%Y%m%dT%H%M%SZ')}",
        "quality_status": "keep", "quality_flags": flags, "metadata_json": metadata or {},
    }
    with session_scope(engine) as session:
        row = session.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one_or_none()
        if row is None:
            session.add(Document(**values))
            created = True
        else:
            for key, value in values.items():
                setattr(row, key, value)
            created = False
            session.execute(DocumentSection.__table__.delete().where(DocumentSection.doc_id == doc_id))
        session.add(DocumentSection(doc_id=doc_id, ordinal=0, title="Toàn văn", start=0, end=len(body)))

    rag: dict = {"indexed": False}
    try:
        from src.services.rag.build import index_documents

        rag = index_documents(engine, [doc_id], settings=settings)
        rag["indexed"] = True
    except Exception as exc:  # noqa: BLE001 - nạp tài liệu vẫn thành công dù chỉ mục lỗi
        # Không trả chi tiết nội bộ ra HTTP; chỉ ghi log phía máy chủ.
        _log.warning("Lập chỉ mục RAG cho %s thất bại: %s: %s", doc_id, exc.__class__.__name__, exc)
        rag = {"indexed": False, "error": "RAG_INDEX_UNAVAILABLE"}

    event = event_id or f"ingest-{doc_id}-{digest[:8]}"
    with session_scope(engine) as session:
        session.merge(IngestionEvent(
            event_id=event, kind="manual_document", status="completed",
            title=f"Nạp tài liệu {doc_id}",
            detail={"doc_id": doc_id, "source": source, "text_chars": len(body),
                    "sha256": digest, "created": created, "rag": rag},
        ))
    return {"doc_id": doc_id, "created": created, "sha256": digest, "text_chars": len(body),
            "quality_status": "keep", "quality_flags": flags, "rag": rag, "event_id": event}
