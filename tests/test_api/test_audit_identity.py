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
from src.models.schemas import AssessmentStatus, CheckpointKind, ClaimInput, RunStatus

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


# --------------------------------------------------------------------------------------
# B1.7 mục 3 — "mọi sự kiện quan trọng": tạo ca, hủy ca, kết xuất, đổi vai, cấp tài khoản
# --------------------------------------------------------------------------------------


def _rows(action: str, *, investigation_id: str | None = None) -> list[dict]:
    store = get_mvp_store()
    return [row for row in store.list_audit(investigation_id=investigation_id, limit=500) if row["action"] == action]


@pytest.mark.asyncio
async def test_creating_a_case_is_attributed_to_the_person_not_to_system(audit_client: AsyncClient):
    """Trước đây ``investigation_created`` luôn ghi ``actor="system"`` — không biết ai mở ca."""
    response = await audit_client.post(
        "/api/v1/investigations", json=CLAIM, headers=_headers("usr_tao_moi", "investigator")
    )
    assert response.status_code == 202, response.text
    case_id = response.json()["investigation_id"]

    created = _rows("investigation_created", investigation_id=case_id)
    assert created and created[0]["actor"] == "usr_tao_moi"
    assert created[0]["actor_role"] == "investigator"
    assert created[0]["legacy_actor"] is False


@pytest.mark.asyncio
async def test_cancelling_a_case_is_attributed_to_the_person_who_clicked(audit_client: AsyncClient):
    """Trước đây hủy ca ghi ``system``, nên không truy được ai đã dừng cuộc điều tra."""
    case_id, _ = _seed_case("usr_nguoi_huy")
    response = await audit_client.post(
        f"/api/v1/investigations/{case_id}/cancel", headers=_headers("usr_nguoi_huy", "investigator")
    )
    assert response.status_code == 200, response.text

    saved = _rows("state_saved", investigation_id=case_id)
    assert saved and saved[-1]["actor"] == "usr_nguoi_huy"
    assert saved[-1]["actor_role"] == "investigator"
    assert saved[-1]["actor"] != "system"
    assert saved[-1]["payload"]["run_status"] == "cancelled"


@pytest.mark.asyncio
async def test_exporting_a_dossier_is_recorded(audit_client: AsyncClient, monkeypatch):
    """Trước đây tải hồ sơ **không** để lại vết nào — không biết ai đã lấy dữ liệu ra ngoài."""
    case_id, _ = _seed_case("usr_nguoi_xuat")
    monkeypatch.setattr(
        "src.api.investigations.export_markdown",
        lambda store, investigation_id: f"# Hồ sơ {investigation_id}\n",
    )
    response = await audit_client.get(
        f"/api/v1/investigations/{case_id}/export", headers=_headers("usr_nguoi_xuat", "investigator")
    )
    assert response.status_code == 200, response.text

    exported = _rows("dossier_exported", investigation_id=case_id)
    assert exported and exported[0]["actor"] == "usr_nguoi_xuat"
    assert exported[0]["actor_role"] == "investigator"
    payload = exported[0]["payload"]
    assert payload["bytes"] == len(response.text.encode("utf-8"))
    # Hai bộ đếm khác nhau phải ghi rõ nhãn: ``state_version`` đếm số lần lưu trạng thái, còn
    # ``dossier_version`` là bản hồ sơ đã duyệt thật sự rời hệ thống. Gộp chúng vào một khoá
    # ``dossier_version`` khiến người đọc nhật ký tưởng sai bản hồ sơ nào đã bị tải.
    assert payload["state_version"] == get_mvp_store().get_state(case_id).version
    assert payload["dossier_version"] is None  # ca này chưa có hồ sơ duyệt (export bị giả lập)


@pytest.mark.asyncio
async def test_the_export_row_names_the_approved_dossier_revision(audit_client: AsyncClient, monkeypatch):
    """Có hồ sơ duyệt thì ``dossier_version`` phải là số phiên bản **của hồ sơ**, không phải của ca."""
    from src.models.schemas import Dossier

    case_id, _ = _seed_case("usr_nguoi_xuat_that")
    store = get_mvp_store()
    dossier = Dossier(
        dossier_id="DOS-1",
        investigation_id=case_id,
        version=7,
        assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
        summary="Hồ sơ giả lập cho bài kiểm thử nhãn phiên bản.",
    )
    monkeypatch.setattr(store, "approved_dossier", lambda investigation_id: dossier)
    monkeypatch.setattr(
        "src.api.investigations.export_markdown",
        lambda store, investigation_id: f"# Hồ sơ {investigation_id}\n",
    )
    response = await audit_client.get(
        f"/api/v1/investigations/{case_id}/export", headers=_headers("usr_nguoi_xuat_that", "investigator")
    )
    assert response.status_code == 200, response.text
    payload = _rows("dossier_exported", investigation_id=case_id)[0]["payload"]
    assert payload["dossier_version"] == 7
    assert payload["state_version"] != 7


@pytest.mark.asyncio
async def test_a_failed_export_leaves_no_export_row(audit_client: AsyncClient):
    """Chỉ ghi nhật ký khi hồ sơ thật sự ra khỏi hệ thống, không ghi cho lần bị chặn."""
    case_id, _ = _seed_case("usr_nguoi_xuat_hong")
    blocked = await audit_client.get(
        f"/api/v1/investigations/{case_id}/export", headers=_headers("usr_nguoi_xuat_hong", "investigator")
    )
    assert blocked.status_code == 409, blocked.text
    assert _rows("dossier_exported", investigation_id=case_id) == []


def test_role_and_status_changes_are_recorded_with_the_actor_who_made_them(audit_client: AsyncClient):
    """Đổi vai / khoá tài khoản phải trả lời được "ai đã cấp quyền cho ai"."""
    store = get_mvp_store()
    store.create_user(user_id="usr_bi_doi", email="bi-doi@benhvien.test", role="investigator")
    store.update_user(
        "usr_bi_doi", role="reviewer", actor="usr_quan_tri", actor_role="admin"
    )
    store.update_user("usr_bi_doi", status="disabled", actor="usr_quan_tri", actor_role="admin")

    role_rows = _rows("user_role_changed")
    status_rows = _rows("user_status_changed")
    assert role_rows and role_rows[-1]["actor"] == "usr_quan_tri"
    assert role_rows[-1]["actor_role"] == "admin"
    assert role_rows[-1]["payload"] == {"user_id": "usr_bi_doi", "role": "reviewer", "status": None}
    assert status_rows and status_rows[-1]["actor"] == "usr_quan_tri"
    assert status_rows[-1]["payload"]["status"] == "disabled"
    # Không được lẫn người bị đổi với người thực hiện.
    assert role_rows[-1]["actor"] != "usr_bi_doi"


def test_creating_an_account_is_recorded_with_its_creator(audit_client: AsyncClient):
    """Không có tài khoản nào tồn tại mà không rõ ai tạo."""
    store = get_mvp_store()
    store.create_user(
        user_id="usr_moi",
        email="moi@benhvien.test",
        role="investigator",
        created_by="usr_quan_tri",
        actor_role="admin",
    )
    rows = _rows("user_created")
    assert rows and rows[-1]["actor"] == "usr_quan_tri"
    assert rows[-1]["payload"]["user_id"] == "usr_moi"
    assert rows[-1]["payload"]["role"] == "investigator"


@pytest.mark.asyncio
async def test_the_test_provider_labels_its_accounts(audit_client: AsyncClient):
    """Tài khoản do ``X-Test-User`` dựng ra là bản ghi mới, không được dán nhãn ``legacy_actor``."""
    response = await audit_client.get("/api/v1/auth/me", headers=_headers("usr_do_test_dung", "reviewer"))
    assert response.status_code == 200, response.text

    rows = _rows("user_created")
    assert rows, "TestProvider phải để lại vết khi tự dựng tài khoản"
    assert rows[-1]["actor"] == "test-provider"
    assert rows[-1]["actor_role"] == "test"
    assert rows[-1]["legacy_actor"] is False
