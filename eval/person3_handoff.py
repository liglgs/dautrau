"""Check Person 3 candidate handoff without manufacturing gold or benchmark metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile

from eval.corpus import digest, read_jsonl, timestamp

ROOT = Path(__file__).resolve().parents[1]


def inspect_handoff(benchmark: Path, bundle: Path) -> dict:
    names = ["mvp_manifest.json", "mvp_claims.jsonl", "mvp_gold.jsonl", "reviewer_a.jsonl", "reviewer_b.jsonl"]
    issues: list[str] = []
    hashes = {}
    for name in names:
        path = benchmark / name
        if not path.is_file():
            issues.append(f"Missing handoff file: {name}")
        else:
            hashes[name] = digest(path.read_bytes())
    report = {
        "schema_version": 1,
        "purpose": "candidate_handoff_readiness_only",
        "clinical_metrics_ready": False,
        "candidate_corpus_valid": False,
        "input_sha256": hashes,
        "blockers": issues,
        "metrics": None,
        "evaluation_exporter_available": (ROOT / "scripts/export_person3_evaluation.py").is_file(),
        "agent_replay_hook_available": (ROOT / "eval/person3_agent.py").is_file(),
    }
    if len(hashes) != len(names):
        return report
    try:
        manifest = json.loads((benchmark / names[0]).read_text(encoding="utf-8"))
        claims, gold, a, b = [read_jsonl(benchmark / name) for name in names[1:]]
        timestamp(manifest["corpus_cutoff"])
        ids = {row["claim_id"] for row in claims}
        if not claims or len(ids) != len(claims):
            issues.append("Proposed claim IDs must be nonempty and unique")
        counts = Counter(row["split"] for row in claims)
        families = {
            split: {row["family_id"] for row in claims if row["split"] == split} for split in ("development", "heldout")
        }
        if set(counts) - set(families):
            issues.append("Unknown split in proposed claims")
        if families["development"] & families["heldout"]:
            issues.append("Claim families overlap between development and heldout")
        for split in families:
            if counts[split] != manifest[f"{split}_count"] or families[split] != set(manifest[f"{split}_families"]):
                issues.append(f"{split} count/families disagree with manifest")
        docs = {
            split: {doc for row in claims if row["split"] == split for doc in row["source_doc_ids"]}
            for split in families
        }
        if docs["development"] & docs["heldout"]:
            issues.append("Source documents overlap between development and heldout")
        completed = {}
        for slot, rows in (("reviewer_a", a), ("reviewer_b", b)):
            if len(rows) != len(ids) or {row["claim_id"] for row in rows} != ids:
                issues.append(f"{slot} must contain exactly one row per proposed claim")
            completed[slot] = sum(row.get("record_status") == "completed_independent_expert_review" for row in rows)
            if completed[slot] != len(claims):
                issues.append(f"{slot}: independent expert review incomplete")
        if not gold:
            issues.append("Clinical gold is empty; no reference labels for scoring")
        elif len(gold) != len(ids) or {row["claim_id"] for row in gold} != ids:
            issues.append("Gold must contain exactly one adjudicated row per claim")
        if manifest.get("status") == "draft_not_frozen_not_gold":
            issues.append("Proposed split/corpus/gold have not been frozen and accepted")
        report.update(
            {
                "manifest_status": manifest.get("status"),
                "claims": len(claims),
                "split_counts": dict(counts),
                "gold_rows": len(gold),
                "completed_reviews": completed,
            }
        )
        if not bundle.is_file():
            issues.append("Source bundle is missing; provide mvp-candidates-50-2026-10-02.zip")
        elif digest(bundle.read_bytes()) != manifest["corpus_sha256"]:
            issues.append("Source bundle SHA-256 disagrees with candidate manifest")
        else:
            from src.services.evidence.annotation_review import compare_reviews
            from src.services.evidence.corpus import load_candidate_corpus

            corpus = load_candidate_corpus(bundle)
            for row in claims:
                if set(row["source_doc_ids"]) - set(corpus.families.get(row["family_id"], [])):
                    issues.append(f"{row['claim_id']}: source document outside claim family")
            report["candidate_corpus_valid"] = not any("outside claim family" in issue for issue in issues)
            report["corpus_audit"] = corpus.audit()
            report["annotation_review"] = compare_reviews(claims, a, b, corpus)
    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as error:
        issues.append(f"Invalid handoff: {error}")
        report["candidate_corpus_valid"] = False
    issues.append(
        "Candidate schema is not P26: export the shared retrieval index and explicitly adjudicated labels before scoring"
    )
    issues.append("Model response recordings are required for RAG/agent scoring; code availability alone is insufficient")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmark")
    parser.add_argument("--bundle", type=Path, default=ROOT / "data/mvp-candidates-50-2026-10-02.zip")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect_handoff(args.benchmark, args.bundle)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 2 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
