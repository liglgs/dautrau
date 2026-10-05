"""Kiểm thử API kho ELT/RAG (``src/api/warehouse_routes.py``).

Chạy hoàn toàn ngoại tuyến: kho là SQLite tạm, bộ nhúng là ``hash``, ChromaDB ghi vào thư mục tạm.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.config import get_settings
from src.services.warehouse.db import get_warehouse_engine

INVESTIGATOR = {"X-API-Token": "inv-token"}
REVIEWER = {"X-API-Token": "rev-token"}

PAIR = {
    "pair_id": "ibuprofen__gastrointestinal-haemorrhage",
    "drug": "ibuprofen",
    "drug_ingredient": "ibuprofen",
    "event": "Gastrointestinal haemorrhage",
    "pubmed_pmids": ["39466269"],
    "dailymed_setids": ["1662a495-4f6a-4515-a405-557681e1a496"],
    "faers_report_ids": ["10006463"],
}


@pytest_asyncio.fixture
async def warehouse_client(monkeypatch, tmp_path: Path):
    from scripts.elt.load_pg import load_documents, load_pairs
    from scripts.elt.parse import ParsedDocument
    from scripts.elt.quality import evaluate_document
    from src.main import app
    from src.services.rag.build import build_index
    from src.services.warehouse.db import create_schema, get_warehouse_engine

    monkeypatch.setenv("INVESTIGATOR_TOKEN", "inv-token")
    monkeypatch.setenv("REVIEWER_TOKEN", "rev-token")
    monkeypatch.setenv("ELT_DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("RAG_CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("RAG_COLLECTION", "api_test_docs")
    monkeypatch.setenv("RAG_ENABLED", "true")
    get_settings.cache_clear()
    get_warehouse_engine.cache_clear()

    engine = get_warehouse_engine()
    create_schema(engine)
    load_pairs(engine, {"pairs": [PAIR]})
    docs = [
        ParsedDocument(
            doc_id="pubmed:39466269:1", source="pubmed", source_id="39466269", version=1,
            title="Peptic Ulcer Disease: A Review.",
            text="Fluoroquinolone and NSAID related gastrointestinal haemorrhage risk in older adults.",
            text_sha256="a" * 64, source_url="https://pubmed.ncbi.nlm.nih.gov/39466269/",
            content_level="abstract_only", metadata={},
            sections=[{"title": "Abstract", "start": 0, "end": 60}],
            pair_id=PAIR["pair_id"], raw_sha256="b" * 64, raw_path="",
            structured={"pmid": "39466269", "journal": "JAMA", "has_abstract": True, "doi": ["10.1/x"]},
        )
    ]
    load_documents(engine, "run-api", docs, {doc.doc_id: evaluate_document(doc) for doc in docs})
    build_index(engine, run_id="run-api", settings=get_settings())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    get_settings.cache_clear()
    get_warehouse_engine.cache_clear()


@pytest.mark.asyncio
async def test_warehouse_requires_token(warehouse_client) -> None:
    assert (await warehouse_client.get("/api/v1/warehouse/overview")).status_code == 401
    assert (
        await warehouse_client.get("/api/v1/warehouse/overview", headers={"X-API-Token": "sai"})
    ).status_code == 401


@pytest.mark.asyncio
async def test_drug_lookup_from_warehouse(warehouse_client) -> None:
    response = await warehouse_client.get("/api/v1/drugs/lookup?name=IBUPROFEN", headers=INVESTIGATOR)
    assert response.status_code == 200
    payload = response.json()
    assert payload["matched"] is True
    assert payload["origin"] == "warehouse"
    assert payload["drugs"][0]["name"] == "ibuprofen"
    assert payload["pairs"][0]["pair_id"] == PAIR["pair_id"]
    assert payload["documents"] == {"pubmed": 1}

    missing = await warehouse_client.get("/api/v1/drugs/lookup?name=khong-co-thuoc-nay", headers=INVESTIGATOR)
    assert missing.status_code == 200
    assert missing.json()["matched"] is False


@pytest.mark.asyncio
async def test_overview_documents_and_detail(warehouse_client) -> None:
    overview = await warehouse_client.get("/api/v1/warehouse/overview", headers=INVESTIGATOR)
    assert overview.status_code == 200
    body = overview.json()
    assert body["documents_by_quality_status"] == {"keep": 1}
    assert body["table_counts"]["documents"] == 1
    assert body["rag"]["embedding_provider"] == "hash"

    listing = await warehouse_client.get("/api/v1/warehouse/documents?source=pubmed", headers=INVESTIGATOR)
    assert listing.status_code == 200
    assert [item["doc_id"] for item in listing.json()["documents"]] == ["pubmed:39466269:1"]

    detail = await warehouse_client.get(
        "/api/v1/warehouse/documents/pubmed:39466269:1", headers=INVESTIGATOR
    )
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["title"] == "Peptic Ulcer Disease: A Review."
    assert payload["pubmed"]["journal"] == "JAMA"
    assert "gastrointestinal" in payload["text_preview"].lower()

    absent = await warehouse_client.get("/api/v1/warehouse/documents/pubmed:1:1", headers=INVESTIGATOR)
    assert absent.status_code == 404


@pytest.mark.asyncio
async def test_rag_search_endpoint(warehouse_client) -> None:
    response = await warehouse_client.post(
        "/api/v1/rag/search", headers=INVESTIGATOR, json={"query": "gastrointestinal haemorrhage", "k": 3}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["hits"], "phải có ít nhất một đoạn khớp"
    hit = payload["hits"][0]
    assert hit["document"]["doc_id"] == "pubmed:39466269:1"
    assert hit["in_postgres"] is True
    assert 0.0 <= hit["score"] <= 1.0

    empty = await warehouse_client.post("/api/v1/rag/search", headers=INVESTIGATOR, json={"query": ""})
    assert empty.status_code == 422


@pytest.mark.asyncio
async def test_ingestion_requires_reviewer_and_records_event(warehouse_client) -> None:
    body = {
        "source": "manual",
        "source_id": "ghi-chu-api-1",
        "version": 1,
        "title": "Ghi chú kiểm thử API",
        "text": "Cảnh báo hạ magnesi khi dùng thuốc ức chế bơm proton kéo dài (kiểm thử API).",
        "metadata": {"purpose": "test"},
    }
    denied = await warehouse_client.post("/api/v1/ingestion/documents", headers=INVESTIGATOR, json=body)
    assert denied.status_code == 403

    created = await warehouse_client.post("/api/v1/ingestion/documents", headers=REVIEWER, json=body)
    assert created.status_code in (200, 201)
    payload = created.json()
    assert payload["doc_id"] == "manual:ghi-chu-api-1:1"
    assert payload["created"] is True
    assert payload["rag"]["indexed"] is True

    conflict = await warehouse_client.post(
        "/api/v1/ingestion/documents",
        headers=REVIEWER,
        json={**body, "text": "Nội dung khác hoàn toàn nhưng vẫn đủ dài cho cùng một định danh tài liệu."},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "INGEST_CONFLICT"

    short = await warehouse_client.post(
        "/api/v1/ingestion/documents", headers=REVIEWER, json={**body, "source_id": "ghi-chu-api-2", "text": "ngắn"}
    )
    assert short.status_code == 422

    events = await warehouse_client.get("/api/v1/ingestion/events", headers=INVESTIGATOR)
    assert events.status_code == 200
    kinds = [event["kind"] for event in events.json()["events"]]
    assert "manual_document" in kinds


@pytest.mark.asyncio
async def test_warehouse_unavailable_returns_503(monkeypatch, tmp_path: Path) -> None:
    from src.main import app

    monkeypatch.setenv("INVESTIGATOR_TOKEN", "inv-token")
    monkeypatch.setenv("ELT_DATABASE_URL", "postgresql+psycopg://khong:khong@127.0.0.1:1/khong")
    get_settings.cache_clear()
    get_warehouse_engine.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/warehouse/overview", headers=INVESTIGATOR)
    get_settings.cache_clear()
    get_warehouse_engine.cache_clear()
    assert response.status_code == 503
    assert response.json()["code"] == "WAREHOUSE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_drug_lookup_falls_back_to_static_dictionary(monkeypatch, tmp_path: Path) -> None:
    """Kho chưa chạy thì tra cứu thuốc vẫn trả về từ điển tĩnh, không vỡ giao diện."""
    from src.main import app

    monkeypatch.setenv("INVESTIGATOR_TOKEN", "inv-token")
    monkeypatch.setenv("ELT_DATABASE_URL", "postgresql+psycopg://khong:khong@127.0.0.1:1/khong")
    get_settings.cache_clear()
    get_warehouse_engine.cache_clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/drugs/lookup?name=ibuprofen", headers=INVESTIGATOR)
    get_settings.cache_clear()
    get_warehouse_engine.cache_clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["origin"] == "dictionary"
    assert payload["matched"] is True
    assert any(drug["name"] == "ibuprofen" for drug in payload["drugs"])
