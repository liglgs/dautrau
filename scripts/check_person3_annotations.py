"""Validate reviewer packets and report disagreements; do not publish clinical gold."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))


def read_rows(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    from src.services.evidence.annotation_review import compare_reviews
    from src.services.evidence.corpus import load_candidate_corpus
    from src.services.evidence.corpus_runtime import DEFAULT_BUNDLE
    bench = ROOT / "data/benchmark"
    report = compare_reviews(read_rows(bench / "mvp_claims.jsonl"), read_rows(bench / "reviewer_a.jsonl"),
                             read_rows(bench / "reviewer_b.jsonl"), load_candidate_corpus(DEFAULT_BUNDLE))
    target = ROOT / "eval/person3/corpus/annotation-status.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Claims={report['claims']}; pending={len(report['pending'])}; disagreements={len(report['disagreements'])}; ready={len(report['ready_for_team_adjudication'])}")
    print("Clinical gold is not published; independent expert review and split acceptance are required.")


if __name__ == "__main__":
    main()
