"""Kiểm thử Cookie Session, đăng nhập, đăng xuất và phân quyền Ownership (Người 2)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth import SESSION_COOKIE_NAME
from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app

CLAIM = {
    "claim_text": "aspirin causes gastrointestinal bleeding",
    "drug": "aspirin",
    "event": "gastrointestinal bleeding",
}


@pytest_asyncio.fixture
async def auth_client(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "test-inv-token")
    monkeypatch.setenv("REVIEWER_TOKEN", "test-rev-token")
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "auth_test.db"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_auth_login_sets_cookie_and_me_reads_it(auth_client: AsyncClient):
    """Đăng nhập bằng token, nhận cookie session HttpOnly và gọi /me."""
    # 1. Đăng nhập với token investigator
    res = await auth_client.post("/api/v1/auth/login", json={"token": "test-inv-token", "username": "alice"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "investigator"
    assert data["user_id"] == "alice"
    assert SESSION_COOKIE_NAME in res.cookies

    # 2. Gọi /me dùng session cookie đã lưu trong client
    res_me = await auth_client.get("/api/v1/auth/me")
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["user_id"] == "alice"
    assert me_data["role"] == "investigator"

    # 3. Đăng xuất
    res_logout = await auth_client.post("/api/v1/auth/logout")
    assert res_logout.status_code == 200
    assert res_logout.json()["logged_out"] is True

    # 4. Gọi lại /me sau khi logout -> 401
    res_me_after = await auth_client.get("/api/v1/auth/me")
    assert res_me_after.status_code == 401


@pytest.mark.asyncio
async def test_ownership_enforcement_on_cancel(auth_client: AsyncClient, monkeypatch, tmp_path):
    """Kiểm tra phân quyền: Người A tạo ca, Người B không được hủy; Reviewer được hủy."""
    # Tạo client riêng cho Alice
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as alice_client:
        await alice_client.post("/api/v1/auth/login", json={"token": "test-inv-token", "username": "alice"})
        # Alice tạo investigation
        create_res = await alice_client.post("/api/v1/investigations", json=CLAIM)
        assert create_res.status_code == 202
        inv_id = create_res.json()["investigation_id"]

    # Bob đăng nhập trên client khác
    async with AsyncClient(transport=transport, base_url="http://test") as bob_client:
        await bob_client.post("/api/v1/auth/login", json={"token": "test-inv-token", "username": "bob"})

        # Bob cố gắng hủy cuộc điều tra của Alice -> 403 Forbidden
        cancel_res = await bob_client.post(f"/api/v1/investigations/{inv_id}/cancel")
        assert cancel_res.status_code == 403
        assert "không có quyền" in cancel_res.json()["error"]["message"]

    # Reviewer đăng nhập
    async with AsyncClient(transport=transport, base_url="http://test") as rev_client:
        await rev_client.post("/api/v1/auth/login", json={"token": "test-rev-token", "username": "dr-reviewer"})

        # Reviewer hủy cuộc điều tra của Alice -> thành công!
        cancel_res = await rev_client.post(f"/api/v1/investigations/{inv_id}/cancel")
        assert cancel_res.status_code == 200
        assert cancel_res.json()["cancelled"] is True
        assert cancel_res.json()["run_status"] == "cancelled"


@pytest.mark.asyncio
async def test_backward_compatibility_with_headers(auth_client: AsyncClient):
    """Đảm bảo các request truyền X-API-Token hoặc Authorization: Bearer vẫn hoạt động bình thường."""
    # Dùng header X-API-Token
    res = await auth_client.get("/api/v1/investigations", headers={"X-API-Token": "test-inv-token"})
    assert res.status_code == 200

    # Dùng header Authorization Bearer
    res_bearer = await auth_client.get("/api/v1/investigations", headers={"Authorization": "Bearer test-rev-token"})
    assert res_bearer.status_code == 200
