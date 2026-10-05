"""Kiểm thử hồ sơ (M06): cấu trúc, validator và bản Markdown chính thức."""

from __future__ import annotations

import pytest

from src.models.schemas import (
    AssessmentStatus,
    CheckpointKind,
    ClaimInput,
    Dossier,
    DossierSection,
    EvidenceUnit,
    QuoteLocator,
    ReviewAction,
    ReviewDecision,
    RunStatus,
    Stance,
)
from src.services.dossier import build_dossier, export_markdown, render_markdown, validate_dossier
from src.services.errors import MvpError
from src.services.review import apply_review
from src.services.runner import InProcessRunner
from src.services.store import MvpStore

CLAIM = {
    "claim_text": "metformin gây lactic acidosis.",
    "drug": "metformin",
    "event": "lactic acidosis",
    "population": "adults with renal impairment",
    "route": "oral",
}


def _run_to_dossier(tmp_path) -> tuple[MvpStore, str]:
    store = MvpStore(str(tmp_path / "dossier.db"))
    state, _ = store.create_investigation(ClaimInput(**CLAIM))
    runner = InProcessRunner(store)
    runner.run(state.investigation_id)
    apply_review(
        store,
        ReviewDecision(
            decision_id="DEC-1",
            investigation_id=state.investigation_id,
            checkpoint=CheckpointKind.ASSESSMENT,
            action=ReviewAction.APPROVE,
            reviewer_id="reviewer-1",
            expected_version=store.get_state(state.investigation_id).version,
        ),
    )
    runner.run(state.investigation_id, resume=True)
    return store, state.investigation_id


def test_dossier_has_all_required_sections(tmp_path):
    store, investigation_id = _run_to_dossier(tmp_path)
    dossier = store.latest_dossier(investigation_id)
    assert dossier is not None
    titles = [section.title for section in dossier.sections]
    assert titles == [
        "Claim",
        "Phạm vi áp dụng",
        "Chiến lược truy xuất",
        "Bằng chứng đã truy xuất",
        "Khoảng trống bằng chứng",
        "Kết luận trong phạm vi claim",
    ]
    assert dossier.citations
    assert dossier.content_hash
    assert dossier.status.value == "pending"

    state = store.get_state(investigation_id)
    assert validate_dossier(dossier, state).ok


def test_validator_blocks_missing_citation(tmp_path):
    store, investigation_id = _run_to_dossier(tmp_path)
    state = store.get_state(investigation_id)
    dossier = store.latest_dossier(investigation_id)
    assert dossier is not None

    tampered = dossier.model_copy(update={"citations": [*dossier.citations, "DOC-KHONG-TON-TAI"]})
    report = validate_dossier(tampered, state)
    assert not report.ok
    assert any("ngoài tập đã truy xuất" in error for error in report.errors)


def test_validator_blocks_evidence_outside_investigation(tmp_path):
    store, investigation_id = _run_to_dossier(tmp_path)
    state = store.get_state(investigation_id)
    dossier = store.latest_dossier(investigation_id)
    assert dossier is not None

    tampered = dossier.model_copy(
        update={
            "sections": [
                *dossier.sections[:-1],
                DossierSection(title="Kết luận trong phạm vi claim", body="Tóm tắt.", evidence_ids=["EVI-LA"]),
            ]
        }
    )
    report = validate_dossier(tampered, state)
    assert not report.ok
    assert any("không còn hoạt động" in error for error in report.errors)


def test_validator_blocks_causal_overclaim(tmp_path):
    store, investigation_id = _run_to_dossier(tmp_path)
    state = store.get_state(investigation_id)
    dossier = store.latest_dossier(investigation_id)
    assert dossier is not None

    overclaimed = dossier.model_copy(update={"summary": "Metformin gây nhiễm toan lactic ở mọi bệnh nhân."})
    report = validate_dossier(overclaimed, state)
    assert not report.ok
    assert any("no_causal_claim" in error for error in report.errors)


def test_abstain_dossier_keeps_reason_and_missing_data(tmp_path):
    store = MvpStore(str(tmp_path / "abstain.db"))
    state, _ = store.create_investigation(ClaimInput(claim_text="orlistat và viêm tuỵ", drug="orlistat", event="pancreatitis"))
    InProcessRunner(store).run(state.investigation_id)
    final = store.get_state(state.investigation_id)
    assert final.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE

    dossier = build_dossier(final)
    assert dossier.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert dossier.gaps
    assert any("Lý do dừng" in item for item in dossier.limitations)
    report = validate_dossier(dossier, final)
    assert report.ok
    assert any("chưa đủ bằng chứng" in warning for warning in report.warnings)


def test_markdown_only_renders_approved_version(tmp_path):
    store, investigation_id = _run_to_dossier(tmp_path)
    with pytest.raises(MvpError) as excinfo:
        export_markdown(store, investigation_id)
    assert excinfo.value.code == "dossier_not_approved"

    apply_review(
        store,
        ReviewDecision(
            decision_id="DEC-2",
            investigation_id=investigation_id,
            checkpoint=CheckpointKind.DOSSIER,
            action=ReviewAction.APPROVE,
            reviewer_id="reviewer-2",
            expected_version=store.get_state(investigation_id).version,
        ),
    )
    markdown = export_markdown(store, investigation_id)
    assert "## Bằng chứng đã truy xuất" in markdown
    assert "## Hạn chế" in markdown or "## Khoảng trống bằng chứng" in markdown
    assert store.get_state(investigation_id).run_status is RunStatus.COMPLETED

    # Bản chưa duyệt vẫn render được nhưng không dùng cho export chính thức.
    pending = render_markdown(store.latest_dossier(investigation_id))
    assert "Hồ sơ điều tra" in pending


def test_dossier_evidence_units_stay_active(tmp_path):
    store, investigation_id = _run_to_dossier(tmp_path)
    dossier = store.latest_dossier(investigation_id)
    state = store.get_state(investigation_id)
    assert dossier is not None
    evidence_section = next(section for section in dossier.sections if section.title == "Bằng chứng đã truy xuất")
    assert evidence_section.evidence_ids
    for evidence_id in evidence_section.evidence_ids:
        item = next(entry for entry in state.evidence if entry.evidence_id == evidence_id)
        assert isinstance(item, EvidenceUnit)
        assert item.stance in {Stance.SUPPORTS, Stance.CONTRADICTS, Stance.UNCERTAIN}
        assert item.excluded is False


def test_dossier_model_rejects_empty_summary():
    with pytest.raises(ValueError):
        Dossier(
            dossier_id="DOS-X",
            investigation_id="INV-X",
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            summary="",
        )


def _faers_only_state_with_quote(tmp_path, quote: str):
    """Chạy kịch bản FAERS-only rồi thay nguyên văn nguồn bằng một câu có số liệu tỷ lệ."""
    store = MvpStore(str(tmp_path / "faers-quote.db"))
    state, _ = store.create_investigation(
        ClaimInput(claim_text="orlistat và viêm tuỵ", drug="orlistat", event="pancreatitis")
    )
    InProcessRunner(store).run(state.investigation_id)
    final = store.get_state(state.investigation_id)
    assert final.documents and final.evidence

    document = final.documents[0].model_copy(update={"text": quote + " " + final.documents[0].text})
    evidence = final.evidence[0].model_copy(
        update={"quote": quote, "locator": QuoteLocator(start=0, end=len(quote), section="4.8")}
    )
    return final.model_copy(update={"documents": [document], "evidence": [evidence]})


def test_verbatim_quote_with_incidence_does_not_block_faers_only_dossier(tmp_path):
    quote = "The incidence of acute pancreatitis was 3.4 per 1000 reports in this spontaneous series."
    state = _faers_only_state_with_quote(tmp_path, quote)

    dossier = build_dossier(state)
    report = validate_dossier(dossier, state)

    assert report.ok, report.errors
    assert any(quote in section.body for section in dossier.sections)


def test_agent_written_incidence_from_faers_is_still_blocked(tmp_path):
    quote = "The incidence of acute pancreatitis was 3.4 per 1000 reports in this spontaneous series."
    state = _faers_only_state_with_quote(tmp_path, quote)

    dossier = build_dossier(state)
    overclaimed = dossier.model_copy(update={"summary": "Tỷ lệ gặp viêm tuỵ là 3.4 trên 1000 báo cáo."})
    report = validate_dossier(overclaimed, state)

    assert not report.ok
    assert any("no_incidence_from_spontaneous_reports" in error for error in report.errors)
