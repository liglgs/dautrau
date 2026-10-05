"""Local, immutable input/output drafts for offline work before M01.

These types do not replace src.models.schemas or the team's API contracts.
Intervals use inclusive bounds. No parsing of clinical prose happens here.
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class IntervalDraft:
    lower: float | None
    upper: float | None
    unit: str

    def __post_init__(self):
        if not self.unit.strip() or (self.lower is None and self.upper is None):
            raise ValueError("An interval needs a unit and at least one bound")
        for value in (self.lower, self.upper):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0
            ):
                raise ValueError("Bounds must be finite nonnegative numbers")
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("Lower bound must not exceed upper bound")


@dataclass(frozen=True)
class ScopeDraft:
    ingredient: str | None
    event: str | None
    population: IntervalDraft | None = None
    dose: IntervalDraft | None = None
    route: str | None = None
    time_window: IntervalDraft | None = None
    comparator: str | None = None
    unresolved_critical_fields: tuple[str, ...] = ()


def scope_from_dict(payload: dict) -> ScopeDraft:
    """Read explicit structured fixture input, preserving unknowns."""
    allowed = set(ScopeDraft.__dataclass_fields__)
    if set(payload) - allowed:
        raise ValueError("Unexpected scope fields")
    values = dict(payload)
    for name in ("ingredient", "event", "route", "comparator"):
        value = values.get(name)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{name} must be a nonblank string or null")
    for name in ("population", "dose", "time_window"):
        value = values.get(name)
        if value is not None:
            values[name] = IntervalDraft(**value)
    values["unresolved_critical_fields"] = tuple(values.get("unresolved_critical_fields", ()))
    return ScopeDraft(**values)


@dataclass(frozen=True)
class FieldMatchDraft:
    field: str
    status: str
    reason: str
    blocking: bool


@dataclass(frozen=True)
class ScopeAssessmentDraft:
    fields: tuple[FieldMatchDraft, ...]
    eligible_as_direct_evidence: bool
    requires_review: bool


@dataclass(frozen=True)
class EvidenceDraft:
    evidence_id: str
    scope: ScopeDraft
    stance: str
    source: str
    uncertainty: str
    direction: str

    def __post_init__(self):
        if not self.evidence_id.strip():
            raise ValueError("Evidence ID is required")
        if self.stance not in {"support", "contradict", "uncertain", "background"}:
            raise ValueError("Unsupported stance")
        if self.source not in {"pubmed", "dailymed", "faers"}:
            raise ValueError("Unsupported source")
        if self.uncertainty not in {"low", "high", "unknown"}:
            raise ValueError("Unsupported uncertainty")
        if self.direction not in {"increase", "decrease", "no_clear_effect", "unknown"}:
            raise ValueError("Unsupported direction")


@dataclass(frozen=True)
class ContradictionDraft:
    left_id: str
    right_id: str
    kind: str
    reason: str
    differing_fields: tuple[str, ...]
    requires_review: bool


@dataclass(frozen=True)
class DocumentDraft:
    document_id: str
    source_id: str
    source_version: str
    source_url: str
    text: str
    content_hash: str
    mode: str = "synthetic"


@dataclass(frozen=True)
class CitationDraft:
    document_id: str
    source_id: str
    source_version: str
    source_url: str
    content_hash: str
    quoted_span: str
    start: int
    end: int


@dataclass(frozen=True)
class CitationCheckDraft:
    span_verified: bool
    errors: tuple[str, ...]
    entailment_status: str = "pending"
    eligible_for_official_statement: bool = False
