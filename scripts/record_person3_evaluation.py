"""Explicit live MODEL recording on frozen local sources; no clinical scoring or source HTTP."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))

from eval.baselines.keyword import BM25  # noqa: E402
from eval.baselines.single_shot_rag import PROMPT, RecordedSynthesis, parse_wire_prediction, request_hash, request_payload  # noqa: E402
from eval.corpus import Corpus, IntegrityError, digest, read_jsonl  # noqa: E402
from eval.person3_agent import RecordedProvider, RecordingProvider, run_agent  # noqa: E402
from eval.run_evaluation import PUBLIC_CLAIM_FIELDS  # noqa: E402
from src.services.llm import TransportProvider  # noqa: E402


def record_rag_claim(index, claim, model, provider, target, *, max_documents=50):
    """One model synthesis; retain invalid responses, reuse only exact valid records."""
    evidence = [hit.unit.public_view() for hit in index.search(
        f"{claim['drug']} {claim['event']}", k=min(20, max_documents), cutoff=claim.get("cutoff"))]
    payload = request_payload(claim, evidence, model)
    key = request_hash(payload)
    if target.is_file():
        recorded = RecordedSynthesis(target, model=model)
        if key in recorded.records:
            recorded.synthesize(claim, evidence)
            return "cached"
    response = provider.complete(task="single_shot_rag", system=PROMPT,
        prompt=payload["rendered_prompt"], json_schema=payload["response_schema"], untrusted=payload["rendered_untrusted"])
    # Append before validation: formatting failures must remain visible, never fabricated/relabelled.
    with target.with_suffix(".rag-responses.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"request_sha256": key, "model": model, "returned_model": response.model,
            "reference_protocol": payload["reference_protocol"], "alias_to_unit_id": payload["alias_to_unit_id"],
            "text": response.text, "input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
            "usage_known": response.usage_known}, ensure_ascii=False) + "\n")
    result = parse_wire_prediction(json.loads(response.text), payload)
    if result.retrieved_ids != [e["unit_id"] for e in evidence]:
        raise IntegrityError("RAG output must preserve all retrieved IDs in order")
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"request_sha256": key, "model": model, "prediction": result.to_dict(),
            "usage": {"input_tokens": response.input_tokens, "output_tokens": response.output_tokens,
                      "usage_known": response.usage_known}}, ensure_ascii=False) + "\n")
    return "recorded"


def record_rag_only(dataset, model, split, provider, *, max_documents=50, max_steps=8, allow_provisional=False, claim_id=None):
    """Finish RAG without rerunning the agent or overwriting the original error report."""
    manifest = dataset / "corpus_manifest.json"
    data = json.loads(manifest.read_bytes())
    if data["synthetic"] or (data["annotation_status"] == "ai_provisional" and not allow_provisional):
        raise IntegrityError("Real AI reference requires --allow-provisional")
    if split == "heldout" and data["annotation_status"] not in {"independently_reviewed", "ai_provisional"}:
        raise IntegrityError("Heldout is not frozen or explicitly provisional")
    claims = [c for c in read_jsonl(dataset / "claims.jsonl") if c["split"] == split]
    previous_path = dataset / f"recording-report-{split}.json"
    previous = json.loads(previous_path.read_bytes())
    prior_rows = previous.get("claims", [])
    if (not claims or len(prior_rows) != len(claims) or
            {r['claim_id'] for r in prior_rows} != {c['claim_id'] for c in claims} or
            any(r.get("agent_error") or r.get("replay_verified") is not True for r in prior_rows)):
        raise IntegrityError("Wait for all agent claims to finish and replay successfully before --rag-only")
    if previous["model"] != model or previous["corpus_manifest_sha256"] != digest(manifest.read_bytes()):
        raise IntegrityError("Existing run uses a different model or corpus")
    agent_path = dataset / f"recordings-{split}.agent.jsonl"
    if not agent_path.is_file():
        raise IntegrityError("Existing agent response recordings are missing")
    RecordedProvider(agent_path, model)
    index = BM25(Corpus.load(manifest))
    target = dataset / f"recordings-{split}.jsonl"
    # Validate successful records before any paid calls.
    if target.is_file():
        RecordedSynthesis(target, model=model)
    rows = []
    for raw in claims:
        if claim_id is not None and raw["claim_id"] != claim_id:
            continue
        claim = {key: value for key, value in raw.items() if key in PUBLIC_CLAIM_FIELDS}
        row = {"claim_id": raw["claim_id"], "rag_error": None}
        try:
            row["rag_recording"] = record_rag_claim(index, claim, model, provider, target, max_documents=max_documents)
        except Exception as exc:
            row["rag_error"] = {"type": type(exc).__name__, "message": str(exc)}
        rows.append(row)
        report = {"model": model, "split": split, "corpus_manifest_sha256": digest(manifest.read_bytes()),
                  "selected_claim_id": claim_id, "total_split_claims": len(claims), "processed_claims": len(rows),
                  "prior_agent_report_sha256": digest(previous_path.read_bytes()),
                  "prompt_sha256": digest(PROMPT.encode()), "agent_live_calls": 0,
                  "prior_failed_RAG_usage": "See original report; v2 did not retain raw failed responses/token counts",
                  "clinical_metrics_measured": False, "reference_kind": data["annotation_status"], "claims": rows}
        (dataset / f"rag-recording-report-{split}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with (dataset / f"rag-attempts-{split}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"prompt_sha256": report["prompt_sha256"], **row}, ensure_ascii=False) + "\n")
        print(f"{raw['claim_id']}: agent=existing_verified; RAG={row.get('rag_recording', 'ERROR')}", flush=True)
    if not rows:
        raise IntegrityError("Requested claim ID is not in this split")
    return int(any(r["rag_error"] for r in rows))


def resume_report(dataset, model, split, manifest, claims, *, max_documents, max_steps):
    """Validate a stopped run before any new paid request or file mutation."""
    path = dataset / f"recording-report-{split}.json"
    if not path.is_file():
        raise IntegrityError("Resume requires the saved recording report; preserve existing files")
    report = json.loads(path.read_bytes())
    expected = {"model": model, "split": split, "corpus_manifest_sha256": digest(manifest.read_bytes()),
                "prompt_sha256": digest(PROMPT.encode()), "max_documents": max_documents, "max_steps": max_steps}
    if any(report.get(key) != value for key, value in expected.items()):
        raise IntegrityError("Resume model/corpus/prompt/budget differs from the stopped run")
    claims_hash = digest((dataset / "claims.jsonl").read_bytes())
    manifest_data = json.loads(manifest.read_bytes())
    pinned = report.get("claims_sha256") or manifest_data.get("claims_sha256")
    if pinned is None or pinned != claims_hash:
        raise IntegrityError("Resume claims hash is missing or changed")
    ids = [c["claim_id"] for c in claims]
    rows = report.get("claims", [])
    row_ids = [r["claim_id"] for r in rows]
    if len(set(ids)) != len(ids) or row_ids != ids[:len(row_ids)]:
        raise IntegrityError("Saved claims are not a unique prefix of this split")
    agent_path = dataset / f"recordings-{split}.agent.jsonl"
    if agent_path.exists():
        RecordedProvider(agent_path, model)
    elif any(r.get("replay_verified") and (r.get("agent_prediction") or {}).get("usage", {}).get("llm_calls") for r in rows):
        raise IntegrityError("Completed agent response recordings are missing")
    target = dataset / f"recordings-{split}.jsonl"
    if target.exists():
        RecordedSynthesis(target, model=model)
    return report


def write_checkpoint(path, report):
    """Replace the small progress report atomically; provider logs stay append-only."""
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def record(dataset, model, split, provider, *, max_documents=50, max_steps=8, allow_provisional=False, resume=False):
    manifest = dataset / "corpus_manifest.json"
    data = json.loads(manifest.read_bytes())
    if data["synthetic"]:
        raise IntegrityError("This recording command expects real frozen candidate sources")
    provisional = data["annotation_status"] == "ai_provisional"
    if provisional and not allow_provisional:
        raise IntegrityError("AI reference dataset requires --allow-provisional; heldout is already exposed")
    if split == "heldout" and data["annotation_status"] != "independently_reviewed" and not (provisional and allow_provisional):
        raise IntegrityError("Freeze and adjudicate the dataset before exposing heldout claims to the model")
    corpus = Corpus.load(manifest)
    index = BM25(corpus)
    claims_path = dataset / "claims.jsonl"
    if data.get("claims_sha256") and digest(claims_path.read_bytes()) != data["claims_sha256"]:
        raise IntegrityError("Claims changed after corpus export")
    claims = [c for c in read_jsonl(claims_path) if c["split"] == split]
    if not claims:
        raise IntegrityError("Requested split is empty")
    target = dataset / f"recordings-{split}.jsonl"
    agent_path = target.with_suffix(".agent.jsonl")
    report_path = dataset / f"recording-report-{split}.json"
    previous = None
    if resume:
        previous = resume_report(dataset, model, split, manifest, claims,
                                 max_documents=max_documents, max_steps=max_steps)
    elif target.exists() or agent_path.exists() or report_path.exists():
        raise FileExistsError("Existing recordings must be preserved; use --resume for an interrupted run")
    prior_rows = {r["claim_id"]: r for r in previous["claims"]} if previous else {}
    # Revalidate completed agent results with no live fallback before any paid calls.
    if previous:
        replay_provider = RecordedProvider(agent_path, model) if agent_path.exists() else None
        for raw in claims:
            saved = prior_rows.get(raw["claim_id"])
            if not saved or saved.get("agent_error") or saved.get("replay_verified") is not True:
                continue
            claim = {key: value for key, value in raw.items() if key in PUBLIC_CLAIM_FIELDS}
            replay = run_agent(claim=claim, index=index, manifest=manifest,
                               provider=replay_provider, max_documents=max_documents, max_steps=max_steps)
            stored = saved.get("agent_prediction", {})
            if any(stored.get(key) != replay.to_dict().get(key) for key in
                   ("assessment_status", "retrieved_ids", "statements")):
                raise IntegrityError("Completed agent result differs on replay; resume stopped before paid calls")
        # Keep the exact old report (including errors) for audit before updates.
        history = dataset / f"recording-history-{split}"
        history.mkdir(exist_ok=True)
        before = report_path.read_bytes()
        snapshot = history / f"{digest(before)}.json"
        if not snapshot.exists():
            snapshot.write_bytes(before)
    recorder = RecordingProvider(provider, model, agent_path, resume=resume)
    rows_by_id = dict(prior_rows)
    report_base = {
        "model": model, "split": split, "corpus_manifest_sha256": digest(manifest.read_bytes()),
        "claims_sha256": digest(claims_path.read_bytes()),
        "clinical_metrics_measured": False, "gold_sent_to_model": False,
        "reference_kind": "ai_provisional" if provisional else data["annotation_status"],
        "heldout_exposed_to_AI_annotator": provisional,
        "prompt_sha256": digest(PROMPT.encode()), "max_documents": max_documents, "max_steps": max_steps,
        "source_http_requests": 0, "resumed": resume, "total_split_claims": len(claims),
    }
    if previous:
        report_base["previous_report_sha256"] = digest(before)
    def save_progress():
        rows = [rows_by_id[c["claim_id"]] for c in claims if c["claim_id"] in rows_by_id]
        write_checkpoint(report_path, {**report_base, "processed_claims": len(rows), "claims": rows})
    save_progress()
    # Record and immediately replay each graph run, using the same code and requests.
    # Write successful RAG records as they finish; keep failed runs explicitly in the report.
    for raw in claims:
        claim = {key: value for key, value in raw.items() if key in PUBLIC_CLAIM_FIELDS}
        saved = prior_rows.get(raw["claim_id"])
        cached_agent = bool(saved and not saved.get("agent_error") and saved.get("replay_verified") is True)
        row = dict(saved) if cached_agent else {"claim_id": raw["claim_id"], "agent_error": None}
        row["rag_error"] = None
        try:
            if not cached_agent:
                prediction = run_agent(claim=claim, index=index, manifest=manifest, provider=recorder,
                                       max_documents=max_documents, max_steps=max_steps)
                replay = run_agent(claim=claim, index=index, manifest=manifest,
                                   provider=RecordedProvider(agent_path, model) if agent_path.exists() else recorder,
                                   max_documents=max_documents, max_steps=max_steps)
                if (prediction.assessment_status != replay.assessment_status or
                        prediction.retrieved_ids != replay.retrieved_ids or prediction.statements != replay.statements):
                    raise IntegrityError("Recorded agent does not reproduce the model run")
                row["agent_prediction"] = prediction.to_dict()
                row["replay_verified"] = True
            row["agent_recording"] = "cached_verified" if cached_agent else "recorded/replayed"
        except Exception as exc:
            row["agent_error"] = {"type": type(exc).__name__, "message": str(exc)}
        try:
            row["rag_recording"] = record_rag_claim(index, claim, model, provider, target, max_documents=max_documents)
        except Exception as exc:
            row["rag_error"] = {"type": type(exc).__name__, "message": str(exc)}
        rows_by_id[raw["claim_id"]] = row
        save_progress()
        print(f"{raw['claim_id']}: agent={'ERROR' if row['agent_error'] else row['agent_recording']}; "
              f"RAG={'ERROR' if row['rag_error'] else row['rag_recording']}", flush=True)
    rows = list(rows_by_id.values())
    return 1 if any(r["agent_error"] or r["rag_error"] for r in rows) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", choices=["development", "heldout"], default="development")
    parser.add_argument("--live-model", action="store_true", help="Explicitly allow paid model calls using your configured .env")
    parser.add_argument("--allow-provisional", action="store_true", help="Acknowledge AI references and previously exposed heldout")
    parser.add_argument("--rag-only", action="store_true", help="Keep completed agent run; record missing RAG responses only")
    parser.add_argument("--resume", action="store_true", help="Continue a stopped batch using exact verified request recordings")
    parser.add_argument("--claim-id", help="With --rag-only, check one claim before paying for the rest")
    parser.add_argument("--max-documents", type=int, default=50)
    parser.add_argument("--max-steps", type=int, default=8)
    args = parser.parse_args()
    if not args.live_model:
        parser.error("Use --live-model to explicitly request model calls; no calls were made")
    if not 1 <= args.max_documents <= 100 or not 1 <= args.max_steps <= 20:
        parser.error("Budget exceeds server ceilings")
    if args.claim_id and not args.rag_only:
        parser.error("--claim-id requires --rag-only")
    if args.resume and args.rag_only:
        parser.error("--resume and --rag-only are separate recording modes")
    from src.config import get_settings
    settings = get_settings()
    model = settings.model_name
    if not model:
        parser.error("Configure MODEL_NAME in your environment")
    runner = record_rag_only if args.rag_only else record
    options = {"max_documents": args.max_documents, "max_steps": args.max_steps, "allow_provisional": args.allow_provisional}
    if args.rag_only:
        options["claim_id"] = args.claim_id
    else:
        options["resume"] = args.resume
    return runner(args.dataset, model, args.split, TransportProvider(), **options)


if __name__ == "__main__":
    raise SystemExit(main())
