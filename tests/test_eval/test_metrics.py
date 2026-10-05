from eval.contracts import Prediction
from eval.metrics import aggregate, detection, ratio, retrieval, score


def test_recall_four_gold_three_retrieved():
    result = retrieval(["a", "b", "c", "x"], ["a", "b", "c", "d"], ["a", "b", "c", "d"])
    assert result["evidence_recall_at_20"]["value"] == 0.75


def test_precision_uses_results_actually_returned_and_deduplicates():
    assert retrieval(["a", "a", "x"], ["a"], ["a"])["precision_at_20"]["value"] == 0.5
    assert ratio(0, 0)["value"] is None


def test_citation_precision_nine_of_ten():
    citations = [str(index) for index in range(10)]
    statement = {"statement_id": "s", "text": "Frozen statement", "kind": "fact", "evidence_ids": citations}
    gold = {
        "required_evidence_ids": [],
        "relevant_evidence_ids": [],
        "abstained": False,
        "assessment_status": "supported_for_scope",
        "statement_reviews": [{**statement, "supporting_evidence_ids": citations[:9]}],
    }
    result = score(Prediction(citations, statements=[statement]), gold)
    assert result["citation_precision"]["value"] == 0.9


def test_statement_review_does_not_apply_after_text_changes():
    statement = {"statement_id": "s", "text": "Changed statement", "kind": "fact", "evidence_ids": ["a"]}
    gold = {
        "required_evidence_ids": [],
        "relevant_evidence_ids": [],
        "statement_reviews": [{**statement, "text": "Old statement", "supporting_evidence_ids": ["a"]}],
    }
    assert score(Prediction(["a"], statements=[statement]), gold)["citation_precision"]["value"] is None


def test_unmeasured_differs_from_empty_detection():
    assert detection(None, ["x"])["measured"] is False
    assert detection([], ["x"])["recall"]["value"] == 0


def test_failed_rows_count_in_coverage_not_macro():
    result = aggregate([{"error": "failed"}, {"error": None, "metrics": {"evidence_recall_at_20": ratio(3, 4)}}])
    assert result["successful"] == 1
    assert result["claims"] == 2
    assert result["evidence_recall_at_20"]["macro"] == 0.75
