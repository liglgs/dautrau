"""Run the production Person 2/3 graph on the shared BM25 index, before human review.

Replay requires exact model request recordings; missing/stale responses are errors.
This module never obtains settings, credentials, gold labels or human approvals.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.baselines.keyword import BM25
from eval.contracts import Prediction
from eval.corpus import IntegrityError, digest, read_jsonl
from eval.person3_dataset import covering_units
from eval.replay import ReplayAdapter
from src.agents.graph import run_investigation
from src.models.schemas import BudgetState, ClaimInput, ScopeOutcome
from src.services.evidence.analysis import effective_public_stance
from src.services.evidence.integration import configure_person3
from src.services.llm import LLMGateway, LLMResponse
from src.services.runner import RunContext
from src.services.store import MvpStore

ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json"


def provider_request(model, kwargs):
    return {"model": model, **kwargs}


def provider_hash(payload):
    return digest(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


class RecordingProvider:
    name = "person3-recording"

    def __init__(self, provider, model, output: Path, *, resume=False):
        self.provider, self.model, self.output = provider, model, output
        self.seen = set()
        self.responses = {}
        self.actual_calls = 0
        self.output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            if not resume:
                raise FileExistsError("Preserve model recordings; choose a new recording path")
            # Exact request hashes cover prompts/schema/context/model. A partially
            # completed claim can replay saved calls before requesting missing ones.
            self.responses = RecordedProvider(output, model).records
            self.seen = set(self.responses)

    def complete(self, **kwargs):
        payload = provider_request(self.model, kwargs)
        key = provider_hash(payload)
        if key in self.responses:
            return self.responses[key].model_copy(deep=True)
        response = self.provider.complete(**kwargs)
        self.actual_calls += 1
        if key not in self.seen:
            record = {"kind": "person3_provider_v1", "model": self.model, "request_sha256": key,
                      "request": payload, "response": response.model_dump()}
            with self.output.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.seen.add(key)
            self.responses[key] = response
        return response


class RecordedProvider:
    name = "person3-replay"

    def __init__(self, path, model):
        self.model, self.records = model, {}
        for row in read_jsonl(Path(path)):
            key = row["request_sha256"]
            if (row.get("kind") != "person3_provider_v1" or row["model"] != model or
                    row["request"].get("model") != model or provider_hash(row["request"]) != key or
                    key in self.records):
                raise IntegrityError("Model recording identity/hash/model mismatch")
            self.records[key] = LLMResponse.model_validate(row["response"])

    def complete(self, **kwargs):
        key = provider_hash(provider_request(self.model, kwargs))
        if key not in self.records:
            raise IntegrityError(f"Missing agent response recording {key}; live fallback disabled")
        return self.records[key].model_copy(deep=True)


class MeteredReplayAdapter(ReplayAdapter):
    """Local snapshot reads spend search steps but zero HTTP requests."""

    def __init__(self, *args, retrieval_order=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ranked_ids = []
        self.retrieval_order = retrieval_order if retrieval_order is not None else []

    def search_with_budget(self, action, budget, charge_request):
        result = self.search(action, budget)
        visited = {doc.doc_id for doc in result.documents}
        hits = self.index.search(action.query or "", k=len(self.index.corpus.units) or 1,
                                 cutoff=self.cutoff, source=self.name)
        # Full snapshots are examined by the extractor. Account for all exposed
        # units, including units whose query score is zero, rather than hiding them.
        ordered = [hit.unit.unit_id for hit in hits if hit.unit.doc_id in visited]
        ordered += [u.unit_id for u in self.index.corpus.visible(self.cutoff)
                    if u.doc_id in visited and u.unit_id not in ordered]
        self.ranked_ids.extend(uid for uid in ordered if uid not in self.ranked_ids)
        self.retrieval_order.extend(uid for uid in ordered if uid not in self.retrieval_order)
        return result.model_copy(update={"requests_used": 0})


def run_agent(*, claim, index: BM25, manifest: Path, provider, max_documents=50, max_steps=8,
              dictionary=DICTIONARY, allow_synthetic=False):
    manifest_data = json.loads(manifest.read_bytes())
    expected = manifest_data.get("versions", {}).get("dictionary_sha256")
    if expected and digest(Path(dictionary).read_bytes()) != expected:
        raise IntegrityError("Agent dictionary changed after corpus export")
    store = MvpStore()
    gateway = LLMGateway(provider=provider)
    retrieval_order = []
    call_start = getattr(provider, "actual_calls", 0)
    adapters = {name: MeteredReplayAdapter(name, index, manifest, cutoff=claim.get("cutoff"),
                                          retrieval_order=retrieval_order)
                for name in ("pubmed", "dailymed", "faers")}
    try:
        public = {k: v for k, v in claim.items() if k in ClaimInput.model_fields}
        state, _ = store.create_investigation(ClaimInput.model_validate(public), investigation_id="INV-P3-EVAL")
        state = store.save_state(state.model_copy(update={"budget": BudgetState(
            max_documents=max_documents, max_steps=max_steps)}), expected_version=state.version)
        ctx = configure_person3(RunContext(store=store, gateway=gateway, adapters=adapters, scenario={}),
                                dictionary, allow_synthetic=allow_synthetic)
        state = run_investigation(state, ctx)
        events = store.list_events(state.investigation_id, limit=1000)
        retrieved = retrieval_order
        mapping = {e.evidence_id: covering_units(index.corpus, e.doc_id, e.locator.start, e.locator.end)
                   for e in state.active_evidence()}
        mismatches, contradictions = set(), set()
        rename = {"drug_ingredient": "drug", "event_term": "event"}
        statements = []
        for e in state.active_evidence():
            comparisons = ctx.evidence_analyzer.scope_matcher.assess_one(e, state.normalized_claim)
            for c in comparisons.comparisons:
                if c.outcome is ScopeOutcome.MISMATCH:
                    mismatches.update(f"{uid}:{rename.get(c.field, c.field)}" for uid in mapping[e.evidence_id])
            statements.append({"statement_id": e.evidence_id, "text": e.quote, "kind": "fact",
                               "evidence_ids": mapping[e.evidence_id]})
        active = [e.model_copy(update={"stance": effective_public_stance(e)}) for e in state.active_evidence()]
        for gap in ctx.evidence_analyzer.contradiction_analyzer.analyze_contradictions(active, state.normalized_claim):
            kind = "direct" if gap.description.startswith("Direct contradiction") else (
                "apparent" if gap.description.startswith("Apparent contradiction") else None)
            if not kind:
                continue
            pair = gap.description.split("[", 1)[1].split("]", 1)[0].split(", ")
            for a in mapping[pair[0]]:
                for b in mapping[pair[1]]:
                    if a != b:
                        contradictions.add(f"{kind}:{min(a, b)}|{max(a, b)}")
        status = str(state.assessment_status) if state.assessment_status else "requires_human_review"
        prediction = Prediction(
            retrieved, assessment_status=status,
            abstained=status not in {"supported_for_scope", "contradicted_for_scope"},
            scope_mismatches=sorted(mismatches), contradictions=sorted(contradictions), statements=statements,
            usage={"steps": state.budget.steps_used, "documents": state.budget.documents_used,
                   "llm_calls": gateway.ledger.llm_calls, "input_tokens": gateway.ledger.input_tokens,
                   "output_tokens": gateway.ledger.output_tokens, "unknown_usage_calls": gateway.ledger.unknown_usage_calls,
                   "live_calls": (getattr(provider, "actual_calls", 0) - call_start),
                   "cost_usd": None, "cost_status": "unknown", "checkpoint": str(state.checkpoint),
                   "protocol": "pre-human-review; BM25 document replay; full snapshot units counted",
                   "human_approvals": 0},
            trace=[{"kind": e["kind"], "message": e["message"], "payload": e["payload"]} for e in events],
        )
        return Prediction.parse(prediction.to_dict(), allowed_ids={u.unit_id for u in index.corpus.visible(claim.get("cutoff"))})
    finally:
        store.close()


def predict(*, claim, index, config):
    """Person 4 --agent-hook eval.person3_agent:predict entry point."""
    if config.get("mode") != "replay" or not config.get("recordings"):
        raise IntegrityError("Agent replay needs model recordings and replay mode")
    # RAG records and provider records have different schemas; keep them separate.
    rag = Path(config["recordings"])
    manifest = rag.parent / "corpus_manifest.json"
    provider = RecordedProvider(rag.with_suffix(".agent.jsonl"), config["model"])
    return run_agent(claim=claim, index=index, manifest=manifest, provider=provider,
                     max_documents=config["max_documents"], max_steps=config["max_steps"])
