"""Đánh giá bằng chứng → ``AssessmentStatus`` (M05, bản mock dùng chung với node của Người 3).

Quy tắc bất biến:
  * chỉ FAERS ⇒ ``insufficient_evidence`` (không bao giờ ``supported_for_scope``);
  * mâu thuẫn cùng phạm vi ⇒ ``contradicted_for_scope``; khác phạm vi ⇒ ``requires_human_review`` (biểu kiến);
  * bằng chứng khác phạm vi với claim ⇒ ``scope_mismatch``;
  * không có bằng chứng hoặc chỉ có bằng chứng ``uncertain`` ⇒ ``insufficient_evidence``.

EV-07: hàm ở đây **không** còn sinh ``confidence``. Các con số cũ (0.0/0.2/0.3/0.4/0.5/0.9) là hằng
số viết tay, chưa từng được hiệu chỉnh bằng dữ liệu thật, nhưng nằm ngay cạnh trích đoạn nên bị
đọc như xác suất đúng. Thay vào đó ``AssessmentResult.coverage`` ghi lại **bằng chứng đã thật sự
tìm được** phủ tới đâu, đếm trực tiếp từ danh sách bằng chứng.
"""

from __future__ import annotations

from src.models.schemas import (
    AssessmentResult,
    AssessmentStatus,
    EvidenceUnit,
    NormalizedClaim,
    ScopeOutcome,
    Stance,
    compare_scope,
)
from src.services.planner import STRONG_EVIDENCE_SOURCES

#: Trùng khớp với ``COVERAGE_KEYS`` của giao diện (``frontend/lib/api/real.ts``).
COVERAGE_FIELDS = ("drug", "adverseEvent", "population", "dose", "route", "timeWindow")

#: Trường của ``EvidenceScope`` ứng với từng khoá báo phủ.
_SCOPE_FIELD = {"population": "population", "dose": "dose", "route": "route", "timeWindow": "time_window"}


def _known_scope_outcomes(claim: NormalizedClaim, evidence: EvidenceUnit) -> dict[str, ScopeOutcome]:
    return {item.field: item.outcome for item in compare_scope(claim, evidence.scope)}


def _mismatch_fields(claim: NormalizedClaim, evidence: EvidenceUnit) -> list[str]:
    return [field for field, outcome in _known_scope_outcomes(claim, evidence).items() if outcome is ScopeOutcome.MISMATCH]


def _matches_claim_scope(claim: NormalizedClaim, evidence: EvidenceUnit) -> bool:
    """Khớp khi không có trường nào mismatch và ít nhất một trường so khớp là ``match``."""
    outcomes = _known_scope_outcomes(claim, evidence)
    if any(outcome is ScopeOutcome.MISMATCH for outcome in outcomes.values()):
        return False
    return any(outcome is ScopeOutcome.MATCH for outcome in outcomes.values())


def coverage_from_evidence(active: list[EvidenceUnit], claim: NormalizedClaim) -> dict[str, str]:
    """Báo phủ bằng chứng theo từng trường của câu hỏi (API-03).

    Đếm từ **bằng chứng đang hoạt động**, không phải từ câu hỏi. Giá trị:

    ``verified``
        Có bằng chứng khớp trường đó. Với ``drug``/``adverseEvent``: có ít nhất một đơn vị bằng
        chứng, vì mọi bằng chứng đều được truy hồi theo đúng thuốc/biến cố của câu hỏi.
    ``partial``
        Có bằng chứng nêu trường đó nhưng không trường nào khớp.
    ``not_specified``
        Câu hỏi có nêu trường đó nhưng chưa bằng chứng nào nói tới.
    ``missing``
        Câu hỏi không nêu trường đó.
    """
    if not active:
        return {field: "not_specified" for field in COVERAGE_FIELDS}

    coverage: dict[str, str] = {"drug": "verified", "adverseEvent": "verified"}
    for key in ("population", "dose", "route", "timeWindow"):
        claim_value = getattr(claim, _SCOPE_FIELD[key], None)
        if claim_value is None or not str(claim_value).strip():
            coverage[key] = "missing"
            continue
        mentioned = False
        matched = False
        for item in active:
            evidence_value = getattr(item.scope, _SCOPE_FIELD[key], None)
            if evidence_value is None or not str(evidence_value).strip():
                continue
            mentioned = True
            for comparison in compare_scope(claim, item.scope):
                if comparison.field == _SCOPE_FIELD[key] and comparison.outcome is ScopeOutcome.MATCH:
                    matched = True
                    break
            if matched:
                break
        coverage[key] = "verified" if matched else ("partial" if mentioned else "not_specified")
    return coverage


def assess_evidence(state_evidence: list[EvidenceUnit], claim: NormalizedClaim) -> AssessmentResult:
    """Sinh ``AssessmentResult`` từ danh sách bằng chứng đang hoạt động."""
    active = [item for item in state_evidence if not item.excluded]
    if not active:
        return AssessmentResult(
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            rationale="Chưa thu được bằng chứng nào cho claim.",
            coverage=coverage_from_evidence(active, claim),
        )

    sources = {item.source for item in active}
    supporting = [item for item in active if item.stance is Stance.SUPPORTS]
    contradicting = [item for item in active if item.stance is Stance.CONTRADICTS]
    strong_supporting = [item for item in supporting if item.source in STRONG_EVIDENCE_SOURCES]
    coverage = coverage_from_evidence(active, claim)

    if sources <= {"faers"}:
        return AssessmentResult(
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            rationale=(
                "Chỉ có báo cáo tự nguyện FAERS: không xác minh được, không tính được tỷ lệ và "
                "không đủ để kết luận."
            ),
            evidence_ids=[item.evidence_id for item in active],
            scope_notes=["FAERS không thiết lập quan hệ nhân quả."],
            coverage=coverage,
        )

    same_scope_contradiction = [
        item
        for item in contradicting
        if _matches_claim_scope(claim, item) and any(_matches_claim_scope(claim, other) for other in supporting)
    ]
    if same_scope_contradiction:
        return AssessmentResult(
            assessment_status=AssessmentStatus.CONTRADICTED_FOR_SCOPE,
            rationale="Có bằng chứng phản bác cùng phạm vi với claim; cần người phân xử.",
            evidence_ids=[item.evidence_id for item in active],
            scope_notes=["Mâu thuẫn trực tiếp trong cùng phạm vi."],
            coverage=coverage,
        )

    if contradicting:
        return AssessmentResult(
            assessment_status=AssessmentStatus.REQUIRES_HUMAN_REVIEW,
            rationale=(
                "Có bằng chứng trái chiều nhưng khác phạm vi (quần thể/liều/đường dùng); "
                "không phải mâu thuẫn trực tiếp nên cần người phân xử."
            ),
            evidence_ids=[item.evidence_id for item in active],
            scope_notes=[
                f"Phạm vi lệch ở: {', '.join(_mismatch_fields(claim, item)) or 'không xác định'}"
                for item in contradicting
            ],
            coverage=coverage,
        )

    matching_support = [item for item in strong_supporting if _matches_claim_scope(claim, item)]
    if matching_support:
        return AssessmentResult(
            assessment_status=AssessmentStatus.SUPPORTED_FOR_SCOPE,
            rationale="Có bằng chứng từ nguồn mạnh khớp phạm vi claim và không có phản bác cùng phạm vi.",
            evidence_ids=[item.evidence_id for item in matching_support],
            scope_notes=[],
            coverage=coverage,
        )

    if strong_supporting:
        fields = sorted({field for item in strong_supporting for field in _mismatch_fields(claim, item)})
        if not fields:
            # Không trường nào lệch thật: mọi so khớp đều ``unknown`` ⇒ chưa đủ căn cứ
            # kết luận "ngoài phạm vi"; giữ ở mức chưa đủ bằng chứng.
            return AssessmentResult(
                assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
                rationale=(
                    "Bằng chứng mạnh nhưng phạm vi chưa xác định được (thiếu trường so khớp) — "
                    "không kết luận khớp hay lệch."
                ),
                evidence_ids=[item.evidence_id for item in strong_supporting],
                scope_notes=["Phạm vi chưa xác định: không có trường nào so khớp được."],
                coverage=coverage,
            )
        return AssessmentResult(
            assessment_status=AssessmentStatus.SCOPE_MISMATCH,
            rationale=(
                "Bằng chứng hiện có nằm ngoài phạm vi claim; không được suy rộng sang quần thể/liều của claim."
            ),
            evidence_ids=[item.evidence_id for item in strong_supporting],
            scope_notes=[f"Lệch phạm vi: {', '.join(fields)}"],
            coverage=coverage,
        )

    return AssessmentResult(
        assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
        rationale="Bằng chứng hiện có chưa đủ hoặc chưa xác định (uncertain).",
        evidence_ids=[item.evidence_id for item in active],
        coverage=coverage,
    )
