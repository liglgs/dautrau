"""API kho dữ liệu ELT/RAG cho VigiLens (P-066 vòng 2).

Nhóm endpoint:
  * ``GET  /api/v1/drugs/lookup``            — tra cứu thuốc, cặp thuốc–biến cố, số tài liệu;
  * ``GET  /api/v1/warehouse/overview``      — số liệu kho + chỉ mục RAG;
  * ``GET  /api/v1/warehouse/documents``     — danh sách tài liệu (lọc theo nguồn/trạng thái);
  * ``GET  /api/v1/warehouse/documents/{id}``— chi tiết tài liệu (kèm trích đoạn đầu);
  * ``POST /api/v1/rag/search``              — truy vấn ngữ nghĩa trên ChromaDB;
  * ``GET  /api/v1/ingestion/events``        — nhật ký nạp tài liệu;
  * ``POST /api/v1/ingestion/documents``     — nạp tài liệu thủ công (chỉ reviewer).

Khi PostgreSQL chưa chạy, endpoint tra cứu thuốc tự hạ cấp sang từ điển tĩnh để giao diện
vẫn dùng được; các endpoint kho khác trả 503 kèm mã ``WAREHOUSE_UNAVAILABLE``.

Các hàm xử lý cố ý viết dạng ``def`` (không ``async``) vì chúng gọi thư viện đồng bộ
(SQLAlchemy, ChromaDB, HTTP client của bộ nhúng). FastAPI chạy chúng trong threadpool,
nhờ vậy một truy vấn RAG chậm không chặn vòng lặp sự kiện và không làm treo các yêu cầu
khác (ví dụ ``/health``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from src.api.auth import Principal, require_permission
from src.config import get_settings
from src.services.identity import Permission
from src.services.warehouse import db as wh_db
from src.services.warehouse import queries as wh_queries
from src.services.warehouse.ingest import ingest_document
from src.vmec import DomainError

_log = logging.getLogger(__name__)

router = APIRouter(tags=["mvp", "warehouse"])


# --------------------------------------------------------------------------------------
# Mô hình vào/ra
# --------------------------------------------------------------------------------------


class DrugLookup(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str
    matched: bool
    origin: Literal["warehouse", "dictionary"]
    drugs: list[dict[str, Any]] = Field(default_factory=list)
    pairs: list[dict[str, Any]] = Field(default_factory=list)
    documents: dict[str, int] = Field(default_factory=dict)


class RagSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2000)
    k: int | None = Field(default=None, ge=1, le=50)
    source: Literal["pubmed", "dailymed", "faers", "reference"] | None = None
    pair_id: str | None = None


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=30)
    source_id: str = Field(min_length=1, max_length=200)
    version: int = Field(default=1, ge=1)
    title: str = Field(default="", max_length=500)
    text: str = Field(min_length=1, max_length=200_000)
    source_url: str = Field(default="", max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _engine():
    try:
        engine = wh_db.get_warehouse_engine()
        with engine.connect() as conn:
            from sqlalchemy import text

            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise DomainError(503, "WAREHOUSE_UNAVAILABLE",
                          "Kho ELT (PostgreSQL) chưa sẵn sàng. Chạy: docker compose -f docker-compose.elt.yml up -d --wait") from exc
    return engine


# --------------------------------------------------------------------------------------
# Tra cứu thuốc
# --------------------------------------------------------------------------------------


@router.get("/drugs/lookup", response_model=DrugLookup)
def drugs_lookup(
    name: Annotated[str, Query(min_length=1, max_length=200)],
    user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_READ))],
) -> DrugLookup:
    """Tra cứu thuốc trong kho ELT; hạ cấp sang từ điển tĩnh khi kho chưa sẵn sàng."""
    try:
        engine = _engine()
    except DomainError:
        return _dictionary_lookup(name)
    result = wh_queries.lookup_drug(engine, name)
    if not result["matched"]:
        fallback = _dictionary_lookup(name)
        if fallback.matched:
            return fallback
    return DrugLookup(origin="warehouse", **result)


def _dictionary_lookup(name: str) -> DrugLookup:
    """Tra cứu trong từ điển 5 cặp đã xác minh + gói 50 mẫu (dùng khi chưa có PostgreSQL)."""
    from src.services.evidence.normalize import load_dictionary

    settings = get_settings()
    needle = wh_queries.normalize_name(name)
    try:
        dictionary = load_dictionary(settings.mvp_dictionary_path)
    except Exception as exc:  # noqa: BLE001 - từ điển thiếu thì báo rõ nguyên nhân
        _log.warning("Không đọc được từ điển tĩnh %s: %s", settings.mvp_dictionary_path, exc)
        raise DomainError(503, "WAREHOUSE_UNAVAILABLE",
                          "Không đọc được từ điển tĩnh; kiểm tra tệp từ điển rồi thử lại.") from exc
    drugs = []
    for record in dictionary.get("drugs", []):
        names = [record["canonical"], *record.get("aliases", [])]
        if any(needle in str(value).lower() for value in names if value):
            drugs.append({
                "drug_id": f"drug:{record['canonical']}", "name": record["canonical"],
                "ingredient": record["canonical"], "verified": True, "aliases": list(record.get("aliases", [])),
            })
    pairs = []
    collection_path = Path("data/mvp-candidates-50-2026-10-02/collection.json")
    if collection_path.exists():
        import json

        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        for pair in collection.get("pairs", []):
            if needle and needle in str(pair.get("drug", "")).lower():
                pairs.append({
                    "pair_id": f"{pair['drug']}__{str(pair['event']).lower().replace(' ', '-')}",
                    "drug_name": pair["drug"], "event_term": pair["event"],
                    "status": collection.get("status", "candidate_not_gold"), "source": "bundle",
                })
    return DrugLookup(query=name, matched=bool(drugs or pairs), origin="dictionary",
                      drugs=drugs, pairs=pairs, documents={})


# --------------------------------------------------------------------------------------
# Kho dữ liệu
# --------------------------------------------------------------------------------------


@router.get("/warehouse/overview")
def warehouse_overview(user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_READ))]) -> dict:
    """Số liệu kho ELT: tài liệu theo nguồn, trạng thái chất lượng, phát hiện và chỉ mục RAG."""
    engine = _engine()
    overview = wh_queries.warehouse_overview(engine)
    overview["table_counts"] = wh_db.table_counts(engine)
    try:
        from src.services.rag.build import index_stats

        overview["rag"] = index_stats(engine)
    except Exception as exc:  # noqa: BLE001 - chỉ mục lỗi không chặn trang quản trị
        # Không trả chi tiết nội bộ ra HTTP; chỉ ghi log phía máy chủ.
        _log.warning("index_stats lỗi: %s: %s", exc.__class__.__name__, exc)
        overview["rag"] = {"error": "RAG_INDEX_UNAVAILABLE"}
    return overview


@router.get("/warehouse/documents")
def warehouse_documents(
    user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_READ))],
    source: Annotated[str | None, Query(max_length=30)] = None,
    pair_id: Annotated[str | None, Query(max_length=120)] = None,
    quality_status: Annotated[Literal["keep", "quarantine", "reject"] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict:
    """Danh sách tài liệu trong kho, lọc theo nguồn, cặp thuốc–biến cố hoặc trạng thái chất lượng."""
    engine = _engine()
    documents = wh_queries.list_documents(
        engine, source=source, pair_id=pair_id, quality_status=quality_status, limit=limit
    )
    return {"documents": documents, "count": len(documents)}


@router.get("/warehouse/documents/{doc_id:path}")
def warehouse_document(
    doc_id: str,
    user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_READ))],
    preview_chars: Annotated[int, Query(ge=0, le=4000)] = 600,
) -> dict:
    """Chi tiết một tài liệu, kèm trích đoạn đầu để kiểm tra nhanh."""
    engine = _engine()
    detail = wh_queries.document_detail(engine, doc_id)
    if detail is None:
        raise DomainError(404, "DOCUMENT_NOT_FOUND", f"Không thấy tài liệu {doc_id} trong kho.")
    if preview_chars:
        from sqlalchemy import select

        from src.services.warehouse.db import read_session
        from src.services.warehouse.models import Document

        with read_session(engine) as session:
            row = session.execute(select(Document).where(Document.doc_id == doc_id)).scalar_one()
        detail["text_preview"] = row.text[:preview_chars]
    return detail


# --------------------------------------------------------------------------------------
# RAG
# --------------------------------------------------------------------------------------


@router.post("/rag/search")
def rag_search(
    payload: Annotated[RagSearchRequest, Body()],
    user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_READ))],
) -> dict:
    """Truy vấn ngữ nghĩa trên chỉ mục ChromaDB đã dựng từ kho ELT."""
    engine = _engine()
    from src.services.rag.search import search

    return search(engine, payload.query, k=payload.k, source=payload.source, pair_id=payload.pair_id)


# --------------------------------------------------------------------------------------
# Nạp tài liệu
# --------------------------------------------------------------------------------------


@router.get("/ingestion/events")
def ingestion_events(
    user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_READ))],
    limit: Annotated[int, Query(ge=1, le=200)] = 30,
) -> dict:
    """Nhật ký nạp tài liệu gần nhất (chạy ELT và nạp thủ công)."""
    engine = _engine()
    events = wh_queries.ingestion_events(engine, limit=limit)
    return {"events": events, "count": len(events)}


@router.post("/ingestion/documents")
def ingest_manual_document(
    payload: Annotated[IngestRequest, Body()],
    user: Annotated[Principal, Depends(require_permission(Permission.WAREHOUSE_INGEST))],
) -> dict:
    """Nạp một tài liệu thủ công (chỉ reviewer). Tài liệu đạt cổng rút gọn sẽ vào kho và chỉ mục RAG."""
    engine = _engine()
    return ingest_document(
        engine,
        source=payload.source,
        source_id=payload.source_id,
        version=payload.version,
        title=payload.title,
        text=payload.text,
        source_url=payload.source_url,
        metadata=payload.metadata,
    )
