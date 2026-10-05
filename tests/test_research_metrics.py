"""Metrics retain denominators and distinguish unresolved handoffs."""

from research.metrics import score
from research.runners import CaseResult


def result(case_id, strategy, issues, *, status="completed", error=None):
    return CaseResult(case_id, "matched", strategy, status, [{"visible_at": "t", "issues": issues, "assertions": [], "actions": []}] if status == "completed" else [], 0, 0, 0, 0, None, 0.0, error)


def test_zero_denominator_is_na_and_failure_retained():
    cases = [result("T1", "A", []), result("T2", "A", [], status="incomplete", error="MODEL_UNAVAILABLE")]
    labels = {"T1": {"expected_issues": [], "accepted_outcomes": []}, "T2": {"expected_issues": ["information_gap"], "accepted_outcomes": []}}
    metrics = score(cases, labels)
    assert metrics["cases_total"] == 2
    assert metrics["cases_incomplete"] == 1
    assert metrics["issue_precision_micro"] == "N/A"
    assert metrics["issue_recall_micro"] == 0


def test_handoff_is_separate_from_resolved_coverage():
    cases = [result("T1", "A", [{"type": "information_gap", "work_status": "handed_off", "evidence_status": "inconclusive"}])]
    labels = {"T1": {"expected_issues": ["information_gap"], "accepted_outcomes": ["handoff"]}}
    metrics = score(cases, labels)
    assert metrics["handed_off_count"] == 1
    assert metrics["resolved_count"] == 0


def test_citation_must_be_visible_and_support_claimed_fields():
    assertion = {"source_id": "S1", "name": "Thuốc A", "dose": "500 mg", "frequency": None,
                 "assertion_type": "ordered", "quote": "Thuốc A 500 mg"}
    case = result("T1", "B1", [])
    case.stages[0]["assertions"] = [assertion]
    case.stages[0]["source_ids"] = ["S1"]
    labels = {"T1": {"expected_issues": [], "accepted_outcomes": [],
                     "expected_fields": [{"source_id": "S1", "name": "Thuốc A", "dose": "0.5 g",
                                          "frequency": None, "assertion_type": "ordered"}],
                     "source_rubric": [{"source_id": "S1", "version": 1, "text": "Y lệnh Thuốc A 500 mg."}]}}
    metrics = score([case], labels)
    assert metrics["field_accuracy"] == 1
    assert metrics["citation_existence"] == 1
    assert metrics["citation_support"] == 1
    case.stages[0]["source_ids"] = []
    invisible = score([case], labels)
    assert invisible["citation_existence"] == 0
