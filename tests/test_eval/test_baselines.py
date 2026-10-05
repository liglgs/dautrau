from eval.baselines.keyword import BM25, tokenize
from eval.corpus import Corpus
from eval.replay import ReplayAdapter
from scripts.seed_demo import build
from src.models.schemas import BudgetState, PlannerActionKind, PlannerDecision


def test_bm25_ranks_matching_drug_event_without_gold(tmp_path):
    build(tmp_path)
    corpus = Corpus.load(tmp_path / "corpus_manifest.json")
    hits = BM25(corpus).search("TestDrugD TestEventD")
    assert len(hits) == 2
    assert all(hit.unit.doc_id.startswith("replan-") for hit in hits)
    assert hits == BM25(corpus).search("TestDrugD TestEventD")


def test_empty_query_returns_no_documents(tmp_path):
    build(tmp_path)
    assert BM25(Corpus.load(tmp_path / "corpus_manifest.json")).search("unmatched") == []


def test_source_filter_and_cutoff(tmp_path):
    build(tmp_path)
    index = BM25(Corpus.load(tmp_path / "corpus_manifest.json"))
    assert len(index.search("TestDrugD", source="pubmed")) == 1
    assert index.search("TestDrugD", cutoff="2026-09-29T00:00:00Z") == []


def test_unicode_tokenization_is_stable():
    assert tokenize("TESTDRUG Ａ") == ["testdrug", "a"]


def test_agent_adapter_uses_shared_corpus_and_document_budget(tmp_path):
    build(tmp_path)
    manifest = tmp_path / "corpus_manifest.json"
    index = BM25(Corpus.load(manifest))
    adapter = ReplayAdapter("pubmed", index, manifest)
    result = adapter.search(
        PlannerDecision(
            action=PlannerActionKind.SEARCH_SOURCE,
            source="pubmed",
            query="TestDrugB TestEventB",
            reason="technical replay",
        ),
        BudgetState(max_documents=1),
    )
    assert len(result.documents) == 1
    assert result.documents[0].metadata["mode"] == "replay"
    assert result.documents[0].hash == next(
        hit.unit.document_hash for hit in index.search("TestDrugB") if hit.unit.doc_id == result.documents[0].doc_id
    )
