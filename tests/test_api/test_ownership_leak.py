"""AUTH-02 — tái hiện hai kịch bản rò rỉ cũ; nay phải thất bại.

Kịch bản 1: gửi lại khoá chống lặp của người khác để nhận **ca của họ**. Trước đây
``investigations.idempotency_key`` là duy nhất toàn cục nên chỉ cần đoán/ăn cắp một khoá là đọc
được ca. Nay khoá chỉ có nghĩa trong phạm vi người tạo.

Kịch bản 2: ``mine_only`` lọc **sau** ``LIMIT`` nên ca cũ biến mất khỏi danh sách khi người dùng
có nhiều ca hơn một trang. Nay bộ lọc nằm trong câu truy vấn, trước ``LIMIT``.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app
from src.models.schemas import ClaimInput, RunStatus

CLAIM = {
    "claim_text": "aspirin gây chảy máu tiêu hoá",
    "drug": "aspirin",
    "event": "chảy máu tiêu hoá",
}

OWNER = "usr_chu_ca"
OUTSIDER = "usr_ngoai_pham_vi"


def _headers(user_id: str, role: str) -> dict[str, str]:
    return {"X-Test-User": f"{user_id}:{role}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def leak_client(monkeypatch, tmp_path):
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "leak.db"))
    async with _client() as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


def _seed_case(created_by: str, *, claim_text: str | None = None) -> str:
    store = get_mvp_store()
    payload = {**CLAIM, "claim_text": claim_text or CLAIM["claim_text"]}
    state, _ = store.create_investigation(ClaimInput(**payload), created_by=created_by)
    store.save_state(state.model_copy(update={"run_status": RunStatus.WAITING_FOR_REVIEW}))
    return state.investigation_id


@pytest.mark.asyncio
async def test_replaying_someone_elses_idempotency_key_is_a_conflict(leak_client: AsyncClient):
    """Khoá chống lặp của người khác ⇒ 409, và **không** trả về mã ca của họ."""
    store = get_mvp_store()
    victim_case, _ = store.create_investigation(
        ClaimInput(**CLAIM), idempotency_key="khoa-cua-nan-nhan", created_by=OWNER
    )

    response = await leak_client.post(
        "/api/v1/investigations",
        json=CLAIM,
        headers={**_headers(OUTSIDER, "investigator"), "Idempotency-Key": "khoa-cua-nan-nhan"},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "idempotency_conflict"
    assert victim_case.investigation_id not in response.text


@pytest.mark.asyncio
async def test_replaying_your_own_key_returns_your_own_case(leak_client: AsyncClient):
    """Cùng người gửi lại khoá của chính mình ⇒ vẫn là ca cũ, ``created=false``."""
    first = await leak_client.post(
        "/api/v1/investigations",
        json=CLAIM,
        headers={**_headers(OWNER, "investigator"), "Idempotency-Key": "khoa-cua-toi"},
    )
    assert first.status_code == 202, first.text
    second = await leak_client.post(
        "/api/v1/investigations",
        json=CLAIM,
        headers={**_headers(OWNER, "investigator"), "Idempotency-Key": "khoa-cua-toi"},
    )
    assert second.status_code == 202, second.text
    assert second.json()["investigation_id"] == first.json()["investigation_id"]
    assert second.json()["created"] is False


@pytest.mark.asyncio
async def test_list_filter_runs_before_limit(leak_client: AsyncClient):
    """Ca cũ không biến mất khi người dùng có nhiều ca hơn một trang."""
    store = get_mvp_store()
    mine = [
        store.create_investigation(
            ClaimInput(**{**CLAIM, "claim_text": f"ca cua toi {index}"}), created_by=OWNER
        )[0].investigation_id
        for index in range(5)
    ]
    # Ca của người khác xen vào giữa, mới hơn — đúng thứ tự từng làm ca cũ bị đẩy khỏi trang.
    for index in range(5):
        store.create_investigation(
            ClaimInput(**{**CLAIM, "claim_text": f"ca cua nguoi khac {index}"}), created_by=OUTSIDER
        )

    seen: list[str] = []
    for offset in (0, 2, 4):
        page = await leak_client.get(
            "/api/v1/investigations",
            params={"limit": 2, "offset": offset, "mine_only": "true"},
            headers=_headers(OWNER, "investigator"),
        )
        assert page.status_code == 200, page.text
        body = page.json()
        assert body["scope"] == "own"
        assert body["total"] == 5
        seen.extend(item["investigation_id"] for item in body["items"])

    assert sorted(seen) == sorted(mine), "Danh sách của chủ ca phải phủ đủ năm ca của chính họ"


@pytest.mark.asyncio
async def test_list_without_mine_only_still_limits_an_own_only_role(leak_client: AsyncClient):
    """Vai chỉ có ``:own`` không thoát được phạm vi bằng cách bỏ ``mine_only``."""
    _seed_case(OUTSIDER)
    response = await leak_client.get(
        "/api/v1/investigations", headers=_headers(OWNER, "investigator")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scope"] == "own"
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_every_read_route_hides_someone_elses_case(leak_client: AsyncClient):
    """Bảy tuyến đọc cũ đều trả 404 cho người ngoài phạm vi."""
    case_id = _seed_case(OWNER)
    headers = _headers(OUTSIDER, "investigator")
    for path in (
        f"/api/v1/investigations/{case_id}",
        f"/api/v1/investigations/{case_id}/events",
        f"/api/v1/investigations/{case_id}/evidence",
        f"/api/v1/investigations/{case_id}/documents/doc-khong-co",
        f"/api/v1/investigations/{case_id}/dossier",
        f"/api/v1/investigations/{case_id}/trace",
        f"/api/v1/investigations/{case_id}/export",
    ):
        response = await leak_client.get(path, headers=headers)
        assert response.status_code == 404, (path, response.text)
        assert response.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_unknown_case_and_forbidden_case_are_indistinguishable(leak_client: AsyncClient):
    """404 cho ca không tồn tại và 404 cho ca của người khác phải giống nhau — nếu không thì
    kẻ tấn công dò được ca nào có thật."""
    case_id = _seed_case(OWNER)
    headers = _headers(OUTSIDER, "investigator")
    forbidden = await leak_client.get(f"/api/v1/investigations/{case_id}", headers=headers)
    missing = await leak_client.get("/api/v1/investigations/INV-khong-ton-tai", headers=headers)
    assert forbidden.status_code == missing.status_code == 404
    assert forbidden.json()["error"]["code"] == missing.json()["error"]["code"]
