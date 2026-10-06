"""Kiểm thử cổng chất lượng ELT (thuần, không cần mạng và không cần cơ sở dữ liệu)."""

from __future__ import annotations

from scripts.elt.parse import ParsedDocument
from scripts.elt.quality import apply_gates, dataset_stats, evaluate_document


def make_doc(source: str, **overrides) -> ParsedDocument:
    base = dict(
        doc_id=f"{source}:X:1",
        source=source,
        source_id="X",
        version=1,
        title="Tiêu đề kiểm thử",
        text="Nội dung kiểm thử đủ dài để vượt ngưỡng tối thiểu của cổng chất lượng.",
        text_sha256="a" * 64,
        source_url="",
        content_level="",
        metadata={},
        sections=[],
        pair_id=None,
        raw_sha256="b" * 64,
        raw_path="",
        structured={},
    )
    base.update(overrides)
    return ParsedDocument(**base)


def test_pubmed_without_abstract_is_quarantined() -> None:
    verdict = evaluate_document(make_doc("pubmed", structured={"has_abstract": False, "journal": "JAMA"}))
    assert verdict.decision == "quarantine"
    assert "missing_abstract" in verdict.flags


def test_pubmed_with_abstract_keeps_and_records_flags() -> None:
    verdict = evaluate_document(
        make_doc("pubmed", structured={"has_abstract": True, "journal": "JAMA", "doi": ["10.1/x"]})
    )
    assert verdict.decision == "keep"
    assert {"has_abstract", "has_journal"} <= set(verdict.flags)


def test_retracted_pubmed_is_rejected() -> None:
    verdict = evaluate_document(
        make_doc("pubmed", structured={"has_abstract": True, "publication_types": ["Retracted Publication"]})
    )
    assert verdict.decision == "reject"
    assert "retracted_publication" in verdict.flags


def test_dailymed_multi_ingredient_is_quarantined() -> None:
    verdict = evaluate_document(
        make_doc(
            "dailymed",
            structured={"single_ingredient": False, "routes": ["ORAL"], "effective_time": "20240101", "n_sections": 5},
        )
    )
    assert verdict.decision == "quarantine"
    assert "multi_ingredient" in verdict.flags


def test_dailymed_without_sections_is_rejected() -> None:
    verdict = evaluate_document(
        make_doc(
            "dailymed",
            structured={"single_ingredient": True, "routes": ["ORAL"], "effective_time": "20240101", "n_sections": 0},
        )
    )
    assert verdict.decision == "reject"
    assert "missing_sections" in verdict.flags


def test_dailymed_single_ingredient_oral_is_kept() -> None:
    verdict = evaluate_document(
        make_doc(
            "dailymed",
            structured={"single_ingredient": True, "routes": ["ORAL"], "effective_time": "20240101", "n_sections": 6},
        )
    )
    assert verdict.decision == "keep"


def test_faers_without_reactions_is_rejected() -> None:
    verdict = evaluate_document(
        make_doc("faers", structured={"n_reactions": 0, "n_drugs": 1, "patient_age": "50", "patient_sex": "F",
                                      "receivedate": "20240101", "drugs": [{"start_date": "20230101"}]})
    )
    assert verdict.decision == "reject"
    assert "no_reactions" in verdict.flags


def test_faers_missing_drug_dates_is_only_a_note() -> None:
    """Thiếu ngày/đường dùng là đặc điểm cố hữu của FAERS: ghi cờ, không cách ly."""
    verdict = evaluate_document(
        make_doc(
            "faers",
            structured={
                "n_reactions": 3,
                "n_drugs": 2,
                "patient_age": "50",
                "patient_sex": "F",
                "receivedate": "20240101",
                "drugs": [{"start_date": None, "route": None}, {"start_date": None, "route": None}],
            },
        )
    )
    assert verdict.decision == "keep"
    assert {"missing_drug_start_date", "missing_drug_route", "multiple_drugs"} <= set(verdict.flags)
    notes = [f for f in verdict.findings if f.check_name in {"missing_drug_start_date", "missing_drug_route"}]
    assert notes and all(f.decision == "note" for f in notes)


def test_faers_missing_patient_fields_is_quarantined() -> None:
    verdict = evaluate_document(
        make_doc(
            "faers",
            structured={"n_reactions": 2, "n_drugs": 1, "patient_age": None, "patient_sex": "M",
                        "receivedate": "20240101", "drugs": [{"start_date": "20230101"}]},
        )
    )
    assert verdict.decision == "quarantine"
    assert "missing_age" in verdict.flags


def test_short_text_is_rejected() -> None:
    verdict = evaluate_document(make_doc("pubmed", text="quá ngắn", structured={"has_abstract": True}))
    assert verdict.decision == "reject"
    assert "text_too_short" in verdict.flags


def test_duplicate_documents_in_one_run_are_rejected() -> None:
    first = make_doc("pubmed", doc_id="pubmed:1:1", source_id="1", structured={"has_abstract": True})
    second = make_doc("pubmed", doc_id="pubmed:1:1", source_id="1", structured={"has_abstract": True})
    keep, quarantine, rejected = apply_gates([first, second])
    assert len(keep) == 1
    assert quarantine == []
    assert [doc.doc_id for doc in rejected] == ["pubmed:1:1"]


def test_dataset_stats_counts_sources_and_pairs() -> None:
    docs = [
        make_doc("pubmed", doc_id="pubmed:1:1", source_id="1", pair_id="a__b", structured={"has_abstract": True}),
        make_doc("faers", doc_id="faers:2:1", source_id="2", pair_id="a__b",
                 structured={"n_reactions": 1, "n_drugs": 3, "patient_age": None, "patient_sex": "F",
                             "receivedate": "20240101", "drugs": [{"start_date": None}]}),
    ]
    keep, quarantine, rejected = apply_gates(docs)
    stats = dataset_stats(docs, [])
    assert stats["documents"] == 2
    assert stats["by_source"]["pubmed"]["count"] == 1
    assert stats["pairs"]["a__b"]["pubmed"] == 1
    assert stats["faers"]["multi_drug_reports"] == 1
    assert stats["faers"]["drug_rows_missing_start_date"] == 1
    assert stats["pubmed"]["with_abstract"] == 1
    assert (len(keep), len(quarantine), len(rejected)) == (1, 1, 0)
