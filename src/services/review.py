"""Nghiệp vụ review của con người (M06).

Quy tắc (planMVPfinal §8 M06, docs/mvp-contracts.md mục "Quy tắc vô hiệu hóa"):

  * quyết định của reviewer được lưu **trước** khi áp dụng (audit trail);
  * ``reviewer_id`` lấy từ token phía server, không bao giờ lấy từ body;
  * sửa claim/scope ⇒ vô hiệu hóa normalization + assessment + dossier;
  * thêm/sửa/xóa bằng chứng ⇒ vô hiệu hóa assessment + dossier;
  * ``approve`` ở checkpoint assessment **không** tự duyệt hồ sơ;
  * ``request_more`` giữ nguyên toàn bộ bộ đếm ngân sách;
  * replay cùng ``decision_id`` hoặc ``expected_version`` cũ bị chặn.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from src.models.schemas import (
    CheckpointKind,
    ClaimInput,
    EvidenceScope,
    EvidenceUnit,
    InvestigationState,
    QuoteLocator,
    ReviewAction,
    ReviewDecision,
    ReviewResult,
    ReviewStatus,
    RunStatus,
)
from src.services.dossier import validate_dossier
from src.services.errors import (
    dossier_invalid,
    idempotency_conflict,
    invalid_request,
    invalid_state,
    not_found,
    validation_details,
    version_conflict,
)
from src.services.store import MvpStore

#: Hành động nào vô hiệu hóa phần nào (dùng cho thông báo ra UI).
INVALIDATION_TABLE: dict[ReviewAction, tuple[str, ...]] = {
    ReviewAction.APPROVE: (),
    ReviewAction.REJECT: ("assessment", "dossier"),
    ReviewAction.EDIT_CLAIM: ("normalization", "assessment", "dossier"),
    ReviewAction.EDIT_EVIDENCE: ("assessment", "dossier"),
    ReviewAction.EXCLUDE_EVIDENCE: ("assessment", "dossier"),
    ReviewAction.REQUEST_MORE: ("assessment", "dossier"),
}

#: Trường được phép sửa trong ``edit_claim``.
CLAIM_EDIT_FIELDS = ("drug", "event", "population", "dose", "route", "time_window")

#: Trường được phép sửa trong ``edit_evidence``.
EVIDENCE_EDIT_FIELDS = ("quote", "stance", "scope", "confidence", "notes")


def apply_review(store: MvpStore, decision: ReviewDecision) -> ReviewResult:
    """Áp dụng một quyết định review lên state; trả về kết quả để API hiển thị."""
    state = _load_state(store, decision.investigation_id)

    if store.get_review_decision(decision.decision_id) is not None:
        raise idempotency_conflict(decision.decision_id)
    if state.version != decision.expected_version:
        raise version_conflict(decision.expected_version, state.version)
    reopen_completed = (
        state.run_status is RunStatus.COMPLETED
        and state.checkpoint is None
        and decision.checkpoint is CheckpointKind.ASSESSMENT
        and decision.action in {
            ReviewAction.EDIT_CLAIM, ReviewAction.EDIT_EVIDENCE,
            ReviewAction.EXCLUDE_EVIDENCE, ReviewAction.REQUEST_MORE,
        }
    )
    if state.checkpoint is not decision.checkpoint and not reopen_completed:
        raise invalid_state(
            "Checkpoint không khớp trạng thái hiện tại của cuộc điều tra.",
            {"expected": str(state.checkpoint), "received": str(decision.checkpoint)},
        )

    # Lưu quyết định trước khi áp dụng để không mất audit trail khi bước sau lỗi.
    store.save_review_decision(decision)

    handler = {
        ReviewAction.APPROVE: _approve,
        ReviewAction.REJECT: _reject,
        ReviewAction.EDIT_CLAIM: _edit_claim,
        ReviewAction.EDIT_EVIDENCE: _edit_evidence,
        ReviewAction.EXCLUDE_EVIDENCE: _exclude_evidence,
        ReviewAction.REQUEST_MORE: _request_more,
    }[decision.action]
    return handler(store, state, decision)


# --------------------------------------------------------------------------------------
# Từng hành động
# --------------------------------------------------------------------------------------


def _approve(store: MvpStore, state: InvestigationState, decision: ReviewDecision) -> ReviewResult:
    if decision.checkpoint is CheckpointKind.DOSSIER:
        dossier = store.latest_dossier(state.investigation_id)
        if dossier is None:
            raise invalid_state("Chưa có hồ sơ nào để duyệt.", {"investigation_id": state.investigation_id})
        if dossier.status is ReviewStatus.APPROVED:
            raise invalid_state("Hồ sơ phiên bản này đã được duyệt.", {"version": dossier.version})
        report = validate_dossier(dossier, state)
        if report.errors:
            raise dossier_invalid(state.investigation_id, report.errors)
        approved = store.update_dossier_status(
            state.investigation_id,
            dossier.version,
            ReviewStatus.APPROVED,
            approved_by=decision.reviewer_id,
            approved_at=datetime.now(UTC),
        )
        saved = _save(
            store,
            state.model_copy(update={"run_status": RunStatus.COMPLETED, "checkpoint": None, "next_stage": None}),
            decision,
            "review_approved",
        )
        return _result(saved, decision, f"Đã duyệt hồ sơ phiên bản {approved.version}.", [])

    # Duyệt kết luận ở checkpoint assessment: hồ sơ vẫn phải được duyệt riêng.
    # Duyệt ở checkpoint normalization chỉ chốt hoạt chất ⇒ quay lại vòng điều tra,
    # không được nhảy thẳng tới hồ sơ khi chưa hề đánh giá bằng chứng.
    next_stage = "build_dossier" if decision.checkpoint is CheckpointKind.ASSESSMENT else "checklist"
    saved = _save(
        store,
        state.model_copy(
            update={
                "run_status": RunStatus.WAITING_FOR_REVIEW,
                "checkpoint": None,
                "next_stage": next_stage,
            }
        ),
        decision,
        "review_approved",
    )
    if next_stage == "build_dossier":
        return _result(
            saved,
            decision,
            "Đã duyệt kết luận; hồ sơ chưa được duyệt và cần một quyết định riêng.",
            [],
        )
    return _result(
        saved,
        decision,
        "Đã chốt hoạt chất; cần gọi continue để chạy tiếp vòng thu thập bằng chứng.",
        [],
    )


def _reject(store: MvpStore, state: InvestigationState, decision: ReviewDecision) -> ReviewResult:
    invalidated = list(INVALIDATION_TABLE[ReviewAction.REJECT])
    store.invalidate_dossiers(state.investigation_id)
    saved = _save(
        store,
        state.model_copy(
            update={
                "run_status": RunStatus.COMPLETED,
                "checkpoint": None,
                "next_stage": None,
            }
        ),
        decision,
        "review_rejected",
    )
    return _result(saved, decision, "Đã từ chối; cuộc điều tra không tự chạy lại.", invalidated)


def _edit_claim(store: MvpStore, state: InvestigationState, decision: ReviewDecision) -> ReviewResult:
    payload = {key: value for key, value in decision.payload.items() if key in CLAIM_EDIT_FIELDS}
    if not payload:
        raise invalid_state(
            "edit_claim cần ít nhất một trường claim hợp lệ.",
            {"allowed": list(CLAIM_EDIT_FIELDS)},
        )
    claim = ClaimInput.model_validate({**state.claim.model_dump(), **payload})
    # Claim đổi ⇒ phải chuẩn hoá lại từ đầu; bằng chứng cũ được giữ để kiểm toán nhưng
    # kết luận cũ không còn giá trị.
    store.invalidate_dossiers(state.investigation_id)
    saved = _save(
        store,
        state.model_copy(
            update={
                "claim": claim,
                "normalized_claim": None,
                "assessment": None,
                "assessment_status": None,
                "run_status": RunStatus.WAITING_FOR_REVIEW,
                "checkpoint": None,
                "next_stage": None,
            }
        ),
        decision,
        "review_edit_claim",
    )
    return _result(
        saved,
        decision,
        "Đã cập nhật claim; cần chuẩn hoá và đánh giá lại trước khi duyệt.",
        list(INVALIDATION_TABLE[ReviewAction.EDIT_CLAIM]),
    )


def _edit_evidence(store: MvpStore, state: InvestigationState, decision: ReviewDecision) -> ReviewResult:
    evidence, updates = _target_evidence(state, decision)
    if not updates:
        raise invalid_state(
            "edit_evidence cần ít nhất một trường bằng chứng hợp lệ.",
            {"allowed": list(EVIDENCE_EDIT_FIELDS)},
        )
    if "scope" in updates and isinstance(updates["scope"], dict):
        try:
            updates["scope"] = EvidenceScope.model_validate({**evidence.scope.model_dump(), **updates["scope"]})
        except ValidationError as exc:
            raise invalid_request(
                "Phạm vi sửa không hợp lệ.", {"errors": validation_details(exc)}
            ) from exc
    if "quote" in updates:
        updates["quote"], updates["locator"] = _relocate_quote(store, state, evidence, str(updates["quote"]))
    if any(field in updates for field in ("quote", "scope", "stance")):
        from src.services.evidence.contracts import read_annotation

        annotation = read_annotation(evidence.notes)
        if annotation is not None:
            # Original extraction context cannot establish semantics of an edited quote/scope.
            annotation.drug_ingredient = None
            annotation.event_term = None
            annotation.comparator = None
            annotation.direction = "unknown"
            annotation.uncertainty = "unknown"
            annotation.issues = ["review_edit_requires_reextraction"]
            updates["notes"] = annotation.to_notes()
    try:
        edited = EvidenceUnit.model_validate(
            {**evidence.model_dump(), **updates, "version": evidence.version + 1}
        )
    except ValidationError as exc:
        raise invalid_request(
            "Dữ liệu sửa bằng chứng không hợp lệ.", {"errors": validation_details(exc)}
        ) from exc
    return _apply_evidence_change(store, state, decision, edited, "Đã sửa bằng chứng")


def _relocate_quote(
    store: MvpStore, state: InvestigationState, evidence: EvidenceUnit, quote: str
) -> tuple[str, QuoteLocator]:
    """Kiểm chứng lại nguyên văn sau khi reviewer sửa: phải có thật trong tài liệu nguồn."""
    if not quote.strip():
        raise invalid_request("Trích dẫn sửa không được để trống.", {"evidence_id": evidence.evidence_id})
    document = store.get_document(state.investigation_id, evidence.doc_id)
    start = document.text.find(quote)
    if start < 0:
        raise invalid_request(
            "Trích dẫn sửa không khớp nguyên văn trong tài liệu nguồn.",
            {"evidence_id": evidence.evidence_id, "doc_id": evidence.doc_id},
        )
    return quote, QuoteLocator(start=start, end=start + len(quote), section=evidence.locator.section)


def _exclude_evidence(store: MvpStore, state: InvestigationState, decision: ReviewDecision) -> ReviewResult:
    evidence, _ = _target_evidence(state, decision)
    excluded = evidence.model_copy(
        update={
            "excluded": True,
            "version": evidence.version + 1,
            "notes": (decision.reason or "Reviewer loại bỏ bằng chứng.")[:1000],
        }
    )
    return _apply_evidence_change(store, state, decision, excluded, "Đã loại bỏ bằng chứng")


def _request_more(store: MvpStore, state: InvestigationState, decision: ReviewDecision) -> ReviewResult:
    # Giữ nguyên toàn bộ budget: chỉ mở lại vòng điều tra.
    store.invalidate_dossiers(state.investigation_id)
    saved = _save(
        store,
        state.model_copy(
            update={
                "run_status": RunStatus.WAITING_FOR_REVIEW,
                "checkpoint": None,
                "next_stage": "checklist",
            }
        ),
        decision,
        "review_request_more",
    )
    return _result(
        saved,
        decision,
        "Yêu cầu thu thập thêm; ngân sách giữ nguyên, cần gọi continue để chạy tiếp.",
        list(INVALIDATION_TABLE[ReviewAction.REQUEST_MORE]),
    )


# --------------------------------------------------------------------------------------
# Helper
# --------------------------------------------------------------------------------------


def _load_state(store: MvpStore, investigation_id: str) -> InvestigationState:
    """Đọc state; store đã ném ``not_found`` (404) cho ID lạ, còn lại để lỗi thật nổi lên."""
    return store.get_state(investigation_id)


def _target_evidence(
    state: InvestigationState, decision: ReviewDecision
) -> tuple[EvidenceUnit, dict[str, object]]:
    if not decision.target_evidence_id:
        raise invalid_state(
            f"{decision.action} cần target_evidence_id.",
            {"action": str(decision.action)},
        )
    evidence = next(
        (item for item in state.evidence if item.evidence_id == decision.target_evidence_id),
        None,
    )
    if evidence is None:
        raise not_found("bằng chứng", decision.target_evidence_id)
    updates = {
        key: value for key, value in decision.payload.items() if key in EVIDENCE_EDIT_FIELDS and value is not None
    }
    return evidence, updates


def _apply_evidence_change(
    store: MvpStore,
    state: InvestigationState,
    decision: ReviewDecision,
    edited: EvidenceUnit,
    message: str,
) -> ReviewResult:
    store.save_evidence(state.investigation_id, edited)
    evidence = [edited if item.evidence_id == edited.evidence_id else item for item in state.evidence]
    store.invalidate_dossiers(state.investigation_id)
    saved = _save(
        store,
        state.model_copy(
            update={
                "evidence": evidence,
                "assessment": None,
                "assessment_status": None,
                "run_status": RunStatus.WAITING_FOR_REVIEW,
                "checkpoint": None,
                "next_stage": "checklist",
            }
        ),
        decision,
        "review_evidence_changed",
    )
    return _result(
        saved,
        decision,
        f"{message} (phiên bản {edited.version}); kết luận và hồ sơ cũ đã bị vô hiệu hóa.",
        list(INVALIDATION_TABLE[decision.action]),
    )


def _save(
    store: MvpStore,
    state: InvestigationState,
    decision: ReviewDecision,
    event_kind: str,
) -> InvestigationState:
    return store.save_state(
        state,
        event=(event_kind, f"{decision.action} bởi {decision.reviewer_id}: {decision.reason or 'không kèm lý do'}"),
        actor=decision.reviewer_id,
    )


def _result(
    state: InvestigationState,
    decision: ReviewDecision,
    message: str,
    invalidated: list[str],
) -> ReviewResult:
    return ReviewResult(
        investigation_id=state.investigation_id,
        version=state.version,
        run_status=state.run_status,
        review_status=_review_status(decision.action),
        invalidated=invalidated,
        message=message,
    )


def _review_status(action: ReviewAction) -> ReviewStatus:
    if action is ReviewAction.APPROVE:
        return ReviewStatus.APPROVED
    if action is ReviewAction.REJECT:
        return ReviewStatus.REJECTED
    return ReviewStatus.CHANGES_REQUESTED


def export_ready(store: MvpStore, investigation_id: str) -> bool:
    """Chỉ hồ sơ đã duyệt mới được export."""
    return store.approved_dossier(investigation_id) is not None


def assessment_approved(store: MvpStore, investigation_id: str) -> bool:
    """Kết luận đã được reviewer duyệt (dùng cho gate ở tầng API)."""
    return any(
        decision.checkpoint is CheckpointKind.ASSESSMENT and decision.action is ReviewAction.APPROVE
        for decision in store.list_review_decisions(investigation_id)
    )
