"""Dựng chỉ mục RAG từ kho ELT (PostgreSQL -> chunk -> vector -> ChromaDB)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from src.config import Settings, get_settings
from src.services.rag.chunking import CHUNK_SIZE, OVERLAP, chunk_text
from src.services.rag.embeddings import get_embedder
from src.services.rag.store import collection_name, get_collection, reset_collection, upsert_chunks
from src.services.warehouse.db import read_session
from src.services.warehouse.models import Document, DocumentChunk


def _documents(engine: Engine, pair_id: str | None, only_keep: bool, limit: int | None):
    stmt = select(Document).order_by(Document.doc_id)
    if only_keep:
        stmt = stmt.where(Document.quality_status == "keep")
    if pair_id:
        stmt = stmt.where(Document.pair_id == pair_id)
    if limit:
        stmt = stmt.limit(limit)
    with read_session(engine) as conn:
        return list(conn.execute(stmt).scalars().all())


def build_index(
    engine: Engine,
    *,
    run_id: str = "manual",
    pair_id: str | None = None,
    only_keep: bool = True,
    reset: bool = False,
    limit: int | None = None,
    settings: Settings | None = None,
) -> dict:
    """Ghi lại toàn bộ đoạn của các tài liệu đủ điều kiện. Trả về thống kê để ghi manifest."""
    settings = settings or get_settings()
    embedder = get_embedder(settings)
    if reset:
        reset_collection(settings, embedder)
    collection = get_collection(settings, embedder)

    documents = _documents(engine, pair_id, only_keep, limit)
    stats = {
        "run_id": run_id,
        "pair_id": pair_id,
        "documents": len(documents),
        "chunks": 0,
        "embedding_provider": embedder.provider,
        "embedding_model": embedder.model_name,
        "collection": collection_name(settings, embedder),
        "chunk_size": CHUNK_SIZE,
        "overlap": OVERLAP,
        "built_at": datetime.now(UTC).isoformat(),
        "skipped": 0,
    }
    for doc in documents:
        written = _index_document(engine, collection, embedder, doc)
        if written == 0:
            stats["skipped"] += 1
        stats["chunks"] += written
    return stats


def _index_document(engine: Engine, collection, embedder, doc: Document) -> int:
    """Ghi toàn bộ đoạn của một tài liệu vào Chroma và bảng document_chunks. Trả về số đoạn."""
    chunks = chunk_text(doc.text, doc.doc_id)
    if not chunks:
        return 0
    metadata = [
            {
                "doc_id": doc.doc_id,
                "source": doc.source,
                "source_id": doc.source_id,
                "version": int(doc.version),
                "title": (doc.title or "")[:300],
                "source_url": doc.source_url or "",
                "pair_id": doc.pair_id or "",
                "content_level": doc.content_level or "",
                "ordinal": int(c.ordinal),
                "char_start": int(c.char_start),
                "char_end": int(c.char_end),
                "text_sha256": c.text_sha256,
            }
            for c in chunks
        ]
    embeddings = embedder.encode([c.text for c in chunks], task_type="RETRIEVAL_DOCUMENT")
    payload = [
        {"chunk_id": c.chunk_id, "text": c.text, "metadata": m} for c, m in zip(chunks, metadata, strict=True)
    ]
    upsert_chunks(collection, payload, embeddings)
    with engine.begin() as conn:
        conn.execute(delete(DocumentChunk).where(DocumentChunk.doc_id == doc.doc_id))
        conn.execute(
            DocumentChunk.__table__.insert(),
            [
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": doc.doc_id,
                    "ordinal": c.ordinal,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "text_sha256": c.text_sha256,
                    "n_chars": len(c.text),
                    "embedding_model": embedder.model_name,
                    "chroma_collection": collection.name,
                }
                for c in chunks
            ],
        )
    return len(chunks)


def index_documents(engine: Engine, doc_ids: list[str], *, settings: Settings | None = None) -> dict:
    """Lập chỉ mục cho một danh sách tài liệu cụ thể (dùng khi nạp thủ công qua API)."""
    settings = settings or get_settings()
    embedder = get_embedder(settings)
    collection = get_collection(settings, embedder)
    indexed = 0
    chunks_written = 0
    with read_session(engine) as session:
        docs = list(session.execute(select(Document).where(Document.doc_id.in_(doc_ids))).scalars().all())
    for doc in docs:
        if doc.quality_status != "keep":
            continue
        chunks_written += _index_document(engine, collection, embedder, doc)
        indexed += 1
    return {"documents_indexed": indexed, "chunks_written": chunks_written,
            "collection": collection_name(settings, embedder), "embedding_model": embedder.model_name}


def index_stats(engine: Engine, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    embedder = get_embedder(settings)
    name = collection_name(settings, embedder)
    try:
        collection = get_collection(settings, embedder, create=False)
        count = int(collection.count())
    except Exception:  # bộ sưu tập chưa tồn tại
        count = 0
    with read_session(engine) as conn:
        rows = conn.execute(select(DocumentChunk.chunk_id)).all()
    return {
        "collection": name,
        "chroma_chunks": count,
        "postgres_chunks": len(rows),
        "embedding_provider": embedder.provider,
        "embedding_model": embedder.model_name,
        "persist_dir": settings.rag_chroma_dir,
    }
