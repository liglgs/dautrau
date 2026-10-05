"""M06 exercised against Person 2's real SQLite store, review and export services."""

from copy import deepcopy

import pytest
from test_person3_contracts import CLAIM, TEXT, document, extract

from src.models.schemas import (
    AssessmentStatus,
    CheckpointKind,
    ClaimInput,
    ReviewAction,
    ReviewDecision,
    RunStatus,
)
from src.services.dossier import content_hash, export_markdown, validate_dossier
from src.services.errors import MvpError
from src.services.evidence.analysis import EvidenceAnalyzer
from src.services.evidence.dossier import build_person3_dossier
from src.services.review import apply_review
from src.services.store import MvpStore


@pytest.fixture
def investigated(tmp_path):
    store = MvpStore(str(tmp_path / "person3.sqlite3"))
    raw = ClaimInput(claim_text="Synthetic comparison", drug="Drug Alpha", event="Event Alpha")
    state, _ = store.create_investigation(raw)
    units, _, _ = extract()
    doc = document()
    store.save_document(state.investigation_id, doc)
    store.save_evidence(state.investigation_id, units[0])
    analysis = EvidenceAnalyzer().analyze(units, CLAIM)
    state = store.save_state(state.model_copy(update={
        "normalized_claim": CLAIM, "evidence": units, "documents": [doc],
        "assessment": analysis.assessment, "assessment_status": analysis.assessment.assessment_status,
        "checkpoint": CheckpointKind.ASSESSMENT, "run_status": RunStatus.WAITING_FOR_REVIEW,
        "searched_sources": ["pubmed"],
    }))
    yield store, state
    store.close()


def approve(store, state, identifier):
    return apply_review(store, ReviewDecision(
        decision_id=identifier, investigation_id=state.investigation_id, checkpoint=state.checkpoint,
        action=ReviewAction.APPROVE, reviewer_id="synthetic-reviewer", expected_version=state.version,
    ))


def save_dossier(store, state):
    dossier = build_person3_dossier(state)
    store.save_dossier(dossier)
    state = store.save_state(state.model_copy(update={
        "checkpoint": CheckpointKind.DOSSIER, "run_status": RunStatus.WAITING_FOR_REVIEW, "next_stage": "export",
    }))
    return dossier, state


def test_dossier_contains_source_versions_and_verifiable_quote(investigated):
    _, state = investigated
    dossier = build_person3_dossier(state)
    statement = next(section.statements[0] for section in dossier.sections if section.statements)
    assert statement.kind == "quote" and statement.text == TEXT
    assert statement.evidence_refs[0].document_hash == state.documents[0].hash
    assert statement.evidence_refs[0].evidence_version == 1
    assert validate_dossier(dossier, state).ok


def test_assessment_approval_does_not_approve_dossier(investigated):
    store, state = investigated
    approve(store, state, "DEC-ASSESS")
    state = store.get_state(state.investigation_id)
    dossier, _ = save_dossier(store, state)
    assert dossier.status.value == "pending"
    with pytest.raises(MvpError) as error:
        export_markdown(store, state.investigation_id)
    assert error.value.code.value == "dossier_not_approved"


def test_reviewed_export_includes_source_link_and_versions(investigated):
    store, state = investigated
    dossier, state = save_dossier(store, state)
    approve(store, state, "DEC-DOSSIER")
    markdown = export_markdown(store, state.investigation_id)
    assert TEXT in markdown and "https://example.org/synthetic/DOC-A" in markdown
    assert "v1" in markdown and state.documents[0].hash in markdown
    assert "{{" not in markdown and "${" not in markdown
    assert store.approved_dossier(state.investigation_id).content_hash == dossier.content_hash


def test_editing_evidence_invalidates_approved_dossier_and_keeps_budget(investigated):
    store, state = investigated
    dossier, state = save_dossier(store, state)
    approve(store, state, "DEC-APPROVE")
    state = store.get_state(state.investigation_id)
    # Open another review point through the server state to exercise its edit handler.
    state = store.save_state(state.model_copy(update={"checkpoint": CheckpointKind.ASSESSMENT,
                                                      "run_status": RunStatus.WAITING_FOR_REVIEW}))
    budget_before = state.budget.model_dump()
    apply_review(store, ReviewDecision(
        decision_id="DEC-EDIT", investigation_id=state.investigation_id,
        checkpoint=CheckpointKind.ASSESSMENT, action=ReviewAction.EDIT_EVIDENCE,
        reviewer_id="synthetic-reviewer", expected_version=state.version,
        target_evidence_id=state.evidence[0].evidence_id, payload={"quote": "Event Alpha"},
    ))
    changed = store.get_state(state.investigation_id)
    assert changed.evidence[0].version == 2 and changed.assessment_status is None
    from src.services.evidence.contracts import read_annotation

    annotation = read_annotation(changed.evidence[0].notes)
    assert annotation.drug_ingredient is None and annotation.uncertainty == "unknown"
    assert changed.budget.model_dump() == budget_before
    assert not validate_dossier(dossier, changed).ok
    with pytest.raises(MvpError):
        export_markdown(store, state.investigation_id)


@pytest.mark.parametrize("mutation", ["evidence_version", "document_hash", "outside_evidence", "no_citation", "fabricated_text"])
def test_typed_statements_reject_stale_or_unsupported_references(investigated, mutation):
    _, state = investigated
    dossier = build_person3_dossier(state)
    altered = deepcopy(dossier)
    section = next(section for section in altered.sections if section.statements)
    statement = section.statements[0]
    reference = statement.evidence_refs[0]
    if mutation == "evidence_version":
        reference.evidence_version += 1
    elif mutation == "document_hash":
        reference.document_hash = "0" * 64
    elif mutation == "outside_evidence":
        reference.evidence_id = "EV-OUTSIDE"
    elif mutation == "no_citation":
        statement.evidence_refs.clear()
    else:
        statement.text = "Invented result"
        section.body = statement.text
    altered.content_hash = content_hash(altered)
    assert not validate_dossier(altered, state).ok


def test_quote_integrity_does_not_auto_approve_semantic_fact(investigated):
    _, state = investigated
    dossier = build_person3_dossier(state)
    section = next(section for section in dossier.sections if section.statements)
    section.statements[0].kind = "fact"
    dossier.content_hash = content_hash(dossier)
    assert any("entailment" in error for error in validate_dossier(dossier, state).errors)


def test_faers_or_unknown_scope_cannot_support_positive_dossier(investigated):
    _, state = investigated
    state = state.model_copy(update={"normalized_claim": CLAIM.model_copy(update={"dose": "unknown dose"})})
    dossier = build_person3_dossier(state)
    assert not validate_dossier(dossier, state).ok


def test_abstention_dossier_survives_without_llm_or_evidence(investigated):
    _, state = investigated
    state = state.model_copy(update={"evidence": [], "documents": [],
                                     "assessment_status": AssessmentStatus.INSUFFICIENT_EVIDENCE,
                                     "assessment": None, "stop_reason": "budget_exhausted"})
    dossier = build_person3_dossier(state)
    assert dossier.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert "budget_exhausted" in dossier.limitations[0] and validate_dossier(dossier, state).ok


def test_request_more_preserves_budget(investigated):
    store, state = investigated
    before = state.budget.model_dump()
    apply_review(store, ReviewDecision(
        decision_id="DEC-MORE", investigation_id=state.investigation_id,
        checkpoint=CheckpointKind.ASSESSMENT, action=ReviewAction.REQUEST_MORE,
        reviewer_id="synthetic-reviewer", expected_version=state.version, reason="Need more evidence",
    ))
    assert store.get_state(state.investigation_id).budget.model_dump() == before
