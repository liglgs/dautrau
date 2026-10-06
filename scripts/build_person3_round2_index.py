"""Build additive Person 3 split metadata without changing source datasets.

The index has two deliberately separate partitions:
* 300 committed drug-event pairs in ``data/gold``;
* 50 documents only referenced through the committed candidate-corpus audit.

It never copies machine labels or source text, so it remains reproducible offline
without tracking the physical candidate bundle.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIR_SOURCE = ROOT / "data/gold/drug-event-pairs.jsonl"
DOCUMENT_AUDIT = ROOT / "eval/person3/corpus/audit.json"
DEFAULT_OUTPUT = ROOT / "data/person3/r2_pair_evaluation_index.json"
STATUS = "đề xuất, chờ dược sĩ xác nhận"
PAIR_SOURCE_SPLITS = {"development": "development", "evaluation": "test"}
DOCUMENT_FAMILIES = {
    "development": ("metformin", "atorvastatin"),
    "evaluation": ("ibuprofen", "lisinopril", "amoxicillin"),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_index(rows: list[dict], audit: dict, *, pair_sha256: str, audit_sha256: str) -> dict:
    """Return the source-pointer-only split index after validating both inputs."""
    if len(rows) != 300 or len({row["pair_id"] for row in rows}) != len(rows):
        raise ValueError("Expected exactly 300 unique committed drug-event pairs")
    pair_groups = {
        role: [row for row in rows if row["split"] == source_split]
        for role, source_split in PAIR_SOURCE_SPLITS.items()
    }
    pair_drugs = {role: {row["drug"] for row in group} for role, group in pair_groups.items()}
    if pair_drugs["development"] & pair_drugs["evaluation"]:
        raise ValueError("A drug family appears in both pair development and evaluation")
    if {role: len(group) for role, group in pair_groups.items()} != {"development": 200, "evaluation": 100}:
        raise ValueError("Expected committed pair split of 200 development and 100 evaluation")

    families = audit.get("families", {})
    if audit.get("status") != "candidate_not_gold" or audit.get("documents") != 50 or audit.get("gold_labels") != 0:
        raise ValueError("Candidate document audit must be a 50-document candidate_not_gold corpus with no gold labels")
    if set(families) != set().union(*DOCUMENT_FAMILIES.values()) or any(len(doc_ids) != 10 for doc_ids in families.values()):
        raise ValueError("Expected five distinct document families with ten documents each")
    document_groups = {
        role: [{"family_id": family, "doc_id": doc_id, "review_status": "candidate_not_gold", "gold_label": None}
               for family in family_ids for doc_id in families[family]]
        for role, family_ids in DOCUMENT_FAMILIES.items()
    }
    development_doc_ids = {row["doc_id"] for row in document_groups["development"]}
    evaluation_doc_ids = {row["doc_id"] for row in document_groups["evaluation"]}
    if development_doc_ids & evaluation_doc_ids or len(development_doc_ids | evaluation_doc_ids) != 50:
        raise ValueError("Document IDs overlap across development and evaluation")

    return {
        "artifact_version": "r2-3-07.2",
        "status": STATUS,
        "mode": "additive_index_only",
        "pair_partition_300": {
            "source_dataset": {"path": "data/gold/drug-event-pairs.jsonl", "sha256": pair_sha256,
                               "pair_count": len(rows), "source_status": "candidate_not_gold",
                               "source_machine_labels": "not copied or consumed by this index"},
            "unit": "drug family",
            "development": {"source_split": "development", "pair_count": len(pair_groups["development"]),
                            "drug_count": len(pair_drugs["development"])},
            "evaluation": {"source_split": "test", "pair_count": len(pair_groups["evaluation"]),
                           "drug_count": len(pair_drugs["evaluation"])},
            "overlapping_drug_families": [],
        },
        "document_package_50": {
            "status": STATUS,
            "proposal": True,
            "source_audit": {"path": "eval/person3/corpus/audit.json", "sha256": audit_sha256,
                             "bundle_sha256": audit["bundle_sha256"], "document_count": audit["documents"],
                             "physical_bundle": "mvp-candidates-50-2026-10-02.zip is not tracked; this index references committed metadata only"},
            "unit": "family",
            "development": {"families": list(DOCUMENT_FAMILIES["development"]), "document_count": len(document_groups["development"]),
                            "entries": document_groups["development"]},
            "evaluation": {"families": list(DOCUMENT_FAMILIES["evaluation"]), "document_count": len(document_groups["evaluation"]),
                           "entries": document_groups["evaluation"]},
            "overlapping_families": [],
            "overlapping_doc_ids": [],
        },
        "labels": {"gold_label": None, "clinical_gold": False,
                   "rule": "AI output, source machine-proposed labels, and candidate status never become gold."},
        "prompt_access": {
            "development_pair_ids_may_be_used_for_tuning": True,
            "evaluation_pair_ids_may_be_used_for_prompt_or_tuning": False,
            "development_document_ids_may_be_used_for_tuning": True,
            "evaluation_document_ids_may_be_used_for_prompt_or_tuning": False,
            "evaluation_labels_may_be_in_prompt": False,
            "check": "Prompt files must not embed evaluation pair IDs, evaluation document IDs, or labels.",
        },
    }


def main(output: Path = DEFAULT_OUTPUT) -> dict:
    value = build_index(read_rows(PAIR_SOURCE), json.loads(DOCUMENT_AUDIT.read_text(encoding="utf-8")),
                        pair_sha256=digest(PAIR_SOURCE), audit_sha256=digest(DOCUMENT_AUDIT))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return value


if __name__ == "__main__":
    result = main()
    documents = result["document_package_50"]
    print(f"Wrote {DEFAULT_OUTPUT.relative_to(ROOT)}: 300 pairs (200/100), "
          f"50 documents ({documents['development']['document_count']}/{documents['evaluation']['document_count']}); {STATUS}.")
