"""Source import, long-document offsets and frozen-source graph regressions."""

import json
import zipfile
from hashlib import sha256

import pytest

from src.models.schemas import BudgetState, ClaimInput, NormalizedClaim, SourceDocument
from src.services.evidence.citations import text_hash, validate_evidence_citation
from src.services.evidence.corpus import corpus_dictionary, load_candidate_corpus
from src.services.evidence.corpus_runtime import make_corpus_runtime
from src.services.evidence.extract import EvidenceExtractor
from src.services.llm import LLMGateway, MockProvider
from src.services.runner import InProcessRunner
from src.services.store import MvpStore


def fixture_bundle(tmp_path, change=None):
    files, reviews = {}, []
    pair = {"drug": "metformin", "event": "Diarrhoea", "sources": {}}
    for source in ("pubmed", "dailymed", "faers"):
        text = "Metformin and diarrhoea are mentioned in this source. Context is not established."
        raw = f"raw/{source}.txt"
        files[raw] = text.encode()
        d = {"doc_id": f"{source}:1:1", "source": source, "source_id": "1", "version": 1,
             "text": text, "hash": text_hash(text), "title": "Technical fixture, not clinical evidence",
             "source_url": "https://example.org/fixture", "metadata": {
                 "raw_ref": raw, "raw_hash": text_hash(text), "parsed_hash": text_hash(text),
                 "sections": [{"title": "Abstract", "start": 0, "end": len(text)}]}}
        name = f"metformin/{source}.json"
        value = {"source": source, "query": "metformin diarrhoea", "fingerprint": "fixture", "status": "ok", "documents": [d], "requests_used": 1} if source == "faers" else [d]
        files[name] = json.dumps(value).encode()
        pair["sources"][source] = {"file": name, "count": 1}
        reviews.append({"doc_id": d["doc_id"], "review_decision": "pending", "gold_label": None})
    files["collection.json"] = json.dumps({"pairs": [pair], "total_unique_documents": 3, "created_at": "2026-10-02"}).encode()
    files["review.jsonl"] = "\n".join(json.dumps(r) for r in reviews).encode()
    if change:
        change(files)
    files["files.sha256.json"] = json.dumps({n: sha256(b).hexdigest() for n, b in files.items()}).encode()
    path = tmp_path / "fixture.zip"
    with zipfile.ZipFile(path, "w") as z:
        for n, b in files.items():
            z.writestr(n, b)
    return path


def test_corpus_preserves_source_offsets_hashes_and_pending_reviews(tmp_path):
    corpus = load_candidate_corpus(fixture_bundle(tmp_path))
    assert len(corpus.documents) == 3 and corpus.audit()["gold_labels"] == 0
    dictionary = corpus_dictionary(corpus)
    for section in ("drugs", "events"):
        for row in dictionary[section]:
            doc = next(d for d in corpus.documents if d.doc_id == row["source_doc_id"])
            span = row["attestation"]
            assert doc.text[span["start"]:span["end"]] == span["quote"]
    copies = corpus.documents_for("metformin")
    copies[0].text = "changed"
    assert corpus.documents[0].text != "changed"


@pytest.mark.parametrize("fault", ["text", "raw", "section", "review", "unsafe"])
def test_corpus_rejects_corrupt_sources_even_with_recomputed_file_manifest(tmp_path, fault):
    def mutate(files):
        if fault in {"text", "section"}:
            name = "metformin/pubmed.json"
            value = json.loads(files[name])
            if fault == "text":
                value[0]["text"] += "tampered"
            else:
                value[0]["metadata"]["sections"][0]["end"] = 99999
            files[name] = json.dumps(value).encode()
        elif fault == "raw":
            files["raw/pubmed.txt"] += b"tampered"
        elif fault == "review":
            files["review.jsonl"] = b'{"doc_id":"wrong"}'
        else:
            files["../escape.txt"] = b"escape"
    with pytest.raises(ValueError):
        load_candidate_corpus(fixture_bundle(tmp_path, mutate))


def claim():
    return NormalizedClaim(claim_text="Requested association", drug_ingredient="metformin", event_term="diarrhoea")


def long_document(text):
    return SourceDocument(doc_id="LONG", source="dailymed", source_id="SPL", text=text, hash=text_hash(text),
                          source_url="https://example.org/long-fixture")


def responding_provider(quote, global_start):
    def respond(prompt, system):
        window = json.loads(prompt.split("Document identity:\n", 1)[1].split("\n\nReturn", 1)[0])
        start, end = window["window_start"], window["window_end"]
        if not start <= global_start < global_start + len(quote) <= end:
            return {"findings": []}
        return {"findings": [{"quote": quote, "locator": {"start": global_start - start, "end": global_start - start + len(quote)},
            "drug_ingredient": "metformin", "event_term": "diarrhoea", "stance": "uncertain"}]}
    return MockProvider({"extract_evidence": respond})


def test_long_document_event_after_first_12000_maps_unicode_offsets_and_cache():
    quote = "Metformin: diarrhoea in the later section."
    text = "Tiếng Việt α. " + "x" * 26000 + quote + "x" * 1000
    doc = long_document(text)
    start = text.index(quote)
    provider = responding_provider(quote, start)
    extractor = EvidenceExtractor(LLMGateway(provider))
    extractor.bind(BudgetState(), "INV-LONG")
    units = extractor.extract_evidence(doc, claim())
    assert len(units) == 1 and not units[0].excluded
    assert units[0].locator.start == start
    assert validate_evidence_citation(doc, units[0]).span_verified
    assert not extractor.coverage[doc.doc_id]["complete"]
    count = len(provider.calls)
    assert extractor.extract_evidence(doc, claim())[0].evidence_id == units[0].evidence_id
    assert len(provider.calls) == count


def test_overlapping_windows_deduplicate_the_same_original_span():
    quote = "Metformin: diarrhoea at a boundary."
    text = "x" * 8500 + quote + "x" * 10000
    extractor = EvidenceExtractor(LLMGateway(responding_provider(quote, 8500)))
    extractor.bind(BudgetState(), "INV-OVERLAP")
    units = extractor.extract_evidence(long_document(text), claim())
    assert len(units) == 1
    assert extractor.coverage["LONG"]["complete"]


def test_budget_failure_keeps_completed_windows_for_node_persistence():
    from src.services.errors import MvpError
    quote = "Metformin: diarrhoea."
    text = quote + "x" * 19000
    extractor = EvidenceExtractor(LLMGateway(responding_provider(quote, 0)))
    budget = BudgetState(max_llm_calls=3)
    extractor.bind(budget, "INV-BUDGET")
    with pytest.raises(MvpError):
        extractor.extract_evidence(long_document(text), claim())
    assert budget.llm_calls == 1
    assert len(extractor.partial_units["LONG"]) == 1
    assert extractor.coverage["LONG"]["examined_chars"] == 10000


def test_frozen_source_graph_abstains_and_builds_valid_dossier_after_review(tmp_path):
    from uuid import uuid4

    from src.models.schemas import ReviewDecision
    from src.services.dossier import export_markdown, validate_dossier
    from src.services.review import apply_review
    bundle = fixture_bundle(tmp_path)
    dictionary = tmp_path / "dictionary.json"
    dictionary.write_text(json.dumps(corpus_dictionary(load_candidate_corpus(bundle))), encoding="utf-8")
    executor, gateway = make_corpus_runtime("metformin", bundle=bundle, dictionary_path=dictionary)
    store = MvpStore(tmp_path / "graph.db")
    try:
        state, _ = store.create_investigation(ClaimInput(claim_text="Requested association", drug="metformin", event="Diarrhoea"))
        runner = InProcessRunner(store, executor=executor, gateway=gateway)
        state = runner.run(state.investigation_id)
        assert state.checkpoint == "assessment" and state.assessment_status == "insufficient_evidence"
        assert len(state.documents) == 3 and state.evidence
        assert all(item.stance == "uncertain" for item in state.evidence)
        for checkpoint in ("assessment", "dossier"):
            apply_review(store, ReviewDecision(decision_id=uuid4().hex, investigation_id=state.investigation_id,
                checkpoint=checkpoint, action="approve", expected_version=state.version,
                reviewer_id="test-reviewer", reason="Technical test of abstaining dossier, not clinical approval."))
            if checkpoint == "assessment":
                state = runner.run(state.investigation_id, resume=True)
                dossier = store.latest_dossier(state.investigation_id)
                assert validate_dossier(dossier, state).ok
        exported = export_markdown(store, state.investigation_id)
        assert "Metformin and diarrhoea are mentioned" in exported
        assert "example.org/fixture" in exported
    finally:
        store.close()
