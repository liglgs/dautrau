"""Blank/invalid expert packets cannot silently become accepted gold."""

from copy import deepcopy

from test_person3_corpus import fixture_bundle

from src.services.evidence.annotation_review import compare_reviews, validate_annotation
from src.services.evidence.corpus import load_candidate_corpus


def packets(tmp_path):
    corpus = load_candidate_corpus(fixture_bundle(tmp_path))
    claim = {"claim_id": "C1", "version": 1, "family_id": "metformin", "split": "development",
             "source_doc_ids": [d.doc_id for d in corpus.documents]}
    row = {"claim_id": "C1", "claim_version": 1, "family_id": "metformin", "split": "development",
        "source_manifest_sha256": corpus.bundle_hash, "record_status": "completed_independent_expert_review",
        "annotator_id": "expert-a", "annotator_role": "clinical_pharmacist", "annotation_timestamp": "2026-10-02T12:00:00Z",
        "expected_assessment_status": "insufficient_evidence", "expected_abstention": True,
        "evidence_annotations": [], "required_gold_evidence_ids": [], "optional_gold_evidence_ids": [],
        "critical_gaps": ["Technical fixture does not establish clinical interpretation."]}
    return corpus, claim, row


def test_pending_packets_are_reported_without_creating_gold(tmp_path):
    corpus, claim, row = packets(tmp_path)
    row["record_status"] = "pending_independent_expert_review"
    result = compare_reviews([claim], [row], [deepcopy(row)], corpus)
    assert result["pending"] and not result["ready_for_team_adjudication"]
    assert result["clinical_gold_published"] is False


def test_two_distinct_reviewers_and_matching_corpus_are_required(tmp_path):
    corpus, claim, row = packets(tmp_path)
    other = deepcopy(row)
    other["source_manifest_sha256"] = "wrong"
    result = compare_reviews([claim], [row], [other], corpus)
    assert any("distinct" in error for error in result["pending"][0]["issues"]["reviewer_b"])
    assert any("stale" in error for error in result["pending"][0]["issues"]["reviewer_b"])


def test_disagreements_require_adjudication_and_never_publish_gold(tmp_path):
    corpus, claim, row = packets(tmp_path)
    other = deepcopy(row)
    other.update(annotator_id="expert-b", expected_assessment_status="scope_mismatch")
    result = compare_reviews([claim], [row], [other], corpus)
    assert result["disagreements"][0]["fields"] == ["expected_assessment_status"]
    assert not result["ready_for_team_adjudication"]
    assert result["clinical_gold_published"] is False


def test_faers_cannot_be_required_direct_support_even_with_verified_quote(tmp_path):
    corpus, claim, row = packets(tmp_path)
    doc = next(d for d in corpus.documents if d.source == "faers")
    row.update(expected_assessment_status="supported_for_scope", required_gold_evidence_ids=["E1"])
    row["evidence_annotations"] = [{"evidence_id": "E1", "document_id": doc.doc_id, "source_id": doc.source_id,
        "source_version": doc.version, "parsed_text_hash": doc.hash, "quoted_span": doc.text,
        "span_locator": {"unit": "unicode_code_points", "start": 0, "end": len(doc.text)},
        "citation_integrity": "verified", "citation_entailment": "supported", "stance": "support",
        "eligible_as_direct_evidence": True, "reason": "Attempted unsupported label", "scope_fields": []}]
    errors = validate_annotation(row, claim, corpus)
    assert any("FAERS" in error for error in errors)
    assert any("scope field" in error for error in errors)


def test_spl_only_maps_explicit_single_active_moiety():
    from src.services.evidence.corpus import spl_ingredient_relations
    def ingredient(name, moiety):
        return f'<ingredient classCode="ACTIB"><ingredientSubstance><name>{name}</name><activeMoiety><activeMoiety><name>{moiety}</name></activeMoiety></activeMoiety></ingredientSubstance></ingredient>'
    raw = '<document xmlns="urn:hl7-org:v3">' + ingredient("METFORMIN HYDROCHLORIDE", "METFORMIN") + '</document>'
    assert spl_ingredient_relations(raw.encode()) == [{"ingredient": "METFORMIN HYDROCHLORIDE", "active_moiety": "METFORMIN"}]
    combination = raw.replace('</document>', ingredient("OTHER", "OTHER") + '</document>')
    assert spl_ingredient_relations(combination.encode()) == []
