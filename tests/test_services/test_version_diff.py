"""Offline tests for immutable version diff reports."""

from __future__ import annotations

import hashlib

from src.services.warehouse.version_diff import VersionedDocument, diff_versions


def _document(version: int, text: str) -> VersionedDocument:
    return VersionedDocument(
        source="dailymed",
        source_id="set-1",
        version=version,
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source_url="https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=set-1",
        published_date="2026-09-29",
        effective_time="2024-09-19",
        retrieved_at=f"2026-10-0{version}T00:00:00+00:00",
    )


def test_unchanged_content_does_not_create_duplicate_review_work() -> None:
    changes = diff_versions(_document(1, "Title\n\nWarnings"), _document(2, "Title\n\nWarnings"))

    assert changes.changed is False
    assert changes.requires_review is False
    assert changes.review_key is None
    assert changes.reason == "content_unchanged"
    assert changes.changes == ()
    assert changes.provenance["old"]["sha256"] == changes.provenance["new"]["sha256"]


def test_changed_content_has_paragraph_diff_and_provenance() -> None:
    changes = diff_versions(
        _document(1, "Title\n\nWarnings\nTake with food."),
        _document(2, "Title\n\nWarnings\nDo not take with food.\n\nNew contraindication."),
    )

    assert changes.changed is True
    assert changes.requires_review is True
    assert changes.review_key
    assert [change.kind for change in changes.changes] == ["changed", "added"]
    assert changes.changes[0].old_paragraph == "Warnings\nTake with food."
    assert changes.changes[0].new_paragraph == "Warnings\nDo not take with food."
    assert changes.provenance["new"]["published_date"] == "2026-09-29"
    assert changes.provenance["new"]["effective_time"] == "2024-09-19"


def test_diff_rejects_a_tampered_or_nonsequential_snapshot() -> None:
    bad = VersionedDocument("dailymed", "set-1", 2, "new", "wrong")
    try:
        diff_versions(_document(1, "old"), bad)
    except ValueError as exc:
        assert "text_sha256" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("must reject a tampered snapshot")
