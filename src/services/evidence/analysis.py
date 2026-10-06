"""Conservative evidence assessment using the shared MVP schema."""

from __future__ import annotations

from dataclasses import dataclass

from src.models.schemas import (
    AssessmentResult,
    AssessmentStatus,
    EvidenceGap,
    EvidenceType,
    EvidenceUnit,
    GapKind,
    NormalizedClaim,
    ScopeAssessment,
    ScopeOutcome,
    SourceDocument,
    Stance,
)
from src.services.assessment import coverage_from_evidence
from src.services.evidence.contracts import read_annotation
from src.services.evidence.contradiction import ContradictionAnalyzer
from src.services.evidence.scope import ScopeMatcher


@dataclass(frozen=True)
class EvidenceAnalysis:
    assessment: AssessmentResult
    scope: ScopeAssessment
    gaps: list[EvidenceGap]


def effective_public_stance(item: EvidenceUnit) -> Stance:
    annotation = read_annotation(item.notes)
    if item.source == "faers" or annotation is None:
        return Stance.UNCERTAIN
    if annotation.uncertainty != "low" or annotation.direction in {"no_clear_effect", "unknown"}:
        return Stance.UNCERTAIN
    if item.stance is Stance.CONTRADICTS and item.evidence_type is not EvidenceType.RCT:
        # An observational null or absent label warning is not a rebuttal.
        return Stance.UNCERTAIN
    return item.stance


class EvidenceAnalyzer:
    def __init__(self):
        self.scope_matcher = ScopeMatcher()
        self.contradiction_analyzer = ContradictionAnalyzer()

    def analyze(self, evidence: list[EvidenceUnit], claim: NormalizedClaim) -> EvidenceAnalysis:
        active = [item for item in evidence if not item.excluded]
        scope = self.scope_matcher.assess_scope(active, claim)
        comparable = [item for item in active if item.evidence_id in scope.matched_evidence_ids]
        precise = [item.model_copy(update={"stance": effective_public_stance(item)}) for item in active]
        gaps = self.contradiction_analyzer.analyze_contradictions(precise, claim)
        support = [item for item in comparable if effective_public_stance(item) is Stance.SUPPORTS]
        contrary = [item for item in comparable if effective_public_stance(item) is Stance.CONTRADICTS]
        status = AssessmentStatus.INSUFFICIENT_EVIDENCE
        reason = "No precise evidence with an established claim target and applicable scope."
        if claim.requires_review or claim.ambiguities:
            status, reason = AssessmentStatus.REQUIRES_HUMAN_REVIEW, "Claim normalization requires review."
        elif any(gap.kind is GapKind.CONTRADICTION for gap in gaps) or (support and contrary):
            status, reason = AssessmentStatus.REQUIRES_HUMAN_REVIEW, "Opposing findings require adjudication."
        elif support:
            status, reason = AssessmentStatus.SUPPORTED_FOR_SCOPE, "Retrieved evidence supports the claim only within the matched scope."
        elif contrary:
            status, reason = AssessmentStatus.CONTRADICTED_FOR_SCOPE, "Precise comparative evidence opposes the claim within the matched scope."
        elif scope.outcome is ScopeOutcome.MISMATCH:
            status, reason = AssessmentStatus.SCOPE_MISMATCH, "Retrieved evidence differs on a critical scope field."
        if scope.notes:
            gaps.append(EvidenceGap(
                gap_id="GAP-P3-SCOPE-UNKNOWN", kind=GapKind.MISSING_EVIDENCE, field="scope",
                description="Scope not established: " + "; ".join(scope.notes)[:900], priority=4,
            ))
        return EvidenceAnalysis(
            assessment=AssessmentResult(
                assessment_status=status, rationale=reason,
                evidence_ids=[item.evidence_id for item in (support + contrary)],
                scope_notes=scope.notes,
                # API-03: cùng cách đếm với đường MVP, để giao diện không phải suy báo phủ từ câu hỏi.
                coverage=coverage_from_evidence(active, claim),
            ), scope=scope, gaps=gaps,
        )


def duplicate_report_candidates(documents: list[SourceDocument]) -> list[tuple[str, ...]]:
    """Tag repeated FAERS case IDs without deleting reports or estimating incidence."""
    groups = {}
    for document in documents:
        case_id = document.metadata.get("case_id")
        if document.source != "faers" or not isinstance(case_id, str) or not case_id.strip():
            continue
        groups.setdefault(case_id.strip(), set()).add(document.doc_id)
    return [tuple(sorted(ids)) for ids in groups.values() if len(ids) > 1]
