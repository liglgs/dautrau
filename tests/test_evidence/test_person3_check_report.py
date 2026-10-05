"""Excluded model text is a review item; active invalid citations remain failures."""

import pytest

from src.services.evidence.check_report import summarize_checks


def row(**changes):
    return {"doc_id": "D1", "valid_quotes": 3, "excluded_quotes": 2, "error": None,
            "citation_errors": [], "dossier_errors": [], **changes}


def test_correctly_filtered_bad_quotes_remain_visible_without_pipeline_failure():
    summary = summarize_checks([row()])
    assert summary["valid_quotes"] == 3 and summary["excluded_quotes"] == 2
    assert summary["documents_with_excluded_quotes"] == ["D1"]
    assert summary["processing_failures"] == []
    assert summary["clinical_metrics_measured"] is False


@pytest.mark.parametrize("changes", [{"error": "model_unavailable"},
    {"citation_errors": ["quote_mismatch"]}, {"dossier_errors": ["stale_reference"]}])
def test_real_processing_errors_are_never_reclassified_as_review_only(changes):
    assert summarize_checks([row(**changes)])["processing_failures"] == ["D1"]


def test_empty_extraction_is_reported_without_claiming_irrelevance_or_success():
    summary = summarize_checks([row(valid_quotes=0, excluded_quotes=0)])
    assert summary["documents_without_quotes"] == ["D1"]
    assert not summary["documents_with_excluded_quotes"]
