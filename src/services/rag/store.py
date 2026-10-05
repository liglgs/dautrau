"""Lớp bọc ChromaDB: tạo, ghi và truy vấn bộ sưu tập vector.

ChromaDB lưu vector và metadata; PostgreSQL vẫn là nguồn chuẩn cho nội dung tài liệu.
Tên bộ sưu tập gắn với mô hình vector để tránh trộn số chiều khác nhau.
"""

from __future__ import annotations

import re
from functools import lru_cache

from src.config import Settings, get_settings
from src.services.rag.embeddings import Embedder, get_embedder


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


def reset_collection(settings: Settings | None = None, embedder: Embedder | None = None) -> str:
    settings = settings or get_settings()
    embedder = embedder or get_embedder(settings)
    name = collection_name(settings, embedder)
    get_client(settings).delete_collection(name)
    return name
