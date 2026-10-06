"""AUTH-03 — nhật ký phải trả lời được "ai làm gì".

Lỗi cũ: ``reviewer_id=actor_for(role)`` với ``actor_for`` trả **chuỗi vai**. Hai người cùng vai
không phân biệt được, nên không đáp ứng được yêu cầu truy vết R2-2-07.
"""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app
from src.models.schemas import CheckpointKind, ClaimInput, RunStatus

CLAIM = {
    "claim_text": "aspirin gây chảy máu tiêu hoá",
    "drug": "aspirin",
    "event": "chảy máu tiêu hoá",
}

REASON = "Bài kiểm thử nhật ký: lý do đủ dài để qua ngưỡng RV-04."
REVIEWER_A = "usr_duyet_a"
REVIEWER_B = "usr_duyet_b"


def _headers(user_id: str, role: str = "reviewer") -> dict[str, str]:
    return {"X-Test-User": f"{user_id}:{role}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def audit_client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "audit.db"))
    async with _client() as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


def _seed_case(created_by: str) -> tuple[str, int]:
    store = get_mvp_store()
    state, _ = store.create_investigation(ClaimInput(**CLAIM), created_by=created_by)
    state = store.save_state(
        state.model_copy(
            update={"run_status": RunStatus.WAITING_FOR_REVIEW, "checkpoint": CheckpointKind.ASSESSMENT}
        )
    )
    return state.investigation_id, state.version


async def _reject(client: AsyncClient, case_id: str, version: int, *, user_id: str, decision_id: str):
    return await client.post(
        f"/api/v1/investigations/{case_id}/reviews",
        headers=_headers(user_id),
        json={
            "decision_id": decision_id,
            "action": "reject",
            "checkpoint": "assessment",
            "expected_version": version,
            "reason": REASON,
        },
    )


@pytest.mark.asyncio
async def test_two_reviewers_with_the_same_role_are_distinguishable(audit_client: AsyncClient):
    """Hai tài khoản cùng vai duyệt hai ca → nhật ký ghi **mã người**, không ghi "reviewer"."""
    case_a, version_a = _seed_case("usr_tao_a")
    case_b, version_b = _seed_case("usr_tao_b")

    first = await _reject(audit_client, case_a, version_a, user_id=REVIEWER_A, decision_id="qđ-a")
    assert first.status_code == 200, first.text
    second = await _reject(audit_client, case_b, version_b, user_id=REVIEWER_B, decision_id="qđ-b")
    assert second.status_code == 200, second.text

    store = get_mvp_store()
    assert store.get_review_decision("qđ-a").reviewer_id == REVIEWER_A
    assert store.get_review_decision("qđ-b").reviewer_id == REVIEWER_B

    log = await audit_client.get("/api/v1/admin/audit", headers=_headers("usr_kt", "auditor"))
    assert log.status_code == 200, log.text
    decisions = [item for item in log.json()["items"] if item["action"] == "review_reject"]
    assert {(item["actor"], item["investigation_id"]) for item in decisions} == {
        (REVIEWER_A, case_a),
        (REVIEWER_B, case_b),
    }
    assert all(item["actor_role"] == "reviewer" for item in decisions)
    assert all(item["legacy_actor"] is False for item in decisions)


@pytest.mark.asyncio
async def test_jsonl_export_carries_the_person_and_the_role(audit_client: AsyncClient):
    """Bản kết xuất JSONL chứa mã người **và** vai, để vẫn lọc được theo vai."""
    case_id, version = _seed_case("usr_tao_c")
    assert (await _reject(audit_client, case_id, version, user_id=REVIEWER_A, decision_id="qđ-c")).status_code == 200

    response = await audit_client.get(
        "/api/v1/admin/audit",
        params={"format": "jsonl", "investigation_id": case_id},
        headers=_headers("usr_kt", "auditor"),
    )
    assert response.status_code == 200
    rows = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert rows, "Bản kết xuất phải có ít nhất một dòng"
    assert all(row["investigation_id"] == case_id for row in rows)
    actors = {row["actor"] for row in rows}
    assert REVIEWER_A in actors
    decision_row = next(row for row in rows if row["action"] == "review_reject")
    assert decision_row["actor_role"] == "reviewer"
    assert decision_row["payload"]["decision_id"] == "qđ-c"


@pytest.mark.asyncio
async def test_legacy_rows_are_marked_not_rewritten(audit_client: AsyncClient):
    """Bản ghi cũ chỉ có chuỗi vai vẫn đọc được, nhưng được đánh dấu ``legacy_actor``."""
    store = get_mvp_store()
    case_id, _ = _seed_case("usr_tao_d")
    with store._lock, store._conn:  # noqa: SLF001 - cố ý ghi thẳng để mô phỏng dữ liệu cũ
        store._conn.execute(
            "INSERT INTO audit_events (investigation_id, actor, action, payload_json, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (case_id, "reviewer", "duyet_ho_so", "{}", "2026-01-01T00:00:00+00:00"),
        )
    log = await audit_client.get(
        "/api/v1/admin/audit",
        params={"investigation_id": case_id},
        headers=_headers("usr_kt", "auditor"),
    )
    rows = log.json()["items"]
    legacy = [row for row in rows if row["actor"] == "reviewer"]
    assert legacy and legacy[0]["legacy_actor"] is True
    assert legacy[0]["actor_role"] is None


@pytest.mark.asyncio
async def test_audit_records_the_role_at_the_time_of_the_action(audit_client: AsyncClient):
    """Đổi vai thì bản ghi cũ giữ nguyên vai cũ — nhật ký là append-only, không viết lại lịch sử."""
    store = get_mvp_store()
    case_id, version = _seed_case("usr_tao_e")
    assert (await _reject(audit_client, case_id, version, user_id=REVIEWER_A, decision_id="qđ-e")).status_code == 200

    store.update_user(REVIEWER_A, role="investigator")
    log = await audit_client.get(
        "/api/v1/admin/audit",
        params={"investigation_id": case_id},
        headers=_headers("usr_kt", "auditor"),
    )
    decision_row = next(row for row in log.json()["items"] if row["action"] == "review_reject")
    assert decision_row["actor_role"] == "reviewer"
    assert decision_row["actor"] == REVIEWER_A


@pytest.mark.asyncio
async def test_audit_rows_carry_the_request_id_the_caller_sees(audit_client: AsyncClient):
    """``request_id`` trong nhật ký phải **trùng** mã trong header ``X-Request-Id`` của phản hồi.

    Trước đây mã chỉ được sinh cho phản hồi lỗi, nên mọi dòng nhật ký đều có ``request_id = NULL``
    và không tra ngược được "lỗi này là do thao tác nào".
    """
    store = get_mvp_store()
    case_id, version = _seed_case("usr_tao_f")

    response = await audit_client.post(
        f"/api/v1/investigations/{case_id}/reviews",
        json={
            "decision_id": "qđ-f",
            "action": "reject",
            "checkpoint": "assessment",
            "expected_version": version,
            "reason": REASON,
        },
        headers=_headers(REVIEWER_A),
    )
    assert response.status_code == 200, response.text
    request_id = response.headers["x-request-id"]
    assert request_id

    log = await audit_client.get(
        "/api/v1/admin/audit",
        params={"investigation_id": case_id},
        headers=_headers("usr_kt", "auditor"),
    )
    decision_row = next(row for row in log.json()["items"] if row["action"] == "review_reject")
    assert decision_row["request_id"] == request_id
    # Đọc thẳng từ kho cũng phải thấy cùng mã, không chỉ qua tuyến admin.
    stored = next(row for row in store.list_audit(investigation_id=case_id, limit=50) if row["action"] == "review_reject")
    assert stored["request_id"] == request_id


@pytest.mark.asyncio
async def test_every_audit_row_written_during_a_request_has_a_request_id(audit_client: AsyncClient):
    """Mọi dòng sinh ra **trong một yêu cầu** đều có mã; dòng do việc chạy nền vẫn được phép trống."""
    case_id, version = _seed_case("usr_tao_g")
    store = get_mvp_store()
    before = {row["id"] for row in store.list_audit(investigation_id=case_id, limit=200)}

    response = await audit_client.post(
        f"/api/v1/investigations/{case_id}/reviews",
        json={
            "decision_id": "qđ-g",
            "action": "reject",
            "checkpoint": "assessment",
            "expected_version": version,
            "reason": REASON,
        },
        headers=_headers(REVIEWER_A),
    )
    assert response.status_code == 200, response.text

    fresh = [row for row in store.list_audit(investigation_id=case_id, limit=200) if row["id"] not in before]
    assert fresh, "yêu cầu duyệt phải ghi ít nhất một dòng nhật ký"
    assert all(row["request_id"] == response.headers["x-request-id"] for row in fresh), [
        row["action"] for row in fresh if row["request_id"] != response.headers["x-request-id"]
    ]


@pytest.mark.asyncio
async def test_inbound_request_id_is_reused_so_traces_join_across_tiers(audit_client: AsyncClient):
    """Cầu nối hoặc hệ thống ngoài gửi ``X-Request-Id`` thì nhật ký dùng đúng mã đó."""
    response = await audit_client.get(
        "/api/v1/admin/audit", params={"limit": 1}, headers={**_headers("usr_kt", "auditor"), "X-Request-Id": "trace-ngoai-01"}
    )
    assert response.headers["x-request-id"] == "trace-ngoai-01"
