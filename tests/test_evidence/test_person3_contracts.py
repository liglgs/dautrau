"""Real shared gateway + Person 3 service contracts; entirely synthetic input."""

from pathlib import Path

import pytest

from src.models.schemas import (
    AssessmentStatus,
    BudgetState,
    ClaimInput,
    EvidenceType,
    GapKind,
    NormalizedClaim,
    ScopeOutcome,
    SourceDocument,
    Stance,
)
from src.services.errors import MvpError
from src.services.evidence.analysis import EvidenceAnalyzer, duplicate_report_candidates
from src.services.evidence.citations import text_hash, validate_evidence_citation
from src.services.evidence.contracts import read_annotation
from src.services.evidence.extract import EvidenceExtractor
from src.services.evidence.normalize import ClaimNormalizer
from src.services.evidence.scope import ScopeMatcher
from src.services.llm import LLMGateway, MockProvider

ROOT = Path(__file__).resolve().parents[2]
TEXT = "Ingredient Alpha increased Event Alpha in the fictional comparison."
CLAIM = NormalizedClaim(
    claim_text="Fictional test claim", drug_ingredient="ingredient_alpha", event_term="event_alpha",
    population="adults", dose="10 mg/day", route="oral", time_window="30 days",
)


def document(source="pubmed", doc_id="DOC-A", text=TEXT, **updates):
    return SourceDocument(
        doc_id=doc_id, source=source, source_id=doc_id, text=text,
        source_url="https://example.org/synthetic/" + doc_id, hash=text_hash(text), **updates,
    )


def finding(**updates):
    return {
        "quote": TEXT, "locator": {"start": 0, "end": len(TEXT)},
        "drug_ingredient": "ingredient_alpha", "event_term": "event_alpha",
        "scope": {"population": "adults", "dose": "10 mg/day", "route": "oral", "time_window": "30 days"},
        "comparator": "placebo", "stance": "supports", "direction": "increase", "uncertainty": "low",
        "evidence_type": "rct", **updates,
    }


def extract(payload=None, doc=None, claim=CLAIM, budget=None):
    provider = MockProvider({"extract_evidence": payload or {"findings": [finding()]}})
    gateway = LLMGateway(provider)
    extractor = EvidenceExtractor(gateway)
    extractor.bind(budget or BudgetState(), "INV-A")
    result = extractor.extract_evidence(doc or document(), claim)
    return result, extractor, provider


def test_public_normalizer_preserves_scope_and_ambiguous_candidates():
    normalizer = ClaimNormalizer(ROOT / "data/dictionaries/person3_synthetic.json", allow_synthetic=True)
    raw = ClaimInput(claim_text="Synthetic", drug="Brand Ambiguous", event="Event Alpha", route="oral")
    normalized = normalizer.normalize_claim(raw)
    assert normalized.drug_ingredient == "Brand Ambiguous"
    assert normalized.requires_review and "ingredient_alpha" in normalized.ambiguities[0]
    assert normalized.event_term == "event_alpha" and normalized.route == "oral"


def test_unmapped_term_requires_review_in_public_schema():
    normalizer = ClaimNormalizer(ROOT / "data/dictionaries/aspirin_demo.json")
    normalized = normalizer.normalize_claim(ClaimInput(claim_text="Demo", drug="Unknown brand", event="stomach bleeding"))
    assert normalized.drug_ingredient == "Unknown brand"
    assert normalized.requires_review and "drug_ingredient" in normalized.unknowns


def test_source_checked_demo_dictionary_is_usable_without_synthetic_opt_in():
    normalizer = ClaimNormalizer(ROOT / "data/dictionaries/aspirin_demo.json")
    normalized = normalizer.normalize_claim(ClaimInput(claim_text="Demo", drug=" ASPIRIN ", event="stomach bleeding"))
    assert normalized.drug_ingredient == "aspirin" and not normalized.requires_review


def test_structured_extraction_uses_real_gateway_budget_and_untrusted_channel():
    budget = BudgetState()
    units, extractor, provider = extract(budget=budget)
    assert budget.llm_calls == 1 and budget.input_tokens > 0
    assert len(units) == 1 and not units[0].excluded
    assert TEXT in provider.calls[0]["untrusted"] and TEXT not in provider.calls[0]["system"]
    assert '"response_schema"' in provider.calls[0]["prompt"] and '"findings"' in provider.calls[0]["prompt"]
    assert extractor.gateway.ledger.records[0].prompt_version == "person3.3"
    assert validate_evidence_citation(document(), units[0]).span_verified
    assert not validate_evidence_citation(document(), units[0]).eligible_for_official_statement


def test_missing_budget_is_rejected_before_llm_call():
    provider = MockProvider()
    with pytest.raises(RuntimeError):
        EvidenceExtractor(LLMGateway(provider)).extract_evidence(document(), CLAIM)
    assert not provider.calls


def test_document_hash_is_checked_before_llm_call():
    extractor = EvidenceExtractor(LLMGateway(MockProvider()))
    extractor.bind(BudgetState(), "INV-A")
    with pytest.raises(ValueError, match="hash mismatch"):
        extractor.extract_evidence(document().model_copy(update={"hash": "bad-hash"}), CLAIM)


def test_cache_is_run_and_claim_specific_and_returns_copies():
    units, extractor, provider = extract()
    units[0].notes = "changed by caller"
    again = extractor.extract_evidence(document(), CLAIM)
    assert len(provider.calls) == 1 and read_annotation(again[0].notes)
    extractor.extract_evidence(document(), CLAIM.model_copy(update={"version": 2}))
    assert len(provider.calls) == 2
    extractor.bind(BudgetState(), "INV-B")
    extractor.extract_evidence(document(), CLAIM)
    assert len(provider.calls) == 3


def test_bad_schema_gets_one_repair_and_both_calls_are_charged():
    provider = MockProvider({"extract_evidence": "{}", "extract_evidence:repair": {"findings": [finding()]}})
    gateway = LLMGateway(provider)
    extractor = EvidenceExtractor(gateway)
    budget = BudgetState()
    extractor.bind(budget, "INV-A")
    assert extractor.extract_evidence(document(), CLAIM)
    assert budget.llm_calls == 2 and gateway.ledger.repairs == 1


def test_second_bad_schema_stops_after_one_repair():
    with pytest.raises(MvpError) as error:
        extract({"findings": [{"invented": "invalid"}]})
    assert error.value.code.value == "llm_format_error"


def test_budget_exhaustion_does_not_call_provider():
    budget = BudgetState(max_llm_calls=2)
    provider = MockProvider({"extract_evidence": {"findings": []}})
    extractor = EvidenceExtractor(LLMGateway(provider))
    extractor.bind(budget, "INV-A")
    with pytest.raises(MvpError) as error:
        extractor.extract_evidence(document(), CLAIM)
    assert error.value.code.value == "budget_exhausted" and not provider.calls


@pytest.mark.parametrize("override", [{"quote": "fabricated source quote"}])
def test_fabricated_quote_is_retained_but_excluded(override):
    units, _, _ = extract({"findings": [finding(**override)]})
    assert units[0].excluded


def test_duplicate_span_is_not_counted_twice():
    units, _, _ = extract({"findings": [finding(), finding()]})
    assert len(units) == 1


def test_observed_alias_uses_dictionary_and_missing_fields_stay_missing():
    from src.services.evidence.normalize import load_dictionary

    provider = MockProvider({"extract_evidence": {"findings": [finding(drug_ingredient="Drug Alpha", event_term=None)]}})
    extractor = EvidenceExtractor(LLMGateway(provider), dictionary=load_dictionary(ROOT / "data/dictionaries/person3_synthetic.json"))
    extractor.bind(BudgetState(), "INV-A")
    item = extractor.extract_evidence(document(), CLAIM)[0]
    annotation = read_annotation(item.notes)
    assert annotation.drug_ingredient == "ingredient_alpha" and annotation.event_term is None


def test_direction_inconsistent_with_stance_is_not_direct_evidence():
    units, _, _ = extract({"findings": [finding(stance="contradicts", direction="increase")]})
    assert units[0].stance is Stance.UNCERTAIN


def test_unexamined_tail_cannot_be_cited():
    text = "x" * 40000 + TEXT
    provider = MockProvider({"extract_evidence": {"findings": [finding(locator=None)]}})
    extractor = EvidenceExtractor(LLMGateway(provider), max_windows=1)
    extractor.bind(BudgetState(), "INV-TAIL")
    units = extractor.extract_evidence(document(text=text), CLAIM)
    assert units[0].excluded and "quote_not_in_examined_window" in units[0].notes


def test_faers_is_uncertain_background_despite_provider_support_label():
    units, _, _ = extract(doc=document(source="faers"))
    assert units[0].stance is Stance.UNCERTAIN and units[0].evidence_type is EvidenceType.FAERS_REPORT
    assert EvidenceAnalyzer().analyze(units, CLAIM).assessment.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("uncertainty,direction", [("high", "decrease"), ("low", "no_clear_effect"), ("unknown", "unknown")])
def test_imprecise_or_null_results_are_not_rebuttal(uncertainty, direction):
    units, _, _ = extract({"findings": [finding(stance="contradicts", uncertainty=uncertainty, direction=direction)]})
    assert units[0].stance is Stance.UNCERTAIN
    assert EvidenceAnalyzer().analyze(units, CLAIM).assessment.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE


def test_missing_document_target_does_not_copy_claim_target():
    units, _, _ = extract({"findings": [finding(drug_ingredient=None)]})
    assert read_annotation(units[0].notes).drug_ingredient is None
    assert ScopeMatcher().assess_scope(units, CLAIM).outcome is ScopeOutcome.UNKNOWN


def test_missing_requested_dose_blocks_matching_even_when_route_matches():
    payload = finding()
    payload["scope"]["dose"] = None
    units, _, _ = extract({"findings": [payload]})
    assert ScopeMatcher().assess_scope(units, CLAIM).outcome is ScopeOutcome.UNKNOWN


def test_route_mismatch_is_explicit_but_population_overlap_remains_unknown():
    payload = finding()
    payload["scope"]["route"] = "intravenous"
    units, _, _ = extract({"findings": [payload]})
    assert ScopeMatcher().assess_scope(units, CLAIM).outcome is ScopeOutcome.MISMATCH
    payload["scope"]["route"] = "oral"
    payload["scope"]["population"] = "adults aged 40-50"
    units, _, _ = extract({"findings": [payload]})
    assert ScopeMatcher().assess_scope(units, CLAIM).outcome is ScopeOutcome.UNKNOWN


def test_comparable_opposing_studies_require_review_not_automatic_rebuttal():
    a, _, _ = extract()
    b, _, _ = extract({"findings": [finding(stance="contradicts", direction="decrease")]}, doc=document(doc_id="DOC-B"))
    analysis = EvidenceAnalyzer().analyze(a + b, CLAIM)
    assert analysis.assessment.assessment_status is AssessmentStatus.REQUIRES_HUMAN_REVIEW
    assert any(gap.kind is GapKind.CONTRADICTION and "Direct" in gap.description for gap in analysis.gaps)


def test_different_population_is_apparent_not_direct_contradiction():
    a, _, _ = extract()
    payload = finding(stance="contradicts", direction="decrease")
    payload["scope"]["population"] = "children"
    b, _, _ = extract({"findings": [payload]}, doc=document(doc_id="DOC-B"))
    analysis = EvidenceAnalyzer().analyze(a + b, CLAIM)
    assert any(gap.kind is GapKind.SCOPE_MISMATCH for gap in analysis.gaps)
    assert not any("Direct contradiction" in gap.description for gap in analysis.gaps)


def test_faers_duplicate_case_ids_are_candidates_without_deleting_reports():
    docs = [document(source="faers", doc_id=name, metadata={"case_id": "CASE-1"}) for name in ("DOC-A", "DOC-B")]
    assert duplicate_report_candidates(docs) == [("DOC-A", "DOC-B")]
    assert len(docs) == 2
