"""Kiểm thử biên cho truy vấn RAG (``src/services/rag/search.py``).

Chạy ngoại tuyến: SQLite tạm, bộ nhúng ``hash`` và ChromaDB trong thư mục tạm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.elt.load_pg import load_documents, load_pairs
from src.config import get_settings
from src.services.rag.build import build_index
from src.services.rag.search import search
from src.services.warehouse.db import create_schema, get_warehouse_engine
from src.vmec import DomainError

PAIR = {
    "pair_id": "ibuprofen__gastrointestinal-haemorrhage",
    "drug": "ibuprofen",
    "drug_ingredient": "ibuprofen",
    "event": "Gastrointestinal haemorrhage",
    "pubmed_pmids": ["1"],
    "dailymed_setids": [],
    "faers_report_ids": [],
}
PAIR_B = {
    "pair_id": "metformin__diarrhoea",
    "drug": "metformin",
    "drug_ingredient": "metformin",
    "event": "Diarrhoea",
    "pubmed_pmids": ["2"],
    "dailymed_setids": [],
    "faers_report_ids": [],
}

PUBMED_TEXT = "Fluoroquinolone use and risk of aortic aneurysm in older adults: a cohort study."
DAILYMED_TEXT = "Metformin associated diarrhoea in type 2 diabetes patients is usually transient."
FAERS_TEXT = "Spontaneous report of gastrointestinal haemorrhage after high dose ibuprofen."


def _settings_for(tmp_path: Path):
    return get_settings().model_copy(
        update={
            "elt_database_url": f"sqlite:///{tmp_path / 'warehouse.db'}",
            "rag_chroma_dir": str(tmp_path / "chroma"),
            "rag_embedding_provider": "hash",
            "rag_enabled": True,
            "rag_collection": "test_search",
        }
    )


@pytest.fixture()
def warehouse(tmp_path: Path):
    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    return engine, settings


def _doc(doc_id: str, source: str, text: str, pair_id: str, content_level: str = "abstract_only"):
    from scripts.elt.parse import ParsedDocument

    return ParsedDocument(
        doc_id=doc_id,
        source=source,
        source_id=doc_id.split(":")[1],
        version=int(doc_id.split(":")[2]),
        title=f"Tài liệu {doc_id}",
        text=text,
        text_sha256="c" * 64,
        source_url="",
        content_level=content_level,
        metadata={},
        sections=[{"title": "Abstract", "start": 0, "end": len(text)}],
        pair_id=pair_id,
        raw_sha256="d" * 64,
        raw_path="",
        structured={"has_abstract": True, "journal": "JAMA"},
    )


@pytest.fixture()
def indexed_warehouse(warehouse):
    engine, settings = warehouse
    docs = [
        _doc("pubmed:1:1", "pubmed", PUBMED_TEXT, PAIR["pair_id"]),
        _doc("dailymed:2:1", "dailymed", DAILYMED_TEXT, PAIR_B["pair_id"], content_level="label_sections"),
        _doc("faers:3:1", "faers", FAERS_TEXT, PAIR["pair_id"], content_level="spontaneous_report"),
    ]
    load_documents(engine, "run-search", docs, {})
    load_pairs(engine, {"pairs": [PAIR, PAIR_B]})
    build_index(engine, run_id="run-search", settings=settings)
    return engine, settings


def test_blank_query_is_rejected_with_422(indexed_warehouse) -> None:
    engine, settings = indexed_warehouse

    with pytest.raises(DomainError) as error:
        search(engine, "   ", settings=settings)

    assert error.value.status == 422
    assert error.value.code == "RAG_QUERY_EMPTY"


def test_missing_index_returns_404(tmp_path: Path) -> None:
    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)

    with pytest.raises(DomainError) as error:
        search(engine, "ibuprofen", settings=settings)

    assert error.value.status == 404
    assert error.value.code == "RAG_INDEX_MISSING"


def test_k_is_capped_and_hits_carry_document_context(indexed_warehouse) -> None:
    engine, settings = indexed_warehouse

    result = search(engine, "ibuprofen haemorrhage", k=1, settings=settings)

    assert result["k"] == 1
    assert len(result["hits"]) == 1
    hit = result["hits"][0]
    assert -1.0 <= hit["score"] <= 1.0
    assert hit["in_postgres"] is True
    assert hit["document"]["doc_id"] == hit["chunk_id"].split("#")[0]
    assert hit["document"]["source"] in {"pubmed", "dailymed", "faers"}
    assert hit["char_start"] < hit["char_end"]
    assert result["embedding_provider"] == "hash"


def test_source_and_pair_filters_are_applied(indexed_warehouse) -> None:
    engine, settings = indexed_warehouse

    by_source = search(engine, "diarrhoea", k=5, source="dailymed", settings=settings)
    assert by_source["source_filter"] == "dailymed"
    assert by_source["hits"], "bộ lọc nguồn phải còn đoạn phù hợp"
    assert all(hit["document"]["source"] == "dailymed" for hit in by_source["hits"])

    by_pair = search(engine, "haemorrhage", k=5, pair_id=PAIR["pair_id"], settings=settings)
    assert by_pair["pair_id_filter"] == PAIR["pair_id"]
    assert by_pair["hits"]
    assert all(hit["document"]["pair_id"] == PAIR["pair_id"] for hit in by_pair["hits"])

    unmatched = search(engine, "diarrhoea", k=5, pair_id=PAIR["pair_id"], settings=settings)
    assert all(hit["document"]["pair_id"] == PAIR["pair_id"] for hit in unmatched["hits"])
