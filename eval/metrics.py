"""Metrics require explicit annotations; no denominator => None (N/A)."""

from __future__ import annotations

from typing import Any

from eval.contracts import Prediction


def ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "value": numerator / denominator if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
    }


def retrieval(retrieved: list[str], required: list[str], relevant: list[str], *, k: int = 20) -> dict[str, Any]:
    ranked = list(dict.fromkeys(retrieved))[:k]
    return {
        "evidence_recall_at_20": ratio(len(set(ranked) & set(required)), len(set(required))),
        f"precision_at_{k}": ratio(len(set(ranked) & set(relevant)), len(ranked)),
    }


def detection(predicted: list[str] | None, gold: list[str]) -> dict[str, Any]:
    if predicted is None:
        return {"precision": ratio(0, 0), "recall": ratio(0, 0), "measured": False}
    matched = len(set(predicted) & set(gold))
    return {
        "precision": ratio(matched, len(set(predicted))),
        "recall": ratio(matched, len(set(gold))),
        "measured": True,
    }


def score(prediction: Prediction, gold: dict[str, Any], *, k: int = 20) -> dict[str, Any]:
    metrics = retrieval(prediction.retrieved_ids, gold["required_evidence_ids"], gold["relevant_evidence_ids"], k=k)
    metrics["scope_mismatch"] = detection(prediction.scope_mismatches, gold.get("scope_mismatches", []))
    # Pair keys include direct/apparent, so a wrong classification cannot match a gold pair.
    metrics["contradiction"] = detection(prediction.contradictions, gold.get("contradictions", []))
    metrics["abstention"] = (
        None
        if prediction.abstained is None
        else {
            "gold": gold["abstained"],
            "predicted": prediction.abstained,
            "correct": prediction.abstained == gold["abstained"],
        }
    )
    metrics["assessment_correct"] = (
        None if prediction.assessment_status is None else prediction.assessment_status == gold["assessment_status"]
    )
    adjudication = {row["statement_id"]: row for row in gold.get("statement_reviews", [])}
    facts = [row for row in prediction.statements or [] if row["kind"] == "fact"]
    checked_links = valid_links = checked_facts = supported_facts = unsupported_facts = 0
    for statement in facts:
        label = adjudication.get(statement.get("statement_id"))
        # Reviews are bound to statement text and citation IDs, never a positional ID alone.
        if (
            label is None
            or label.get("text") != statement["text"]
            or set(label.get("evidence_ids", [])) != set(statement.get("evidence_ids", []))
        ):
            continue
        checked_facts += 1
        supporting = set(label.get("supporting_evidence_ids", [])) & set(statement.get("evidence_ids", []))
        checked_links += len(set(statement.get("evidence_ids", [])))
        valid_links += len(supporting)
        supported_facts += bool(supporting)
        unsupported_facts += not bool(supporting)
    metrics.update(
        {
            "citation_precision": ratio(valid_links, checked_links),
            "citation_completeness": ratio(supported_facts, len(facts)) if checked_facts == len(facts) else ratio(0, 0),
            "unsupported_claim_rate": ratio(unsupported_facts, len(facts))
            if checked_facts == len(facts)
            else ratio(0, 0),
            "statement_review_coverage": ratio(checked_facts, len(facts)),
        }
    )
    return metrics


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Macro averages with sample count; N/A and failed runs never become perfect scores."""
    paths = [
        "evidence_recall_at_20",
        "precision_at_20",
        "citation_precision",
        "citation_completeness",
        "unsupported_claim_rate",
    ]
    result: dict[str, Any] = {"claims": len(rows), "successful": sum(row.get("error") is None for row in rows)}
    for key in paths:
        measurements = [
            row["metrics"][key] for row in rows if row.get("metrics", {}).get(key, {}).get("value") is not None
        ]
        result[key] = {
            "macro": sum(item["value"] for item in measurements) / len(measurements) if measurements else None,
            "samples": len(measurements),
            "denominator": sum(item["denominator"] for item in measurements),
        }
    matrix = {"abstain_correct": 0, "answer_correct": 0, "false_abstain": 0, "false_answer": 0}
    for row in rows:
        abstention = row.get("metrics", {}).get("abstention")
        if abstention:
            key = (
                "abstain_correct"
                if abstention["gold"] and abstention["predicted"]
                else "answer_correct"
                if not abstention["gold"] and not abstention["predicted"]
                else "false_abstain"
                if abstention["predicted"]
                else "false_answer"
            )
            matrix[key] += 1
    result["abstention_confusion"] = matrix
    for metric in ("scope_mismatch", "contradiction"):
        result[metric] = {}
        for measure in ("precision", "recall"):
            values = [
                row["metrics"][metric][measure]
                for row in rows
                if row.get("metrics", {}).get(metric, {}).get(measure, {}).get("value") is not None
            ]
            result[metric][measure] = {
                "macro": sum(item["value"] for item in values) / len(values) if values else None,
                "samples": len(values),
                "denominator": sum(item["denominator"] for item in values),
            }
    return result
