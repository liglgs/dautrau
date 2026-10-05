"""Exercise Person 3 through the real graph, configured API runner and review/export."""

import asyncio
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.mvp_runtime import configure_mvp, get_mvp_runner, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app
from src.models.schemas import ClaimInput
from src.services.evidence.contracts import read_annotation
from src.services.evidence.demo import SCENARIOS, graph_inputs, make_demo_runtime
from src.services.runner import InProcessRunner
from src.services.store import MvpStore

INVESTIGATOR = {"X-API-Token": "person3-test-investigator"}
REVIEWER = {"X-API-Token": "person3-test-reviewer"}


@pytest.fixture
def configured_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTIGATOR_TOKEN", INVESTIGATOR["X-API-Token"])
    monkeypatch.setenv("REVIEWER_TOKEN", REVIEWER["X-API-Token"])
    monkeypatch.setenv("MVP_EVIDENCE_MODE", "person3_demo")
    monkeypatch.setenv("MVP_PERSON3_DEMO_SCENARIO", "match")
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "person3-api.db"))
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    get_settings.cache_clear()
    reset_mvp()
    yield
    reset_mvp()
    get_settings.cache_clear()


@pytest.mark.parametrize("name", SCENARIOS)
def test_full_graph_scenarios(name, tmp_path):
    store = MvpStore(tmp_path / f"{name}.db")
    try:
        state, _ = store.create_investigation(ClaimInput(**graph_inputs(name)[0]))
        executor, gateway = make_demo_runtime(name)
        result = InProcessRunner(store, executor=executor, gateway=gateway).run(state.investigation_id)
        assert result.run_status == "waiting_for_review"
        assert result.budget.steps_used <= result.budget.max_steps
        if name == "ambiguous_brand":
            assert result.checkpoint == "normalization"
            assert not result.documents and not result.evidence and not gateway.provider.calls
        else:
            assert result.checkpoint == "assessment"
            assert result.assessment_status == SCENARIOS[name][1]
            assert any(event["kind"] == "assess" and "Person 3" in event["message"]
                       for event in store.list_events(state.investigation_id))
        if name == "fake_quote":
            assert all(item.excluded for item in result.evidence)
    finally:
        store.close()


def test_api_lazy_initialization_uses_person3_runner(configured_runtime):
    store = get_mvp_store()
    state, _ = store.create_investigation(ClaimInput(**graph_inputs("match")[0]))
    result = get_mvp_runner().run(state.investigation_id)
    assert result.assessment_status == "supported_for_scope"
    assert len(result.evidence) == 2
    assert all(read_annotation(item.notes) is not None for item in result.evidence)


def test_scenarios_can_share_persistent_demo_database(tmp_path):
    store = MvpStore(tmp_path / "shared-demo.db")
    try:
        for name in ("match", "route_mismatch", "fake_quote", "contradiction"):
            state, _ = store.create_investigation(ClaimInput(**graph_inputs(name)[0]))
            executor, gateway = make_demo_runtime(name)
            result = InProcessRunner(store, executor=executor, gateway=gateway).run(state.investigation_id)
            assert result.assessment_status == SCENARIOS[name][1]
    finally:
        store.close()


async def wait_for_review(client, investigation_id):
    for _ in range(200):
        response = await client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
        assert response.status_code == 200, response.text
        state = response.json()
        if state["checkpoint"] or state["run_status"] in {"failed", "completed"}:
            assert state["run_status"] != "failed", state
            return state
        await asyncio.sleep(0.025)
    raise AssertionError("Timed out waiting for the actual graph runner")


async def review(client, investigation_id, state, action="approve", **extra):
    return await client.post(f"/api/v1/investigations/{investigation_id}/reviews", headers=REVIEWER, json={
        "decision_id": uuid4().hex, "action": action, "checkpoint": state["checkpoint"] or "assessment",
        "expected_version": state["version"], "reason": "Synthetic end-to-end test decision", **extra,
    })


@pytest.mark.asyncio
async def test_api_review_export_and_edit_invalidates_approval(configured_runtime):
    # No direct store mutation or node calls: all user actions travel through HTTP routes.
    configure_mvp()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/investigations")).status_code == 401
        created = await client.post("/api/v1/investigations", headers=INVESTIGATOR,
                                    json=graph_inputs("match")[0])
        assert created.status_code == 202, created.text
        investigation_id = created.json()["investigation_id"]
        base = f"/api/v1/investigations/{investigation_id}"
        state = await wait_for_review(client, investigation_id)
        assert state["checkpoint"] == "assessment"
        assert state["assessment_status"] == "supported_for_scope"
        evidence = (await client.get(base + "/evidence", headers=INVESTIGATOR)).json()["items"]
        assert len(evidence) == 2
        item = evidence[0]
        assert item["scope_match"] == "match"
        assert item["scope"]["population"] == "adults"
        assert item["scope"]["dose"] == "10 mg/day"
        document = (await client.get(base + "/documents/" + item["doc_id"], headers=INVESTIGATOR)).json()["document"]
        assert document["text"][item["locator"]["start"]:item["locator"]["end"]] == item["quote"]
        assert (await client.get(base + "/export", headers=INVESTIGATOR)).status_code == 409
        assert (await review(client, investigation_id, state)).status_code == 200
        assert (await review(client, investigation_id, state)).status_code == 409
        continuation = await client.post(base + "/continue", headers=INVESTIGATOR,
                                         json={"expected_version": state["version"] + 1})
        assert continuation.status_code == 202, continuation.text
        dossier_state = await wait_for_review(client, investigation_id)
        assert dossier_state["checkpoint"] == "dossier"
        assert dossier_state["budget"] == state["budget"]  # resume never resets counters
        dossier = (await client.get(base + "/dossier", headers=INVESTIGATOR)).json()
        assert dossier["validation"]["ok"] is True, dossier
        assert dossier["approved"] is None
        assert dossier["dossier"]["dossier_id"].startswith("DOS-P3-")
        assert (await client.get(base + "/export", headers=INVESTIGATOR)).status_code == 409
        denied = await client.post(base + "/reviews", headers=INVESTIGATOR, json={
            "decision_id": uuid4().hex, "action": "approve", "checkpoint": "dossier",
            "expected_version": dossier_state["version"],
        })
        assert denied.status_code == 403
        assert (await review(client, investigation_id, dossier_state)).status_code == 200
        exported = await client.get(base + "/export", headers=INVESTIGATOR)
        assert exported.status_code == 200, exported.text
        assert "SYNTHETIC-DEMO" in exported.text
        approved_state = (await client.get(base, headers=INVESTIGATOR)).json()
        # Editing a completed/approved investigation must reopen review, not bypass it.
        edited = await review(client, investigation_id, approved_state, "edit_evidence",
                              target_evidence_id=item["evidence_id"], payload={"quote": "Event Alpha"})
        assert edited.status_code == 200, edited.text
        assert (await client.get(base + "/export", headers=INVESTIGATOR)).status_code == 409
        current = (await client.get(base, headers=INVESTIGATOR)).json()
        assert current["assessment_status"] is None
        assert current["next_stage"] == "checklist"
        assert current["budget"] == approved_state["budget"]
        assert (await client.post(base + "/continue", headers=INVESTIGATOR,
                                  json={"expected_version": current["version"]})).status_code == 202
        reassessed = await wait_for_review(client, investigation_id)
        assert reassessed["assessment_status"] != "supported_for_scope"
        events = (await client.get(base + "/events", headers=INVESTIGATOR)).json()["items"]
        assert any(event["kind"] == "runtime" and event["payload"]["mode"] == "person3_demo" for event in events)
