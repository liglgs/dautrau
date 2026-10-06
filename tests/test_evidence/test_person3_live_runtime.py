"""Configured API + Person 1 parsers + Person 3 extraction, with mocked I/O.

These authored responses exercise integration, not clinical accuracy or live access.
"""

import asyncio
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from src.api.mvp_runtime import configure_mvp, get_mvp_runner, reset_mvp
from src.config import get_settings
from src.main import app
from src.services.errors import MvpError
from src.services.evidence.contracts import read_annotation
from src.services.llm import MockProvider, TransportProvider
from src.services.sources.transport import SourceTransport

ROOT = Path(__file__).resolve().parents[2]
DICTIONARY = ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json"
INVESTIGATOR = {"X-API-Token": "live-runtime-test-investigator"}
REVIEWER = {"X-API-Token": "live-runtime-test-reviewer"}
QUOTES = {
    "pubmed": "Test abstract reports metformin and diarrhoea.",
    "dailymed": "Test label lists metformin and diarrhoea.",
    "faers": '"reactionmeddrapt":"Diarrhoea"',
}


@pytest.fixture
def live_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("MVP_EVIDENCE_MODE", "person3")
    monkeypatch.setenv("MVP_SOURCE_MODE", "live")
    monkeypatch.setenv("MVP_PUBMED_MODE", "api")
    monkeypatch.setenv("MVP_DICTIONARY_PATH", str(DICTIONARY))
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "live-runtime.db"))
    monkeypatch.setenv("MVP_SNAPSHOT_ROOT", str(tmp_path / "snapshots"))
    monkeypatch.setenv("INVESTIGATOR_TOKEN", INVESTIGATOR["X-API-Token"])
    monkeypatch.setenv("REVIEWER_TOKEN", REVIEWER["X-API-Token"])
    get_settings.cache_clear()
    reset_mvp()
    yield
    reset_mvp()
    get_settings.cache_clear()


async def checkpoint(client, base):
    for _ in range(200):
        response = await client.get(base, headers=INVESTIGATOR)
        assert response.status_code == 200, response.text
        state = response.json()
        assert state["run_status"] != "failed", state
        if state["checkpoint"]:
            return state
        await asyncio.sleep(0.01)
    raise AssertionError("Configured Person 3 API did not reach a checkpoint")


@pytest.mark.asyncio
@pytest.mark.parametrize("output", ["valid", "fabricated_quote", "invalid_schema"])
async def test_configured_sources_extraction_review_export(live_runtime, monkeypatch, output):
    store = configure_mvp()
    runner = get_mvp_runner()
    assert isinstance(runner.gateway.provider, TransportProvider)
    request_counts = []

    def handler(request):
        # The actual adapters and graph must persist the request before transport.
        state = store.get_state(store.list_investigations()[0]["investigation_id"])
        request_counts.append(state.budget.source_requests)
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json={"esearchresult": {"idlist": ["123"]}})
        if request.url.path.endswith("efetch.fcgi"):
            return httpx.Response(200, headers={"content-type": "application/xml"}, content=(
                '<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID Version="2">123</PMID>'
                '<Article><ArticleTitle>Authored integration test</ArticleTitle><Abstract><AbstractText>'
                + QUOTES["pubmed"] + '</AbstractText></Abstract></Article></MedlineCitation>'
                '</PubmedArticle></PubmedArticleSet>'
            ).encode())
        if request.url.path.endswith("spls.json"):
            assert request.url.params["drug_name"] == "metformin"
            return httpx.Response(200, json={"data": [{"setid": "test-label"}]})
        if request.url.path.endswith("test-label.xml"):
            return httpx.Response(200, headers={"content-type": "application/xml"}, content=(
                '<document xmlns="urn:hl7-org:v3"><setId root="test-label"/><versionNumber value="3"/>'
                '<title>Authored label</title><section><title>Adverse reactions</title><text>'
                + QUOTES["dailymed"] + '</text></section></document>'
            ).encode())
        assert request.url.host == "api.fda.gov"
        return httpx.Response(200, json={"results": [{
            "safetyreportid": "test-report", "safetyreportversion": "4",
            "patient": {"drug": [{"medicinalproduct": "metformin"}],
                        "reaction": [{"reactionmeddrapt": "Diarrhoea"}]},
        }]})

    def respond(prompt, system):
        if output == "invalid_schema":
            return {"unexpected": True}
        source = next(name for name in QUOTES if f'"source": "{name}"' in prompt)
        return {"findings": [{
            "quote": QUOTES[source] if output == "valid" else "Fabricated text absent from every source.",
            "drug_ingredient": "metformin hydrochloride", "event_term": "diarrhea",
            "stance": "supports" if source == "faers" else "uncertain",
            "direction": "increase" if source == "faers" else "unknown",
            "uncertainty": "low" if source == "faers" else "unknown",
        }]}

    provider = MockProvider({"extract_evidence": respond})
    runner.gateway.provider = provider
    with httpx.Client(transport=httpx.MockTransport(handler)) as source_client:
        monkeypatch.setattr("src.services.sources.SourceTransport", lambda: SourceTransport(
            client=source_client, interval=0,
        ))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/investigations", headers=INVESTIGATOR, json={
                "claim_text": "Authored integration test for metformin and diarrhoea",
                "drug": "metformin hydrochloride", "event": "diarrhea",
            })
            assert created.status_code == 202, created.text
            base = "/api/v1/investigations/" + created.json()["investigation_id"]
            state = await checkpoint(client, base)
            assert state["checkpoint"] == "assessment"
            assert state["assessment_status"] == "insufficient_evidence"
            saved = store.get_state(state["investigation_id"])
            assert saved.normalized_claim.drug_ingredient == "metformin"
            assert saved.normalized_claim.event_term == "diarrhoea"
            assert saved.budget.llm_calls == len(provider.calls) > 0, (
                request_counts, [gap.description for gap in saved.gaps]
            )
            assert request_counts == list(range(1, len(request_counts) + 1))
            assert saved.budget.source_requests == len(request_counts)
            if output == "invalid_schema":
                assert saved.stop_reason == "needs_review"
                assert "llm_format_error" in saved.assessment.rationale
                assert len(provider.calls) == 2  # first response plus one repair
                assert not saved.evidence
            else:
                assert {doc.source for doc in saved.documents} == set(QUOTES)
                assert len(saved.evidence) == 3  # repeated retrieval never duplicates evidence
                assert {doc.version for doc in saved.documents} == {2, 3, 4}
                assert all(item.evidence_id.startswith("EV-P3-") for item in saved.evidence)
                assert all(item.excluded == (output == "fabricated_quote") for item in saved.evidence)
                for item in saved.active_evidence():
                    doc = next(doc for doc in saved.documents if doc.doc_id == item.doc_id)
                    assert doc.text[item.locator.start:item.locator.end] == item.quote
                    assert read_annotation(item.notes).document_hash == doc.hash
                    assert item.scope.population is None and item.scope.dose is None
                    if item.source == "faers":
                        assert item.stance == "uncertain"
                        assert "faers_background_only" in read_annotation(item.notes).issues
            assert (await client.get(base + "/export", headers=INVESTIGATOR)).status_code == 409
            budget = state["budget"]
            for kind in ("assessment", "dossier"):
                reviewed = await client.post(base + "/reviews", headers=REVIEWER, json={
                    "decision_id": uuid4().hex, "action": "approve", "checkpoint": kind,
                    "expected_version": state["version"],
                    "reason": "Authored technical abstention test; no clinical approval.",
                })
                assert reviewed.status_code == 200, reviewed.text
                if kind == "assessment":
                    continued = await client.post(base + "/continue", headers=INVESTIGATOR,
                                                  json={"expected_version": state["version"] + 1})
                    assert continued.status_code == 202, continued.text
                    state = await checkpoint(client, base)
                    assert state["checkpoint"] == "dossier"
                    assert state["budget"] == budget
                    dossier = (await client.get(base + "/dossier", headers=INVESTIGATOR)).json()
                    assert dossier["dossier"]["dossier_id"].startswith("DOS-P3-")
                    assert dossier["validation"]["ok"], dossier
                    assert (await client.get(base + "/export", headers=INVESTIGATOR)).status_code == 409
            exported = await client.get(base + "/export", headers=INVESTIGATOR)
            assert exported.status_code == 200, exported.text
            assert "SYNTHETIC-DEMO" not in exported.text


@pytest.mark.parametrize("problem", ["fixture_sources", "missing_dictionary", "synthetic_dictionary"])
def test_invalid_live_configuration_fails_before_store(live_runtime, monkeypatch, tmp_path, problem):
    if problem == "fixture_sources":
        monkeypatch.setenv("MVP_SOURCE_MODE", "fixture")
    else:
        path = tmp_path / "missing.json" if problem == "missing_dictionary" else (
            ROOT / "data/dictionaries/person3_synthetic.json"
        )
        monkeypatch.setenv("MVP_DICTIONARY_PATH", str(path))
    get_settings.cache_clear()
    # RT-01: tổ hợp ``MVP_SOURCE_MODE=fixture`` + ``MVP_EVIDENCE_MODE=person3`` bị chặn bằng
    # ``MvpError`` (mã ``invalid_state``) chứ không còn là ``ValueError`` trần.
    with pytest.raises((MvpError, ValueError, FileNotFoundError)):
        configure_mvp()
    assert not Path(get_settings().mvp_db_path).exists()


@pytest.mark.asyncio
async def test_unmapped_brand_pauses_before_source_or_model(live_runtime):
    store = configure_mvp()
    provider = MockProvider()
    get_mvp_runner().gateway.provider = provider
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/investigations", headers=INVESTIGATOR, json={
            "claim_text": "Unmapped brand must be reviewed", "drug": "Unknown Brand", "event": "diarrhea",
        })
        assert response.status_code == 202, response.text
        state = await checkpoint(client, "/api/v1/investigations/" + response.json()["investigation_id"])
        assert state["checkpoint"] == "normalization"
        saved = store.get_state(state["investigation_id"])
        assert saved.normalized_claim.requires_review
        assert state["assessment_status"] is None  # no assessment before normalization review
        assert not saved.documents and not saved.evidence
        assert saved.budget.source_requests == saved.budget.llm_calls == 0
        assert not provider.calls
