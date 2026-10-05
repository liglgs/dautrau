"""Bộ đánh giá dừng/tiếp tục (M05).

Thứ tự ưu tiên:
  1. Claim mơ hồ / cần người phân xử ⇒ ``needs_review`` (không tự kết luận).
  2. Mâu thuẫn thật hoặc biểu kiến ⇒ ``needs_review``.
  3. Bão hoà: 2 bước liên tiếp không có thông tin mới ⇒ ``saturation`` → ``insufficient_evidence``.
  4. Hết ngân sách bước (đã trừ dự phòng hồ sơ) ⇒ ``budget_exhausted`` → ``insufficient_evidence``.
  5. Nguồn chính lỗi và không còn bằng chứng ⇒ ``source_error`` → ``insufficient_evidence``.
  6. Đủ bằng chứng đạt chuẩn ⇒ ``success``.
  7. Còn chiến lược ⇒ tiếp tục.
"""

from __future__ import annotations

from src.models.schemas import (
    AssessmentStatus,
    GapKind,
    InvestigationState,
    RunStatus,
    SourceStatus,
    StopDecision,
    StopReason,
)
from src.services.budget import can_spend, dossier_step_available
from src.services.planner import SOURCE_PRIORITY, contrary_attempted

#: Số bước liên tiếp không có thông tin mới thì coi là bão hoà.
SATURATION_THRESHOLD = 2

#: Nguồn được coi là "mạnh" cho kết luận supported_for_scope.
CONCLUSIVE_STATUSES = {
    AssessmentStatus.SUPPORTED_FOR_SCOPE,
    AssessmentStatus.SCOPE_MISMATCH,
    AssessmentStatus.CONTRADICTED_FOR_SCOPE,
}


def evaluate_stop(state: InvestigationState) -> StopDecision:
    """Quyết định dừng/tiếp tục cho state hiện tại."""
    claim = state.normalized_claim

    if claim is not None and claim.ambiguities:
        return StopDecision(
            should_stop=True,
            reason=StopReason.NEEDS_REVIEW,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=None,
            message="Claim mơ hồ: cần reviewer chốt hoạt chất trước khi truy xuất.",
        )

    if any(gap.kind is GapKind.CONTRADICTION for gap in state.gaps):
        return StopDecision(
            should_stop=True,
            reason=StopReason.NEEDS_REVIEW,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=AssessmentStatus.REQUIRES_HUMAN_REVIEW,
            message="Có mâu thuẫn cần người phân xử.",
        )

    status = state.assessment_status
    if status in CONCLUSIVE_STATUSES and state.active_evidence() and _ready_to_conclude(state):
        return StopDecision(
            should_stop=True,
            reason=StopReason.SUCCESS,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=status,
            message="Đủ bằng chứng đạt chuẩn cho kết luận trong phạm vi claim.",
        )

    if _primary_source_failed(state):
        return StopDecision(
            should_stop=True,
            reason=StopReason.SOURCE_ERROR,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            message="Nguồn chính lỗi và không có bằng chứng thay thế.",
        )

    if state.no_progress_streak >= SATURATION_THRESHOLD and not _unsearched_sources(state):
        return StopDecision(
            should_stop=True,
            reason=StopReason.SATURATION,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            message=f"{SATURATION_THRESHOLD} bước liên tiếp không có thông tin mới.",
        )

    if not dossier_step_available(state.budget):
        return StopDecision(
            should_stop=True,
            reason=StopReason.BUDGET_EXHAUSTED,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            message="Hết ngân sách bước; chuyển sang hồ sơ thiếu sót kèm lý do dừng.",
        )

    ok, _ = can_spend(state.budget, steps=1)
    if not ok and not state.evidence:
        return StopDecision(
            should_stop=True,
            reason=StopReason.BUDGET_EXHAUSTED,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            message="Hết ngân sách trước khi thu được bằng chứng nào.",
        )

    return StopDecision(should_stop=False, run_status=RunStatus.RUNNING)


def _unsearched_sources(state: InvestigationState) -> list[str]:
    return [source for source in SOURCE_PRIORITY if source not in state.searched_sources]


def _ready_to_conclude(state: InvestigationState) -> bool:
    """Chỉ kết luận khi đã chủ động tìm bằng chứng phản bác.

    Riêng kết luận ``supported_for_scope`` (khẳng định dương tính) luôn phải có bước
    tìm bằng chứng phản bác **và** bằng chứng thật sự đến từ ≥2 nguồn; nếu chỉ có một
    nguồn thì phải là ≥2 đơn vị bằng chứng từ ≥2 tài liệu khác nhau (hai nghiên cứu độc
    lập cùng nguồn vẫn tính, hai trích đoạn của cùng một tài liệu thì không). Nguồn đã
    gọi nhưng không trả kết quả không tính là nguồn thứ hai.
    Các kết luận còn lại có thể dừng khi đã thử ≥2 nguồn.
    """
    contrary = contrary_attempted(state)
    if state.assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE:
        evidence = state.active_evidence()
        # Person 3 supplies verified target/scope context. Only observations used
        # in its current assessment count toward the independent-document gate;
        # edited/unknown observations remain visible for audit, not corroboration.
        from src.services.evidence.contracts import read_annotation

        if state.assessment and any(read_annotation(item.notes) is not None for item in evidence):
            qualifying_ids = set(state.assessment.evidence_ids)
            evidence = [item for item in evidence if item.evidence_id in qualifying_ids]
        distinct_documents = {item.doc_id for item in evidence}
        return contrary and (
            len({item.source for item in evidence}) >= 2 or (len(evidence) >= 2 and len(distinct_documents) >= 2)
        )
    return contrary or len(set(state.searched_sources)) >= 2


def _primary_source_failed(state: InvestigationState) -> bool:
    """Có nguồn lỗi, chưa thu được bằng chứng nào, và đã thử ít nhất 2 bước (hoặc hết nguồn để thử)."""
    if state.evidence:
        return False
    statuses = state.source_status
    if not statuses or not any(status is SourceStatus.ERROR for status in statuses.values()):
        return False
    return state.step_index >= 2 or not _unsearched_sources(state)
