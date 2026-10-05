"""Candidate comparisons of explicit evidence drafts, not medical adjudication."""

from src.services.evidence.drafts import ContradictionDraft, EvidenceDraft
from src.services.evidence.scope import assess_scope


def effective_stance(evidence: EvidenceDraft) -> str:
    if evidence.source == "faers":
        return "background"
    if evidence.stance in {"support", "contradict"} and (
        evidence.uncertainty != "low" or evidence.direction in {"unknown", "no_clear_effect"}
    ):
        return "uncertain"
    return evidence.stance


def compare_evidence(left: EvidenceDraft, right: EvidenceDraft) -> ContradictionDraft:
    if left.evidence_id == right.evidence_id:
        raise ValueError("Cannot compare an evidence unit with itself")

    def result(kind: str, reason: str, fields: tuple[str, ...] = (), review: bool = False):
        return ContradictionDraft(left.evidence_id, right.evidence_id, kind, reason, fields, review)

    assessment = assess_scope(right.scope, left.scope)
    by_field = {item.field: item for item in assessment.fields}
    if any(by_field[name].status != "matched" for name in ("ingredient", "event")):
        return result("not_comparable", "Different or unresolved drug/event target")
    if left.source == "faers" or right.source == "faers":
        return result("not_comparable", "Spontaneous reports cannot establish a comparative contradiction")
    if {effective_stance(left), effective_stance(right)} != {"support", "contradict"}:
        return result("none", "No pair of sufficiently precise opposing findings")
    if {left.direction, right.direction} != {"increase", "decrease"}:
        return result("needs_review", "Stance labels disagree but explicit directions are not opposite", review=True)
    mismatches = tuple(item.field for item in assessment.fields if item.status == "mismatched")
    unknowns = tuple(item.field for item in assessment.fields if item.status == "unknown")
    if left.scope.comparator is None and right.scope.comparator is None:
        unknowns += ("comparator",)
    if mismatches:
        return result("apparent", "Opposing findings apply to different scopes", mismatches, True)
    if unknowns:
        return result("needs_review", "Comparability is incomplete; a direct contradiction is not established", unknowns, True)
    return result("direct", "Opposing findings in the same explicit scope; reviewer must resolve", review=True)


class ContradictionAnalyzer:
    """Convert comparable opposing findings into typed planner gaps."""

    def analyze_contradictions(self, evidence, claim):
        from hashlib import sha256
        from itertools import combinations

        from src.models.schemas import EvidenceGap, GapKind, ScopeComparison, ScopeOutcome, Stance
        from src.services.evidence.contracts import read_annotation

        gaps = []
        for left, right in combinations([item for item in evidence if not item.excluded], 2):
            if left.doc_id == right.doc_id or left.source == "faers" or right.source == "faers":
                continue
            if {left.stance, right.stance} != {Stance.SUPPORTS, Stance.CONTRADICTS}:
                continue
            a, b = read_annotation(left.notes), read_annotation(right.notes)
            if a is None or b is None or a.uncertainty != "low" or b.uncertainty != "low":
                continue
            if {a.direction, b.direction} != {"increase", "decrease"}:
                continue
            targets = [ScopeComparison.compare(name, getattr(a, name), getattr(b, name))
                       for name in ("drug_ingredient", "event_term")]
            if any(item.outcome is not ScopeOutcome.MATCH for item in targets):
                continue
            comparisons = [ScopeComparison.compare(name, getattr(left.scope, name), getattr(right.scope, name))
                           for name in ("population", "dose", "route", "time_window")]
            comparisons.append(ScopeComparison.compare("comparator", a.comparator, b.comparator))
            differences = [item.field for item in comparisons if item.outcome is ScopeOutcome.MISMATCH]
            unknowns = [item.field for item in comparisons if item.outcome is ScopeOutcome.UNKNOWN]
            pair = ", ".join(sorted((left.evidence_id, right.evidence_id)))
            suffix = sha256(pair.encode("utf-8")).hexdigest()[:20]
            if differences:
                kind = GapKind.SCOPE_MISMATCH
                description = f"Apparent contradiction [{pair}]: differing scope ({', '.join(differences)}); not direct rebuttal."
            elif unknowns:
                kind = GapKind.CONTRADICTION
                description = f"Comparability pending [{pair}]: unknown {', '.join(unknowns)}; review required."
            else:
                kind = GapKind.CONTRADICTION
                description = f"Direct contradiction candidate [{pair}]: opposing findings in the same explicit scope; review required."
            gaps.append(EvidenceGap(
                gap_id=f"GAP-P3-PAIR-{suffix}", kind=kind, description=description,
                priority=5 if kind is GapKind.CONTRADICTION else 3,
            ))
        return gaps
