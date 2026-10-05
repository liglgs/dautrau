"""M01 — Kiểm thử hợp đồng dữ liệu (schemas, enum, ngân sách, fixture).

Nghiệm thu: ``python -m pytest tests/test_models/test_mvp_contracts.py -q``
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models.schemas import (
    DEFAULT_MAX_DOCUMENTS,
    DEFAULT_MAX_STEPS,
    HARD_MAX_DOCUMENTS,
    HARD_MAX_STEPS,
    MAX_INPUT_TOKENS,
    MAX_LLM_CALLS,
    MAX_OUTPUT_TOKENS,
    MAX_SOURCE_REQUESTS,
    AssessmentResult,
    AssessmentStatus,
    BudgetState,
    CheckpointKind,
    ClaimInput,
    Dossier,
    EvidenceGap,
    EvidenceScope,
    EvidenceUnit,
    InvestigationState,
    NormalizedClaim,
    PlannerDecision,
    ReviewAction,
    ReviewDecision,
    ReviewStatus,
    RunStatus,
    ScopeComparison,
    ScopeOutcome,
    SourceDocument,
    StopDecision,
    StopReason,
    compare_scope,
    is_unknown,
    validate_budget_ceiling,
)
from src.services.contracts import DossierBuilder, EvidenceExtractor, SourceAdapter
from src.services.policy import (
    PolicyError,
    assert_citations_retrieved,
    assert_no_causal_claim,
    assert_no_incidence_inference,
    assert_supported_needs_strong_source,
)
from tests.fixtures.mvp import NAMES, load, load_all

# --------------------------------------------------------------------------------------
# Enum hợp đồng
# --------------------------------------------------------------------------------------


def test_run_status_values():
    assert {item.value for item in RunStatus} == {
        "queued",
        "running",
        "waiting_for_review",
        "completed",
        "cancelled",
        "interrupted",
        "failed",
    }


def test_assessment_status_values():
    assert {item.value for item in AssessmentStatus} == {
        "supported_for_scope",
        "contradicted_for_scope",
        "insufficient_evidence",
        "scope_mismatch",
        "out_of_scope",
        "requires_human_review",
    }


def test_review_status_values():
    assert {item.value for item in ReviewStatus} == {"pending", "approved", "rejected", "changes_requested"}


def test_checkpoint_kind_values():
    assert {item.value for item in CheckpointKind} == {"normalization", "assessment", "dossier"}


# --------------------------------------------------------------------------------------
# Trần ngân sách
# --------------------------------------------------------------------------------------


def test_budget_defaults_follow_plan():
    budget = BudgetState()
    assert budget.max_steps == DEFAULT_MAX_STEPS == 8
    assert budget.max_documents == DEFAULT_MAX_DOCUMENTS == 50
    assert budget.max_source_requests == MAX_SOURCE_REQUESTS == 80
    assert budget.max_llm_calls == MAX_LLM_CALLS == 80
    assert budget.max_input_tokens == MAX_INPUT_TOKENS == 150_000
    assert budget.max_output_tokens == MAX_OUTPUT_TOKENS == 25_000


def test_budget_rejects_steps_above_hard_cap():
    with pytest.raises(ValidationError):
        BudgetState(max_steps=HARD_MAX_STEPS + 1)


def test_budget_rejects_documents_above_hard_cap():
    with pytest.raises(ValidationError):
        BudgetState(max_documents=HARD_MAX_DOCUMENTS + 1)


def test_validate_budget_ceiling_blocks_over_limit():
    validate_budget_ceiling(HARD_MAX_STEPS, HARD_MAX_DOCUMENTS)
    with pytest.raises(ValueError):
        validate_budget_ceiling(HARD_MAX_STEPS + 1, 10)
    with pytest.raises(ValueError):
        validate_budget_ceiling(10, HARD_MAX_DOCUMENTS + 1)


def test_budget_counters_cannot_exceed_limits():
    with pytest.raises(ValidationError):
        BudgetState(max_steps=5, steps_used=6)
    with pytest.raises(ValidationError):
        BudgetState(max_documents=5, documents_used=6)


def test_budget_remaining_helpers():
    budget = BudgetState(max_steps=8, max_documents=50, steps_used=3, documents_used=12)
    assert budget.steps_remaining == 5
    assert budget.documents_remaining == 38


# --------------------------------------------------------------------------------------
# Kết luận nhân quả bị cấm
# --------------------------------------------------------------------------------------


def test_causal_is_not_a_valid_assessment_status():
    assert "causal" not in {item.value for item in AssessmentStatus}
    with pytest.raises(ValidationError):
        AssessmentResult(assessment_status="causal", rationale="x")


def test_investigation_state_rejects_causal_assessment():
    state = InvestigationState(
        investigation_id="INV-1",
        claim=ClaimInput(claim_text="Metformin gây toan lactic.", drug="metformin", event="lactic acidosis"),
    )
    with pytest.raises(ValidationError):
        InvestigationState(**{**state.model_dump(mode="json"), "assessment_status": "causal"})


def test_claim_input_requires_event():
    with pytest.raises(ValidationError):
        ClaimInput(claim_text="Metformin gây toan lactic.", drug="metformin")


# --------------------------------------------------------------------------------------
# Trường unknown không được gộp thành match
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("unknown", [None, "", "  ", "unknown", "n/a", "không rõ"])
def test_unknown_values_are_detected(unknown):
    assert is_unknown(unknown)


def test_unknown_never_becomes_match():
    comparison = ScopeComparison.compare("population", None, "adults")
    assert comparison.outcome is ScopeOutcome.UNKNOWN
    comparison = ScopeComparison.compare("population", "adults", "unknown")
    assert comparison.outcome is ScopeOutcome.UNKNOWN


def test_scope_comparison_rejects_forced_match_on_unknown():
    with pytest.raises(ValidationError):
        ScopeComparison(field="population", claim_value=None, evidence_value="adults", outcome=ScopeOutcome.MATCH)


def test_compare_scope_keeps_unknown_separate_from_match():
    claim = NormalizedClaim(
        claim_text="x",
        drug_ingredient="metformin",
        event_term="lactic acidosis",
        population="adults with renal impairment",
    )
    evidence = EvidenceScope(population="adults with renal impairment", route=None)
    outcomes = {item.field: item.outcome for item in compare_scope(claim, evidence)}
    assert outcomes["population"] is ScopeOutcome.MATCH
    assert outcomes["dose"] is ScopeOutcome.UNKNOWN
    assert outcomes["route"] is ScopeOutcome.UNKNOWN
    assert ScopeOutcome.MATCH not in {outcomes["dose"], outcomes["route"]}


def test_compare_scope_flags_mismatch():
    claim = NormalizedClaim(
        claim_text="x", drug_ingredient="ibuprofen", event_term="bleeding", population="children (under 12 years)"
    )
    evidence = EvidenceScope(population="adults (18-65 years)")
    outcomes = {item.field: item.outcome for item in compare_scope(claim, evidence)}
    assert outcomes["population"] is ScopeOutcome.MISMATCH


# --------------------------------------------------------------------------------------
# Models phụ trợ
# --------------------------------------------------------------------------------------


def test_review_decision_requires_reason_for_reject():
    with pytest.raises(ValidationError):
        ReviewDecision(
            decision_id="RD-1",
            investigation_id="INV-1",
            checkpoint=CheckpointKind.ASSESSMENT,
            action=ReviewAction.REJECT,
            reviewer_id="reviewer-1",
            expected_version=1,
        )
    decision = ReviewDecision(
        decision_id="RD-1",
        investigation_id="INV-1",
        checkpoint=CheckpointKind.ASSESSMENT,
        action=ReviewAction.REJECT,
        reviewer_id="reviewer-1",
        expected_version=1,
        reason="Bằng chứng chưa đủ.",
    )
    assert decision.reviewer_id == "reviewer-1"


def test_evidence_actions_require_target():
    with pytest.raises(ValidationError):
        ReviewDecision(
            decision_id="RD-2",
            investigation_id="INV-1",
            checkpoint=CheckpointKind.ASSESSMENT,
            action=ReviewAction.EXCLUDE_EVIDENCE,
            reviewer_id="reviewer-1",
            expected_version=1,
        )


def test_planner_decision_requires_source_and_query_when_searching():
    with pytest.raises(ValidationError):
        PlannerDecision(action="search_source", reason="thiếu nguồn")
    decision = PlannerDecision(
        action="change_query", source="pubmed", query="metformin lactic acidosis", reason="ít kết quả"
    )
    assert decision.action == "change_query"


def test_stop_decision_requires_reason_when_stopping():
    with pytest.raises(ValidationError):
        StopDecision(should_stop=True)
    assert StopDecision(should_stop=False).reason is None
    assert StopDecision(should_stop=True, reason=StopReason.SATURATION).reason is StopReason.SATURATION


def test_dossier_defaults_to_pending():
    dossier = Dossier(
        dossier_id="DOS-1",
        investigation_id="INV-1",
        assessment_status=AssessmentStatus.SUPPORTED_FOR_SCOPE,
        summary="Tóm tắt",
    )
    assert dossier.status is ReviewStatus.PENDING
    assert dossier.approved_at is None


def test_investigation_state_json_roundtrip():
    state = InvestigationState(
        investigation_id="INV-1",
        claim=ClaimInput(claim_text="Metformin gây toan lactic.", drug="metformin", event="lactic acidosis"),
        gaps=[EvidenceGap(gap_id="GAP-1", kind="missing_source", description="Thiếu nhãn DailyMed")],
    )
    payload = json.loads(state.model_dump_json())
    restored = InvestigationState.model_validate(payload)
    assert restored == state


def test_evidence_unit_locator_must_be_ordered():
    with pytest.raises(ValidationError):
        EvidenceUnit(
            evidence_id="EVI-1",
            doc_id="DOC-1",
            source="pubmed",
            stance="supports",
            quote="abc",
            locator={"start": 10, "end": 5},
        )


# --------------------------------------------------------------------------------------
# Policy an toàn
# --------------------------------------------------------------------------------------


def test_policy_blocks_causal_language():
    with pytest.raises(PolicyError):
        assert_no_causal_claim("Metformin gây nhiễm toan lactic ở người suy thận.")
    with pytest.raises(PolicyError):
        assert_no_causal_claim("The event was caused by the suspect drug.")
    assert_no_causal_claim("Metformin được báo cáo liên quan tới nhiễm toan lactic ở người suy thận.")


def test_policy_blocks_incidence_from_spontaneous_reports_only():
    with pytest.raises(PolicyError):
        assert_no_incidence_inference("Tỷ lệ gặp biến cố là 1.5% trên 1000 người.", {"faers"})
    assert_no_incidence_inference("Tỷ lệ gặp biến cố là 1.5% trên 1000 người.", {"faers", "pubmed"})


def test_policy_blocks_citations_outside_retrieved_set():
    with pytest.raises(PolicyError):
        assert_citations_retrieved(["DOC-KHONG-CO"], {"DOC-CO"})
    assert_citations_retrieved(["DOC-CO"], {"DOC-CO"})


def test_policy_blocks_supported_from_faers_only():
    with pytest.raises(PolicyError):
        assert_supported_needs_strong_source(AssessmentStatus.SUPPORTED_FOR_SCOPE, {"faers"})
    assert_supported_needs_strong_source(AssessmentStatus.SUPPORTED_FOR_SCOPE, {"pubmed", "faers"})
    assert_supported_needs_strong_source(AssessmentStatus.INSUFFICIENT_EVIDENCE, {"faers"})


# --------------------------------------------------------------------------------------
# Mock fixtures
# --------------------------------------------------------------------------------------


def test_fixture_names_are_complete():
    assert set(NAMES) == {
        "supported",
        "insufficient",
        "scope_mismatch",
        "contradiction",
        "source_error",
        "ambiguous_brand",
        "replanning",
    }


@pytest.mark.parametrize("name", NAMES)
def test_fixture_documents_validate_and_hashes_match(name):
    fixture = load(name)
    for document in fixture["documents"]:
        model = SourceDocument.model_validate(document)
        assert hashlib.sha256(model.text.encode("utf-8")).hexdigest() == model.hash


@pytest.mark.parametrize("name", NAMES)
def test_fixture_evidence_quotes_are_locatable(name):
    fixture = load(name)
    documents = {document["doc_id"]: document for document in fixture["documents"]}
    for evidence in fixture["evidence"]:
        model = EvidenceUnit.model_validate(evidence)
        text = documents[model.doc_id]["text"]
        assert text[model.locator.start : model.locator.end] == model.quote


@pytest.mark.parametrize("name", NAMES)
def test_fixture_claims_and_expected_statuses(name):
    fixture = load(name)
    ClaimInput.model_validate(fixture["claim"])
    expected = fixture["expected"]
    if expected["assessment_status"] is not None:
        AssessmentStatus(expected["assessment_status"])
    StopReason(expected["stop_reason"])
    CheckpointKind(expected["checkpoint"])
    RunStatus(expected["run_status_at_stop"])


def test_ambiguous_brand_fixture_requires_normalization_review():
    fixture = load("ambiguous_brand")
    normalization = fixture["normalization"]
    assert normalization["requires_review"] is True
    assert len(normalization["candidates"]) == 2
    assert fixture["expected"]["checkpoint"] == "normalization"


def test_all_fixtures_load():
    assert set(load_all()) == set(NAMES)


def test_fixtures_are_labelled_synthetic():
    for name in NAMES:
        assert load(name)["synthetic"] is True, f"{name} phải được đánh dấu synthetic"


def test_contract_protocols_accept_mock_implementations():
    """Điểm cắm M01: mock của Người 1/Người 3 phải thoả mãn protocol."""

    class MockAdapter:
        name = "mock"

        def search(self, action, budget):  # pragma: no cover - chỉ kiểm tra chữ ký
            raise NotImplementedError

    class MockExtractor:
        def extract_evidence(self, document, claim):  # pragma: no cover
            raise NotImplementedError

    class MockDossierBuilder:
        def build_dossier(self, state):  # pragma: no cover
            raise NotImplementedError

    assert isinstance(MockAdapter(), SourceAdapter)
    assert isinstance(MockExtractor(), EvidenceExtractor)
    assert isinstance(MockDossierBuilder(), DossierBuilder)


# --------------------------------------------------------------------------------------
# Payload sai (fixture âm) — tên kiểm thử khớp yêu cầu P01 của QUY_TAC
# --------------------------------------------------------------------------------------

_MODEL_BY_NAME = {
    "ClaimInput": ClaimInput,
    "BudgetState": BudgetState,
    "AssessmentResult": AssessmentResult,
    "EvidenceUnit": EvidenceUnit,
    "SourceDocument": SourceDocument,
    "ReviewDecision": ReviewDecision,
    "PlannerDecision": PlannerDecision,
    "StopDecision": StopDecision,
}

_INVALID_CASES = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "mvp" / "invalid_payloads.json").read_text(encoding="utf-8")
)["cases"]


@pytest.mark.parametrize("case", _INVALID_CASES, ids=[case["id"] for case in _INVALID_CASES])
def test_invalid_payloads_are_rejected(case):
    model = _MODEL_BY_NAME[case["model"]]
    with pytest.raises(ValidationError):
        model.model_validate(case["payload"])


def test_rejects_budget_above_cap():
    """P01: 21 steps hoặc 101 docs phải lỗi."""
    with pytest.raises(ValidationError):
        BudgetState(max_steps=21)
    with pytest.raises(ValidationError):
        BudgetState(max_documents=101)


def test_rejects_unknown_assessment():
    """P01: `causal` không hợp lệ."""
    with pytest.raises(ValidationError):
        AssessmentResult(assessment_status="causal", rationale="x")


def test_unknown_scope_is_not_match():
    """P01: giữ unknown, không gộp thành match."""
    assert ScopeComparison.compare("population", None, "adults").outcome is ScopeOutcome.UNKNOWN
    with pytest.raises(ValidationError):
        ScopeComparison(field="population", claim_value="unknown", evidence_value="adults", outcome=ScopeOutcome.MATCH)
