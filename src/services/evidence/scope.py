"""Conservative rules for already-normalized, structured scopes."""

from src.services.evidence.drafts import FieldMatchDraft, IntervalDraft, ScopeAssessmentDraft, ScopeDraft

CORE_FIELDS = ("ingredient", "event", "population", "dose", "route", "time_window")


def _compare(field: str, claim, evidence, *, required: bool = False) -> FieldMatchDraft:
    if claim is None and evidence is None:
        return FieldMatchDraft(field, "unknown", "No scope value in either input", required)
    if claim is None:
        return FieldMatchDraft(field, "unknown", "Claim is broader than the documented scope; narrow or review", True)
    if evidence is None:
        return FieldMatchDraft(field, "unknown", "Source does not establish the requested scope", True)
    if isinstance(claim, IntervalDraft) and isinstance(evidence, IntervalDraft):
        if claim.unit != evidence.unit:
            return FieldMatchDraft(field, "unknown", "Units differ; a verified conversion is required", True)
        if claim == evidence:
            return FieldMatchDraft(field, "matched", "Same documented interval and unit", False)
        left_min = claim.lower if claim.lower is not None else float("-inf")
        left_max = claim.upper if claim.upper is not None else float("inf")
        right_min = evidence.lower if evidence.lower is not None else float("-inf")
        right_max = evidence.upper if evidence.upper is not None else float("inf")
        if left_max < right_min or right_max < left_min:
            return FieldMatchDraft(field, "mismatched", "Intervals do not overlap", True)
        return FieldMatchDraft(
            field, "unknown", "Different overlapping intervals; aggregate results do not establish subgroup effects", True
        )
    if type(claim) is not type(evidence):
        return FieldMatchDraft(field, "unknown", "Representations differ; normalize before comparison", True)
    if isinstance(claim, str) and isinstance(evidence, str):
        if " ".join(claim.casefold().split()) == " ".join(evidence.casefold().split()):
            return FieldMatchDraft(field, "matched", "Same normalized term", False)
        return FieldMatchDraft(field, "mismatched", "Different normalized terms", True)
    return FieldMatchDraft(field, "unknown", "Unsupported representation", True)


def assess_scope(evidence: ScopeDraft, claim: ScopeDraft) -> ScopeAssessmentDraft:
    """Scope eligibility is a necessary gate, not an assessment or an approval."""
    fields = [
        _compare(name, getattr(claim, name), getattr(evidence, name), required=name in {"ingredient", "event"})
        for name in CORE_FIELDS
    ]
    if claim.comparator is not None or evidence.comparator is not None:
        fields.append(_compare("comparator", claim.comparator, evidence.comparator))
    for name in sorted(set(claim.unresolved_critical_fields + evidence.unresolved_critical_fields)):
        fields.append(FieldMatchDraft(name, "unknown", "Critical context needs reviewer assessment", True))
    blocked = any(item.blocking for item in fields)
    return ScopeAssessmentDraft(tuple(fields), not blocked, blocked)


class ScopeMatcher:
    """Public-schema adapter. Missing targets never inherit the claim's values."""

    def assess_one(self, evidence, claim):
        from src.models.schemas import ScopeAssessment, ScopeComparison, ScopeOutcome, is_unknown
        from src.services.evidence.contracts import read_annotation

        annotation = read_annotation(evidence.notes)
        comparisons = []
        notes = []
        blocking_unknown = False
        for field in ("drug_ingredient", "event_term", "population", "dose", "route", "time_window"):
            claimed = getattr(claim, field)
            observed = getattr(annotation, field) if field in {"drug_ingredient", "event_term"} and annotation else (
                None if field in {"drug_ingredient", "event_term"} else getattr(evidence.scope, field)
            )
            comparison = ScopeComparison.compare(field, claimed, observed)
            # Different population/dose/time descriptions can overlap. Strings
            # alone do not establish disjoint intervals or subgroup effects.
            if comparison.outcome is ScopeOutcome.MISMATCH and field in {"population", "dose", "time_window"}:
                comparison = comparison.model_copy(update={"outcome": ScopeOutcome.UNKNOWN})
            optional_unspecified = field not in {"drug_ingredient", "event_term"} and is_unknown(claimed) and is_unknown(observed)
            if comparison.outcome is ScopeOutcome.UNKNOWN and not optional_unspecified:
                blocking_unknown = True
                notes.append(f"{evidence.evidence_id}: {field} requires scope review")
            comparisons.append(comparison)
        if claim.requires_review or claim.ambiguities or any(
            field in claim.unknowns for field in ("drug_ingredient", "event_term")
        ):
            blocking_unknown = True
            notes.append(f"{evidence.evidence_id}: claim target is unresolved")
        mismatch = any(item.outcome is ScopeOutcome.MISMATCH for item in comparisons)
        outcome = ScopeOutcome.MISMATCH if mismatch else ScopeOutcome.UNKNOWN if blocking_unknown else ScopeOutcome.MATCH
        return ScopeAssessment(
            outcome=outcome, comparisons=comparisons,
            matched_evidence_ids=[evidence.evidence_id] if outcome is ScopeOutcome.MATCH else [],
            mismatched_evidence_ids=[evidence.evidence_id] if mismatch else [], notes=notes,
        )

    def assess_scope(self, evidence, claim):
        from src.models.schemas import ScopeAssessment, ScopeOutcome

        results = [self.assess_one(item, claim) for item in evidence if not item.excluded]
        matched = [identifier for result in results for identifier in result.matched_evidence_ids]
        mismatched = [identifier for result in results for identifier in result.mismatched_evidence_ids]
        outcome = (
            ScopeOutcome.MATCH if matched else ScopeOutcome.MISMATCH
            if results and all(result.outcome is ScopeOutcome.MISMATCH for result in results)
            else ScopeOutcome.UNKNOWN
        )
        return ScopeAssessment(
            outcome=outcome, comparisons=[item for result in results for item in result.comparisons],
            matched_evidence_ids=matched, mismatched_evidence_ids=mismatched,
            notes=[note for result in results for note in result.notes],
        )
