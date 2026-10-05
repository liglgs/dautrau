import hashlib
import importlib
import json
from pathlib import Path

import pytest

from src.models.schemas import BudgetState, PlannerActionKind, PlannerDecision, SourceStatus
from src.services.sources import build_adapters
from src.services.sources.transport import SourceError

EXPORT = """PMID- 101
TI  - Metformin diarrhea in adults
AB  - Diarrhea occurred during metformin treatment.
      Follow-up: dữ liệu thật, không tự gán nhãn.
DP  - 2022 Jan
PT  - Randomized Controlled Trial
AID - 10.1000/example [doi]

PMID- 102
TI  - Lisinopril cough
DP  - 2023

PMID- 103
TI  - Metformin diabetes
AB  - Diarrhea was recorded in adults receiving metformin.
"""


def local_module():
    return importlib.import_module("src.services.sources.pubmed_local")


def corpus(tmp_path, text=EXPORT):
    export = tmp_path / "export.txt"
    export.write_text(text, encoding="utf-8")
    root = tmp_path / "corpus"
    docs = local_module().import_pubmed_file(export, root, query="metformin diarrhea")
    return root, docs, export


def search(tmp_path, root, query, limit=5):
    adapter = build_adapters(
        snapshot_root=tmp_path / "snapshots", pubmed_mode="local", pubmed_corpus_root=root, max_documents=limit
    )["pubmed"]
    action = PlannerDecision(action=PlannerActionKind.SEARCH_SOURCE, source="pubmed", query=query, reason="test")
    return adapter.search(action, BudgetState(max_source_requests=1, source_requests=1))


def test_import_preserves_unicode_raw_provenance_and_quote_offsets(tmp_path):
    root, docs, export = corpus(tmp_path)
    assert [d.source_id for d in docs] == ["101", "102", "103"]
    d = docs[0]
    assert "dữ liệu thật, không tự gán nhãn." in d.text
    assert d.metadata["publication_types"] == ["Randomized Controlled Trial"]
    assert d.metadata["doi"] == ["10.1000/example"]
    assert d.metadata["source_record_version"] is None
    assert d.metadata["import_query"] == "metformin diarrhea"
    raw = (root / d.metadata["raw_ref"]).read_bytes()
    assert raw == export.read_bytes()
    assert d.metadata["raw_hash"] == hashlib.sha256(raw).hexdigest()
    loc = d.metadata["sections"][0]
    assert d.text[loc["start"] : loc["end"]] == (
        "Abstract\nDiarrhea occurred during metformin treatment. Follow-up: dữ liệu thật, không tự gán nhãn."
    )


def test_missing_abstract_is_metadata_only_not_fabricated(tmp_path):
    _, docs, _ = corpus(tmp_path)
    assert docs[1].text == "Lisinopril cough"
    assert docs[1].metadata["content_level"] == "metadata_only"
    assert "missing_abstract" in docs[1].metadata["warnings"]


@pytest.mark.parametrize("text", ["not a PubMed export", "PMID- bad\nTI  - title", "PMID- 1\nAB  - body"])
def test_invalid_export_does_not_create_corpus(tmp_path, text):
    source = tmp_path / "invalid.txt"
    source.write_text(text, encoding="utf-8")
    with pytest.raises(SourceError, match="parse_error"):
        local_module().import_pubmed_file(source, tmp_path / "corpus", query="x")
    assert not (tmp_path / "corpus" / "manifest.json").exists()


def test_duplicate_pmids_in_one_export_are_rejected_before_write(tmp_path):
    source = tmp_path / "duplicate.txt"
    source.write_text("PMID- 101\nTI  - Same title\n\nPMID- 101\nTI  - Same title", encoding="utf-8")
    with pytest.raises(SourceError, match="duplicate PMID"):
        local_module().import_pubmed_file(source, tmp_path / "corpus", query="x")
    assert not (tmp_path / "corpus").exists()


def test_reimport_deduplicates_and_conflict_preserves_existing_corpus(tmp_path):
    root, _, export = corpus(tmp_path)
    local_module().import_pubmed_file(export, root, query="another query")
    before = (root / "manifest.json").read_bytes()
    assert len(json.loads(before)["documents"]) == 3
    export.write_text("PMID- 101\nTI  - Changed title\nAB  - Different result", encoding="utf-8")
    with pytest.raises(SourceError, match="conflicting PMID"):
        local_module().import_pubmed_file(export, root, query="x")
    assert (root / "manifest.json").read_bytes() == before


@pytest.mark.parametrize("field", ["AU  - Added author", "JT  - Changed journal"])
def test_reimport_rejects_bibliographic_changes_without_overwriting(tmp_path, field):
    root, _, export = corpus(tmp_path)
    before = (root / "manifest.json").read_bytes()
    export.write_text(EXPORT.replace("PMID- 101", f"PMID- 101\n{field}"), encoding="utf-8")
    with pytest.raises(SourceError, match="conflicting PMID"):
        local_module().import_pubmed_file(export, root, query="x")
    assert (root / "manifest.json").read_bytes() == before


def test_local_search_ranks_query_not_claim_and_never_uses_http(tmp_path):
    root, _, _ = corpus(tmp_path)
    result = search(tmp_path, root, "metformin diarrhoea", limit=1)
    assert result.status == SourceStatus.OK
    assert [d.source_id for d in result.documents] == ["101"]
    assert result.requests_used == 0
    d = result.documents[0]
    assert d.metadata["retrieval_method"] == "local_lexical"
    assert "local_corpus_not_live_pubmed" in d.metadata["warnings"]
    assert hashlib.sha256(Path(d.metadata["raw_ref"]).read_bytes()).hexdigest() == d.metadata["raw_hash"]
    other = search(tmp_path, root, "lisinopril cough")
    assert [d.source_id for d in other.documents] == ["102"]


def test_unrelated_query_is_empty_and_missing_corpus_is_error(tmp_path):
    root, _, _ = corpus(tmp_path)
    assert search(tmp_path, root, "amoxicillin rash").status == SourceStatus.EMPTY
    missing = search(tmp_path, tmp_path / "missing", "metformin")
    assert missing.status == SourceStatus.ERROR
    assert missing.requests_used == 0


@pytest.mark.parametrize("query", ["!!!", "metformin[Title] AND diarrhea", "metformin OR lisinopril"])
def test_local_search_rejects_empty_or_unsupported_pubmed_syntax(tmp_path, query):
    root, _, _ = corpus(tmp_path)
    result = search(tmp_path, root, query)
    assert result.status == SourceStatus.ERROR
    assert "invalid_query" in result.error


@pytest.mark.parametrize("mutation", ["raw", "text", "rehashed_text", "path", "doi", "title", "locator"])
def test_local_search_rejects_tampered_corpus(tmp_path, mutation):
    root, docs, _ = corpus(tmp_path)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if mutation == "raw":
        (root / docs[0].metadata["raw_ref"]).write_bytes(b"tampered")
    elif mutation in {"text", "rehashed_text"}:
        manifest["documents"][0]["text"] = "fabricated quote"
        if mutation == "rehashed_text":
            digest = hashlib.sha256(b"fabricated quote").hexdigest()
            manifest["documents"][0]["hash"] = digest
            manifest["documents"][0]["metadata"]["parsed_hash"] = digest
            manifest["documents"][0]["metadata"]["sections"] = []
    elif mutation == "path":
        manifest["documents"][0]["metadata"]["raw_ref"] = "../export.txt"
    elif mutation == "doi":
        manifest["documents"][0]["metadata"]["doi"] = ["fabricated-doi"]
    elif mutation == "title":
        manifest["documents"][0]["title"] = "fabricated title"
    else:
        manifest["documents"][0]["metadata"]["sections"][0]["start"] += 1
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert search(tmp_path, root, "metformin diarrhea").status == SourceStatus.ERROR


def test_cached_adapter_rechecks_original_corpus_after_tampering(tmp_path):
    root, docs, _ = corpus(tmp_path)
    adapter = build_adapters(snapshot_root=tmp_path / "snapshots", pubmed_mode="local", pubmed_corpus_root=root)[
        "pubmed"
    ]
    action = PlannerDecision(
        action=PlannerActionKind.SEARCH_SOURCE, source="pubmed", query="metformin diarrhea", reason="test"
    )
    assert adapter.search(action, BudgetState()).status == SourceStatus.OK
    (root / docs[0].metadata["raw_ref"]).write_bytes(b"tampered")
    assert adapter.search(action, BudgetState()).status == SourceStatus.ERROR


def test_import_cli_reports_error_without_creating_a_corpus(tmp_path):
    import subprocess
    import sys

    source = tmp_path / "invalid.txt"
    source.write_bytes(b"not a PubMed export")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.import_pubmed",
            "--input",
            str(source),
            "--corpus-root",
            str(tmp_path / "corpus"),
            "--query",
            "x",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "parse_error" in result.stderr
    assert not (tmp_path / "corpus" / "manifest.json").exists()


@pytest.mark.parametrize("source_requests", [0, 1])
def test_runtime_selects_local_pubmed_explicitly_and_graph_saves_real_document(monkeypatch, tmp_path, source_requests):
    from src.agents.graph import retrieve_node
    from src.agents.state import MvpGraphState
    from src.config import get_settings
    from src.models.schemas import ClaimInput, NormalizedClaim
    from src.services.runner import InProcessRunner
    from src.services.store import MvpStore

    root, _, _ = corpus(tmp_path)
    monkeypatch.setenv("MVP_SOURCE_MODE", "live")
    monkeypatch.setenv("MVP_PUBMED_MODE", "local")
    monkeypatch.setenv("MVP_PUBMED_CORPUS_ROOT", str(root))
    monkeypatch.setenv("MVP_SNAPSHOT_ROOT", str(tmp_path / "snapshots"))
    get_settings.cache_clear()
    try:
        store = MvpStore(tmp_path / "mvp.sqlite3")
        state, _ = store.create_investigation(ClaimInput(claim_text="test", drug="metformin", event="diarrhea"))
        state = store.save_state(
            state.model_copy(
                update={
                    "normalized_claim": NormalizedClaim(
                        claim_text="test", drug_ingredient="metformin", event_term="diarrhea"
                    ),
                    "budget": state.budget.model_copy(update={"max_source_requests": 1, "source_requests": source_requests}),
                }
            )
        )
        ctx = InProcessRunner(store).context()
        action = PlannerDecision(
            action=PlannerActionKind.SEARCH_SOURCE, source="pubmed", query="metformin diarrhea", reason="test"
        )
        result = retrieve_node(MvpGraphState(investigation=state, ctx=ctx, decision=action, scenario={}))
        saved = store.get_state(state.investigation_id)
        assert [d.source_id for d in result["investigation"].documents] == ["101", "103"]
        assert saved.budget.source_requests == source_requests
        assert saved.budget.documents_used == 2
        assert saved.budget.steps_used == 1
    finally:
        get_settings.cache_clear()
