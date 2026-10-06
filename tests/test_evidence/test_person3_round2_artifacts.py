"""Offline checks for the additive Person 3 round-two preparation artifacts."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "data/person3"
STATUS = "đề xuất, chờ dược sĩ xác nhận"


def load(name):
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def abstract_sections(path):
    root = ET.parse(path).getroot()
    return {
        node.attrib.get("Label"): "".join(node.itertext()).strip()
        for node in root.iter()
        if node.tag.endswith("AbstractText")
    }


def test_evidence_bundles_are_traceable_to_committed_xml_and_keep_study_fields():
    artifact = load("r2_evidence_bundles.json")
    manifest = json.loads((ROOT / "docs/research/2026-10-05/data-real/manifest.json").read_text(encoding="utf-8"))
    sources = {entry["id"]: entry for entry in manifest}
    assert artifact["status"] == STATUS
    assert {item["source"]["pmid"] for item in artifact["evidence_bundles"]} == {"39975698", "40285433"}

    for bundle in artifact["evidence_bundles"]:
        source = bundle["source"]
        snapshot = ROOT / source["snapshot_file"]
        manifest_entry = sources[f"pubmed-{source['pmid']}"]
        assert bundle["status"] == STATUS
        assert source["coverage"] == "abstract_only"
        assert source["snapshot_sha256"] == manifest_entry["sha256"] == sha256(snapshot)
        study = bundle["study"]
        assert all(study[field] for field in ("design", "population", "setting", "comparator", "outcome", "time_window", "estimates", "limitations"))
        assert study["route"]["status"] == "unknown" and study["route"]["value"] is None
        assert all("ci_95" in estimate and estimate["unit"] for estimate in study["estimates"])
        sections = abstract_sections(snapshot)
        for quote in bundle["quotes"]:
            assert quote["xml_tag"] == "AbstractText"
            assert quote["text"] in sections[quote["xml_label"]]


def test_glossary_separates_intake_from_conclusion_and_preserves_unknown():
    content = (ROOT / "docs/person3/round2/field-glossary.md").read_text(encoding="utf-8")
    assert STATUS in content
    assert "`required-for-intake`" in content
    assert "`required-for-conclusion`" in content
    for field in ("purpose", "indication", "population", "setting", "route", "comparator", "outcome", "time"):
        assert f"`{field}`" in content
    assert "Không chuyển bất cứ trạng thái nào thành `false`" in content
    assert "không tự match sản phẩm khác đường" in content.lower()


def test_case_scenarios_keep_missing_data_duplicates_and_versions_explicit():
    specification = (ROOT / "docs/person3/round2/case-field-specification.md").read_text(encoding="utf-8")
    scenarios = load("r2_case_scenarios.json")
    assert STATUS in specification
    assert scenarios["status"] == STATUS
    assert scenarios["synthetic"] is True
    rows = scenarios["scenarios"]
    assert all(row["synthetic"] is True for row in rows)
    initial = next(row for row in rows if row["scenario_id"] == "missing-data-initial")
    duplicate = next(row for row in rows if row["scenario_id"] == "duplicate-candidate")
    follow_up = next(row for row in rows if row["scenario_id"] == "follow-up-same-case-versioned")
    assert initial["outcome"]["seriousness"] == "not_assessed"
    assert initial["dechallenge"] == "unknown" and initial["rechallenge"] == "not_done"
    assert duplicate["duplicate_candidate_of"] == initial["case_id"]
    assert duplicate["deduplication_status"] == "requires_pharmacist_review"
    assert follow_up["case_id"] == initial["case_id"]
    assert follow_up["case_version"] == initial["case_version"] + 1
    assert follow_up["supersedes_version"] == initial["case_version"]


def test_separate_pair_and_document_partitions_keep_candidate_state_and_block_evaluation_leakage():
    index = load("r2_pair_evaluation_index.json")
    partition = index["pair_partition_300"]
    source = ROOT / partition["source_dataset"]["path"]
    pairs = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line]
    audit_path = ROOT / index["document_package_50"]["source_audit"]["path"]
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    documents = index["document_package_50"]
    assert index["status"] == STATUS
    assert len(pairs) == partition["source_dataset"]["pair_count"] == 300
    assert partition["source_dataset"]["sha256"] == sha256(source)
    assert all(pair["review"]["status"] == "candidate_not_gold" for pair in pairs)
    assert partition["development"]["pair_count"] == 200
    assert partition["evaluation"]["pair_count"] == 100
    assert partition["overlapping_drug_families"] == []
    assert documents["source_audit"]["sha256"] == sha256(audit_path)
    assert documents["source_audit"]["bundle_sha256"] == audit["bundle_sha256"]
    assert documents["development"]["families"] == ["metformin", "atorvastatin"]
    assert documents["evaluation"]["families"] == ["ibuprofen", "lisinopril", "amoxicillin"]
    development_docs = {entry["doc_id"] for entry in documents["development"]["entries"]}
    evaluation_docs = {entry["doc_id"] for entry in documents["evaluation"]["entries"]}
    assert len(development_docs) == documents["development"]["document_count"] == 20
    assert len(evaluation_docs) == documents["evaluation"]["document_count"] == 30
    assert not development_docs & evaluation_docs
    assert development_docs | evaluation_docs == {doc_id for values in audit["families"].values() for doc_id in values}
    assert all(entry["review_status"] == "candidate_not_gold" and entry["gold_label"] is None
               for group in ("development", "evaluation") for entry in documents[group]["entries"])
    assert index["labels"]["gold_label"] is None and not index["labels"]["clinical_gold"]
    assert not index["prompt_access"]["evaluation_pair_ids_may_be_used_for_prompt_or_tuning"]
    assert not index["prompt_access"]["evaluation_document_ids_may_be_used_for_prompt_or_tuning"]
    prompt_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "src/prompts").glob("*.md"))
    evaluation_pair_ids = [pair["pair_id"] for pair in pairs if pair["split"] == "test"]
    assert not any(pair_id in prompt_text for pair_id in evaluation_pair_ids)
    assert not any(doc_id in prompt_text for doc_id in evaluation_docs)


def test_annotation_ledger_requires_independent_identity_date_and_disagreement_audit():
    guide = (ROOT / "docs/person3/round2/annotation-guide.md").read_text(encoding="utf-8")
    ledger = json.loads((ARTIFACTS / "r2_annotation_ledger.template.jsonl").read_text(encoding="utf-8"))
    assert STATUS in guide
    assert ledger["status"] == STATUS
    assert ledger["record_status"] == "blank_independent_annotation_not_gold"
    assert ledger["gold_label"] is None and ledger["ai_generated"] is False
    for field in ("annotator_id", "annotator_role", "annotation_date", "independent_label"):
        assert field in ledger
    assert ledger["disagreement"]["status"] == "none"
    assert "Không xem ledger còn lại hay model prediction" in guide
