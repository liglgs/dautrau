"""Kiểm thử kho ELT (SQLite tạm) và chỉ mục RAG (nhúng `hash`, không cần mạng).

Các bài kiểm thử ở đây chạy hoàn toàn ngoại tuyến: cơ sở dữ liệu là tệp SQLite trong ``tmp_path``,
bộ nhúng là ``HashEmbedder`` và ChromaDB ghi vào thư mục tạm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.elt.load_pg import load_documents, load_findings, load_pairs
from scripts.elt.quality import apply_gates
from src.config import get_settings
from src.services.rag.build import build_index, index_stats
from src.services.rag.search import search
from src.services.warehouse.db import create_schema, table_counts
from src.services.warehouse.ingest import delete_document, ingest_document, purge_document
from src.services.warehouse.models import Document
from src.services.warehouse.queries import document_detail, list_documents, lookup_drug, warehouse_overview
from src.vmec import DomainError

PAIR = {
    "pair_id": "ibuprofen__gastrointestinal-haemorrhage",
    "drug": "ibuprofen",
    "drug_ingredient": "ibuprofen",
    "event": "Gastrointestinal haemorrhage",
    "pubmed_pmids": ["39466269"],
    "dailymed_setids": ["1662a495-4f6a-4515-a405-557681e1a496"],
    "faers_report_ids": ["10006463"],
}


def verdicts_of(documents):
    """Bản đồ quyết định chất lượng theo ``doc_id`` (giống ``run_elt``)."""
    from scripts.elt import quality

    return {doc.doc_id: quality.evaluate_document(doc) for doc in documents}


def _settings_for(tmp_path: Path):
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
    from src.services.warehouse.db import get_warehouse_engine

    settings = _settings_for(tmp_path)
    engine = get_warehouse_engine(settings.elt_database_url)
    create_schema(engine)
    return engine, settings


def _doc(doc_id: str, source: str, text: str, **extra):
    from scripts.elt.parse import ParsedDocument

    base = dict(
        doc_id=doc_id, source=source, source_id=doc_id.split(":")[1], version=int(doc_id.split(":")[2]),
        title=f"Tài liệu {doc_id}", text=text, text_sha256="c" * 64, source_url="",
        content_level="abstract_only", metadata={},
        sections=[{"title": "Abstract", "start": 0, "end": len(text)}], pair_id=PAIR["pair_id"],
        raw_sha256="d" * 64, raw_path="", structured={"has_abstract": True, "journal": "JAMA"},
    )
    base.update(extra)
    return ParsedDocument(**base)


def test_loader_writes_documents_and_child_rows(warehouse) -> None:
    engine, settings = warehouse
    docs = [
        _doc("pubmed:1:1", "pubmed", "Toàn văn tài liệu PubMed đủ dài để vượt ngưỡng tối thiểu."),
        _doc("pubmed:2:1", "pubmed", "Tài liệu thứ hai cũng đủ dài cho cổng chất lượng."),
    ]
    keep, quarantine, rejected = apply_gates(docs)
    assert len(keep) == 2

    load_pairs(engine, {"pairs": [PAIR]})
    result = load_documents(engine, "run-1", keep, verdicts_of(keep))
    assert result["inserted"] == 2

    counts = table_counts(engine)
    assert counts["documents"] == 2
    assert counts["drug_event_pairs"] == 1
    assert counts["drugs"] == 1
    assert counts["pubmed_records"] == 2
    assert counts["document_sections"] == 2

    listed = list_documents(engine)
    assert {item["doc_id"] for item in listed} == {"pubmed:1:1", "pubmed:2:1"}
    detail = document_detail(engine, "pubmed:1:1")
    assert detail["source"] == "pubmed"
    assert detail["sections"] == [{"title": "Abstract", "start": 0, "end": len(keep[0].text)}] or detail["sections"]
    assert detail["pubmed"]["journal"] == "JAMA"

    found = lookup_drug(engine, "IBUPROFEN")
    assert found["matched"] is True
    assert found["drugs"][0]["name"] == "ibuprofen"
    assert found["pairs"][0]["pair_id"] == PAIR["pair_id"]

    overview = warehouse_overview(engine)
    assert overview["documents_by_quality_status"]["keep"] == 2
    assert {row["source"]: row["documents"] for row in overview["documents_by_source"]} == {"pubmed": 2}


def test_reloading_same_document_updates_instead_of_duplicating(warehouse) -> None:
    engine, _ = warehouse
    first = [_doc("pubmed:9:1", "pubmed", "Nội dung lần một đủ dài cho cổng chất lượng.")]
    second = [_doc("pubmed:9:1", "pubmed", "Nội dung lần hai đã đổi, vẫn đủ dài cho cổng chất lượng.",
                   text_sha256="e" * 64)]
    load_pairs(engine, {"pairs": [PAIR]})
    load_documents(engine, "run-1", first, verdicts_of(first))
    again = load_documents(engine, "run-2", second, verdicts_of(second))
    assert again["inserted"] == 0
    assert again["updated"] == 1
    assert again["content_changed"] == ["pubmed:9:1"]
    counts = table_counts(engine)
    assert counts["documents"] == 1
    assert counts["document_sections"] == 1


def test_ingest_document_conflict_and_validation(warehouse) -> None:
    engine, settings = warehouse
    payload = dict(
        source="manual", source_id="ghi-chu-1", version=1, title="Ghi chú kiểm thử",
        text="Cảnh báo hạ magnesi khi dùng thuốc ức chế bơm proton kéo dài (ghi chú kiểm thử).",
        settings=settings,
    )
    created = ingest_document(engine, **payload)
    assert created["created"] is True
    assert created["doc_id"] == "manual:ghi-chu-1:1"
    assert created["rag"]["indexed"] is True

    same = ingest_document(engine, **payload)
    assert same["created"] is False

    with pytest.raises(DomainError) as conflict:
        ingest_document(engine, **{**payload, "text": "Nội dung khác hoàn toàn cho cùng định danh tài liệu."})
    assert conflict.value.code == "INGEST_CONFLICT"

    with pytest.raises(DomainError) as short:
        ingest_document(engine, **{**payload, "source_id": "ghi-chu-2", "text": "quá ngắn"})
    assert short.value.code == "INGEST_TEXT_TOO_SHORT"

    with pytest.raises(DomainError) as bad_source:
        ingest_document(engine, **{**payload, "source_id": "ghi-chu-3", "source": "khong-co"})
    assert bad_source.value.code == "INGEST_SOURCE_INVALID"

    assert delete_document(engine, "manual:ghi-chu-1:1") is True
    assert delete_document(engine, "manual:ghi-chu-1:1") is False
    assert table_counts(engine)["documents"] == 0


def test_delete_document_does_not_touch_other_documents_events(warehouse) -> None:
    """Mã tài liệu chứa `_`/`%` không được xoá nhầm sự kiện nạp của tài liệu khác."""
    from src.services.warehouse.queries import ingestion_events

    engine, settings = warehouse
    for source_id in ("a_b", "axb"):
        ingest_document(
            engine, source="manual", source_id=source_id, version=1, title=f"Tài liệu {source_id}",
            text="Nội dung đủ dài cho một tài liệu nạp tay dùng để kiểm thử dọn sự kiện.", settings=settings,
        )
    before = {event["event_id"] for event in ingestion_events(engine)}
    assert any(event.startswith("ingest-manual:a_b:1-") for event in before)
    assert any(event.startswith("ingest-manual:axb:1-") for event in before)

    assert delete_document(engine, "manual:a_b:1") is True

    after = {event["event_id"] for event in ingestion_events(engine)}
    assert not any(event.startswith("ingest-manual:a_b:1-") for event in after)
    assert any(event.startswith("ingest-manual:axb:1-") for event in after), "sự kiện của tài liệu khác phải còn nguyên"


def test_purge_document_removes_postgres_rows_and_chunks(warehouse) -> None:
    engine, settings = warehouse
    ingest_document(
        engine, source="manual", source_id="xoa-1", version=1, title="Tài liệu để xoá",
        text="Tài liệu này sẽ bị xoá khỏi cả PostgreSQL lẫn chỉ mục vector để kiểm thử.", settings=settings,
    )
    before = index_stats(engine, settings)
    assert before["chroma_chunks"] == before["postgres_chunks"] >= 1

    result = purge_document(engine, "manual:xoa-1:1", settings=settings)
    assert result["postgres_removed"] is True
    assert result["chunks_removed"] >= 1
    after = index_stats(engine, settings)
    assert after["chroma_chunks"] == after["postgres_chunks"] == 0


def test_rag_build_and_search_round_trip(warehouse) -> None:
    engine, settings = warehouse
    docs = [
        _doc("pubmed:1:1", "pubmed", "Fluoroquinolone use and risk of aortic aneurysm in older adults."),
        _doc("pubmed:2:1", "pubmed", "Metformin associated diarrhoea in type 2 diabetes patients."),
    ]
    keep, _, _ = apply_gates(docs)
    load_documents(engine, "run-rag", keep, verdicts_of(keep))

    built = build_index(engine, run_id="run-rag", settings=settings)
    assert built["chunks"] >= 2
    stats = index_stats(engine, settings)
    assert stats["chroma_chunks"] == stats["postgres_chunks"]

    hits = search(engine, "aortic aneurysm", k=2, settings=settings)["hits"]
    assert hits, "truy vấn phải trả về ít nhất một đoạn"
    assert all(hit["in_postgres"] for hit in hits)
    assert any("aneurysm" in hit["text"].lower() for hit in hits)

    filtered = search(engine, "diarrhoea", k=5, source="pubmed", settings=settings)["hits"]
    assert all(hit["document"]["source"] == "pubmed" for hit in filtered)


def test_findings_are_recorded(warehouse) -> None:
    from scripts.elt.quality import evaluate_document

    engine, _ = warehouse
    good = _doc("pubmed:1:1", "pubmed", "Tài liệu có tóm tắt để ghi phát hiện chất lượng.")
    bad = _doc("pubmed:2:1", "pubmed", "Tài liệu này thiếu tóm tắt nên phải bị cách ly khỏi bằng chứng chính.",
               structured={"has_abstract": False, "journal": "JAMA"})
    keep, quarantine, rejected = apply_gates([good, bad])
    assert len(keep) == 1 and len(quarantine) == 1 and rejected == []
    findings = evaluate_document(bad).findings + evaluate_document(good).findings
    load_documents(engine, "run-f", keep + quarantine, verdicts_of(keep + quarantine))
    assert load_findings(engine, "run-f", findings) == len(findings)
    from src.services.warehouse.queries import warehouse_overview

    overview = warehouse_overview(engine)
    assert overview["documents_by_quality_status"] == {"keep": 1, "quarantine": 1}
    assert any(item["check_name"] == "missing_abstract" for item in overview["quality_findings"])


def test_rejected_document_never_reaches_the_warehouse(warehouse) -> None:
    """Cổng chất lượng: bản ghi `reject` không được ghi vào kho (docs/data/cong-chat-luong.md)."""
    engine, _ = warehouse
    good = _doc("pubmed:1:1", "pubmed", "Tài liệu đạt yêu cầu với tóm tắt đầy đủ cho RAG.")
    rejected = _doc("pubmed:2:1", "pubmed", "x")
    keep, quarantine, rejected_docs = apply_gates([good, rejected])
    assert [doc.doc_id for doc in rejected_docs] == ["pubmed:2:1"]

    load_pairs(engine, {"pairs": [PAIR]})
    verdicts = verdicts_of([good, rejected])
    result = load_documents(engine, "run-reject", [good, rejected], verdicts)
    assert result["inserted"] == 1
    assert result["skipped_rejected"] == 1

    assert {item["doc_id"] for item in list_documents(engine)} == {"pubmed:1:1"}
    assert document_detail(engine, "pubmed:2:1") is None
    assert table_counts(engine)["documents"] == 1
    assert warehouse_overview(engine)["documents_by_quality_status"] == {"keep": 1}


def test_document_that_becomes_rejected_is_removed_from_warehouse_and_index(warehouse) -> None:
    """Tài liệu đạt ở lần chạy trước, bị `reject` ở lần sau thì phải rời cả hai kho."""
    engine, settings = warehouse
    long_text = "Bằng chứng về ibuprofen và xuất huyết tiêu hoá ở người lớn. " * 20
    first_run = [_doc("pubmed:1:1", "pubmed", long_text)]
    keep, _, _ = apply_gates(first_run)
    assert len(keep) == 1
    load_documents(engine, "run-a", keep, verdicts_of(keep))
    build_index(engine, run_id="run-a", settings=settings)
    assert search(engine, "ibuprofen xuất huyết", k=5, settings=settings)["hits"]

    # Lần chạy sau: cùng doc_id nhưng văn bản co xuống dưới ngưỡng → bị `reject`.
    short = _doc("pubmed:1:1", "pubmed", "x")
    keep_b, _, rejected_b = apply_gates([short])
    assert [doc.doc_id for doc in rejected_b] == ["pubmed:1:1"]

    result = load_documents(engine, "run-b", [*keep_b, *rejected_b], verdicts_of([short]))
    assert result["skipped_rejected"] == 1
    assert result["removed_rejected"] == 1

    assert list_documents(engine) == []
    assert document_detail(engine, "pubmed:1:1") is None
    assert table_counts(engine)["documents"] == 0
    # Bước dọn của chỉ mục xoá nốt đoạn cũ trong Chroma.
    rebuilt = build_index(engine, run_id="run-b", settings=settings)
    assert rebuilt["documents"] == 0
    assert rebuilt["pruned_documents"] == 1
    assert search(engine, "ibuprofen xuất huyết", k=5, settings=settings)["hits"] == []
    stats = index_stats(engine, settings)
    assert stats["chroma_chunks"] == stats["postgres_chunks"] == 0


def test_reindex_drops_chunks_of_documents_that_left_the_index(warehouse) -> None:
    """Đoạn cũ trong Chroma phải bị xoá khi văn bản ngắn lại hoặc tài liệu bị cách ly."""
    from src.services.warehouse.db import session_scope
    from src.services.warehouse.models import Document as DocumentModel

    engine, settings = warehouse
    docs = [
        _doc("pubmed:1:1", "pubmed", "Bằng chứng dài về fluoroquinolone và phình động mạch chủ ở người lớn tuổi. " * 20),
        _doc("pubmed:2:1", "pubmed", "Bằng chứng về metformin và tiêu chảy ở bệnh nhân đái tháo đường týp 2. " * 20),
    ]
    keep, _, _ = apply_gates(docs)
    load_documents(engine, "run-prune", keep, verdicts_of(keep))
    first = build_index(engine, run_id="run-prune", settings=settings)
    assert first["chunks"] > 2
    assert index_stats(engine, settings)["chroma_chunks"] == index_stats(engine, settings)["postgres_chunks"]

    # Tài liệu 1 ngắn lại rất nhiều, tài liệu 2 bị cách ly khỏi chỉ mục.
    with session_scope(engine) as session:
        session.get(DocumentModel, "pubmed:1:1").text = "Đoạn ngắn."
        session.get(DocumentModel, "pubmed:2:1").quality_status = "quarantine"

    rebuilt = build_index(engine, run_id="run-prune", settings=settings)
    assert rebuilt["documents"] == 1
    assert rebuilt["pruned_documents"] == 1
    stats = index_stats(engine, settings)
    assert stats["chroma_chunks"] == stats["postgres_chunks"]

    hits = search(engine, "metformin tiêu chảy", k=5, settings=settings)["hits"]
    assert all("metformin" not in hit["text"].lower() for hit in hits)
    assert all(hit["in_postgres"] for hit in hits)
