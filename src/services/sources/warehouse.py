"""Adapter nguồn đọc từ kho ELT + chỉ mục RAG (chế độ ``warehouse``).

Không gọi mạng: chỉ mục Chroma xếp hạng đoạn theo ngữ nghĩa, rồi toàn văn được đọc
từ PostgreSQL — nguồn chuẩn của nội dung. Nhờ vậy mọi tài liệu đưa vào điều tra đều
có provenance trong kho, trích dẫn trỏ đúng vào văn bản đã lưu, và khi chỉ mục thiếu
thì adapter trả lỗi nguồn (ghi thành gap) chứ không bịa tài liệu.

Hợp đồng giống các adapter khác của graph: ``search(action, budget) -> SourceSearchResult``.
Truy hồi cục bộ không tiêu tốn request nguồn (``requests_used=0``) nhưng vẫn tính một
bước nghiệp vụ, đúng quy tắc ngân sách.
"""

from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy.engine import Engine

from src.config import Settings
from src.models.schemas import SourceDocument, SourceSearchResult, SourceStatus
from src.services.planner import SOURCE_PRIORITY, query_fingerprint
from src.services.rag.search import search as rag_search
from src.services.warehouse.queries import documents_by_ids
from src.vmec import DomainError

#: Độ dài đoạn khớp được lưu kèm trong metadata để truy vết (không dùng làm nội dung tài liệu).
MAX_EXCERPT_CHARS = 400


class WarehouseAdapter:
    """Truy hồi bằng chứng từ kho ELT theo hợp đồng adapter nguồn của graph."""

    def __init__(
        self,
        *,
        name: str,
        engine: Engine,
        settings: Settings,
        drug: str = "",
        event: str = "",
        max_documents: int = 5,
    ) -> None:
        self.name = name
        self.engine = engine
        self.settings = settings
        self.drug = drug
        self.event = event
        self.max_documents = max(1, max_documents)

    def _query(self, action: Any) -> str:
        query = (action.query or "").strip()
        if query:
            return query
        # Planner luôn gửi câu truy vấn; đường lùi này chỉ để không bao giờ truy vấn rỗng.
        fallback = " ".join(part for part in (self.drug, self.event) if part).strip()
        return fallback or "tài liệu kho"

    def search(self, action: Any, budget: Any) -> SourceSearchResult:  # noqa: ANN401 - BudgetState
        query = self._query(action)
        fingerprint = action.fingerprint or query_fingerprint(self.name, query)
        try:
            result = rag_search(self.engine, query, k=self.max_documents, source=self.name, settings=self.settings)
        except DomainError as exc:
            return SourceSearchResult(
                source=self.name,  # type: ignore[arg-type]
                query=query[:500],
                fingerprint=fingerprint,
                status=SourceStatus.ERROR,
                error=f"{exc.code}: {exc.message}"[:1000],
                retryable=False,
            )

        ranked: list[tuple[str, dict]] = []
        seen: set[str] = set()
        for hit in result["hits"]:
            document = hit.get("document") or {}
            doc_id = document.get("doc_id") or str(hit.get("chunk_id", "")).split("#")[0]
            # Chỉ nhận bản ghi còn trong PostgreSQL: chỉ mục có thể chứa tài liệu đã rời kho.
            if not doc_id or doc_id in seen or not hit.get("in_postgres"):
                continue
            seen.add(doc_id)
            ranked.append((doc_id, hit))

        rows = {row["doc_id"]: row for row in documents_by_ids(self.engine, [doc_id for doc_id, _ in ranked])}
        documents = [self._to_document(rows[doc_id], hit, query) for doc_id, hit in ranked if doc_id in rows]
        return SourceSearchResult(
            source=self.name,  # type: ignore[arg-type]
            query=query[:500],
            fingerprint=fingerprint,
            status=SourceStatus.OK if documents else SourceStatus.EMPTY,
            documents=documents,
            requests_used=0,
        )

    def _to_document(self, row: dict, hit: dict, query: str) -> SourceDocument:
        text = row.get("text") or ""
        metadata = {
            "retrieval_method": "warehouse_rag",
            "retrieval_query": query[:300],
            "retrieval_score": hit.get("score"),
            "chunk_id": hit.get("chunk_id"),
            "chunk_char_start": hit.get("char_start"),
            "chunk_char_end": hit.get("char_end"),
            "matched_excerpt": (hit.get("text") or "")[:MAX_EXCERPT_CHARS],
            "quality_status": row.get("quality_status"),
            "quality_flags": list(row.get("quality_flags") or []),
            "content_level": row.get("content_level"),
            "pair_id": row.get("pair_id"),
            "sections": row.get("sections") or [],
            "in_warehouse": True,
        }
        return SourceDocument(
            doc_id=str(row["doc_id"])[:120],
            source=row["source"],
            source_id=str(row["source_id"])[:200],
            version=int(row.get("version") or 1),
            title=str(row.get("title") or "")[:500],
            source_url=str(row.get("source_url") or "")[:1000],
            text=text,
            hash=str(row.get("text_sha256") or hashlib.sha256(text.encode("utf-8")).hexdigest()),
            metadata=metadata,
        )


def build_warehouse_adapters(
    *,
    engine: Engine,
    settings: Settings,
    drug: str = "",
    event: str = "",
    max_documents: int = 5,
) -> dict[str, WarehouseAdapter]:
    """Bộ adapter cho cả ba nguồn, dùng chung một kết nối kho và cấu hình RAG."""
    return {
        source: WarehouseAdapter(
            name=source,
            engine=engine,
            settings=settings,
            drug=drug,
            event=event,
            max_documents=max_documents,
        )
        for source in SOURCE_PRIORITY
    }
