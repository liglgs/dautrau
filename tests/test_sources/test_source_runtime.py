import hashlib

import pytest

from src.models.schemas import ClaimInput, PlannerActionKind, PlannerDecision, SourceStatus
from src.services.runner import InProcessRunner
from src.services.store import MvpStore


def test_configured_live_runtime_builds_connectors(monkeypatch, tmp_path):
    from src.config import get_settings

    monkeypatch.setenv("MVP_SOURCE_MODE", "live")
    monkeypatch.setenv("MVP_SNAPSHOT_ROOT", str(tmp_path))
    get_settings.cache_clear()
    try:
        context = InProcessRunner(MvpStore()).context()
        assert callable(context.source_factory)
    finally:
        get_settings.cache_clear()


def test_graph_persists_each_http_request_before_fetch(tmp_path):
    import httpx

    from src.agents.graph import retrieve_node
    from src.agents.state import MvpGraphState
    from src.models.schemas import NormalizedClaim
    from src.services.sources import build_adapters
    from src.services.sources.transport import SourceTransport

    store = MvpStore(tmp_path / "mvp.sqlite3")
    state, _ = store.create_investigation(ClaimInput(claim_text="x", drug="ibuprofen", event="bleeding"))
    state = store.save_state(
        state.model_copy(
            update={
                "normalized_claim": NormalizedClaim(claim_text="x", drug_ingredient="ibuprofen", event_term="bleeding")
            }
        )
    )
    counts = []

    def handler(request):
        counts.append(store.get_state(state.investigation_id).budget.source_requests)
        return httpx.Response(503)

    ctx = InProcessRunner(store).context()
    ctx.adapters = build_adapters(
        transport=SourceTransport(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0),
        snapshot_root=tmp_path,
        drug="ibuprofen",
        event="bleeding",
    )
    decision = PlannerDecision(
        action=PlannerActionKind.SEARCH_SOURCE, source="pubmed", query="ibuprofen bleeding", reason="test"
    )
    result = retrieve_node(MvpGraphState(investigation=state, ctx=ctx, decision=decision, scenario={}))
    assert counts == [1, 2]
    assert result["investigation"].budget.source_requests == 2


@pytest.mark.parametrize("cache_hit", [False, True])
def test_graph_exhausted_http_budget_allows_cache_but_blocks_network(tmp_path, cache_hit):
    import httpx

    from src.agents.graph import retrieve_node
    from src.agents.state import MvpGraphState
    from src.models.schemas import BudgetState
    from src.services.sources import build_adapters
    from src.services.sources.transport import SourceTransport

    calls = []
    raw = b"<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>One</ArticleTitle></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["1"]}})
        return httpx.Response(200, content=raw, headers={"content-type": "application/xml"})

    adapter = build_adapters(
        transport=SourceTransport(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0),
        snapshot_root=tmp_path,
    )["pubmed"]
    action = PlannerDecision(action=PlannerActionKind.SEARCH_SOURCE, source="pubmed", query="one", reason="test")
    if cache_hit:
        assert adapter.search(action, BudgetState()).status == SourceStatus.OK
        assert len(calls) == 2
        calls.clear()
    store = MvpStore(tmp_path / "mvp.sqlite3")
    state, _ = store.create_investigation(ClaimInput(claim_text="x", drug="a", event="b"))
    state = store.save_state(state.model_copy(update={
        "budget": state.budget.model_copy(update={"max_source_requests": 2, "source_requests": 2}),
    }))
    ctx = InProcessRunner(store).context()
    ctx.adapters = {"pubmed": adapter}
    result = retrieve_node(MvpGraphState(investigation=state, ctx=ctx, decision=action, scenario={}))
    saved = store.get_state(state.investigation_id)
    assert calls == []
    assert saved.budget.source_requests == 2
    assert saved.budget.steps_used == 1
    assert len(result["investigation"].documents) == int(cache_hit)
    if not cache_hit:
        assert any("budget_exhausted" in gap.description for gap in saved.gaps)


def test_snapshot_tampering_is_rejected(tmp_path):
    import httpx

    from src.models.schemas import BudgetState
    from src.services.sources import build_adapters
    from src.services.sources.transport import SourceTransport

    raw = b"<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article><ArticleTitle>One</ArticleTitle></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"

    def handler(request):
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["1"]}})
        return httpx.Response(200, content=raw, headers={"content-type": "application/xml"})

    transport = SourceTransport(client=httpx.Client(transport=httpx.MockTransport(handler)), interval=0)
    options = dict(transport=transport, snapshot_root=tmp_path)
    adapter = build_adapters(**options)["pubmed"]
    decision = PlannerDecision(action=PlannerActionKind.SEARCH_SOURCE, source="pubmed", query="one", reason="test")
    adapter.search(decision, BudgetState())
    (tmp_path / "pubmed" / (hashlib.sha256(raw).hexdigest() + ".raw")).write_bytes(b"tampered")
    result = build_adapters(**options)["pubmed"].search(decision, BudgetState())
    assert result.status == SourceStatus.ERROR
    assert "corrupt snapshot" in result.error
    cached_result = adapter.search(decision, BudgetState())
    assert cached_result.status == SourceStatus.ERROR
