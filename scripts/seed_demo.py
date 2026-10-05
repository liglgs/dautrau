"""Build isolated synthetic demo/replay files for Người 4. Does not seed a live database."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval.baselines.keyword import BM25  # noqa: E402
from eval.baselines.single_shot_rag import request_hash, request_payload  # noqa: E402
from eval.corpus import Corpus  # noqa: E402

MODEL = "synthetic-fixture-v1"
CUTOFF = "2026-09-30T00:00:00+00:00"
# Invented drugs/events avoid presenting authored fixtures as medical evidence.
SCENARIOS = [
    (
        "broad",
        "development",
        "TestDrugA",
        "TestEventA",
        "scope_mismatch",
        True,
        [("pubmed", "Only adults received TestDrugA. TestEventA was observed in this adult sample.")],
    ),
    (
        "apparent",
        "development",
        "TestDrugB",
        "TestEventB",
        "requires_human_review",
        True,
        [
            ("pubmed", "Adults receiving TestDrugB reported TestEventB."),
            ("pubmed", "Children receiving TestDrugB did not report TestEventB in this sample."),
        ],
    ),
    (
        "faers",
        "development",
        "TestDrugC",
        "TestEventC",
        "insufficient_evidence",
        True,
        [("faers", "A spontaneous report lists TestDrugC and TestEventC. No denominator is available.")],
    ),
    (
        "replan",
        "development",
        "TestDrugD",
        "TestEventD",
        "supported_for_scope",
        False,
        [
            ("dailymed", "The fictional label for TestDrugD lists TestEventD in adults."),
            ("pubmed", "The fictional adult study observed an association of TestDrugD with TestEventD."),
        ],
    ),
    (
        "heldout-support",
        "heldout",
        "TestDrugE",
        "TestEventE",
        "supported_for_scope",
        False,
        [("dailymed", "The fictional label for TestDrugE lists TestEventE.")],
    ),
    ("heldout-empty", "heldout", "TestDrugF", "TestEventF", "insufficient_evidence", True, []),
]


def json_file(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("snapshots").mkdir(exist_ok=True)
    root.joinpath("dossiers").mkdir(exist_ok=True)
    documents, claims, labels = [], [], []
    for name, split, drug, event, status, abstained, sources in SCENARIOS:
        required = []
        for index, (source, text) in enumerate(sources, 1):
            doc_id = f"{name}-doc-{index}"
            unit_id = f"{doc_id}-span-1"
            raw = text.encode("utf-8")
            root.joinpath("snapshots", f"{doc_id}.txt").write_bytes(raw)
            documents.append(
                {
                    "doc_id": doc_id,
                    "source": source,
                    "source_id": doc_id,
                    "version": 1,
                    "title": f"SYNTHETIC {name} {drug} {event}",
                    "available_at": CUTOFF,
                    "path": f"snapshots/{doc_id}.txt",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "units": [{"unit_id": unit_id, "start": 0, "end": len(text), "text": text}],
                }
            )
            required.append(unit_id)
        claims.append(
            {
                "claim_id": name,
                "family_id": name,
                "split": split,
                "claim_text": f"Investigate {drug} and {event}.",
                "drug": drug,
                "event": event,
                "cutoff": CUTOFF,
                "related_doc_ids": [row["doc_id"] for row in documents if row["doc_id"].startswith(name + "-doc-")],
            }
        )
        labels.append(
            {
                "claim_id": name,
                "required_evidence_ids": required,
                "relevant_evidence_ids": required,
                "assessment_status": status,
                "abstained": abstained,
                "scope_mismatches": [required[0] + ":population"] if name == "broad" else [],
                "contradictions": ["apparent:" + "|".join(required)] if name == "apparent" else [],
                "statement_reviews": [],
            }
        )
        markdown = [
            f"# Synthetic demo: {name}",
            "",
            "Authored technical fixture; no clinical validation; not approved for publication.",
            "",
            f"Claim: {drug} / {event}",
            f"Assessment fixture: `{status}`",
            f"Abstain fixture: `{abstained}`",
            "",
            "## Evidence (invented)",
        ]
        markdown += [f"- [{unit_id}] {text}" for unit_id, (_, text) in zip(required, sources, strict=True)]
        markdown += [
            "",
            "## Gaps and limits",
            "No expert annotation, real sources, causal inference, incidence estimate or reviewer-time measurement.",
            "",
            "## Audit / review",
            "Fixture authored by seed_demo.py. Approval: pending. Backend replanning must be verified separately.",
        ]
        root.joinpath("dossiers", f"{name}.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    json_file(
        root / "corpus_manifest.json",
        {
            "schema_version": 1,
            "mode": "replay",
            "synthetic": True,
            "annotation_status": "authored_technical_fixture",
            "cutoff": CUTOFF,
            "versions": {"dictionary": "fixture-v1", "parser": "whole-text-v1", "policy": "no-clinical-claims-v1"},
            "documents": documents,
        },
    )
    corpus = Corpus.load(root / "corpus_manifest.json")
    index = BM25(corpus)
    recordings = []
    for claim, label in zip(claims, labels, strict=True):
        public = {key: value for key, value in claim.items() if key in {"drug", "event", "claim_text", "cutoff"}}
        context = [hit.unit.public_view() for hit in index.search(f"{claim['drug']} {claim['event']}")]
        statements = []
        if label["required_evidence_ids"]:
            statement = {
                "statement_id": "fixture-statement-1",
                "kind": "fact",
                "text": "This synthetic fixture contains the quoted text.",
                "evidence_ids": [label["required_evidence_ids"][0]],
            }
            statements.append(statement)
            label["statement_reviews"] = [
                {
                    **statement,
                    "supporting_evidence_ids": statement["evidence_ids"],
                    "reviewer": "fixture-author (not independent)",
                }
            ]
        prediction = {
            "retrieved_ids": [row["unit_id"] for row in context],
            "assessment_status": label["assessment_status"],
            "abstained": label["abstained"],
            "scope_mismatches": label["scope_mismatches"],
            "contradictions": label["contradictions"],
            "statements": statements,
        }
        recordings.append(
            {
                "request_sha256": request_hash(request_payload(public, context, MODEL)),
                "model": MODEL,
                "origin": "authored synthetic output; not a model experiment",
                "prediction": prediction,
                "usage": {"input_tokens": None, "output_tokens": None},
            }
        )
    for filename, rows in [("claims.jsonl", claims), ("annotations.jsonl", labels), ("recordings.jsonl", recordings)]:
        root.joinpath(filename).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
    print(f"Wrote six synthetic scenarios to {root}; no database changes or network calls.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/demo/person4"))
    build(parser.parse_args().output)
