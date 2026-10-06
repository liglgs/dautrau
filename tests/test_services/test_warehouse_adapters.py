"""Kiểm thử adapter kho ELT (chế độ ``mvp_source_mode=warehouse``) và luồng graph.

Chạy ngoại tuyến: SQLite tạm, ChromaDB tạm, bộ nhúng ``hash``. Không gọi mạng.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.elt.load_pg import load_documents, load_pairs
from src.config import get_settings
from src.models.schemas import (
    ClaimInput,
    EvidenceScope,
    EvidenceUnit,
    NormalizedClaim,
    PlannerDecision,
    QuoteLocator,
    RunStatus,
    SourceDocument,
    Stance,
)
from src.services.rag.build import build_index
from src.services.sources.warehouse import WarehouseAdapter, build_warehouse_adapters
from src.services.warehouse.db import create_schema, get_warehouse_engine
from src.services.warehouse.queries import documents_by_ids

PAIR = {
    "pair_id": "ibuprofen__gastrointestinal-haemorrhage",
    "drug": "ibuprofen",
    "drug_ingredient": "ibuprofen",
    "event": "Gastrointestinal haemorrhage",
    "pubmed_pmids": ["1"],
    "dailymed_setids": [],
    "faers_report_ids": [],
}

PUBMED_TEXT = (
    "Ibuprofen and gastrointestinal haemorrhage in older adults: a cohort study.\n\n"
    "Among adults aged over 65, high-dose ibuprofen was associated with a higher rate of "
    "gastrointestinal haemorrhage than low-dose use.\n\n"
    "The association persisted after adjustment for aspirin and anticoagulant use.\n"
)
DAILYMED_TEXT = (
    "Ibuprofen label, section 5.1.\n\n"
    "Gastrointestinal haemorrhage, sometimes fatal, can occur without warning symptoms.\n"
)
FAERS_TEXT = "Spontaneous report: gastrointestinal haemorrhage after ibuprofen in a 71-year-old patient.\n"


def _settings_for(tmp_path: Path):
    return get_settings().model_copy(
        update={
            "elt_database_url": f"sqlite:///{tmp_path / 'warehouse.db'}",
            "rag_chroma_dir": str(tmp_path / "chroma"),
            "rag_embedding_provider": "hash",
            "rag_enabled": True,
            "rag_collection": "test_adapters",
            "mvp_source_mode": "warehouse",
            "mvp_source_max_documents": 5,
        }
    )


def _doc(doc_id: str, source: str, text: str, content_level: str = "abstract_only", flags: list[str] | None = None):
    from scripts.elt.parse import ParsedDocument

    return ParsedDocument(
        doc_id=doc_id,
        source=source,
        source_id=doc_id.split(":")[1],
        version=int(doc_id.split(":")[2]),
        title=f"Tài liệu {doc_id}",
        text=text,
        text_sha256="c" * 64,
        source_url=f"https://example.test/{doc_id}",
        content_level=content_level,
        metadata={},
        sections=[{"title": "Abstract", "start": 0, "end": len(text)}],
        pair_id=PAIR["pair_id"],
        raw_sha256="d" * 64,
        raw_path="",
        structured={"has_abstract": True, "journal": "JAMA", "quality_flags": flags or []},
    )


@pytest.fixture()
def warehouse(tmp_path: Path):
    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    documents = [
        _doc("pubmed:1:1", "pubmed", PUBMED_TEXT),
        _doc("dailymed:2:1", "dailymed", DAILYMED_TEXT, content_level="label_sections"),
        _doc("faers:3:1", "faers", FAERS_TEXT, content_level="spontaneous_report"),
    ]
    load_documents(engine, "run-adapters", documents, {})
    load_pairs(engine, {"pairs": [PAIR]})
    build_index(engine, run_id="run-adapters", settings=settings)
    return engine, settings


def _decision(source: str, query: str) -> PlannerDecision:
    return PlannerDecision(
        action="search_source",
        source=source,
        query=query,
        fingerprint="",
        reason="kiểm thử adapter kho",
    )


@pytest.mark.needs_chroma
def test_documents_by_ids_returns_full_text_in_input_order(warehouse) -> None:
    engine, _ = warehouse

    rows = documents_by_ids(engine, ["dailymed:2:1", "khong:ton:tai", "pubmed:1:1"])

    assert [row["doc_id"] for row in rows] == ["dailymed:2:1", "pubmed:1:1"]
    assert rows[0]["text"] == DAILYMED_TEXT
    assert rows[1]["text"] == PUBMED_TEXT
    assert rows[0]["sections"] == [{"title": "Abstract", "start": 0, "end": len(DAILYMED_TEXT)}]
    assert documents_by_ids(engine, []) == []


@pytest.mark.needs_chroma
def test_adapter_returns_full_documents_ranked_by_the_rag_index(warehouse) -> None:
    engine, settings = warehouse
    adapter = WarehouseAdapter(name="pubmed", engine=engine, settings=settings, drug="ibuprofen", event="haemorrhage")

    result = adapter.search(_decision("pubmed", "ibuprofen gastrointestinal haemorrhage"), budget=None)

    assert result.status.value == "ok"
    assert result.requests_used == 0, "truy hồi cục bộ không tiêu tốn request nguồn"
    assert len(result.documents) == 1
    document = result.documents[0]
    assert document.source == "pubmed"
    assert document.doc_id == "pubmed:1:1"
    # Toàn văn từ PostgreSQL, không phải đoạn rút gọn của chỉ mục.
    assert document.text == PUBMED_TEXT
    assert "adjustment for aspirin" in document.text
    assert document.hash == "c" * 64
    assert document.metadata["retrieval_method"] == "warehouse_rag"
    assert document.metadata["chunk_id"].startswith("pubmed:1:1#")
    assert document.metadata["matched_excerpt"]
    assert document.metadata["in_warehouse"] is True


@pytest.mark.needs_chroma
def test_adapter_is_empty_when_the_source_has_no_documents(tmp_path: Path) -> None:
    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    load_documents(engine, "run-pubmed-only", [_doc("pubmed:1:1", "pubmed", PUBMED_TEXT)], {})
    build_index(engine, run_id="run-pubmed-only", settings=settings)
    adapter = WarehouseAdapter(name="faers", engine=engine, settings=settings)

    result = adapter.search(_decision("faers", "ibuprofen haemorrhage"), budget=None)

    assert result.documents == []
    assert result.status.value == "empty"


def test_missing_index_is_a_source_error_not_a_crash(tmp_path: Path) -> None:
    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    adapter = WarehouseAdapter(name="pubmed", engine=engine, settings=settings)

    result = adapter.search(_decision("pubmed", "ibuprofen"), budget=None)

    assert result.status.value == "error"
    assert "RAG_INDEX_MISSING" in (result.error or "")
    assert result.documents == []


@pytest.mark.needs_chroma
def test_build_warehouse_adapters_covers_all_sources(warehouse) -> None:
    engine, settings = warehouse

    adapters = build_warehouse_adapters(engine=engine, settings=settings, drug="ibuprofen", event="haemorrhage")

    assert set(adapters) == {"pubmed", "dailymed", "faers"}
    assert all(adapter.max_documents >= 1 for adapter in adapters.values())


class _QuoteExtractor:
    """Extractor tối giản: trích câu chứa hoạt chất làm bằng chứng ủng hộ (như node Người 3)."""

    def __init__(self, needle: str) -> None:
        self.needle = needle
        self.seen: list[str] = []

    def extract_evidence(self, document: SourceDocument, claim: NormalizedClaim) -> list[EvidenceUnit]:
        self.seen.append(document.doc_id)
        for sentence in document.text.split("\n\n"):
            if self.needle.casefold() in sentence.casefold():
                quote = sentence.strip()
                start = document.text.find(quote)
                return [
                    EvidenceUnit(
                        evidence_id=f"EVI-{document.source.upper()}-1",
                        doc_id=document.doc_id,
                        source=document.source,
                        stance=Stance.SUPPORTS,
                        quote=quote,
                        locator=QuoteLocator(start=start, end=start + len(quote), section="abstract"),
                        scope=EvidenceScope(study_type="cohort"),
                    )
                ]
        return []


@pytest.mark.needs_chroma
def test_graph_run_in_warehouse_mode_stores_warehouse_documents(warehouse, tmp_path, monkeypatch) -> None:
    from src.agents.graph import run_investigation
    from src.services.runner import InProcessRunner
    from src.services.store import MvpStore

    engine, settings = warehouse
    monkeypatch.setattr("src.config.get_settings", lambda: settings)

    store = MvpStore(str(tmp_path / "mvp.db"))
    runner = InProcessRunner(store, executor=run_investigation)
    state, _ = store.create_investigation(
        ClaimInput(
            claim_text="ibuprofen gây xuất huyết tiêu hoá ở người cao tuổi.",
            drug="ibuprofen",
            event="gastrointestinal haemorrhage",
        )
    )

    context = runner.context()
    assert context.source_factory is not None, "chế độ warehouse phải cắm factory adapter kho"
    extractor = _QuoteExtractor("ibuprofen")
    context.extractor = extractor

    result = run_investigation(store.get_state(state.investigation_id), context)

    assert result.run_status is RunStatus.WAITING_FOR_REVIEW
    assert result.documents, "graph phải nhận tài liệu từ kho"
    assert {document.source for document in result.documents} <= {"pubmed", "dailymed", "faers"}
    assert all(document.metadata.get("retrieval_method") == "warehouse_rag" for document in result.documents)
    for document in result.documents:
        stored = store.get_document(state.investigation_id, document.doc_id)
        assert stored is not None and stored.hash == document.hash
    assert extractor.seen, "extractor phải nhận tài liệu kho"
    assert result.active_evidence(), "phải có bằng chứng trích từ tài liệu kho"
    assert any(gap.kind.value == "missing_source" for gap in result.gaps) or result.assessment_status is not None


def test_graph_records_a_gap_when_the_index_is_missing(tmp_path: Path, monkeypatch) -> None:
    from src.agents.graph import run_investigation
    from src.services.runner import InProcessRunner
    from src.services.store import MvpStore

    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    monkeypatch.setattr("src.config.get_settings", lambda: settings)

    store = MvpStore(str(tmp_path / "mvp-missing.db"))
    runner = InProcessRunner(store, executor=run_investigation)
    state, _ = store.create_investigation(
        ClaimInput(
            claim_text="ibuprofen gây xuất huyết tiêu hoá.",
            drug="ibuprofen",
            event="gastrointestinal haemorrhage",
        )
    )

    result = run_investigation(store.get_state(state.investigation_id), runner.context())

    assert result.documents == []
    assert result.run_status in {RunStatus.WAITING_FOR_REVIEW, RunStatus.COMPLETED}
    assert any(gap.kind.value in {"missing_source", "no_results"} for gap in result.gaps)
