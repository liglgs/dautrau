"""Kiểm thử lớp truy vấn đọc của kho ELT (``src/services/warehouse/queries.py``).

Chạy hoàn toàn ngoại tuyến: kho là tệp SQLite trong ``tmp_path``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.elt.load_pg import load_documents, load_findings, load_pairs
from scripts.elt.quality import Finding
from src.services.warehouse.db import create_schema, get_warehouse_engine
from src.services.warehouse.ingest import ingest_document
from src.services.warehouse.queries import (
    document_detail,
    ingestion_events,
    list_documents,
    lookup_drug,
    normalize_name,
    warehouse_overview,
)

PAIR = {
    "pair_id": "ibuprofen__gastrointestinal-haemorrhage",
    "drug": "ibuprofen",
    "drug_ingredient": "ibuprofen",
    "event": "Gastrointestinal haemorrhage",
    "pubmed_pmids": ["39466269"],
    "dailymed_setids": ["1662a495-4f6a-4515-a405-557681e1a496"],
    "faers_report_ids": ["10006463"],
}

# Cặp thứ hai để kiểm tra lọc theo ``pair_id`` và tìm kiếm theo tên khác.
PAIR_B = {
    "pair_id": "pantoprazole__hypomagnesaemia",
    "drug": "pantoprazole",
    "drug_ingredient": "pantoprazole",
    "event": "Hypomagnesaemia",
    "pubmed_pmids": [],
    "dailymed_setids": [],
    "faers_report_ids": [],
}


def _settings_for(tmp_path: Path):
    from src.config import get_settings

    return get_settings().model_copy(
        update={
            "elt_database_url": f"sqlite:///{tmp_path / 'warehouse.db'}",
            "rag_chroma_dir": str(tmp_path / "chroma"),
            "rag_embedding_provider": "hash",
            "rag_enabled": True,
            "rag_collection": "test_docs",
        }
    )


@pytest.fixture()
def warehouse(tmp_path: Path):
    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    return engine, settings


def _doc(doc_id: str, source: str, text: str, **extra):
    from scripts.elt.parse import ParsedDocument

    base = dict(
        doc_id=doc_id,
        source=source,
        source_id=doc_id.split(":")[1],
        version=int(doc_id.split(":")[2]),
        title=f"Tài liệu {doc_id}",
        text=text,
        text_sha256="c" * 64,
        source_url="",
        content_level="abstract_only",
        metadata={},
        sections=[{"title": "Abstract", "start": 0, "end": len(text)}],
        pair_id=PAIR["pair_id"],
        raw_sha256="d" * 64,
        raw_path="",
        structured={"has_abstract": True, "journal": "JAMA"},
    )
    base.update(extra)
    return ParsedDocument(**base)


def _load(engine, docs) -> None:
    """Nạp tài liệu với quyết định "keep" (bài kiểm thử này chỉ quan tâm lớp truy vấn đọc)."""
    load_documents(engine, "run-queries", docs, {})
    load_pairs(engine, {"pairs": [PAIR, PAIR_B]})


def _add_run(engine, run_id: str, started_at) -> None:
    from src.services.warehouse.models import EltRun

    with engine.begin() as conn:
        conn.execute(
            EltRun.__table__.insert().values(
                run_id=run_id,
                profile="all",
                status="loaded",
                started_at=started_at,
                stats={},
            )
        )


TEXT = (
    "Ibuprofen làm tăng nguy cơ xuất huyết tiêu hoá ở người cao tuổi, đặc biệt khi dùng "
    "cùng thuốc chống viêm steroid hoặc thuốc chống đông. "
) * 12


def test_normalize_name_collapses_spaces_and_case() -> None:
    assert normalize_name("  IbuPROFEN   Viên nén ") == "ibuprofen viên nén"
    assert normalize_name(None) == ""


def test_lookup_drug_matches_name_and_ingredient_with_documents(warehouse) -> None:
    engine, _ = warehouse
    _load(engine, [_doc("pubmed:39466269:1", "pubmed", TEXT)])

    payload = lookup_drug(engine, "IBUPROFEN")

    assert payload["matched"] is True
    assert payload["query"] == "IBUPROFEN"
    assert [d["name"] for d in payload["drugs"]] == ["ibuprofen"]
    assert payload["drugs"][0]["ingredient"] == "ibuprofen"
    assert [p["pair_id"] for p in payload["pairs"]] == [PAIR["pair_id"]]
    # Chỉ tài liệu đạt chất lượng (keep) của cặp thuốc–biến cố mới được đếm.
    assert payload["documents"] == {"pubmed": 1}


def test_lookup_drug_returns_empty_result_for_unknown_name(warehouse) -> None:
    engine, _ = warehouse
    _load(engine, [_doc("pubmed:39466269:1", "pubmed", TEXT)])

    payload = lookup_drug(engine, "thuốc-không-tồn-tại")

    assert payload["matched"] is False
    assert payload["drugs"] == [] and payload["pairs"] == [] and payload["documents"] == {}


def test_lookup_drug_with_blank_query_does_not_touch_the_database(warehouse) -> None:
    engine, _ = warehouse
    _load(engine, [_doc("pubmed:39466269:1", "pubmed", TEXT)])

    payload = lookup_drug(engine, "   ")

    assert payload["matched"] is False
    assert payload["documents"] == {}


def test_overview_scopes_quality_findings_to_the_latest_run(warehouse) -> None:
    engine, _ = warehouse
    docs = [_doc("pubmed:39466269:1", "pubmed", TEXT)]
    _load(engine, docs)

    def finding(check_name: str, severity: str, detail: str) -> Finding:
        return Finding(
            doc_id="pubmed:39466269:1",
            pair_id=PAIR["pair_id"],
            source="pubmed",
            check_name=check_name,
            severity=severity,
            decision="keep",
            detail=detail,
        )

    _add_run(engine, "run-cu", datetime(2026, 10, 4, 8, 0, tzinfo=UTC))
    _add_run(engine, "run-moi", datetime(2026, 10, 5, 8, 0, tzinfo=UTC))
    load_findings(engine, "run-cu", [finding("missing_doi", "info", "cũ")])
    load_findings(
        engine, "run-moi", [finding("missing_doi", "info", "mới"), finding("missing_abstract", "warn", "mới")]
    )

    overview = warehouse_overview(engine)

    assert overview["documents_by_source"][0]["source"] == "pubmed"
    assert overview["documents_by_source"][0]["documents"] == 1
    assert overview["documents_by_source"][0]["by_content_level"] == {"abstract_only": 1}
    assert overview["documents_by_quality_status"] == {"keep": 1}
    assert overview["quality_findings_run_id"] == "run-moi"
    counts = {(f["check_name"], f["severity"]): f["count"] for f in overview["quality_findings"]}
    assert counts == {("missing_doi", "info"): 1, ("missing_abstract", "warn"): 1}


def test_list_documents_filters_and_caps_the_limit(warehouse) -> None:
    engine, _ = warehouse
    _load(
        engine,
        [
            _doc("pubmed:39466269:1", "pubmed", TEXT),
            _doc("dailymed:1662a495:2", "dailymed", TEXT, content_level="label_sections"),
            _doc("faers:10006463:1", "faers", TEXT, content_level="spontaneous_report", pair_id=PAIR_B["pair_id"]),
        ],
    )

    assert {d["doc_id"] for d in list_documents(engine)} == {
        "pubmed:39466269:1",
        "dailymed:1662a495:2",
        "faers:10006463:1",
    }
    assert [d["doc_id"] for d in list_documents(engine, source="faers")] == ["faers:10006463:1"]
    assert [d["doc_id"] for d in list_documents(engine, pair_id=PAIR["pair_id"])] == [
        "dailymed:1662a495:2",
        "pubmed:39466269:1",
    ]
    assert list_documents(engine, quality_status="reject") == []
    assert len(list_documents(engine, limit=2)) == 2
    assert len(list_documents(engine, limit=0)) == 1  # sàn là 1


def test_document_detail_exposes_source_specific_payload(warehouse) -> None:
    engine, _ = warehouse
    _load(
        engine,
        [
            _doc("pubmed:39466269:1", "pubmed", TEXT),
            _doc(
                "dailymed:1662a495:2",
                "dailymed",
                TEXT,
                content_level="label_sections",
                source_url="https://dailymed.nlm.nih.gov/x",
                structured={
                    "setid": "1662a495",
                    "effective_time": "2024-09-19",
                    "published_date": "2026-09-29",
                    "routes": ["ORAL"],
                    "ingredients": ["ibuprofen"],
                    "n_sections": 7,
                },
            ),
            _doc(
                "faers:10006463:1",
                "faers",
                TEXT,
                content_level="spontaneous_report",
                structured={
                    "safetyreportid": "10006463",
                    "receivedate": "20250101",
                    "serious": "serious",
                    "patient_age": 71,
                    "patient_sex": "F",
                    "n_drugs": 3,
                    "n_reactions": 2,
                    "reactions": [{"term": "Gastrointestinal haemorrhage", "outcome": "hospitalised"}],
                    "matched_drugs": [{"medicinalproduct": "IBUPROFEN"}],
                },
            ),
        ],
    )

    pubmed = document_detail(engine, "pubmed:39466269:1")
    assert pubmed is not None
    assert pubmed["pubmed"]["journal"] == "JAMA"
    assert pubmed["pubmed"]["has_abstract"] is True
    assert pubmed["sections"] == [{"title": "Abstract", "start": 0, "end": len(TEXT)}]

    dailymed = document_detail(engine, "dailymed:1662a495:2")
    assert dailymed is not None
    assert dailymed["dailymed"]["routes"] == ["ORAL"]
    assert dailymed["dailymed"]["n_sections"] == 7

    faers = document_detail(engine, "faers:10006463:1")
    assert faers is not None
    assert faers["faers"]["reactions"] == [{"term": "Gastrointestinal haemorrhage", "outcome": "hospitalised"}]
    assert faers["faers"]["matched_drugs"] == [{"medicinalproduct": "IBUPROFEN"}]

    assert document_detail(engine, "khong:ton:tai") is None


def test_ingestion_events_are_newest_first_and_respect_the_limit(warehouse) -> None:
    engine, settings = warehouse
    for index in range(3):
        ingest_document(
            engine,
            source="manual",
            source_id=f"ghi-chu-{index}",
            version=1,
            title=f"Ghi chú {index}",
            text=TEXT + str(index),
            settings=settings,
        )

    events = ingestion_events(engine)
    assert [e["title"] for e in events] == [
        "Nạp tài liệu manual:ghi-chu-2:1",
        "Nạp tài liệu manual:ghi-chu-1:1",
        "Nạp tài liệu manual:ghi-chu-0:1",
    ]
    assert len(ingestion_events(engine, limit=2)) == 2
    assert len(ingestion_events(engine, limit=0)) == 1  # sàn là 1
    assert all(e["kind"] == "manual_document" for e in events)
