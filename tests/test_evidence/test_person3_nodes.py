"""Exercise the exact node wired into graph, with real RunContext/store/gateway."""

import pytest
from test_person3_contracts import CLAIM, ROOT, document, finding

from src.models.schemas import AssessmentStatus, BudgetState, ClaimInput, StopReason
from src.services.evidence.integration import configure_person3
from src.services.evidence.nodes import extract_assess_person3
from src.services.llm import LLMGateway, MockProvider
from src.services.runner import RunContext
from src.services.store import MvpStore


@pytest.fixture
def context(tmp_path):
    store = MvpStore(str(tmp_path / "node.sqlite3"))
    state, _ = store.create_investigation(ClaimInput(claim_text="Synthetic", drug="Drug Alpha", event="Event Alpha"))
    doc = document()
    store.save_document(state.investigation_id, doc)
    state = store.save_state(state.model_copy(update={"normalized_claim": CLAIM, "documents": [doc]}))
    provider = MockProvider({"extract_evidence": {"findings": [finding()]}})
    ctx = configure_person3(RunContext(store=store, gateway=LLMGateway(provider)),
                            ROOT / "data/dictionaries/person3_synthetic.json", allow_synthetic=True)
    yield state, ctx, provider
    store.close()


def test_node_persists_evidence_budget_trace_and_does_not_reextract(context):
    state, ctx, provider = context
    result = extract_assess_person3({"investigation": state, "ctx": ctx})["investigation"]
    assert result.assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE
    assert result.budget.llm_calls == 1 and len(result.evidence) == 1
    again = extract_assess_person3({"investigation": result, "ctx": ctx})["investigation"]
    assert len(provider.calls) == 1 and len(again.evidence) == 1
    assert ctx.store.get_state(state.investigation_id).budget.llm_calls == 1


def test_budget_stop_preserves_state_for_abstention_and_review(context):
    state, ctx, provider = context
    state = state.model_copy(update={"budget": BudgetState(max_llm_calls=2)})
    result = extract_assess_person3({"investigation": state, "ctx": ctx})
    assert result["stop"].reason is StopReason.BUDGET_EXHAUSTED and not provider.calls
    assert result["investigation"].assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert result["investigation"].gaps


def test_invalid_schema_stops_at_review_after_one_charged_repair(context):
    state, ctx, provider = context
    provider.responses = {"extract_evidence": "{}"}
    result = extract_assess_person3({"investigation": state, "ctx": ctx})
    assert result["stop"].reason is StopReason.NEEDS_REVIEW
    assert result["investigation"].budget.llm_calls == 2
    assert len(provider.calls) == 2
