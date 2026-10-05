"""Prediction contract shared by RAG and the agent integration hook."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, NotRequired

from pydantic import TypeAdapter
from typing_extensions import TypedDict

ASSESSMENTS = {
    "supported_for_scope",
    "contradicted_for_scope",
    "insufficient_evidence",
    "scope_mismatch",
    "out_of_scope",
    "requires_human_review",
}

SCOPE_FIELDS = {"drug", "event", "population", "dose", "route", "time_window", "study_type"}


class Statement(TypedDict):
    statement_id: NotRequired[str]
    text: str
    kind: Literal["fact", "inference", "hypothesis"]
    evidence_ids: list[str]


def detection_evidence(value: Any, field: str, *, allowed_ids: set[str]) -> set[str]:
    """Validate measured detection keys and return all referenced evidence IDs."""
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of string keys")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} contains duplicate keys")
    references: set[str] = set()
    for key in value:
        if field == "scope_mismatches":
            unit_id, separator, scope_field = key.rpartition(":")
            if not separator or not unit_id or scope_field not in SCOPE_FIELDS:
                raise ValueError("Invalid scope mismatch key: expected unit_id:scope_field")
            references.add(unit_id)
        elif field == "contradictions":
            kind, separator, pair = key.partition(":")
            ids = pair.split("|")
            if (
                not separator
                or kind not in {"direct", "apparent"}
                or len(ids) != 2
                or not ids[0]
                or not ids[0] < ids[1]
            ):
                raise ValueError("Invalid contradiction key: expected kind:unit_a|unit_b in canonical order")
            references.update(ids)
        else:
            raise ValueError("Unknown detection field")
    if references - allowed_ids:
        raise ValueError(f"{field} references evidence outside allowed context")
    return references


@dataclass
class Prediction:
    retrieved_ids: list[str]
    assessment_status: str | None = None
    abstained: bool | None = None
    # None = not measured, [] = measured and none detected.
    scope_mismatches: list[str] | None = None
    contradictions: list[str] | None = None
    statements: list[Statement] | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def parse(cls, raw: dict[str, Any], *, allowed_ids: set[str]) -> Prediction:
        prediction = cls(**raw)
        if prediction.assessment_status is not None and prediction.assessment_status not in ASSESSMENTS:
            raise ValueError("Invalid assessment status (causality is not an assessment)")
        if prediction.abstained is not None and not isinstance(prediction.abstained, bool):
            raise ValueError("abstained must be boolean or null")
        if not isinstance(prediction.retrieved_ids, list) or any(
            not isinstance(item, str) for item in prediction.retrieved_ids
        ):
            raise ValueError("retrieved_ids must contain strings")
        if len(set(prediction.retrieved_ids)) != len(prediction.retrieved_ids):
            raise ValueError("Duplicate retrieved evidence IDs")
        if set(prediction.retrieved_ids) - allowed_ids:
            raise ValueError("Prediction references foreign/future evidence")
        for field_name in ("scope_mismatches", "contradictions"):
            value = getattr(prediction, field_name)
            if value is not None:
                detection_evidence(value, field_name, allowed_ids=set(prediction.retrieved_ids))
        if prediction.statements is not None and not isinstance(prediction.statements, list):
            raise ValueError("statements must be an array or null")
        for statement in prediction.statements or []:
            if not isinstance(statement, dict) or not isinstance(statement.get("text"), str) or statement.get("kind") not in {
                "fact",
                "inference",
                "hypothesis",
            }:
                raise ValueError("Statement needs text and fact/inference/hypothesis classification")
            refs = statement.get("evidence_ids", [])
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                raise ValueError("Statement evidence_ids must be an array of strings")
            if set(statement.get("evidence_ids", [])) - set(prediction.retrieved_ids):
                raise ValueError("Statement references evidence outside retrieved context")
        return prediction

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PREDICTION_SCHEMA = TypeAdapter(Prediction).json_schema()
