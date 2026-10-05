"""Run the shared graph with a frozen real-source corpus and Person 3 services."""

from pathlib import Path

from src.models.schemas import SourceSearchResult, SourceStatus
from src.services.evidence.candidate_provider import CandidateQuoteProvider
from src.services.evidence.corpus import load_candidate_corpus
from src.services.evidence.integration import configure_person3
from src.services.evidence.normalize import load_dictionary
from src.services.llm import LLMGateway, TransportProvider

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUNDLE = ROOT / "data/mvp-candidates-50-2026-10-02.zip"
DEFAULT_DICTIONARY = ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json"


class SnapshotSourceAdapter:
    """Expose frozen candidates once. Not a live search or query-relevance test."""

    def __init__(self, source, documents):
        self.name, self.used = source, False
        self.documents = [d for d in documents if d.source == source]

    def search(self, action, budget):
        documents = [] if self.used else self.documents
        self.used = True
        return SourceSearchResult(source=self.name, query=action.query or "snapshot candidates",
            fingerprint=action.fingerprint or "snapshot-candidates", documents=documents,
            status=SourceStatus.OK if documents else SourceStatus.EMPTY)


def make_corpus_runtime(family="metformin", *, bundle=DEFAULT_BUNDLE,
                        dictionary_path=DEFAULT_DICTIONARY, provider="offline"):
    corpus = load_candidate_corpus(bundle)
    documents = corpus.documents_for(family)
    dictionary = load_dictionary(dictionary_path)
    if dictionary.get("corpus_sha256") != corpus.bundle_hash:
        raise ValueError("Dictionary does not belong to this corpus; prepare it again")
    if provider not in {"offline", "transport"}:
        raise ValueError("provider must be offline or transport")
    gateway = LLMGateway(CandidateQuoteProvider(dictionary) if provider == "offline" else TransportProvider())

    def execute(state, ctx):
        from src.agents.graph import run_investigation
        from src.services.dossier import content_hash
        from src.services.evidence.dossier import build_person3_dossier

        configure_person3(ctx, dictionary_path)
        def build_dossier(current):
            dossier = build_person3_dossier(current)
            limitations = list(dossier.limitations) + [
                "Frozen candidate corpus replay; no live query execution or retrieval relevance evaluation.",
                "Different DailyMed SETIDs do not establish independent clinical studies.",
            ]
            if provider == "offline":
                limitations.append("Offline lexical quotation suggestions: no model extraction, clinical gold or semantic entailment evaluation.")
            dossier = dossier.model_copy(update={"limitations": limitations})
            return dossier.model_copy(update={"content_hash": content_hash(dossier)})
        ctx.dossier_builder = build_dossier
        ctx.adapters = {s: SnapshotSourceAdapter(s, documents) for s in ("pubmed", "dailymed", "faers")}
        ctx.scenario = {"name": family, "synthetic": False, "provider": provider, "frozen_candidates": True}
        ctx.emit(state.investigation_id, "runtime", "Frozen real-source candidates; specialist review pending", {
            "family": family, "bundle_sha256": corpus.bundle_hash, "provider": provider,
            "live_search": False, "clinical_gold": False,
        })
        normalized = ctx.normalizer.normalize_claim(state.claim)
        pair = next(p for p in corpus.collection["pairs"] if p["drug"] == family)
        if not normalized.requires_review and (normalized.drug_ingredient != family or normalized.event_term != pair["event"].casefold()):
            raise ValueError(f"This snapshot runtime is limited to {family} / {pair['event']}")
        return run_investigation(state, ctx)

    return execute, gateway
