"""Deterministic HTTP coverage for the managed casework workflow."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from src.api.v2_routes import get_casework_store
from src.main import app
from src.services.casework.models import CaseworkRun, InputRevision
from src.services.casework.store import CaseWorkStore
from src.services.warehouse.db import get_warehouse_engine, session_scope


def headers(user: str, role: str, key: str | None = None) -> dict[str, str]:
    result = {"X-Test-User": f"{user}:{role}"}
    if key:
        result["Idempotency-Key"] = key
    return result


@pytest_asyncio.fixture
async def workflow_client(tmp_path):
    store = CaseWorkStore(get_warehouse_engine(f"sqlite:///{tmp_path / 'workflow-http.db'}"))
    app.dependency_overrides[get_casework_store] = lambda: store
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, store
    app.dependency_overrides.pop(get_casework_store, None)


@pytest.mark.asyncio
async def test_raw_intake_to_independent_approval_export_and_reload(workflow_client):
    client, _ = workflow_client
    payload = {"kind": "di", "raw_text": "Có cần giảm liều metformin ở người cao tuổi?"}
    first = await client.post(
        "/api/v2/work-items/intake", json=payload, headers=headers("author", "reviewer", "intake-1")
    )
    assert first.status_code == 201, first.text
    retry = await client.post(
        "/api/v2/work-items/intake", json=payload, headers=headers("author", "reviewer", "intake-1")
    )
    assert retry.status_code == 201 and retry.json()["id"] == first.json()["id"]
    work_id = first.json()["id"]

    aggregate = await client.get(f"/api/v2/work-items/{work_id}/workflow", headers=headers("author", "reviewer"))
    assert aggregate.status_code == 200 and aggregate.json()["work_item"]["raw_text"] == payload["raw_text"]
    # A fresh HTTP client sees the same aggregate: no in-process workflow state is required.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as reloaded:
        assert (
            await reloaded.get(f"/api/v2/work-items/{work_id}/workflow", headers=headers("author", "reviewer"))
        ).status_code == 200

    draft = await client.post(
        f"/api/v2/work-items/{work_id}/drafts",
        json={
            "expected_version": 1,
            "expected_input_revision": 1,
            "sections": {"summary": "Bản trả lời giới hạn, chờ duyệt."},
        },
        headers=headers("author", "reviewer", "draft-1"),
    )
    assert draft.status_code == 201, draft.text
    submitted = await client.post(
        f"/api/v2/responses/{draft.json()['response_id']}/submit-review",
        json={"expected_version": 1, "expected_work_version": 1, "basis_hash": draft.json()["basis_hash"]},
        headers=headers("author", "reviewer", "submit-1"),
    )
    assert submitted.status_code == 200, submitted.text

    self_review = await client.post(
        f"/api/v2/responses/{draft.json()['response_id']}/review",
        json={
            "expected_version": 1,
            "expected_work_version": 2,
            "basis_hash": draft.json()["basis_hash"],
            "action": "approve",
        },
        headers=headers("author", "reviewer", "self-review"),
    )
    assert self_review.status_code == 409
    approved = await client.post(
        f"/api/v2/responses/{draft.json()['response_id']}/review",
        json={
            "expected_version": 1,
            "expected_work_version": 2,
            "basis_hash": draft.json()["basis_hash"],
            "action": "approve",
        },
        headers=headers("other-reviewer", "reviewer", "review-1"),
    )
    assert approved.status_code == 200, approved.text
    approval_retry = await client.post(
        f"/api/v2/responses/{draft.json()['response_id']}/review",
        json={
            "expected_version": 1,
            "expected_work_version": 2,
            "basis_hash": draft.json()["basis_hash"],
            "action": "approve",
        },
        headers=headers("other-reviewer", "reviewer", "review-1"),
    )
    assert approval_retry.status_code == 200
    assert approval_retry.json() == approved.json()
    exported = await client.get(
        f"/api/v2/work-items/{work_id}/response-export", headers=headers("other-reviewer", "reviewer")
    )
    assert exported.status_code == 200 and exported.json()["basis_hash"] == draft.json()["basis_hash"]


@pytest.mark.asyncio
async def test_editor_draft_is_actor_scoped_versioned_and_idempotent(workflow_client):
    client, _ = workflow_client
    created = await client.post(
        "/api/v2/work-items/intake",
        json={"kind": "di", "raw_text": "Câu hỏi cần lưu nháp."},
        headers=headers("author", "investigator", "draft-intake"),
    )
    work_id = created.json()["id"]
    body = {"base_versions": {"work_item": 1, "input_revision": 1}, "content": {"summary": "Bản nháp"}}
    saved = await client.patch(
        f"/api/v2/work-items/{work_id}/editor-draft",
        json=body,
        headers=headers("author", "investigator", "draft-save-1"),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 1
    assert saved.json()["actor_id"] == "author"

    retry = await client.patch(
        f"/api/v2/work-items/{work_id}/editor-draft",
        json=body,
        headers=headers("author", "investigator", "draft-save-1"),
    )
    assert retry.status_code == 200 and retry.json() == saved.json()

    reopened = await client.get(f"/api/v2/work-items/{work_id}/editor-draft", headers=headers("author", "investigator"))
    assert reopened.status_code == 200 and reopened.json()["content"] == body["content"]
    other_actor = await client.get(
        f"/api/v2/work-items/{work_id}/editor-draft", headers=headers("other", "investigator")
    )
    assert other_actor.status_code == 404


@pytest.mark.asyncio
async def test_version_conflict_and_source_partial_error_are_preserved(workflow_client):
    client, store = workflow_client
    created = await client.post(
        "/api/v2/work-items/intake",
        json={"kind": "di", "raw_text": "Aspirin gây xuất huyết?"},
        headers=headers("owner", "investigator", "case-1"),
    )
    work_id = created.json()["id"]
    # Seed one proposal through the service, then issue an HTTP mutation against its
    # old work version.  The API must return a real optimistic-concurrency conflict.
    with session_scope(store.engine) as session:
        source = (
            session.execute(select(InputRevision).where(InputRevision.work_item_id == work_id))
            .scalar_one()
            .sources_json[0]
        )
    store.update_fields(
        work_item_id=work_id,
        expected_version=1,
        actor={"id": "owner", "role": "investigator"},
        assertions=[
            {
                "field_key": "drug",
                "value": "aspirin",
                "status": "proposed",
                "source_spans": [{"source_id": source["source_id"], "start": 0, "end": 7, "quote": "Aspirin"}],
            }
        ],
    )
    stale = await client.patch(
        f"/api/v2/work-items/{work_id}/fields",
        json={
            "expected_version": 1,
            "operations": [
                {
                    "assertion_id": (
                        await client.get(
                            f"/api/v2/work-items/{work_id}/workflow", headers=headers("owner", "investigator")
                        )
                    ).json()["field_assertions"][0]["assertion_id"],
                    "expected_assertion_version": 1,
                    "action": "confirm",
                }
            ],
        },
        headers=headers("owner", "investigator", "fields-1"),
    )
    assert stale.status_code == 409

    run = store.create_casework_run(
        work_item_id=work_id,
        purpose="preliminary_retrieval",
        actor={"id": "owner", "role": "investigator"},
        idempotency_key="run-seed",
    )
    with session_scope(store.engine) as session:
        row = session.get(CaseworkRun, run["run_id"])
        row.source_results_json = [
            {"source": "pubmed", "outcome": "partial", "coverage": "abstract_only"},
            {
                "source": "dailymed",
                "outcome": "http_error",
                "coverage": "unavailable",
                "http_status": 404,
                "source_gap": True,
            },
        ]
    aggregate = await client.get(f"/api/v2/work-items/{work_id}/workflow", headers=headers("owner", "investigator"))
    assert aggregate.status_code == 200
    assert aggregate.json()["runs"][-1]["source_results"][0]["outcome"] == "partial"
    assert aggregate.json()["runs"][-1]["source_results"][1]["outcome"] == "http_error"


@pytest.mark.asyncio
async def test_adr_with_all_minimum_groups_missing_is_saved(workflow_client):
    client, _ = workflow_client
    groups = {
        name: {"status": "missing"}
        for name in (
            "identifiable_patient",
            "identifiable_reporter",
            "suspected_medicinal_product",
            "suspected_adverse_reaction",
        )
    }
    result = await client.post(
        "/api/v2/work-items/intake",
        json={"kind": "adr", "raw_text": "Người báo mô tả một phản ứng bất lợi.", "adr_facts": groups},
        headers=headers("adr-owner", "investigator", "adr-missing"),
    )
    assert result.status_code == 201, result.text
    aggregate = await client.get(
        f"/api/v2/work-items/{result.json()['id']}/workflow", headers=headers("adr-owner", "investigator")
    )
    assert aggregate.status_code == 200
    assert aggregate.json()["adr_intake"]["validity"] == "incomplete"
    assert aggregate.json()["adr_intake"]["reportability"]["status"] == "not_assessed"
