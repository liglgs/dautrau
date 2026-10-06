"""Kiểm thử API nghiệp vụ MVP (M07).

Phạm vi:
  * token/role: thiếu token, sai token, investigator không được duyệt;
  * tạo cuộc điều tra 202 + Idempotency-Key (double request chỉ tạo 1 job);
  * luồng đầy đủ: tạo → polling → duyệt kết luận → continue → hồ sơ → duyệt → export;
  * export khi chưa duyệt trả 409; tài liệu/bằng chứng phải thuộc đúng cuộc điều tra;
  * route template ``/chat`` đã bị gỡ.
"""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app

INVESTIGATOR = {"X-API-Token": "inv-token"}
REVIEWER = {"X-API-Token": "rev-token"}
CLAIM = {
    "claim_text": "metformin gây lactic acidosis.",
    "drug": "metformin",
    "event": "lactic acidosis",
    "population": "adults with renal impairment",
    "route": "oral",
}


@pytest_asyncio.fixture
async def mvp_client(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "inv-token")
    monkeypatch.setenv("REVIEWER_TOKEN", "rev-token")
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "mvp-api.db"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


async def _wait_for_checkpoint(client: AsyncClient, investigation_id: str, *, timeout: float = 15.0) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    last: dict = {}
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
        assert response.status_code == 200, response.text
        last = response.json()
        if last["checkpoint"] is not None or last["run_status"] in {"completed", "failed", "interrupted"}:
            return last
        await asyncio.sleep(0.05)
    raise AssertionError(f"Hết thời gian chờ runner: {last}")


async def _create(client: AsyncClient, key: str = "key-1", claim: dict | None = None) -> dict:
    response = await client.post(
        "/api/v1/investigations",
        json=claim or CLAIM,
        headers={**INVESTIGATOR, "Idempotency-Key": key},
    )
    assert response.status_code == 202, response.text
    return response.json()


#: RV-04 — máy chủ đòi lý do duyệt dài ít nhất 15 ký tự, giống giao diện.
REVIEW_REASON = "Kiểm thử tự động: lý do đủ dài để qua ngưỡng RV-04."


async def _current_version(client: AsyncClient, investigation_id: str) -> int:
    """Đọc phiên bản hiện tại để gửi kèm ``/continue`` (RV-06 bắt buộc ``expected_version``)."""
    response = await client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    assert response.status_code == 200, response.text
    return int(response.json()["version"])


# --------------------------------------------------------------------------------------
# Token & phân quyền
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_token_is_401(mvp_client):
    response = await mvp_client.get("/api/v1/investigations")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_wrong_token_is_401(mvp_client):
    response = await mvp_client.get("/api/v1/investigations", headers={"X-API-Token": "khong-dung"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bearer_header_is_accepted(mvp_client):
    response = await mvp_client.get("/api/v1/investigations", headers={"Authorization": "Bearer inv-token"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_investigator_cannot_submit_review(mvp_client):
    created = await _create(mvp_client)
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)

    response = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=INVESTIGATOR,
        json={
            "decision_id": "DEC-1",
            "action": "approve",
            "checkpoint": state["checkpoint"],
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


# --------------------------------------------------------------------------------------
# Tạo cuộc điều tra & idempotency
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_returns_202_and_idempotency_key_creates_one_job(mvp_client):
    first = await _create(mvp_client, key="same-key")
    second = await _create(mvp_client, key="same-key")
    assert first["investigation_id"] == second["investigation_id"]
    assert first["created"] is True
    assert second["created"] is False

    listing = await mvp_client.get("/api/v1/investigations", headers=INVESTIGATOR)
    assert len(listing.json()["items"]) == 1

    await _wait_for_checkpoint(mvp_client, first["investigation_id"])


@pytest.mark.asyncio
async def test_invalid_claim_is_422(mvp_client):
    response = await mvp_client.post(
        "/api/v1/investigations",
        json={"claim_text": "", "drug": "", "event": ""},
        headers=INVESTIGATOR,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_investigation_is_404(mvp_client):
    response = await mvp_client.get("/api/v1/investigations/INV-khong-ton-tai", headers=INVESTIGATOR)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --------------------------------------------------------------------------------------
# Luồng đầy đủ
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_flow_from_claim_to_approved_export(mvp_client):
    created = await _create(mvp_client, key="flow-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    assert state["checkpoint"] == "assessment"
    assert state["assessment_status"] == "supported_for_scope"
    assert state["counters"]["evidence"] >= 2
    assert state["budget"]["steps_used"] <= state["budget"]["max_steps"] - 1

    events = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/events", headers=INVESTIGATOR)
    assert events.status_code == 200
    kinds = {item["kind"] for item in events.json()["items"]}
    assert {"normalize", "retrieve", "assess", "waiting_for_review"} <= kinds

    export_blocked = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=REVIEWER)
    assert export_blocked.status_code == 409
    assert export_blocked.json()["error"]["code"] == "dossier_not_approved"

    approve_assessment = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-ASSESS",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert approve_assessment.status_code == 200, approve_assessment.text
    assert approve_assessment.json()["review_status"] == "approved"

    still_blocked = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=REVIEWER)
    assert still_blocked.status_code == 409, "duyệt kết luận không được tự mở export"

    resumed = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=INVESTIGATOR,
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    assert resumed.status_code == 202
    dossier_state = await _wait_for_checkpoint(mvp_client, investigation_id)
    assert dossier_state["checkpoint"] == "dossier"

    dossier_response = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/dossier", headers=INVESTIGATOR)
    payload = dossier_response.json()
    assert payload["dossier"]["version"] == 1
    assert payload["dossier"]["status"] == "pending"
    assert payload["validation"]["ok"] is True
    assert payload["approved"] is None

    approve_dossier = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-DOSSIER",
            "action": "approve",
            "checkpoint": "dossier",
            "expected_version": dossier_state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert approve_dossier.status_code == 200, approve_dossier.text

    exported = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=REVIEWER)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert f"Hồ sơ điều tra {investigation_id}" in exported.text
    assert "## Bằng chứng đã truy xuất" in exported.text


@pytest.mark.asyncio
async def test_review_status_is_exposed_and_a_rejection_is_not_an_approval(mvp_client):
    """``run_status=completed`` không nói lên hồ sơ đã duyệt; API phải trả ``review_status``."""
    created = await _create(mvp_client, key="review-status-1")
    investigation_id = created["investigation_id"]

    listed = await mvp_client.get("/api/v1/investigations", headers=INVESTIGATOR)
    row = next(item for item in listed.json()["items"] if item["investigation_id"] == investigation_id)
    assert row["review_status"] is None, "chưa có hồ sơ thì chưa có trạng thái duyệt"

    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    detail = await mvp_client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    assert detail.json()["review_status"] is None

    approve = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-RS-1",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert approve.status_code == 200, approve.text

    resumed = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=INVESTIGATOR,
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    assert resumed.status_code == 202
    dossier_state = await _wait_for_checkpoint(mvp_client, investigation_id)
    assert dossier_state["checkpoint"] == "dossier"

    rejected = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-RS-2",
            "action": "reject",
            "checkpoint": "dossier",
            "expected_version": dossier_state["version"],
            "reason": "Thiếu nguồn thứ hai và trích dẫn chưa khớp phạm vi quần thể.",
        },
    )
    assert rejected.status_code == 200, rejected.text

    detail = await mvp_client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    payload = detail.json()
    assert payload["run_status"] == "completed"
    assert payload["review_status"] == "rejected", "hồ sơ bị từ chối không được coi là đã duyệt"

    listed = await mvp_client.get("/api/v1/investigations", headers=INVESTIGATOR)
    row = next(item for item in listed.json()["items"] if item["investigation_id"] == investigation_id)
    assert row["review_status"] == "rejected"

    blocked = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=REVIEWER)
    assert blocked.status_code == 409


@pytest.mark.asyncio
async def test_last_review_records_a_human_rejection_at_the_assessment_checkpoint(mvp_client):
    """Từ chối ở checkpoint ``assessment`` không tạo hồ sơ, nên ``review_status`` vẫn ``None``.

    Giao diện cần biết con người đã can thiệp, nếu không ca này hiện như "chưa ai duyệt".
    """
    created = await _create(mvp_client, key="last-review-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)

    detail = await mvp_client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    assert detail.json()["last_review"] is None

    rejected = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-LR-1",
            "action": "reject",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": "Bằng chứng chưa đủ để kết luận ở phạm vi người lớn.",
        },
    )
    assert rejected.status_code == 200, rejected.text

    detail = await mvp_client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    payload = detail.json()
    assert payload["run_status"] == "completed"
    assert payload["review_status"] is None, "chưa có hồ sơ thì chưa có trạng thái hồ sơ"
    assert payload["last_review"] is not None
    assert payload["last_review"]["action"] == "reject"
    assert payload["last_review"]["checkpoint"] == "assessment"

    listed = await mvp_client.get("/api/v1/investigations", headers=INVESTIGATOR)
    row = next(item for item in listed.json()["items"] if item["investigation_id"] == investigation_id)
    assert row["last_review"]["action"] == "reject"


@pytest.mark.asyncio
async def test_reviewer_identity_comes_from_token(mvp_client):
    created = await _create(mvp_client, key="identity-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    response = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-ID",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
            "reviewer_id": "ke-gia-mao",
        },
    )
    assert response.status_code == 422, "trường reviewer_id không được nhận từ body"


@pytest.mark.asyncio
async def test_stale_expected_version_returns_409(mvp_client):
    created = await _create(mvp_client, key="stale-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    ok = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-A",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert ok.status_code == 200

    stale = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-B",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] in {"version_conflict", "invalid_state"}


@pytest.mark.asyncio
async def test_reject_requires_reason(mvp_client):
    created = await _create(mvp_client, key="reject-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    response = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-REJECT",
            "action": "reject",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": "   ",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_continue_while_checkpoint_pending_is_409(mvp_client):
    created = await _create(mvp_client, key="continue-1")
    investigation_id = created["investigation_id"]
    await _wait_for_checkpoint(mvp_client, investigation_id)
    response = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=INVESTIGATOR,
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state"


# --------------------------------------------------------------------------------------
# Dữ liệu bằng chứng / tài liệu
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_continue_double_click_is_idempotent(mvp_client):
    """Hai lần bấm "chạy tiếp" với cùng Idempotency-Key chỉ khởi động một lượt chạy."""
    created = await _create(mvp_client, key="double-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-DOUBLE",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    headers = {**INVESTIGATOR, "Idempotency-Key": "continue-key"}
    # Double-click thật là hai lần gửi **y hệt nhau**, nên phải cùng một phiên bản; đọc lại phiên
    # bản giữa hai lần sẽ biến lần thứ hai thành một yêu cầu mới hợp lệ, không còn là bấm trùng.
    version = await _current_version(mvp_client, investigation_id)
    first = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=headers,
        json={"expected_version": version},
    )
    second = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=headers,
        json={"expected_version": version},
    )
    assert first.status_code == 202 and first.json()["resumed"] is True
    assert second.status_code == 202 and second.json()["resumed"] is False

    final = await _wait_for_checkpoint(mvp_client, investigation_id)
    assert final["checkpoint"] == "dossier"
    events = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/events", headers=INVESTIGATOR)
    resumed_events = [item for item in events.json()["items"] if item["kind"] == "running"]
    assert len(resumed_events) == 2, "chỉ được có 2 lượt chạy: lần đầu và một lần chạy tiếp"


@pytest.mark.asyncio
async def test_continue_after_completion_is_409(mvp_client):
    created = await _create(mvp_client, key="done-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-DONE-A",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=INVESTIGATOR,
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    dossier_state = await _wait_for_checkpoint(mvp_client, investigation_id)
    done = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-DONE-B",
            "action": "approve",
            "checkpoint": "dossier",
            "expected_version": dossier_state["version"],
            "reason": REVIEW_REASON,
        },
    )
    assert done.status_code == 200
    response = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=INVESTIGATOR,
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_evidence_and_document_endpoints(mvp_client):
    created = await _create(mvp_client, key="evidence-1")
    investigation_id = created["investigation_id"]
    await _wait_for_checkpoint(mvp_client, investigation_id)

    evidence = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/evidence", headers=INVESTIGATOR)
    items = evidence.json()["items"]
    assert items and items[0]["quote"]
    assert items[0]["document"]["source_url"].startswith("http")

    doc_id = items[0]["doc_id"]
    document = await mvp_client.get(
        f"/api/v1/investigations/{investigation_id}/documents/{doc_id}", headers=INVESTIGATOR
    )
    assert document.status_code == 200
    body = document.json()
    assert body["document"]["doc_id"] == doc_id
    assert body["document"]["text"]
    assert body["locators"], "phải có locator để đối chiếu trích dẫn"
    locator = body["locators"][0]["locator"]
    text = body["document"]["text"]
    assert text[locator["start"] : locator["end"]] == body["locators"][0]["quote"]


@pytest.mark.asyncio
async def test_document_of_other_investigation_is_404(mvp_client):
    first = await _create(mvp_client, key="doc-1")
    await _wait_for_checkpoint(mvp_client, first["investigation_id"])
    evidence = await mvp_client.get(
        f"/api/v1/investigations/{first['investigation_id']}/evidence", headers=INVESTIGATOR
    )
    doc_id = evidence.json()["items"][0]["doc_id"]

    second = await _create(mvp_client, key="doc-2", claim={**CLAIM, "drug": "orlistat", "event": "pancreatitis"})
    response = await mvp_client.get(
        f"/api/v1/investigations/{second['investigation_id']}/documents/{doc_id}", headers=INVESTIGATOR
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_events_cursor_returns_only_new_items(mvp_client):
    created = await _create(mvp_client, key="events-1")
    investigation_id = created["investigation_id"]
    await _wait_for_checkpoint(mvp_client, investigation_id)

    all_events = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/events", headers=INVESTIGATOR)
    items = all_events.json()["items"]
    last_id = all_events.json()["last_id"]
    assert len(items) > 3

    incremental = await mvp_client.get(
        f"/api/v1/investigations/{investigation_id}/events?after_id={last_id}", headers=INVESTIGATOR
    )
    assert incremental.json()["items"] == []
    assert incremental.json()["last_id"] == last_id


@pytest.mark.asyncio
async def test_chat_route_is_removed(mvp_client):
    response = await mvp_client.post("/api/v1/chat", json={"message": "xin chào"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_still_available(mvp_client):
    response = await mvp_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_reports_store_and_runner(mvp_client):
    response = await mvp_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "runner_busy" in body


# --------------------------------------------------------------------------------------
# Hồi quy hợp đồng HTTP (đợt review M07): envelope lỗi, retry 429, export media type
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validation_error_uses_documented_envelope(mvp_client):
    response = await mvp_client.post("/api/v1/investigations", json={"drug": "metformin"}, headers=INVESTIGATOR)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_request"
    assert body["error"]["request_id"]
    assert isinstance(body["error"]["details"].get("errors"), list)


@pytest.mark.asyncio
async def test_unknown_route_uses_documented_envelope(mvp_client):
    response = await mvp_client.get("/api/v1/khong-ton-tai", headers=INVESTIGATOR)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_export_returns_markdown_media_type(mvp_client):
    created = await _create(mvp_client, key="media-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-MEDIA-1",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers={**INVESTIGATOR, "Idempotency-Key": "media-continue"},
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    dossier_state = await _wait_for_checkpoint(mvp_client, investigation_id)
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-MEDIA-2",
            "action": "approve",
            "checkpoint": "dossier",
            "expected_version": dossier_state["version"],
            "reason": REVIEW_REASON,
        },
    )
    exported = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=INVESTIGATOR)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "attachment" in exported.headers["content-disposition"]


@pytest.mark.asyncio
async def test_new_continue_while_running_is_409(mvp_client):
    """Yêu cầu chạy tiếp MỚI trong lúc cuộc điều tra đang chạy phải bị từ chối rõ ràng."""
    created = await _create(mvp_client, key="running-1")
    investigation_id = created["investigation_id"]
    # Ngay sau khi tạo, cuộc điều tra đang chạy nền.
    running = await mvp_client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    if running.json()["run_status"] != "running":  # pragma: no cover - phụ thuộc thời điểm
        pytest.skip("lượt chạy đã kết thúc trước khi kiểm tra")
    response = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers={**INVESTIGATOR, "Idempotency-Key": "running-continue"},
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    assert response.status_code in (409, 429)
    # Cuộc đang chạy làm phiên bản nhảy liên tục, nên 409 có thể là "đang chạy" hoặc
    # "phiên bản đã cũ"; cả hai đều buộc client đọc lại trạng thái rồi mới thử tiếp.
    assert response.json()["error"]["code"] in ("invalid_state", "runner_busy", "version_conflict")


@pytest.mark.asyncio
async def test_retry_after_runner_busy_starts_the_queued_job(mvp_client):
    """Tạo lần đầu bị 429 ⇒ job nằm 'queued'; gọi lại cùng Idempotency-Key phải chạy nốt."""
    from src.api.mvp_runtime import get_mvp_runner

    runner = get_mvp_runner()
    runner.acquire("INV-KHAC")  # giữ khoá để mô phỏng runner đang bận việc khác
    try:
        busy = await mvp_client.post(
            "/api/v1/investigations", json=CLAIM, headers={**INVESTIGATOR, "Idempotency-Key": "busy-1"}
        )
    finally:
        runner.release()
    assert busy.status_code == 429, busy.text
    assert busy.json()["error"]["retryable"] is True
    investigation_id = busy.json()["error"]["details"]["investigation_id"]

    queued = await mvp_client.get(f"/api/v1/investigations/{investigation_id}", headers=INVESTIGATOR)
    assert queued.json()["run_status"] == "queued"

    retry = await mvp_client.post(
        "/api/v1/investigations", json=CLAIM, headers={**INVESTIGATOR, "Idempotency-Key": "busy-1"}
    )
    assert retry.status_code == 202, retry.text
    body = retry.json()
    assert body["created"] is False
    assert body["started"] is True
    finished = await _wait_for_checkpoint(mvp_client, investigation_id)
    assert finished["run_status"] == "waiting_for_review"
    assert finished["checkpoint"] == "assessment"


def test_openapi_documents_mvp_token_scheme():
    schema = app.openapi()
    scheme = schema["components"]["securitySchemes"]["MvpApiToken"]
    assert scheme["type"] == "apiKey" and scheme["name"] == "X-API-Token"
    create = schema["paths"]["/api/v1/investigations"]["post"]
    assert {"MvpApiToken": []} in create["security"]
    export = schema["paths"]["/api/v1/investigations/{investigation_id}/export"]["get"]
    assert "text/markdown" in " ".join(export["responses"]["200"]["content"].keys())


@pytest.mark.asyncio
async def test_export_and_approval_refuse_a_tampered_dossier(mvp_client):
    """Trích dẫn bị đổi ngoài luồng review ⇒ không duyệt được và không export được."""
    from src.api.mvp_runtime import get_mvp_store

    created = await _create(mvp_client, key="tamper-1")
    investigation_id = created["investigation_id"]
    state = await _wait_for_checkpoint(mvp_client, investigation_id)
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-TAMPER-ASSESS",
            "action": "approve",
            "checkpoint": "assessment",
            "expected_version": state["version"],
            "reason": REVIEW_REASON,
        },
    )
    await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/continue",
        headers=INVESTIGATOR,
        json={"expected_version": await _current_version(mvp_client, investigation_id)},
    )
    dossier_state = await _wait_for_checkpoint(mvp_client, investigation_id)
    assert dossier_state["checkpoint"] == "dossier"

    store = get_mvp_store()
    current = store.get_state(investigation_id)
    evidence = list(current.evidence)
    evidence[0] = evidence[0].model_copy(update={"quote": "trích dẫn bị sửa ngoài luồng"})
    store.save_state(current.model_copy(update={"evidence": evidence}))

    approve = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-TAMPER-DOSSIER",
            "action": "approve",
            "checkpoint": "dossier",
            "expected_version": store.get_state(investigation_id).version,
            "reason": REVIEW_REASON,
        },
    )
    assert approve.status_code == 409, approve.text
    assert approve.json()["error"]["code"] == "dossier_invalid"
    assert any("không khớp" in item for item in approve.json()["error"]["details"]["errors"])

    # Khôi phục nguyên văn rồi duyệt bình thường: export mở.
    store.save_state(current)
    approve_ok = await mvp_client.post(
        f"/api/v1/investigations/{investigation_id}/reviews",
        headers=REVIEWER,
        json={
            "decision_id": "DEC-TAMPER-DOSSIER-OK",
            "action": "approve",
            "checkpoint": "dossier",
            "expected_version": store.get_state(investigation_id).version,
            "reason": REVIEW_REASON,
        },
    )
    assert approve_ok.status_code == 200, approve_ok.text
    assert (
        await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=REVIEWER)
    ).status_code == 200

    # Sửa lại trích dẫn sau khi đã duyệt: export phải từ chối.
    tampered = store.get_state(investigation_id)
    evidence = list(tampered.evidence)
    evidence[0] = evidence[0].model_copy(update={"quote": "trích dẫn bị sửa sau khi duyệt"})
    store.save_state(tampered.model_copy(update={"evidence": evidence}))

    exported = await mvp_client.get(f"/api/v1/investigations/{investigation_id}/export", headers=REVIEWER)
    assert exported.status_code == 409
    assert exported.json()["error"]["code"] == "dossier_invalid"
