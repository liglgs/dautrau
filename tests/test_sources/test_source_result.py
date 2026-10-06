"""Offline tests for additive SourceResult normalization."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.models.schemas import SourceDocument, SourceSearchResult, SourceStatus
from src.services.sources.result import source_result_from_fetch, source_result_from_search


def _document(*, warnings: list[str] | None = None) -> SourceDocument:
    return SourceDocument(
        doc_id="pubmed:1:1",
        source="pubmed",
        source_id="1",
        version=1,
        title="Abstract only",
        source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        text="An abstract.",
        hash="a" * 64,
        retrieved_at=datetime(2026, 10, 6, tzinfo=UTC),
        metadata={"content_level": "abstract_only", "warnings": warnings or []},
    )


def test_source_result_keeps_abstract_only_coverage_when_document_is_truncated() -> None:
    result = SourceSearchResult(
        source="pubmed", query="drug event", fingerprint="query", status=SourceStatus.OK,
        documents=[_document(warnings=["truncated_document"])], requests_used=1,
    )

    normalized = source_result_from_search(result)

    assert normalized.outcome == "partial"
    assert normalized.coverage == "abstract_only"
    assert normalized.documents[0].metadata["content_level"] == "abstract_only"
    assert normalized.retrieved_at == "2026-10-06T00:00:00+00:00"


def test_skipped_and_ok_without_documents_are_non_results() -> None:
    base = dict(source="faers", query="drug event", fingerprint="query", requests_used=0)
    skipped = source_result_from_search(SourceSearchResult(status=SourceStatus.SKIPPED, **base))
    no_documents = source_result_from_search(SourceSearchResult(status=SourceStatus.OK, **base))

    assert (skipped.outcome, skipped.coverage, skipped.ok) == ("skipped", "not_requested", False)
    assert (no_documents.outcome, no_documents.coverage, no_documents.ok) == ("empty", "empty", False)


def test_source_result_distinguishes_timeout_rate_limit_and_empty() -> None:
    base = dict(source="faers", query="drug event", fingerprint="query", requests_used=1)

    timeout = source_result_from_search(SourceSearchResult(status=SourceStatus.ERROR, error="timeout", retryable=True, **base))
    rate_limited = source_result_from_search(
        SourceSearchResult(status=SourceStatus.ERROR, error="rate_limited", retryable=True, **base)
    )
    empty = source_result_from_search(SourceSearchResult(status=SourceStatus.EMPTY, **base))

    assert (timeout.outcome, timeout.retryable, timeout.coverage) == ("timeout", True, "unavailable")
    assert (rate_limited.outcome, rate_limited.retryable) == ("rate_limited", True)
    assert (empty.outcome, empty.source_gap, empty.coverage) == ("empty", False, "empty")


@pytest.mark.parametrize(
    ("error", "outcome"),
    [
        ("parse_error: malformed XML", "parse_error"),
        ("unavailable: upstream maintenance", "unavailable"),
        ("budget_exhausted", "budget_exhausted"),
        ("invalid_query: empty drug", "invalid_query"),
        ("http_503", "http_error"),
    ],
)
def test_source_result_preserves_non_http_failure_semantics(error: str, outcome: str) -> None:
    result = source_result_from_search(SourceSearchResult(
        source="dailymed", query="drug", fingerprint="query", status=SourceStatus.ERROR,
        error=error, retryable=True,
    ))

    assert result.outcome == outcome
    assert result.coverage == "unavailable"


def test_fetch_404_is_source_gap_not_empty_and_metadata_is_preserved() -> None:
    class Fetch:
        source = "dailymed"
        status = 404
        error = "http_404"
        # Error responses can contain an HTML/JSON diagnostic body.  That is
        # not source content and must not turn a source gap into full coverage.
        body = b"<html>not found</html>"
        url = "https://dailymed.nlm.nih.gov/missing"
        params = {"setid": "missing"}
        sha256 = ""
        path = ""

    result = source_result_from_fetch(
        Fetch(), metadata={
            "version": 9,
            "published_date": "2026-01-01",
            "effective_time": "2025-11-01",
            "retrieved_at": "2026-10-06T17:31:41+00:00",
        }
    )

    assert result.outcome == "http_error"
    assert result.source_gap is True
    assert result.http_status == 404
    assert result.coverage == "unavailable"
    assert result.version == 9
    assert result.published_date == "2026-01-01"
    assert result.effective_time == "2025-11-01"
    assert result.retrieved_at == "2026-10-06T17:31:41+00:00"
