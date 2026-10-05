"""Kiểm thử nghiệp vụ review & versioning (M06).

Phạm vi:
  * các hành động reviewer: approve / reject / edit_claim / edit_evidence / exclude_evidence / request_more;
  * invalidation: sửa bằng chứng ⇒ export bị chặn tới khi duyệt lại;
  * ``approve`` kết luận không tự duyệt hồ sơ;
  * ``request_more`` giữ nguyên bộ đếm ngân sách;
  * chống replay: cùng ``decision_id`` hoặc ``expected_version`` cũ bị chặn;
  * export Markdown chỉ có từ phiên bản đã duyệt.
"""

from __future__ import annotations

import pytest

from src.models.schemas import (
    CheckpointKind,
    ClaimInput,
    ReviewAction,
    ReviewDecision,
    ReviewStatus,
    RunStatus,
)
from src.services.dossier import export_markdown, render_markdown, validate_dossier
from src.services.errors import MvpError
from src.services.review import apply_review, assessment_approved, export_ready
from src.services.runner import InProcessRunner
from src.services.store import MvpStore

CLAIM = {
    "claim_text": "metformin gây lactic acidosis.",
    "drug": "metformin",
    "event": "lactic acidosis",
    "population": "adults with renal impairment",
    "route": "oral",
}


def _to_assessment_checkpoint(tmp_path) -> tuple[MvpStore, InProcessRunner, str]:
    store = MvpStore(str(tmp_path / "review.db"))
    state, _ = store.create_investigation(ClaimInput(**CLAIM))
    runner = InProcessRunner(store)
    stopped = runner.run(state.investigation_id)
    assert stopped.checkpoint is CheckpointKind.ASSESSMENT
    return store, runner, state.investigation_id


def _to_dossier_checkpoint(tmp_path) -> tuple[MvpStore, InProcessRunner, str]:
    store, runner, investigation_id = _to_assessment_checkpoint(tmp_path)
    state = store.get_state(investigation_id)
    decision = ReviewDecision(
        decision_id="DEC-ASSESS-OK",
        investigation_id=investigation_id,
        checkpoint=CheckpointKind.ASSESSMENT,
        action=ReviewAction.APPROVE,
        reviewer_id="reviewer-1",
        expected_version=state.version,
    )
    apply_review(store, decision)
    runner.run(investigation_id, resume=True)
    assert store.get_state(investigation_id).checkpoint is CheckpointKind.DOSSIER
    return store, runner, investigation_id


def _decision(store: MvpStore, investigation_id: str, **overrides) -> ReviewDecision:
    state = store.get_state(investigation_id)
    base = {
        "decision_id": f"DEC-{state.version}",
        "investigation_id": investigation_id,
        "checkpoint": state.checkpoint,
        "action": ReviewAction.APPROVE,
        "reviewer_id": "reviewer-1",
        "expected_version": state.version,
    }
    return ReviewDecision(**{**base, **overrides})


# --------------------------------------------------------------------------------------
# Duyệt
# --------------------------------------------------------------------------------------


def test_approve_assessment_does_not_approve_dossier(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    result = apply_review(store, _decision(store, investigation_id))
    assert result.review_status is ReviewStatus.APPROVED
    assert result.run_status is RunStatus.WAITING_FOR_REVIEW
    state = store.get_state(investigation_id)
    assert state.next_stage == "build_dossier"
    assert state.checkpoint is None
    assert store.approved_dossier(investigation_id) is None
    assert assessment_approved(store, investigation_id) is True
    assert export_ready(store, investigation_id) is False


def test_approve_dossier_enables_export(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    result = apply_review(store, _decision(store, investigation_id))
    assert result.run_status is RunStatus.COMPLETED
    dossier = store.approved_dossier(investigation_id)
    assert dossier is not None
    assert dossier.approved_by == "reviewer-1"
    assert dossier.approved_at is not None

    markdown = export_markdown(store, investigation_id)
    assert f"Hồ sơ điều tra {investigation_id}" in markdown
    assert dossier.content_hash in markdown
    assert "Kết luận trong phạm vi" in markdown


def test_export_blocked_before_dossier_approval(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    with pytest.raises(MvpError) as excinfo:
        export_markdown(store, investigation_id)
    assert excinfo.value.code == "dossier_not_approved"


# --------------------------------------------------------------------------------------
# Invalidation
# --------------------------------------------------------------------------------------


def test_edit_evidence_blocks_export_until_reapproved(tmp_path):
    store, runner, investigation_id = _to_dossier_checkpoint(tmp_path)
    with pytest.raises(MvpError) as pending:
        export_markdown(store, investigation_id)
    assert pending.value.code == "dossier_not_approved"

    state = store.get_state(investigation_id)
    target = state.active_evidence()[0]
    document = store.get_document(investigation_id, target.doc_id)
    corrected_quote = document.text[:80].strip()
    result = apply_review(
        store,
        _decision(
            store,
            investigation_id,
            checkpoint=CheckpointKind.DOSSIER,
            action=ReviewAction.EDIT_EVIDENCE,
            target_evidence_id=target.evidence_id,
            payload={"quote": corrected_quote},
            reason="Trích dẫn sai chính tả so với nguồn.",
        ),
    )
    assert "assessment" in result.invalidated and "dossier" in result.invalidated
    assert store.latest_dossier(investigation_id).status is ReviewStatus.REJECTED
    with pytest.raises(MvpError) as blocked:
        export_markdown(store, investigation_id)
    assert blocked.value.code == "dossier_not_approved"

    edited = next(item for item in store.list_evidence(investigation_id) if item.evidence_id == target.evidence_id)
    assert edited.version == 2
    assert edited.quote == corrected_quote
    # Locator được tính lại theo nguyên văn mới (kiểm chứng được với tài liệu nguồn).
    assert document.text[edited.locator.start : edited.locator.end] == corrected_quote
    assert store.get_state(investigation_id).assessment is None

    # Chạy lại và duyệt lại: export chỉ mở khi hồ sơ mới được duyệt.
    runner.run(investigation_id, resume=True)
    apply_review(store, _decision(store, investigation_id, checkpoint=CheckpointKind.ASSESSMENT))
    runner.run(investigation_id, resume=True)
    apply_review(store, _decision(store, investigation_id, checkpoint=CheckpointKind.DOSSIER))
    assert store.latest_dossier(investigation_id).version == 2
    assert export_markdown(store, investigation_id)


def test_edit_claim_resets_normalization_and_invalidates(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    result = apply_review(
        store,
        _decision(
            store,
            investigation_id,
            checkpoint=CheckpointKind.DOSSIER,
            action=ReviewAction.EDIT_CLAIM,
            payload={"population": "adults 65 years and older"},
            reason="Thu hẹp quần thể theo yêu cầu chuyên môn.",
        ),
    )
    assert result.invalidated == ["normalization", "assessment", "dossier"]
    state = store.get_state(investigation_id)
    assert state.claim.population == "adults 65 years and older"
    assert state.normalized_claim is None
    assert state.assessment_status is None
    assert store.latest_dossier(investigation_id).status is ReviewStatus.REJECTED


def test_exclude_evidence_removes_it_from_active_set(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    state = store.get_state(investigation_id)
    target = state.active_evidence()[0].evidence_id
    apply_review(
        store,
        _decision(
            store,
            investigation_id,
            action=ReviewAction.EXCLUDE_EVIDENCE,
            target_evidence_id=target,
            reason="Bằng chứng không cùng phạm vi quần thể.",
        ),
    )
    after = store.get_state(investigation_id)
    assert target not in {item.evidence_id for item in after.active_evidence()}
    assert target in {item.evidence_id for item in after.evidence}
    assert after.assessment is None


# --------------------------------------------------------------------------------------
# Request more / từ chối
# --------------------------------------------------------------------------------------


def test_request_more_keeps_budget_counters(tmp_path):
    store, runner, investigation_id = _to_assessment_checkpoint(tmp_path)
    before = store.get_state(investigation_id).budget
    result = apply_review(
        store,
        _decision(
            store,
            investigation_id,
            action=ReviewAction.REQUEST_MORE,
            reason="Cần thêm bằng chứng ở quần thể trẻ em.",
        ),
    )
    assert result.review_status is ReviewStatus.CHANGES_REQUESTED
    after = store.get_state(investigation_id)
    assert after.budget.steps_used == before.steps_used
    assert after.budget.documents_used == before.documents_used
    assert after.budget.source_requests == before.source_requests
    assert after.budget.max_steps == before.max_steps
    assert after.next_stage == "checklist"

    resumed = runner.run(investigation_id, resume=True)
    assert resumed.budget.steps_used >= before.steps_used
    assert resumed.checkpoint is CheckpointKind.ASSESSMENT


def test_reject_requires_reason_and_stops_run(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    with pytest.raises(ValueError):
        _decision(store, investigation_id, action=ReviewAction.REJECT, reason="   ")

    result = apply_review(
        store,
        _decision(store, investigation_id, action=ReviewAction.REJECT, reason="Claim ngoài phạm vi đề tài."),
    )
    assert result.review_status is ReviewStatus.REJECTED
    state = store.get_state(investigation_id)
    assert state.run_status is RunStatus.COMPLETED
    assert state.checkpoint is None


# --------------------------------------------------------------------------------------
# Chống replay / xung đột phiên bản
# --------------------------------------------------------------------------------------


def test_replayed_decision_is_not_applied_twice(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    decision = _decision(store, investigation_id)
    apply_review(store, decision)
    with pytest.raises(MvpError) as excinfo:
        apply_review(store, decision)
    assert excinfo.value.code == "idempotency_conflict"
    assert len(store.list_review_decisions(investigation_id)) == 1


def test_stale_review_returns_conflict(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    stale = _decision(store, investigation_id)
    apply_review(store, stale)

    state = store.get_state(investigation_id)
    with pytest.raises(MvpError) as excinfo:
        apply_review(
            store,
            ReviewDecision(
                decision_id="DEC-SECOND",
                investigation_id=investigation_id,
                checkpoint=CheckpointKind.ASSESSMENT,
                action=ReviewAction.APPROVE,
                reviewer_id="reviewer-2",
                expected_version=stale.expected_version,
            ),
        )
    assert excinfo.value.code == "version_conflict"
    assert len(store.list_review_decisions(investigation_id)) == 1
    assert store.get_state(investigation_id).version == state.version


def test_review_at_wrong_checkpoint_is_rejected(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    with pytest.raises(MvpError) as excinfo:
        apply_review(store, _decision(store, investigation_id, checkpoint=CheckpointKind.DOSSIER))
    assert excinfo.value.code == "invalid_state"


def test_reviewer_id_comes_from_server_not_payload(tmp_path):
    store, _, investigation_id = _to_assessment_checkpoint(tmp_path)
    decision = _decision(store, investigation_id, reviewer_id="reviewer-1")
    apply_review(store, decision)
    stored = store.list_review_decisions(investigation_id)[0]
    assert stored.reviewer_id == "reviewer-1"
    assert "reviewer_id" not in decision.payload


# --------------------------------------------------------------------------------------
# Hồ sơ Markdown
# --------------------------------------------------------------------------------------


def test_render_markdown_contains_required_sections(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    apply_review(store, _decision(store, investigation_id))
    dossier = store.approved_dossier(investigation_id)
    assert dossier is not None

    markdown = render_markdown(dossier)
    for title in (
        "Claim",
        "Phạm vi áp dụng",
        "Chiến lược truy xuất",
        "Bằng chứng đã truy xuất",
        "Khoảng trống bằng chứng",
    ):
        assert title in markdown
    state = store.get_state(investigation_id)
    report = validate_dossier(dossier, state)
    assert report.ok, report.errors


def test_dossier_audit_trail_records_reviewer(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    apply_review(store, _decision(store, investigation_id))
    audit = store.list_audit(investigation_id)
    actions = [row["action"] for row in audit]
    assert "dossier_status_changed" in actions
    assert any(row["actor"] == "reviewer-1" for row in audit)


# --------------------------------------------------------------------------------------
# Chặn hồ sơ hỏng: trích dẫn không còn khớp nguồn thì không được duyệt/export
# --------------------------------------------------------------------------------------


def _tamper_first_quote(store: MvpStore, investigation_id: str) -> None:
    """Sửa trích dẫn trong state (mô phỏng dữ liệu bị đổi ngoài luồng review)."""
    state = store.get_state(investigation_id)
    evidence = list(state.evidence)
    evidence[0] = evidence[0].model_copy(update={"quote": "câu này không hề có trong tài liệu nguồn"})
    store.save_state(state.model_copy(update={"evidence": evidence}))


def test_dossier_approval_is_refused_when_a_quote_no_longer_matches(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    _tamper_first_quote(store, investigation_id)

    with pytest.raises(MvpError) as excinfo:
        apply_review(store, _decision(store, investigation_id))
    assert excinfo.value.code == "dossier_invalid"
    assert excinfo.value.status == 409
    assert any("không khớp" in item for item in excinfo.value.details["errors"])
    assert store.approved_dossier(investigation_id) is None


def test_export_is_refused_when_an_approved_dossier_no_longer_validates(tmp_path):
    store, _, investigation_id = _to_dossier_checkpoint(tmp_path)
    apply_review(store, _decision(store, investigation_id))
    assert export_markdown(store, investigation_id)

    _tamper_first_quote(store, investigation_id)

    with pytest.raises(MvpError) as excinfo:
        export_markdown(store, investigation_id)
    assert excinfo.value.code == "dossier_invalid"
