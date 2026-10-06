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
        assert "comparators" not in study
        assert study["route"]["status"] == "unknown" and study["route"]["value"] is None
        assert all("ci_95" in estimate and estimate["unit"] for estimate in study["estimates"])
        sections = abstract_sections(snapshot)
        quotes_by_id = {quote["id"]: quote for quote in bundle["quotes"] if "id" in quote}
        for quote in bundle["quotes"]:
            assert quote["xml_tag"] == "AbstractText"
            assert quote["text"] in sections[quote["xml_label"]]
        assert all(estimate["source_quote_id"] in quotes_by_id for estimate in study["estimates"])

        if source["pmid"] == "40285433":
            expected = {
                "macrolides": (1.52, [1.33, 1.74]),
                "tetracyclines": (1.86, [1.54, 2.24]),
                "penicillins with extended spectrum": (1.45, [1.28, 1.65]),
                "cephalosporins": (1.23, [1.10, 1.37]),
                "lincosamides": (1.73, [1.43, 2.11]),
            }
            extracted = {estimate["comparator"]: (estimate["estimate"], estimate["ci_95"])
                         for estimate in study["estimates"] if estimate["exposure"] == "FQ"}
            assert extracted == expected
            coverage = study["estimate_extraction_coverage"]
            assert coverage["extracted_estimate_count"] == len(study["estimates"]) == 6
            assert coverage["source_quote_id"] in quotes_by_id


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
    assert initial["dechallenge"] == "unknown" and initial["rechallenge"] == "unknown"
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
    assert partition["overlapping_ingredients"] == []
    assert documents["source_audit"]["sha256"] == sha256(audit_path)
    assert documents["source_audit"]["bundle_sha256"] == audit["bundle_sha256"]
    assert documents["development"]["ingredients"] == ["metformin", "ibuprofen", "amoxicillin"]
    assert documents["evaluation"]["ingredients"] == ["atorvastatin", "lisinopril"]
    development_docs = {entry["doc_id"] for entry in documents["development"]["entries"]}
    evaluation_docs = {entry["doc_id"] for entry in documents["evaluation"]["entries"]}
    development_ingredients = {entry["ingredient_id"] for entry in documents["development"]["entries"]}
    evaluation_ingredients = {entry["ingredient_id"] for entry in documents["evaluation"]["entries"]}
    pair_development_ingredients = {pair["drug"] for pair in pairs if pair["split"] == "development"}
    pair_evaluation_ingredients = {pair["drug"] for pair in pairs if pair["split"] == "test"}
    assert len(development_docs) == documents["development"]["document_count"] == 30
    assert len(evaluation_docs) == documents["evaluation"]["document_count"] == 20
    assert not development_docs & evaluation_docs
    assert development_docs | evaluation_docs == {doc_id for values in audit["families"].values() for doc_id in values}
    assert development_ingredients == set(audit["families"]) & pair_development_ingredients
    assert not evaluation_ingredients & pair_development_ingredients
    assert evaluation_ingredients & pair_evaluation_ingredients == {"atorvastatin"}
    assert evaluation_ingredients - (pair_development_ingredients | pair_evaluation_ingredients) == {"lisinopril"}
    assert documents["overlapping_ingredients"] == []
    assert "exact-ingredient split only" in documents["residual_drug_class_overlap_limitation"]
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
    assert ledger["gold_label"] is None and ledger["ai_generated"] is None
    for field in ("annotator_id", "annotator_role", "annotation_date", "independent_label"):
        assert field in ledger
    assert ledger["disagreement"]["status"] == "not_compared"
    assert "Không xem ledger còn lại hay model prediction" in guide
