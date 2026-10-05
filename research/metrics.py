"""Descriptive technical metrics. N/A is explicit for zero denominators."""

from collections import Counter

from research.runners import CaseResult
from src.vmec import parse_dose, parse_frequency


def _ratio(numerator: int, denominator: int) -> float | str:
    return round(numerator / denominator, 4) if denominator else "N/A"


def _field_equal(field: str, actual, expected) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if not isinstance(actual, str) or not isinstance(expected, str):
        return False
    if field == "dose" and parse_dose(actual) is not None and parse_dose(expected) is not None:
        return parse_dose(actual) == parse_dose(expected)
    if field == "frequency" and parse_frequency(actual) is not None and parse_frequency(expected) is not None:
        return parse_frequency(actual) == parse_frequency(expected)
    return actual.casefold().strip() == expected.casefold().strip()


def score(results: list[CaseResult], labels: dict[str, dict]) -> dict:
    true_positive = false_positive = false_negative = 0
    macro_precision = []
    macro_recall = []
    closed = false_closure = resolved = handed_off = 0
    field_correct = field_total = citation_exists = citation_supported = citation_total = 0
    repeated_questions = delayed_visible = delayed_total = 0
    resolvable_total = 0
    for result in results:
        label = labels[result.case_id]
        expected_fields = label.get("expected_fields", [])
        field_total += len(expected_fields) * 4
        resolvable_total += label.get("resolvable_issue_count", 0)
        if label.get("delayed_source_id"):
            delayed_total += 1
        if result.status != "completed":
            missed = len(label.get("expected_issues", []))
            false_negative += missed
            if missed:
                macro_recall.append(0.0)
            continue
        if label.get("delayed_source_id") and label["delayed_source_id"] in result.stages[-1].get("source_ids", []):
            delayed_visible += 1
        predicted_fields = result.stages[0].get("assertions", [])
        for gold in expected_fields:
            candidates = [item for item in predicted_fields if item.get("source_id") == gold["source_id"]]
            prediction = candidates[0] if candidates else {}
            field_correct += sum(_field_equal(field, prediction.get(field), gold.get(field))
                                 for field in ("name", "dose", "frequency", "assertion_type"))
        seen_citations = set()
        for stage in result.stages:
            for assertion in stage.get("assertions", []):
                source_id = assertion.get("source_id")
                quote = assertion.get("quote")
                if not source_id or not isinstance(quote, str):
                    citation_total += 1
                    continue
                identity = (stage["visible_at"], source_id, quote)
                if identity in seen_citations:
                    continue
                seen_citations.add(identity)
                citation_total += 1
                # The runner's input feed is immutable; the quote must be present in a visible source.
                source = next((s for s in label.get("source_rubric", []) if s["source_id"] == source_id), None)
                if source and source_id in stage.get("source_ids", []) and quote in source["text"]:
                    citation_exists += 1
                    if all(not isinstance(assertion.get(field), str) or assertion[field].casefold() in quote.casefold()
                           for field in ("name", "dose", "frequency")):
                        citation_supported += 1
        if "expected_issue_keys" in label:
            expected = Counter((issue["type"], issue.get("product"), issue.get("field"))
                               for issue in label["expected_issue_keys"])
            predicted = Counter((issue.get("type"), issue.get("product"), issue.get("field"))
                                for issue in result.stages[0]["issues"])
        else:
            expected = Counter(label.get("expected_issues", []))
            predicted = Counter(issue.get("type") for issue in result.stages[0]["issues"])
        tp = sum(min(predicted[k], expected[k]) for k in predicted)
        fp = sum(predicted.values()) - tp
        fn = sum(expected.values()) - tp
        true_positive += tp
        false_positive += fp
        false_negative += fn
        if tp + fp:
            macro_precision.append(tp / (tp + fp))
        if tp + fn:
            macro_recall.append(tp / (tp + fn))
        asked = Counter()
        for stage in result.stages:
            by_id = {issue.get("id"): issue for issue in stage["issues"]}
            for action in stage["actions"]:
                if action.get("action") == "create_verification_task":
                    issue = by_id.get(action.get("issue_id"), {})
                    asked[(issue.get("type"), issue.get("product"), issue.get("field"))] += 1
        repeated_questions += sum(max(0, count - 1) for count in asked.values())
        for issue in result.stages[-1]["issues"]:
                status = issue.get("work_status")
                if status == "handed_off":
                    handed_off += 1
                elif status == "closed":
                    closed += 1
                    if issue.get("evidence_status") not in (
                        "confirmed_information_resolved", "confirmed_no_difference",
                        "confirmed_intentional", "confirmed_unintentional",
                    ):
                        false_closure += 1
                    else:
                        resolved += 1
    return {
        "cases_total": len(results),
        "cases_completed": sum(r.status == "completed" for r in results),
        "cases_incomplete": sum(r.status != "completed" for r in results),
        "issue_tp": true_positive, "issue_fp": false_positive, "issue_fn": false_negative,
        "issue_precision_micro": _ratio(true_positive, true_positive + false_positive),
        "issue_recall_micro": _ratio(true_positive, true_positive + false_negative),
        "issue_precision_macro": round(sum(macro_precision) / len(macro_precision), 4) if macro_precision else "N/A",
        "issue_recall_macro": round(sum(macro_recall) / len(macro_recall), 4) if macro_recall else "N/A",
        "closed_count": closed, "false_closure_count": false_closure,
        "false_closure_rate": _ratio(false_closure, closed),
        "resolved_count": resolved, "handed_off_count": handed_off,
        "resolved_coverage": _ratio(resolved, resolvable_total),
        "field_accuracy": _ratio(field_correct, field_total),
        "field_correct": field_correct, "field_total": field_total,
        "citation_existence": _ratio(citation_exists, citation_total),
        "citation_support": _ratio(citation_supported, citation_total),
        "citation_total": citation_total,
        "repeated_questions": repeated_questions,
        "delayed_source_visibility": _ratio(delayed_visible, delayed_total),
        "model_calls": sum(r.model_calls for r in results),
        "prompt_tokens": sum(r.prompt_tokens for r in results),
        "completion_tokens": sum(r.completion_tokens for r in results),
        "total_tokens": sum(r.total_tokens for r in results),
        "latency_seconds": round(sum(r.latency_seconds for r in results), 3),
        "cost_usd": round(sum(r.cost_usd or 0 for r in results), 8)
        if all(r.cost_usd is not None for r in results) else None,
    }
