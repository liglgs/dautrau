"""Truy vấn ngữ nghĩa trên chỉ mục RAG, kèm ngữ cảnh tài liệu từ PostgreSQL."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Engine

from src.config import Settings, get_settings
from src.services.rag.embeddings import get_embedder
from src.services.rag.store import get_collection
from src.services.warehouse.db import read_session
from src.services.warehouse.models import Document
from src.vmec import DomainError


def search(
    engine: Engine,
    query: str,
    *,
    k: int | None = None,
    source: str | None = None,
    pair_id: str | None = None,
    settings: Settings | None = None,
) -> dict:
    """Trả về các đoạn gần nghĩa nhất, kèm trạng thái chất lượng và liên kết tài liệu gốc."""
    settings = settings or get_settings()
    top_k = k or settings.rag_top_k
    text = (query or "").strip()
    if not text:
        raise DomainError(422, "RAG_QUERY_EMPTY", "Cần nhập câu truy vấn.")
    embedder = get_embedder(settings)
    try:
        collection = get_collection(settings, embedder, create=False)
    except Exception as exc:
        raise DomainError(404, "RAG_INDEX_MISSING", "Chỉ mục RAG chưa được dựng. Hãy chạy bước build-index.") from exc

    vector = embedder.encode([text], task_type="RETRIEVAL_QUERY")[0]
    where: dict = {}
    if source:
        where["source"] = source
    if pair_id:
        where["pair_id"] = pair_id
    result = collection.query(
        query_embeddings=[vector],
        n_results=max(1, min(top_k, 50)),
        where=where or None,
        include=["metadatas", "distances", "documents"],
    )
    ids = (result.get("ids") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]

    doc_ids = [m.get("doc_id") for m in metadatas if m.get("doc_id")]
    known: dict[str, dict] = {}
    if doc_ids:
        with read_session(engine) as conn:
            rows = conn.execute(select(Document).where(Document.doc_id.in_(doc_ids))).scalars().all()
        known = {
            d.doc_id: {
                "doc_id": d.doc_id,
                "source": d.source,
                "source_id": d.source_id,
                "version": d.version,
                "title": d.title,
                "source_url": d.source_url,
                "quality_status": d.quality_status,
                "quality_flags": list(d.quality_flags or []),
                "pair_id": d.pair_id,
                "content_level": d.content_level,
            }
            for d in rows
        }
    hits = []
    for chunk_id, meta, distance, chunk_text in zip(ids, metadatas, distances, documents, strict=False):
        doc = known.get(meta.get("doc_id", ""), {})
        hits.append(
            {
                "chunk_id": chunk_id,
                # Khoảng cách cosine của Chroma có thể > 1 (đã chuẩn hoá lại), nên kẹp
                # độ tương đồng về [-1, 1] để điểm số luôn có nghĩa.
                "score": round(max(-1.0, min(1.0, 1.0 - float(distance))), 6),
                "text": chunk_text,
                "ordinal": meta.get("ordinal"),
                "char_start": meta.get("char_start"),
                "char_end": meta.get("char_end"),
                "document": doc or {"doc_id": meta.get("doc_id"), "source": meta.get("source")},
                "in_postgres": bool(doc),
            }
        )
    return {
        "query": text,
        "k": top_k,
        "source_filter": source,
        "pair_id_filter": pair_id,
        "embedding_model": embedder.model_name,
        "embedding_provider": embedder.provider,
        "hits": hits,
    }
