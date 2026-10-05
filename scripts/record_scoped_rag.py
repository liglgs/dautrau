"""Separate scoped RAG experiment; default preview, explicit --live-model for API calls."""

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

from eval.baselines.keyword import BM25
from eval.baselines.scoped_rag import DICTIONARY, PROMPT, VERSION, POSTPROCESSOR_VERSION, RecordedScopedSynthesis, parse_response, prepare
from eval.baselines.single_shot_rag import request_hash
from eval.corpus import Corpus, IntegrityError, digest, read_jsonl


def checkpoint(path, value):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_dataset(dataset, split, allow_provisional):
    manifest = dataset / "corpus_manifest.json"
    data = json.loads(manifest.read_bytes())
    if data.get("annotation_status") == "ai_provisional" and not allow_provisional:
        raise IntegrityError("AI reference requires --allow-provisional")
    if not data.get("synthetic") and data.get("annotation_status") not in {"ai_provisional", "independently_reviewed"}:
        raise IntegrityError("Sources require an explicit frozen reference protocol")
    claims_path = dataset / "claims.jsonl"
    if data.get("claims_sha256") and digest(claims_path.read_bytes()) != data["claims_sha256"]:
        raise IntegrityError("Claims changed after corpus export")
    claims = [c for c in read_jsonl(claims_path) if c["split"] == split]
    return manifest, data, claims_path, claims, BM25(Corpus.load(manifest))


def summarize_prediction(prediction):
    trace = prediction.trace[0]
    return {"assessment_status": prediction.assessment_status,
            "accepted_findings": len(trace["checks"]),
            "excluded_findings": len(trace["excluded_findings"]),
            "excluded_finding_details": trace["excluded_findings"],
            "null_scope_fields": trace["null_scope_fields"],
            "whitespace_restorations": trace["whitespace_restorations"],
            "scope_normalizations": trace["scope_normalizations"],
            "study_type_normalizations": trace["study_type_normalizations"],
            "needs_quote_review": bool(trace["excluded_findings"])}


def reparse(dataset, recordings, split, *, dictionary_path=DICTIONARY,
            allow_provisional=False, claim_id=None):
    """Offline diagnostic with original requests; never pretends a new prompt ran."""
    manifest, data, claims_path, claims, index = load_dataset(dataset, split, allow_provisional)
    chosen = [c for c in claims if claim_id is None or c["claim_id"] == claim_id]
    if not chosen:
        raise IntegrityError("Requested claim is not in this split")
    recordings = Path(recordings)
    before = digest(recordings.read_bytes())
    originals = read_jsonl(recordings)
    rows = []
    from src.services.evidence.normalize import load_dictionary
    dictionary = load_dictionary(Path(dictionary_path))
    for claim in chosen:
        row = {"claim_id": claim["claim_id"], "error": None, "recording": "offline_reparsed"}
        try:
            candidates = []
            skipped_contexts = []
            for original in originals:
                request = original["request"]
                if (original.get("kind") not in {"scoped-rag-v1", "scoped-rag-v2", VERSION} or
                        request_hash(request) != original.get("request_sha256") or
                        request.get("model") != original.get("model")):
                    raise IntegrityError("Original recording protocol/model/hash mismatch")
                current = prepare(index, claim, original["model"], dictionary_path=dictionary_path)
                if request["claim"] != current["claim"]:
                    continue
                # Compare the full supplied context, aliases and normalization to
                # this frozen corpus. Prompt/schema/code legitimately differ;
                # they remain retained in the original request and hash.
                fields = ("evidence", "alias_to_unit_id", "normalization", "retrieval_queries", "rendered_untrusted")
                changed = [f for f in fields if json.dumps(request[f], sort_keys=True) != json.dumps(current[f], sort_keys=True)]
                if request["protocol"]["dictionary_sha256"] != current["protocol"]["dictionary_sha256"]:
                    changed.append("dictionary")
                if changed:
                    skipped_contexts.append({"request_sha256": original["request_sha256"], "changed_fields": changed})
                    continue
                candidates.append(original)
            row["skipped_incompatible_contexts"] = skipped_contexts
            if not candidates:
                if skipped_contexts:
                    raise IntegrityError("Original context/dictionary differs from current frozen corpus; no compatible recording")
                raise IntegrityError("No original recording for this claim; live fallback disabled")
            original = candidates[-1]  # Report the latest attempt, including errors.
            prediction = parse_response(original["raw_response"], original["request"], dictionary)
            row.update(summarize_prediction(prediction))
            row.update(original_request_sha256=original["request_sha256"],
                       original_inference_version=original["kind"], model=original["model"],
                       prediction=prediction.to_dict())
        except (ValueError, TypeError, KeyError) as exc:
            row.update(error={"type": type(exc).__name__, "message": str(exc)}, recording="ERROR")
        rows.append(row)
        print(f"{claim['claim_id']}: scoped-RAG={row['recording']}" +
              (f"; {row['assessment_status']}; accepted={row['accepted_findings']}; "
               f"excluded={row['excluded_findings']}" if 'assessment_status' in row else "") +
              ("; needs_quote_review" if row.get("needs_quote_review") else ""), flush=True)
    if digest(recordings.read_bytes()) != before:
        raise IntegrityError("Original recordings changed during offline diagnosis")
    report = {"version": VERSION, "postprocessor_version": POSTPROCESSOR_VERSION,
              "split": split, "mode": "offline reprocessing of original raw responses",
              "live_calls": 0, "prompt_resent": False, "new_model_run": False,
              "prediction_accuracy_measured": False, "clinical_validation_claimed": False,
              "recordings_path": str(recordings), "recordings_sha256": before,
              "corpus_manifest_sha256": digest(manifest.read_bytes()), "claims_sha256": digest(claims_path.read_bytes()),
              "reference_kind": data.get("annotation_status"), "selected_claim_id": claim_id,
              "postprocessor_sha256": digest((ROOT / "eval/baselines/scoped_rag.py").read_bytes()), "claims": rows}
    checkpoint(dataset / f"{VERSION}-{split}.reparse.report.json", report)
    return report


def record(dataset, model, split, provider=None, *, dictionary_path=DICTIONARY,
           allow_provisional=False, claim_id=None, max_documents=20):
    manifest, data, claims_path, claims, index = load_dataset(dataset, split, allow_provisional)
    chosen = [c for c in claims if claim_id is None or c["claim_id"] == claim_id]
    if not chosen:
        raise IntegrityError("Requested claim is not in this split")
    path = dataset / f"{VERSION}-{split}.responses.jsonl"
    synthesis = RecordedScopedSynthesis(path, model=model, dictionary_path=dictionary_path) if provider is not None else None
    report_path = dataset / f"{VERSION}-{split}.report.json"
    rows = []
    for raw in chosen:
        payload = prepare(index, raw, model, dictionary_path=dictionary_path, k=max_documents)
        row = {"claim_id": raw["claim_id"], "request_sha256": request_hash(payload),
               "retrieved_units": len(payload["evidence"]), "source_counts": {
                   source: sum(u["source"] == source for u in payload["evidence"])
                   for source in ("pubmed", "dailymed", "faers")}, "error": None,
               "retrieval_fallback_used": "empty_pool_fallback" in payload["protocol"]}
        if provider is None:
            row["recording"] = "preview"
        else:
            try:
                prediction = synthesis.cached(payload)
                if prediction is not None:
                    row["recording"] = "cached_reprocessed" if prediction.usage.get("reprocessed_unchanged_model_input") else "cached"
                    row["original_request_sha256"] = prediction.usage["request_sha256"]
                else:
                    if payload["normalization"]["requires_review"] or not payload["evidence"]:
                        response = {"findings": []}
                        usage = {"input_tokens": 0, "output_tokens": 0, "live_calls": 0, "llm_calls": 0,
                                 "usage_known": True, "local_checkpoint": True}
                    else:
                        reply = provider.complete(task=VERSION, system=PROMPT, prompt=payload["rendered_prompt"],
                            json_schema=payload["response_schema"], untrusted=payload["rendered_untrusted"])
                        # Retain raw text before attempting JSON/schema/quote validation.
                        response = reply.text
                        usage = {"input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens,
                                 "usage_known": reply.usage_known, "live_calls": 1, "llm_calls": 1,
                                 "returned_model": reply.model}
                    attempt = {"kind": VERSION, "model": model, "request_sha256": request_hash(payload),
                               "request": payload, "raw_response": response, "usage": usage}
                    with path.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps(attempt, ensure_ascii=False) + "\n")
                    decoded = json.loads(response) if isinstance(response, str) else response
                    prediction = parse_response(decoded, payload, synthesis.dictionary)
                    synthesis.records[request_hash(payload)].append(attempt)
                    row["recording"] = "local_checkpoint" if usage.get("local_checkpoint") else "recorded"
                row.update(summarize_prediction(prediction))
            except Exception as exc:
                row["error"] = {"type": type(exc).__name__, "message": str(exc)}
                row["recording"] = "ERROR"
        rows.append(row)
        report = {"version": VERSION, "split": split, "model": model, "clinical_validation_claimed": False,
                  "interpretation": "post-hoc technical experiment, not blind heldout validation",
                  "reference_kind": data.get("annotation_status"), "gold_sent_to_model": False,
                  "corpus_manifest_sha256": digest(manifest.read_bytes()), "claims_sha256": digest(claims_path.read_bytes()),
                  "protocol": payload["protocol"], "total_split_claims": len(claims), "processed_claims": len(rows),
                  "selected_claim_id": claim_id, "mode": "preview" if provider is None else "live-recording",
                  "original_baseline_files_modified": False, "claims": rows}
        if provider is not None:
            with (dataset / f"{VERSION}-{split}.attempts.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            checkpoint(report_path, report)
        print(f"{raw['claim_id']}: scoped-RAG={row['recording']}; units={row['retrieved_units']}" +
              (f"; {row['assessment_status']}; accepted={row['accepted_findings']}; "
               f"excluded={row['excluded_findings']}" if 'assessment_status' in row else "") +
              ("; needs_quote_review" if row.get("needs_quote_review") else ""), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", choices=["development", "heldout"], default="development")
    parser.add_argument("--allow-provisional", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live-model", action="store_true")
    mode.add_argument("--replay-recorded", type=Path, help="Recheck stored responses offline; original files stay unchanged.")
    parser.add_argument("--claim-id")
    parser.add_argument("--dictionary", type=Path, default=DICTIONARY)
    parser.add_argument("--max-documents", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.max_documents <= 20:
        parser.error("Scoped RAG accepts 1 to 20 units")
    if args.replay_recorded:
        report = reparse(args.dataset, args.replay_recorded, args.split, dictionary_path=args.dictionary,
                         allow_provisional=args.allow_provisional, claim_id=args.claim_id)
        return int(any(r["error"] for r in report["claims"]))
    provider, model = None, "preview-no-model-calls"
    if args.live_model:
        from src.config import get_settings
        from src.services.llm import TransportProvider
        model = get_settings().model_name
        if not model:
            parser.error("Configure MODEL_NAME; no calls were made")
        provider = TransportProvider()
    report = record(args.dataset, model, args.split, provider, dictionary_path=args.dictionary,
                    allow_provisional=args.allow_provisional, claim_id=args.claim_id, max_documents=args.max_documents)
    return int(any(r["error"] for r in report["claims"]))


if __name__ == "__main__":
    raise SystemExit(main())
