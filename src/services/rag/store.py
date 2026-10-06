"""Lớp bọc ChromaDB: tạo, ghi và truy vấn bộ sưu tập vector.

ChromaDB lưu vector và metadata; PostgreSQL vẫn là nguồn chuẩn cho nội dung tài liệu.
Tên bộ sưu tập gắn với mô hình vector để tránh trộn số chiều khác nhau.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from src.config import Settings, get_settings
from src.services.rag.embeddings import Embedder, get_embedder

_log = logging.getLogger(__name__)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def collection_name(settings: Settings, embedder: Embedder) -> str:
    return f"{settings.rag_collection}__{embedder.provider}__{slug(embedder.model_name)}"


@lru_cache(maxsize=4)
def _client(path: str):
    import chromadb

    return chromadb.PersistentClient(path=path)


def get_client(settings: Settings | None = None):
    settings = settings or get_settings()
    return _client(settings.rag_chroma_dir)


def get_collection(settings: Settings | None = None, embedder: Embedder | None = None, create: bool = True):
    settings = settings or get_settings()
    embedder = embedder or get_embedder(settings)
    client = get_client(settings)
    name = collection_name(settings, embedder)
    if create:
        return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
    return client.get_collection(name=name)


def upsert_chunks(collection, chunks: list[dict], embeddings: list[list[float]], batch_size: int = 128) -> int:
    """Ghi theo lô. ``chunks`` là dict có ``chunk_id``, ``text`` và ``metadata``."""
    written = 0
    for start in range(0, len(chunks), batch_size):
        window = chunks[start:start + batch_size]
        collection.upsert(
            ids=[c["chunk_id"] for c in window],
            documents=[c["text"] for c in window],
            metadatas=[c["metadata"] for c in window],
            embeddings=embeddings[start:start + batch_size],
        )
        written += len(window)
    return written


def delete_document(collection, doc_id: str) -> None:
    collection.delete(where={"doc_id": doc_id})


def list_indexed_doc_ids(collection) -> set[str]:
    """Tập ``doc_id`` đang có mặt trong bộ sưu tập (đọc theo lô để không kéo cả corpus vào RAM)."""
    doc_ids: set[str] = set()
    offset = 0
    batch = 1000
    while True:
        window = collection.get(include=["metadatas"], limit=batch, offset=offset)
        metadatas = window.get("metadatas") or []
        if not metadatas:
            break
        doc_ids.update(str(meta.get("doc_id", "")) for meta in metadatas if meta)
        offset += len(metadatas)
    return doc_ids


def reset_collection(settings: Settings | None = None, embedder: Embedder | None = None) -> str:
    """Xoá bộ sưu tập nếu đang tồn tại (chạy trên máy mới thì chưa có gì để xoá)."""
    settings = settings or get_settings()
    embedder = embedder or get_embedder(settings)
    name = collection_name(settings, embedder)
    client = get_client(settings)
    try:
        client.delete_collection(name)
    except Exception as exc:  # noqa: BLE001 - thiếu bộ sưu tập không phải lỗi
        if exc.__class__.__name__ != "NotFoundError":
            raise
        _log.info("Bộ sưu tập %s chưa tồn tại; bỏ qua bước xoá.", name)
    return name
