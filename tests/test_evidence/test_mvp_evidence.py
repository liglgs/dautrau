"""Offline behavior checks for Person 3 drafts, independent of FastAPI/LLM."""

import json
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.preview_person3 import changed_scope, fixture_document, run_preparation, write_preview
from src.services.evidence.citations import validate_citation
from src.services.evidence.contradiction import compare_evidence, effective_stance
from src.services.evidence.drafts import EvidenceDraft, IntervalDraft, scope_from_dict
from src.services.evidence.normalize import load_dictionary, normalize_claim
from src.services.evidence.scope import assess_scope

TASK_ROOT = Path(__file__).resolve().parents[2]


class Person3EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((TASK_ROOT / "tests/fixtures/mvp/person3/cases.json").read_text(encoding="utf-8"))
        cls.base = scope_from_dict(cls.fixture["base_scope"])
        cls.dictionary = load_dictionary(TASK_ROOT / "data/dictionaries/person3_synthetic.json")

    def test_twenty_documented_cases_have_expected_behavior(self):
        report = run_preparation()
        self.assertEqual(report["total"], 20)
        ids = [case["id"] for case in report["results"]]
        self.assertEqual(len(set(ids)), 20)
        for case in report["results"]:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["passed"], case)

    def test_synthetic_dictionary_requires_explicit_opt_in(self):
        with self.assertRaises(ValueError):
            normalize_claim("Alpha", "Event Alpha", self.dictionary)

    def test_missing_required_terms_are_rejected(self):
        for drug, event in (("", "Event Alpha"), ("Alpha", " ")):
            with self.assertRaises(ValueError):
                normalize_claim(drug, event, self.dictionary, allow_synthetic=True)

    def test_ambiguous_brand_does_not_pick_first_ingredient(self):
        result = normalize_claim("Brand Ambiguous", "Event Alpha", self.dictionary, allow_synthetic=True)
        self.assertEqual(len(result.ingredient_candidates), 2)
        self.assertIn("ingredient", result.ambiguities)
        self.assertTrue(result.requires_review)

    def test_unlisted_terms_remain_unknown(self):
        result = normalize_claim("Not in dictionary", "Not in dictionary", self.dictionary, allow_synthetic=True)
        self.assertEqual(result.unknown_fields, ("ingredient", "event"))
        self.assertEqual(result.original_drug, "Not in dictionary")

    def test_aggregate_population_does_not_establish_subgroup_effect(self):
        narrow_claim = replace(self.base, population=IntervalDraft(18, 30, "years"))
        result = assess_scope(self.base, narrow_claim)
        self.assertFalse(result.eligible_as_direct_evidence)
        self.assertEqual(next(field.status for field in result.fields if field.field == "population"), "unknown")

    def test_different_units_require_verified_conversion(self):
        evidence = replace(self.base, dose=IntervalDraft(0.01, 0.01, "g/day"))
        result = assess_scope(evidence, self.base)
        self.assertFalse(result.eligible_as_direct_evidence)
        self.assertEqual(next(field.status for field in result.fields if field.field == "dose"), "unknown")

    def test_critical_unhandled_context_blocks_direct_evidence(self):
        evidence = replace(self.base, unresolved_critical_fields=("comorbidity",))
        result = assess_scope(evidence, self.base)
        self.assertFalse(result.eligible_as_direct_evidence)
        self.assertTrue(result.requires_review)

    def test_missing_ingredient_never_matches(self):
        result = assess_scope(replace(self.base, ingredient=None), replace(self.base, ingredient=None))
        self.assertFalse(result.eligible_as_direct_evidence)
        self.assertEqual(result.fields[0].status, "unknown")

    def test_missing_optional_field_is_unknown_even_when_not_blocking(self):
        scope = replace(self.base, dose=None)
        result = assess_scope(scope, scope)
        self.assertEqual(next(field.status for field in result.fields if field.field == "dose"), "unknown")

    def test_interval_bounds_are_validated(self):
        for lower, upper in ((20, 10), (-1, 2), (float("nan"), 2), (0, float("inf")), (True, 2)):
            with self.subTest(lower=lower, upper=upper), self.assertRaises(ValueError):
                IntervalDraft(lower, upper, "years")

    def test_unexpected_scope_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            changed_scope(self.fixture["base_scope"], {"approve": True})

    def test_high_uncertainty_is_not_negative_evidence(self):
        evidence = EvidenceDraft("E1", self.base, "contradict", "pubmed", "high", "decrease")
        self.assertEqual(effective_stance(evidence), "uncertain")

    def test_faers_does_not_become_comparative_support(self):
        evidence = EvidenceDraft("E1", self.base, "support", "faers", "low", "increase")
        self.assertEqual(effective_stance(evidence), "background")

    def test_incomplete_comparator_cannot_form_direct_contradiction(self):
        left = EvidenceDraft("E1", replace(self.base, comparator=None), "support", "pubmed", "low", "increase")
        right = EvidenceDraft("E2", replace(self.base, comparator=None), "contradict", "pubmed", "low", "decrease")
        result = compare_evidence(left, right)
        # Comparator must be explicit for comparing findings, even when absent from both.
        self.assertNotEqual(result.kind, "direct")

    def test_inconsistent_stance_and_direction_requires_review(self):
        left = EvidenceDraft("E1", self.base, "support", "pubmed", "low", "increase")
        right = EvidenceDraft("E2", self.base, "contradict", "pubmed", "low", "increase")
        self.assertEqual(compare_evidence(left, right).kind, "needs_review")

    def test_self_comparison_is_rejected(self):
        evidence = EvidenceDraft("E1", self.base, "support", "pubmed", "low", "increase")
        with self.assertRaises(ValueError):
            compare_evidence(evidence, evidence)

    def test_wrong_target_is_not_comparable(self):
        left = EvidenceDraft("E1", self.base, "support", "pubmed", "low", "increase")
        right = EvidenceDraft("E2", replace(self.base, event="event_beta"), "contradict", "pubmed", "low", "decrease")
        self.assertEqual(compare_evidence(left, right).kind, "not_comparable")

    def test_verified_quote_does_not_auto_verify_entailment_or_approval(self):
        document, citation = fixture_document(self.fixture["document"])
        result = validate_citation(document, citation)
        self.assertTrue(result.span_verified)
        self.assertEqual(result.entailment_status, "pending")
        self.assertFalse(result.eligible_for_official_statement)

    def test_changed_document_text_invalidates_hash(self):
        document, citation = fixture_document(self.fixture["document"])
        result = validate_citation(replace(document, text=document.text + " changed"), citation)
        self.assertIn("document_hash_mismatch", result.errors)

    def test_changed_source_version_invalidates_citation(self):
        document, citation = fixture_document(self.fixture["document"])
        result = validate_citation(document, replace(citation, source_version="2"))
        self.assertIn("source_version_mismatch", result.errors)

    def test_unsafe_url_is_rejected_without_fetching(self):
        document, citation = fixture_document(self.fixture["document"])
        result = validate_citation(replace(document, source_url="javascript:alert(1)"), replace(citation, source_url="javascript:alert(1)"))
        self.assertIn("invalid_source_url", result.errors)

    def test_unicode_locator_uses_code_points(self):
        payload = dict(self.fixture["document"], text="Dữ liệu giả lập: trẻ em và người lớn.", quote="trẻ em")
        document, citation = fixture_document(payload)
        self.assertTrue(validate_citation(document, citation).span_verified)

    def test_boolean_locator_is_not_an_offset(self):
        document, citation = fixture_document(self.fixture["document"])
        self.assertIn("invalid_locator", validate_citation(document, replace(citation, start=True)).errors)

    def test_preview_is_draft_and_does_not_claim_clinical_success(self):
        report = run_preparation()
        with TemporaryDirectory() as directory:
            write_preview(report, Path(directory))
            dossier = (Path(directory) / "dossier-synthetic-draft.md").read_text(encoding="utf-8")
            results = json.loads((Path(directory) / "technical-results.json").read_text(encoding="utf-8"))
            self.assertIn("NHÁP SYNTHETIC", dossier)
            self.assertIn("entailment pending", dossier)
            self.assertEqual(results["mode"], "synthetic")


if __name__ == "__main__":
    unittest.main()
