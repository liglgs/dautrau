"""AUTH-01 — bốn bài bắt buộc của B1.7 mục 1, tất cả qua điểm cuối HTTP thật.

Mọi bài ở đây đi qua ``ASGITransport`` và gọi tuyến thật. Không bài nào gọi thẳng hàm nội bộ,
vì lỗi cũ nằm đúng ở chỗ: hàm nội bộ đúng nhưng tuyến lại tin dữ liệu người gọi khai.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth import SESSION_COOKIE_NAME, hash_password
from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings
from src.main import app

PASSWORD = "mat-khau-kiem-thu-01"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture
async def hardening_client(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "inv-token")
    monkeypatch.setenv("REVIEWER_TOKEN", "rev-token")
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "hardening.db"))
    store = get_mvp_store()
    store.create_user(
        user_id="usr_active",
        email="active@benhvien.test",
        role="investigator",
        display_name="Người dùng đang hoạt động",
        password_hash=hash_password(PASSWORD),
    )
    store.create_user(
        user_id="usr_locked",
        email="locked@benhvien.test",
        role="reviewer",
        display_name="Người dùng bị khoá",
        password_hash=hash_password(PASSWORD),
    )
    store.update_user("usr_locked", status="disabled")
    async with _client() as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_login_without_credential_is_rejected(hardening_client: AsyncClient):
    """Thiếu credential ⇒ 422 (thiếu trường) chứ không phải một phiên mới."""
    response = await hardening_client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    assert SESSION_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_login_with_self_declared_role_is_rejected(hardening_client: AsyncClient):
    """Bài gốc của AUTH-01: khai ``role`` (hoặc ``user_id``) không được cấp phiên."""
    for body in (
        {"role": "reviewer"},
        {"user_id": "reviewer"},
        {"email": "active@benhvien.test", "password": PASSWORD, "role": "reviewer"},
        {"email": "active@benhvien.test", "password": PASSWORD, "user_id": "usr_khac"},
    ):
        response = await hardening_client.post("/api/v1/auth/login", json=body)
        assert response.status_code == 422, (body, response.text)
        assert SESSION_COOKIE_NAME not in response.cookies


@pytest.mark.asyncio
async def test_disabled_account_token_is_rejected(hardening_client: AsyncClient):
    """Khoá hợp lệ nhưng tài khoản đã bị khoá ⇒ 401, không phải danh tính dùng được."""
    store = get_mvp_store()
    from src.services.identity import generate_token

    raw = generate_token()
    store.issue_token(user_id="usr_locked", raw_token=raw, label="khoá của người đã bị khoá")
    headers = {"X-API-Token": raw}
    assert (await hardening_client.get("/api/v1/investigations", headers=headers)).status_code == 401

    # Đăng nhập bằng mật khẩu cũng bị chặn vì trạng thái tài khoản, không chỉ vì mật khẩu.
    login = await hardening_client.post(
        "/api/v1/auth/login", json={"email": "locked@benhvien.test", "password": PASSWORD}
    )
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_cookie_is_secure_when_app_env_is_production(monkeypatch, tmp_path):
    """``SESSION_COOKIE_SECURE`` bật ⇒ cookie phiên mang cờ ``Secure``."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "1")
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "prod.db"))
    get_settings.cache_clear()
    reset_mvp()
    try:
        configure_mvp(str(tmp_path / "prod.db"))
        store = get_mvp_store()
        store.create_user(
            user_id="usr_prod",
            email="prod@benhvien.test",
            role="investigator",
            display_name="Người dùng production",
            password_hash=hash_password(PASSWORD),
        )
        async with _client() as client:
            response = await client.post(
                "/api/v1/auth/login", json={"email": "prod@benhvien.test", "password": PASSWORD}
            )
            assert response.status_code == 200, response.text
            set_cookie = response.headers["set-cookie"]
            assert "Secure" in set_cookie
            assert "HttpOnly" in set_cookie
            assert "SameSite=lax" in set_cookie.replace("samesite", "SameSite")
    finally:
        reset_mvp()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_browser_chosen_role_header_changes_nothing(hardening_client: AsyncClient):
    """Đổi ``X-Vigilens-Role`` không đổi quyền: vai chỉ đến từ credential đã xác minh."""
    response = await hardening_client.post(
        "/api/v1/investigations",
        json={"claim_text": "aspirin gây chảy máu", "drug": "aspirin", "event": "chảy máu"},
        headers={"X-Vigilens-Role": "reviewer", "Idempotency-Key": "ke-gia-danh"},
    )
    assert response.status_code == 401

    me = await hardening_client.get("/api/v1/auth/me", headers={"X-Vigilens-Role": "admin"})
    assert me.status_code == 401
