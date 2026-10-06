"""B1.7 mục 5 — chọn nhà cung cấp danh tính theo cấu hình.

Ba điều phải đúng, vì sai một trong ba là hoặc khoá hết người dùng thật, hoặc mở cửa hậu:

1. Thiếu ``SUPABASE_URL`` ⇒ chạy chế độ nội bộ (``local``), không phải chế độ không nhà cung cấp nào.
2. ``TestProvider`` **bị chặn** khi ``app_env=production``, kể cả khi ``VIGILENS_TEST_AUTH=1``.
3. Khoá tĩnh cũ (``INVESTIGATOR_TOKEN``/``REVIEWER_TOKEN``) cũng bị chặn ở production.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth import LocalProvider, SupabaseProvider, TestProvider, provider_chain
from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app

SUPABASE_ENV_KEYS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")


@pytest.fixture(autouse=True)
def _clean_settings(monkeypatch):
    # Ghim rỗng chứ không chỉ xoá: pydantic-settings đọc thẳng tệp ``.env`` của máy phát triển.
    for key in SUPABASE_ENV_KEYS:
        monkeypatch.setenv(key, "")
    monkeypatch.delenv("VIGILENS_TEST_AUTH", raising=False)
    monkeypatch.delenv("AUTH_PROVIDER", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _names() -> list[str]:
    return [provider.name for provider in provider_chain()]


def test_local_is_the_default_without_supabase_url(monkeypatch):
    """Chế độ ``auto`` mà không có ``SUPABASE_URL`` ⇒ chuỗi có ``local``, không có ``supabase``."""
    monkeypatch.setenv("AUTH_PROVIDER", "auto")
    get_settings.cache_clear()
    assert "local" in _names()
    assert "supabase" not in _names()
    assert isinstance(provider_chain()[0], LocalProvider)


def test_supabase_url_switches_auto_to_supabase(monkeypatch):
    """Có ``SUPABASE_URL`` ⇒ ``auto`` chọn Supabase thay cho chế độ nội bộ."""
    monkeypatch.setenv("AUTH_PROVIDER", "auto")
    monkeypatch.setenv("SUPABASE_URL", "https://vi-du.supabase.co")
    get_settings.cache_clear()
    chain = provider_chain()
    assert isinstance(chain[0], SupabaseProvider)
    assert not any(isinstance(provider, LocalProvider) for provider in chain)


def test_explicit_local_ignores_supabase_url(monkeypatch):
    """Chọn thẳng ``local`` thì ``SUPABASE_URL`` không chen vào được."""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("SUPABASE_URL", "https://vi-du.supabase.co")
    get_settings.cache_clear()
    assert isinstance(provider_chain()[0], LocalProvider)
    assert "supabase" not in _names()


def test_test_mode_has_no_local_provider(monkeypatch):
    """``AUTH_PROVIDER=test`` ⇒ chỉ có ``TestProvider``; không âm thầm mở chế độ nội bộ."""
    monkeypatch.setenv("AUTH_PROVIDER", "test")
    monkeypatch.setenv("VIGILENS_TEST_AUTH", "1")
    get_settings.cache_clear()
    assert _names() == ["test"]


def test_test_provider_is_appended_only_when_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    get_settings.cache_clear()
    assert _names() == ["local"]
    monkeypatch.setenv("VIGILENS_TEST_AUTH", "1")
    get_settings.cache_clear()
    assert _names() == ["local", "test"]


def test_test_provider_is_never_appended_in_production(monkeypatch):
    """Bật cờ thử nghiệm ở production cũng không có tác dụng — đây là hàng rào cứng."""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("VIGILENS_TEST_AUTH", "1")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    assert _names() == ["local"]


@pytest_asyncio.fixture
async def provider_client(monkeypatch, tmp_path):
    reset_mvp()
    configure_mvp(str(tmp_path / "providers.db"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_production_rejects_the_test_header(provider_client: AsyncClient, monkeypatch):
    """``X-Test-User`` ở production ⇒ 401, dù cờ thử nghiệm có bật."""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("VIGILENS_TEST_AUTH", "1")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    response = await provider_client.get(
        "/api/v1/investigations", headers={"X-Test-User": "usr_ke_tan_cong:admin"}
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_production_rejects_the_legacy_static_token(provider_client: AsyncClient, monkeypatch):
    """Khoá tĩnh cũ là khoá tạm của giai đoạn ngoại tuyến; ở production phải là 401."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "khoa-tam")
    get_settings.cache_clear()
    response = await provider_client.get(
        "/api/v1/investigations", headers={"X-API-Token": "khoa-tam"}
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_test_header_works_outside_production(provider_client: AsyncClient, monkeypatch):
    """Ngoài production, với cờ bật, ``X-Test-User`` dựng được danh tính — đây là đường kiểm thử."""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    monkeypatch.setenv("VIGILENS_TEST_AUTH", "1")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    response = await provider_client.get(
        "/api/v1/auth/me", headers={"X-Test-User": "usr_kiem_thu:reviewer"}
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "user_id": "usr_kiem_thu",
        "email": "usr_kiem_thu@test.local",
        "display_name": "usr_kiem_thu",
        "role": "reviewer",
        "auth_method": "test",
    }


@pytest.mark.asyncio
async def test_unknown_credential_is_401_not_500(provider_client: AsyncClient, monkeypatch):
    """Khoá lạ đúng dạng ``vln_`` ⇒ 401 rõ ràng, không rơi vào lỗi máy chủ."""
    monkeypatch.setenv("AUTH_PROVIDER", "local")
    get_settings.cache_clear()
    response = await provider_client.get(
        "/api/v1/investigations", headers={"X-API-Token": "vln_khong-he-ton-tai-tren-he-thong-nay"}
    )
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_test_provider_verify_refuses_in_production_directly(monkeypatch):
    """Gọi thẳng ``TestProvider.verify`` ở production cũng phải ném 401 — không chỉ dựa vào chuỗi."""
    from src.services.errors import MvpError

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("VIGILENS_TEST_AUTH", "1")
    get_settings.cache_clear()

    class _Request:
        headers = {"X-Test-User": "usr_ke_tan_cong:admin"}

    with pytest.raises(MvpError) as excinfo:
        TestProvider().verify(_Request())  # type: ignore[arg-type]
    assert excinfo.value.status == 401
