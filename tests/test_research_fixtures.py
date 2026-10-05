"""The benchmark split is frozen and cannot leak evaluator-only data."""

from collections import Counter

from research.fixtures import load_cases, public_view
from research.manifest import build_manifest


def test_frozen_split_groups_and_no_family_overlap():
    dev = load_cases("dev")
    test = load_cases("test")
    assert len(dev) == 10
    assert len(test) == 30
    assert len({case.case_id for case in dev + test}) == 40
    assert not ({case.family_id for case in dev} & {case.family_id for case in test})
    assert Counter(case.group for case in test) == {
        "matched": 5, "explained": 5, "response_needed": 5,
        "ambiguous": 5, "handoff": 5, "late_source": 5,
    }


def test_public_view_hides_labels_and_unreleased_events():
    cases = load_cases("test")
    for case in cases:
        initial = public_view(case, case.initial_visible_at)
        serialized = str(initial)
        assert "expected_issues" not in serialized
        assert "accepted_outcomes" not in serialized
        assert "forbidden_conclusions" not in serialized
        assert all(source["available_at"] <= case.initial_visible_at for source in initial["sources"])
        assert all(event["source_id"] not in serialized for event in case.delayed_sources)
    assert any(event.get("event_time") is None for case in cases for event in case.delayed_sources)


def test_manifest_is_stable_and_contains_checksums():
    first = build_manifest(load_cases("dev"), load_cases("test"))
    second = build_manifest(load_cases("dev"), load_cases("test"))
    assert first == second
    assert first["dataset_version"]
    assert first["schema_version"]
    assert first["catalog_version"]
    assert len(first["cases"]) == 40
    assert all(len(item["sha256"]) == 64 for item in first["cases"])
