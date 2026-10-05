"""Offline development retrieval check; labels are read only after ranking finishes."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))

from eval.baselines.keyword import BM25
from eval.baselines.scoped_rag import DICTIONARY, VERSION, prepare, protocol
from eval.contracts import Prediction
from eval.corpus import Corpus, digest, read_jsonl
from eval.metrics import aggregate, score
from eval.run_evaluation import offline


def check(dataset, dictionary_path=DICTIONARY):
    manifest = dataset / "corpus_manifest.json"
    index = BM25(Corpus.load(manifest))
    payloads = []
    with offline():
        for claim in read_jsonl(dataset / "claims.jsonl"):
            if claim["split"] == "development":
                payloads.append((claim["claim_id"], prepare(index, claim, "preview-no-model-calls",
                                                          dictionary_path=dictionary_path)))
    # Scoring stage only: the inference/retrieval function has no label input.
    labels = {r["claim_id"]: r for r in read_jsonl(dataset / "annotations.jsonl")}
    rows, details = [], []
    for claim_id, payload in payloads:
        metrics = score(Prediction(list(payload["alias_to_unit_id"].values())), labels[claim_id])
        rows.append({"claim_id": claim_id, "error": None, "metrics": metrics})
        details.append({"claim_id": claim_id, "normalization_requires_review": payload["normalization"]["requires_review"],
            "units": len(payload["evidence"]), "source_counts": {s: sum(u["source"] == s for u in payload["evidence"])
                for s in ["pubmed", "dailymed", "faers"]}, "queries": payload["retrieval_queries"],
            "required_span_recall": metrics["evidence_recall_at_20"],
            "rendered_context_chars": len(payload["rendered_untrusted"])})
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "version": VERSION,
        "split": "development", "mode": "offline retrieval preview only", "live_model_calls": 0,
        "heldout_rerun": False, "prediction_accuracy_measured": False, "clinical_validation_claimed": False,
        "reference_kind": json.loads(manifest.read_bytes()).get("annotation_status"),
        "protocol": protocol(Path(dictionary_path)), "corpus_manifest_sha256": digest(manifest.read_bytes()),
        "claims": details, "aggregate": aggregate(rows),
        "note": "This command measures selected-span retrieval only; model synthesis reports are separate. No clinical entailment review."}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, default=DICTIONARY)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/person3/scoped-rag-readiness.json")
    args = parser.parse_args()
    result = check(args.dataset, args.dictionary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Development selected-span recall:", result["aggregate"]["evidence_recall_at_20"])
    print("No model calls. Output:", args.output)


if __name__ == "__main__":
    main()
