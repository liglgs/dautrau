"""Real-model offset failures: recover exact unique text without fuzzy matching."""

import pytest
from test_person3_contracts import CLAIM, TEXT, document, finding

from src.models.schemas import BudgetState
from src.services.evidence.contracts import read_annotation
from src.services.evidence.extract import EvidenceExtractor
from src.services.llm import LLMGateway, MockProvider


@pytest.mark.parametrize("locator", [None, {"start": 1, "end": 2}, {"start": 9999, "end": 10000}])
def test_exact_unique_quote_gets_source_offsets_and_auditable_alignment(locator):
    prefix = "Tiếng Việt α.\n"
    doc = document(text=prefix + TEXT)
    extractor = EvidenceExtractor(LLMGateway(MockProvider({"extract_evidence": {"findings": [finding(locator=locator)]}})))
    extractor.bind(BudgetState(), "ALIGN")
    unit = extractor.extract_evidence(doc, CLAIM)[0]
    assert not unit.excluded
    assert unit.locator.start == len(prefix) and unit.locator.end == len(doc.text)
    assert "realigned_exact_unique" in read_annotation(unit.notes).issues
    assert extractor.alignment_events[0]["model_locator"] == (None if locator is None else {**locator, "section": None})


def test_ambiguous_quote_with_missing_locator_stays_excluded():
    doc = document(text=TEXT + "\n" + TEXT)
    extractor = EvidenceExtractor(LLMGateway(MockProvider({"extract_evidence": {"findings": [finding(locator=None)]}})))
    extractor.bind(BudgetState(), "AMBIGUOUS")
    unit = extractor.extract_evidence(doc, CLAIM)[0]
    assert unit.excluded and "ambiguous_quote_locator" in read_annotation(unit.notes).issues


def test_repeated_quote_with_correct_reported_locator_is_unambiguous():
    doc = document(text=TEXT + "\n" + TEXT)
    extractor = EvidenceExtractor(LLMGateway(MockProvider({"extract_evidence": {"findings": [finding()]}})))
    extractor.bind(BudgetState(), "REPORTED")
    unit = extractor.extract_evidence(doc, CLAIM)[0]
    assert not unit.excluded and not extractor.alignment_events


def test_paraphrase_or_changed_whitespace_is_never_repaired():
    changed = TEXT.replace(" ", "  ", 1)
    extractor = EvidenceExtractor(LLMGateway(MockProvider({"extract_evidence": {"findings": [finding(quote=changed, locator=None)]}})))
    extractor.bind(BudgetState(), "PARAPHRASE")
    unit = extractor.extract_evidence(document(), CLAIM)[0]
    assert unit.excluded and "quote_not_in_examined_window" in unit.notes
