"""Validate the supplied ZIP and prepare dictionaries, claim drafts and review queues."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_initial(path, value):
    """Never overwrite human annotation or a previously frozen split."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(value, encoding="utf-8")


def prepare(bundle):
    from src.services.evidence.corpus import load_candidate_corpus, corpus_dictionary
    corpus = load_candidate_corpus(bundle)
    write_json(ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json", corpus_dictionary(corpus))
    write_json(ROOT / "eval/person3/corpus/audit.json", corpus.audit())
    local = ROOT / "data/person3/corpus"
    local.mkdir(parents=True, exist_ok=True)
    (local / "documents.jsonl").write_text("".join(d.model_dump_json() + "\n" for d in corpus.documents), encoding="utf-8")
    write_initial(local / "document_reviews.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in corpus.reviews))
    claims = []
    selected = ["metformin", "ibuprofen", "lisinopril", "amoxicillin"]
    for family in selected:
        pair = next(p for p in corpus.collection["pairs"] if p["drug"] == family)
        event = pair["event"].casefold()
        variants = [({}, "broad_scope"), ({"population": "adults", "route": "oral"}, "population_route"),
                    ({"dose": "1000 mg/day", "time_window": "90 days"}, "specified_scope_requires_review"),
                    ({"route": "intravenous"}, "route_challenge"), ({"drug": "Unresolved brand"}, "technical_ambiguity")]
        for i, (scope, category) in enumerate(variants, 1):
            claim = {"claim_text": f"Investigate reported association: {family} / {event}; requested scope: {json.dumps(scope)}.",
                     "drug": family, "event": event, "population": None, "dose": None, "route": None, "time_window": None, **scope}
            claims.append({"claim_id": f"P3-{family.upper()}-{i:02}", "version": 1, "family_id": family,
                "split": "development" if family == "metformin" else "heldout",
                "status": "draft_not_expert_reviewed", "case_category": category,
                "dataset_mode": "technical_real_source_candidates", "claim": claim,
                "source_doc_ids": corpus.families[family], "expected_assessment_status": None})
    bench = ROOT / "data/benchmark"
    write_initial(bench / "mvp_claims.jsonl", "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in claims))
    # An empty gold file is intentional: no expert labels have been supplied.
    write_initial(bench / "mvp_gold.jsonl", "")
    manifest = {"version": "person3-candidate-draft-2026-10-02.1", "status": "draft_not_frozen_not_gold",
        "corpus_sha256": corpus.bundle_hash, "corpus_cutoff": corpus.collection["created_at"],
        "development_families": ["metformin"], "heldout_families": ["ibuprofen", "lisinopril", "amoxicillin"],
        "reserve_families": ["atorvastatin"], "development_count": 5, "heldout_count": 15,
        "split_family_overlap": [], "clinical_metrics_ready": False,
        "gold_file": "mvp_gold.jsonl", "expert_reviews_required": 2,
        "limitations": ["Claims and split are proposals awaiting Person 4/expert acceptance.",
            "Dose/time/population challenges are requested hypotheses, not source-established contexts.",
            "Unresolved-brand cases are technical inputs, not attested medicines.",
            "Supported/contradicted/direct-contradiction coverage is not yet established by experts.",
            "Heldout validity requires freezing before prompt tuning and recording exposure.",
            "DailyMed SETIDs may repeat label content; PubMed revision is not verified; FAERS is background."]}
    write_initial(bench / "mvp_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    template = json.loads((ROOT / "docs/person3/annotation_template.json").read_text(encoding="utf-8"))
    # Re-read persistent draft claims so reruns respect human changes.
    existing_claims = [json.loads(l) for l in (bench / "mvp_claims.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for reviewer in ["reviewer_a", "reviewer_b"]:
        rows = []
        for c in existing_claims:
            row = deepcopy(template)
            row.pop("evidence_annotation_shape", None)
            row.update({"record_status": "pending_independent_expert_review", "claim_id": c["claim_id"],
                "claim_version": c["version"], "family_id": c["family_id"], "split": c["split"],
                "dataset_mode": c["dataset_mode"], "source_manifest_version": manifest["version"],
                "source_manifest_sha256": corpus.bundle_hash,
                "document_family_ids": c["source_doc_ids"], "reviewer_slot": reviewer})
            rows.append(row)
        write_initial(bench / f"{reviewer}.jsonl", "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"Validated {len(corpus.documents)} real-source documents; dictionary and review queues ready.")
    print("20 draft claims (5 development / 15 heldout proposal); gold labels remain empty.")
    return corpus


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "data/mvp-candidates-50-2026-10-02.zip")
    prepare(parser.parse_args().bundle)
