"""Replay-only CLI. Agent is injected by its owner; missing integrations are reported."""

from __future__ import annotations

import argparse
import importlib
import json
import socket
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from eval.baselines import scoped_rag
from eval.baselines.keyword import BM25, TOKENIZER_VERSION
from eval.baselines.single_shot_rag import PROMPT, RecordedSynthesis, run
from eval.contracts import ASSESSMENTS, Prediction, detection_evidence
from eval.corpus import Corpus, IntegrityError, digest, read_jsonl
from eval.metrics import aggregate, score

PUBLIC_CLAIM_FIELDS = {"claim_text", "drug", "event", "population", "dose", "route", "time_window", "cutoff"}


@dataclass(frozen=True)
class EvaluationConfig:
    manifest: Path = Path("data/benchmark/corpus_manifest.json")
    claims: Path = Path("data/benchmark/claims.jsonl")
    annotations: Path = Path("data/benchmark/annotations.jsonl")
    recordings: Path | None = None
    system: str = "all"
    split: str = "development"
    mode: str = "replay"
    model: str = "recorded-model"
    agent_hook: str | None = None
    allow_synthetic: bool = False
    allow_provisional: bool = False
    scoped_dictionary: Path | None = None
    max_documents: int = 50
    max_steps: int = 8
    output: Path = Path("eval/results/drug-safety")

    def validate(self) -> None:
        if self.mode != "replay":
            raise ValueError("Only replay mode is supported; live fallback is disabled")
        if self.system not in {"all", "keyword", "single_shot_rag", "agent", "scoped_rag"}:
            raise ValueError("Unknown system")
        if self.split not in {"development", "heldout"}:
            raise ValueError("Invalid split")
        if not self.model.strip():
            raise ValueError("Model identifier is required")
        for name, limit in (("max_documents", 100), ("max_steps", 20)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= limit:
                raise ValueError(f"{name} must be an integer from 1 to {limit}")


@dataclass
class EvaluationReport:
    rows: list[dict[str, Any]]
    summaries: dict[str, Any]
    manifest: dict[str, Any]
    markdown: str
    output: Path

    @property
    def errors(self) -> int:
        return sum(row["error"] is not None for row in self.rows)

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 0


@contextmanager
def offline():
    def reject(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network disabled during replay evaluation")

    with (
        patch.object(socket.socket, "connect", reject),
        patch.object(socket.socket, "connect_ex", reject),
        patch.object(socket.socket, "sendto", reject),
        patch.object(socket, "create_connection", reject),
        patch.object(socket, "getaddrinfo", reject),
    ):
        yield


def _id_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise IntegrityError(f"{field} must contain nonempty string IDs")
    if len(value) != len(set(value)):
        raise IntegrityError(f"{field} contains duplicate IDs")
    return value


def validate_dataset(claims: list[dict[str, Any]], annotations: list[dict[str, Any]], corpus: Corpus) -> None:
    seen: set[str] = set()
    families: dict[str, str] = {}
    doc_splits: dict[tuple[str, str], str] = {}
    units = {unit.unit_id: unit for unit in corpus.units}
    documents = {unit.doc_id: (unit.source, unit.source_id) for unit in corpus.units}
    doc_ids = {unit.doc_id for unit in corpus.units}
    for claim in claims:
        if claim["claim_id"] in seen:
            raise IntegrityError("Duplicate claim ID")
        seen.add(claim["claim_id"])
        split = claim["split"]
        if split not in {"development", "heldout"}:
            raise IntegrityError("Invalid split")
        if families.setdefault(claim["family_id"], split) != split:
            raise IntegrityError("Claim family overlaps development and heldout")
        for doc_id in _id_list(claim.get("related_doc_ids", []), "related_doc_ids"):
            if doc_id not in doc_ids:
                raise IntegrityError("Related document does not resolve to frozen corpus")
            if doc_splits.setdefault(documents[doc_id], split) != split:
                raise IntegrityError("Related document overlaps splits")
        corpus.visible(claim.get("cutoff"))
        if not claim.get("drug", "").strip() or not claim.get("event", "").strip():
            raise IntegrityError("Claim needs drug and event")
    labels: set[str] = set()
    for label in annotations:
        if label["claim_id"] not in seen or label["claim_id"] in labels:
            raise IntegrityError("Duplicate/orphan annotation")
        labels.add(label["claim_id"])
        if label.get("assessment_status") not in ASSESSMENTS:
            raise IntegrityError("Gold assessment_status is missing or invalid")
        if type(label.get("abstained")) is not bool:
            raise IntegrityError("Gold abstained must be boolean")
        required = _id_list(label.get("required_evidence_ids"), "required_evidence_ids")
        relevant = _id_list(label.get("relevant_evidence_ids"), "relevant_evidence_ids")
        claim = next(item for item in claims if item["claim_id"] == label["claim_id"])
        visible = {unit.unit_id for unit in corpus.visible(claim.get("cutoff"))}
        if set(required) - visible or set(relevant) - visible:
            raise IntegrityError("Gold retrieval reference does not resolve to a visible evidence version")
        if set(required) - set(relevant):
            raise IntegrityError("Required evidence must be relevant")
        detection_ids: set[str] = set()
        for field in ("scope_mismatches", "contradictions"):
            try:
                detection_ids.update(detection_evidence(label.get(field, []), field, allowed_ids=visible))
            except ValueError as exc:
                raise IntegrityError(f"Invalid gold {field}: {exc}") from exc
        # Gold reveals related documents even when the optional claim hints are absent.
        # Keep this validation outside retrieval/model inputs.
        for unit_id in set(relevant) | detection_ids:
            source_identity = (units[unit_id].source, units[unit_id].source_id)
            if doc_splits.setdefault(source_identity, claim["split"]) != claim["split"]:
                raise IntegrityError("Gold evidence document overlaps splits")
    if labels != seen:
        raise IntegrityError("Every claim must have an annotation")


def agent_prediction(hook: str | None, claim: dict[str, Any], index: BM25, config: dict[str, Any]) -> Prediction:
    if not hook:
        raise RuntimeError(
            "Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction"
        )
    module, function = hook.split(":", 1)
    result = getattr(importlib.import_module(module), function)(claim=claim.copy(), index=index, config=config.copy())
    prediction = Prediction.parse(
        result.to_dict() if isinstance(result, Prediction) else result,
        allowed_ids={unit.unit_id for unit in index.corpus.visible(claim.get("cutoff"))},
    )
    if (
        len({unit.doc_id for unit in index.corpus.units if unit.unit_id in prediction.retrieved_ids})
        > config["max_documents"]
    ):
        raise ValueError("Agent exceeded common document budget")
    if prediction.usage.get("steps", 0) > config["max_steps"]:
        raise ValueError("Agent exceeded common step budget")
    return prediction


def evaluate(
    *,
    corpus: Corpus,
    claims: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
    system: str,
    split: str,
    model: str,
    recordings: Path | None = None,
    agent_hook: str | None = None,
    max_documents: int = 50,
    max_steps: int = 8,
    scoped_dictionary: Path | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= max_documents <= 100 or not 1 <= max_steps <= 20:
        raise ValueError("Budget exceeds server ceilings")
    validate_dataset(claims, annotations, corpus)
    index = BM25(corpus)
    gold = {item["claim_id"]: item for item in annotations}
    systems = ["keyword", "single_shot_rag", "agent"] if system == "all" else [system]
    rows = []
    synthesis = None
    synthesis_error: Exception | None = None
    if "single_shot_rag" in systems and recordings:
        try:
            synthesis = RecordedSynthesis(recordings, model=model)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            # Keep keyword/agent runs available and retain the failure on every RAG row.
            synthesis_error = exc
    scoped_synthesis = None
    scoped_error = None
    if "scoped_rag" in systems and recordings:
        try:
            scoped_synthesis = scoped_rag.RecordedScopedSynthesis(recordings, model=model,
                dictionary_path=scoped_dictionary or scoped_rag.DICTIONARY)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            scoped_error = exc
    for claim in claims:
        if claim["split"] != split:
            continue
        public_claim = {key: value for key, value in claim.items() if key in PUBLIC_CLAIM_FIELDS}
        for selected in systems:
            start = time.perf_counter()
            row: dict[str, Any] = {
                "claim_id": claim["claim_id"],
                "system": selected,
                "synthetic": corpus.synthetic,
                "error": None,
            }
            try:
                with offline():
                    if selected == "keyword":
                        hits = index.search(
                            f"{public_claim['drug']} {public_claim['event']}",
                            k=min(20, max_documents),
                            cutoff=public_claim.get("cutoff"),
                        )
                        prediction = Prediction(
                            [hit.unit.unit_id for hit in hits], usage={"queries": 1, "live_calls": 0, "llm_calls": 0}
                        )
                    elif selected == "single_shot_rag":
                        if synthesis_error is not None:
                            raise ValueError(f"Synthesis recording unavailable: {synthesis_error}") from synthesis_error
                        if synthesis is None:
                            raise RuntimeError("Synthesis recordings missing; no live/model fallback")
                        prediction = run(index, public_claim, synthesis, k=min(20, max_documents))
                        prediction.usage["queries"] = 1
                    elif selected == "agent":
                        prediction = agent_prediction(
                            agent_hook,
                            public_claim,
                            index,
                            {
                                "model": model,
                                "max_documents": max_documents,
                                "max_steps": max_steps,
                                "mode": "replay",
                                "recordings": str(recordings) if recordings else None,
                            },
                        )
                    elif selected == "scoped_rag":
                        if scoped_error:
                            raise ValueError(f"Scoped RAG recordings unavailable: {scoped_error}") from scoped_error
                        if scoped_synthesis is None:
                            raise RuntimeError("Scoped RAG recordings missing; no live fallback")
                        prediction = scoped_rag.run(index, public_claim, scoped_synthesis, k=min(20, max_documents))
                    else:
                        raise ValueError("Unknown system")
                row["prediction"] = prediction.to_dict()
                row["metrics"] = score(prediction, gold[claim["claim_id"]])
            except Exception as exc:
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
            row["duration_ms"] = round((time.perf_counter() - start) * 1000, 3)
            rows.append(row)
    if not rows:
        raise IntegrityError("Requested split is empty")
    return rows


def report(rows: list[dict[str, Any]], synthetic: bool, *, provisional: bool = False) -> str:
    lines = [
        "# Drug-safety replay evaluation",
        "",
        "AI provisional reference: technical agreement only. No independent specialist review; heldout was exposed to the AI annotator. Clinical accuracy is not measured."
        if provisional else "Synthetic technical verification; not clinical validation."
        if synthetic
        else "Frozen replay corpus; see manifest for annotation provenance.",
        "",
        "| Claim | System | Recall@20 | Citation precision | Error |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        metric = row.get("metrics", {})
        values = []
        for key in ("evidence_recall_at_20", "citation_precision"):
            value = metric.get(key, {}).get("value")
            values.append("N/A" if value is None else f"{value:.4f}")
        message = row["error"]["message"].replace("|", "/").replace("\n", " ") if row["error"] else ""
        lines.append(f"| {row['claim_id']} | {row['system']} | {' | '.join(values)} | {message} |")
    lines += [
        "",
        "Keyword has retrieval metrics only. Citation support needs statement-level independent review; a valid ID alone is insufficient.",
        "Missing recordings/integrations are errors, excluded from successful metric denominators and counted in run coverage.",
        "Replay makes no live source/model requests. Replayed token usage is historical; cost is unknown without verified prices.",
        "Reviewer-time reduction is unmeasured until a paired user study is supplied.",
    ]
    return "\n".join(lines) + "\n"


def run_evaluation(config: EvaluationConfig) -> EvaluationReport:
    """Run the same checked protocol for CLI callers and Python integrations."""
    config.validate()
    corpus = Corpus.load(config.manifest)
    manifest_data = json.loads(config.manifest.read_text(encoding="utf-8"))
    if corpus.synthetic and not config.allow_synthetic:
        raise IntegrityError("Synthetic data requires --allow-synthetic; do not mix with clinical evaluation")
    provisional = manifest_data.get("annotation_status") == "ai_provisional"
    if provisional:
        if not config.allow_provisional:
            raise IntegrityError("AI provisional references require --allow-provisional; they are not clinical gold")
        provenance = manifest_data.get("annotation_provenance", {})
        if (provenance.get("annotator_type") != "ai" or
                provenance.get("independent_expert_reviews") != 0 or
                provenance.get("clinical_metrics_ready") is not False or
                provenance.get("heldout_exposed_to_annotator") is not True):
            raise IntegrityError("Provisional provenance must disclose AI authorship and heldout exposure")
        if manifest_data.get("annotations_sha256") != digest(config.annotations.read_bytes()):
            raise IntegrityError("Provisional annotation hash mismatch")
        if manifest_data.get("claims_sha256") != digest(config.claims.read_bytes()):
            raise IntegrityError("Provisional claims hash mismatch")
    if not corpus.synthetic and not provisional and manifest_data.get("annotation_status") != "independently_reviewed":
        raise IntegrityError("Real corpus requires independently reviewed gold labels from Người 3")
    rows = evaluate(
        corpus=corpus,
        claims=read_jsonl(config.claims),
        annotations=read_jsonl(config.annotations),
        system=config.system,
        split=config.split,
        model=config.model,
        recordings=config.recordings,
        agent_hook=config.agent_hook,
        max_documents=config.max_documents,
        max_steps=config.max_steps,
        scoped_dictionary=config.scoped_dictionary,
    )
    if provisional:
        for row in rows:
            row["reference_kind"] = "ai_provisional"
            row["metric_interpretation"] = "agreement_with_AI_reference_not_clinical_accuracy"
    config.output.mkdir(parents=True, exist_ok=True)
    config.output.joinpath("per-claim.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    summaries = {
        system: aggregate([row for row in rows if row["system"] == system])
        for system in sorted({row["system"] for row in rows})
    }
    if provisional:
        for summary in summaries.values():
            summary["reference_kind"] = "ai_provisional"
            summary["clinical_validation_claimed"] = False
            summary["metric_interpretation"] = "agreement_with_AI_reference_not_clinical_accuracy"
    config.output.joinpath("aggregate.json").write_text(json.dumps(summaries, indent=2) + "\n", encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()
    except (OSError, subprocess.SubprocessError):
        commit = "unknown"
    code_files = sorted([*repo_root.joinpath("eval").rglob("*.py"), *repo_root.joinpath("src").rglob("*.py")])
    agent_recordings = config.recordings.with_suffix(".agent.jsonl") if config.recordings else None
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "mode": "replay",
        "synthetic": corpus.synthetic,
        "reference_kind": "ai_provisional" if provisional else "independently_reviewed" if not corpus.synthetic else "synthetic",
        "annotation_provenance": manifest_data.get("annotation_provenance"),
        "clinical_validation_claimed": False,
        "metric_interpretation": "agreement_with_AI_reference_not_clinical_accuracy" if provisional else "see_annotation_provenance",
        "corpus_sha256": corpus.manifest_hash,
        "cutoff": corpus.cutoff,
        "source_versions": corpus.versions,
        "claims_sha256": digest(config.claims.read_bytes()),
        "annotations_sha256": digest(config.annotations.read_bytes()),
        "recordings_sha256": digest(config.recordings.read_bytes())
        if config.recordings and config.recordings.is_file()
        else None,
        "agent_recordings_sha256": digest(agent_recordings.read_bytes())
        if config.agent_hook == "eval.person3_agent:predict" and agent_recordings and agent_recordings.is_file()
        else None,
        "model": config.model,
        "prompt_sha256": digest((scoped_rag.PROMPT if config.system == "scoped_rag" else PROMPT).encode()),
        "code_commit": commit,
        "code_sha256": {path.relative_to(repo_root).as_posix(): digest(path.read_bytes()) for path in code_files},
        "agent_hook": config.agent_hook,
        "split": config.split,
        "system": config.system,
        "max_documents": config.max_documents,
        "max_steps": config.max_steps,
        "top_k": min(20, config.max_documents),
        "tokenizer": TOKENIZER_VERSION,
        "bm25": {"k1": 1.2, "b": 0.75},
        "network": "disabled",
    }
    if config.system == "scoped_rag":
        manifest["scoped_rag_protocol"] = scoped_rag.protocol(config.scoped_dictionary or scoped_rag.DICTIONARY)
        manifest["experiment_interpretation"] = "post-hoc improvement; existing heldout already exposed, not blind validation"
    config.output.joinpath("manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    markdown = report(rows, corpus.synthetic, provisional=provisional)
    config.output.joinpath("report.md").write_text(markdown, encoding="utf-8")
    return EvaluationReport(rows, summaries, manifest, markdown, config.output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", choices=["all", "keyword", "single_shot_rag", "agent", "scoped_rag"], default="all")
    parser.add_argument("--scoped-dictionary", type=Path, help="Pinned dictionary for the separate scoped RAG experiment")
    parser.add_argument("--split", choices=["development", "heldout"], default="development")
    parser.add_argument("--mode", choices=["replay"], default="replay")
    parser.add_argument("--manifest", type=Path, default=Path("data/benchmark/corpus_manifest.json"))
    parser.add_argument("--claims", type=Path, default=Path("data/benchmark/claims.jsonl"))
    parser.add_argument("--annotations", type=Path, default=Path("data/benchmark/annotations.jsonl"))
    parser.add_argument("--recordings", type=Path)
    parser.add_argument("--model", default="recorded-model")
    parser.add_argument("--agent-hook")
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--allow-provisional", action="store_true", help="Allow explicitly attributed AI references for technical agreement only")
    parser.add_argument("--max-documents", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("eval/results/drug-safety"))
    args = parser.parse_args()
    try:
        result = run_evaluation(EvaluationConfig(**vars(args)))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Evaluation unavailable: {exc}\n")
    print(f"{len(result.rows)} rows, {result.errors} errors. Output: {result.output}")
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
