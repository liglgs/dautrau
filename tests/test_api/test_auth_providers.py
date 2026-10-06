"""B1.7 mục 5 — chọn nhà cung cấp danh tính theo cấu hình.

Ba điều phải đúng, vì sai một trong ba là hoặc khoá hết người dùng thật, hoặc mở cửa hậu:

1. Thiếu ``SUPABASE_URL`` ⇒ chạy chế độ nội bộ (``local``), không phải chế độ không nhà cung cấp nào.
2. ``TestProvider`` **bị chặn** khi ``app_env=production``, kể cả khi ``VIGILENS_TEST_AUTH=1``.
3. Khoá tĩnh cũ (``INVESTIGATOR_TOKEN``/``REVIEWER_TOKEN``) cũng bị chặn ở production.
"""

from __future__ import annotations

import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.auth import LocalProvider, SupabaseProvider, TestProvider, provider_chain
from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app
from src.models.schemas import ErrorCode
from src.services.errors import MvpError

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


def test_auto_prefers_supabase_but_keeps_local_as_fallback(monkeypatch):
    """``auto`` là chế độ chuyển tiếp: Supabase đứng trước, chế độ nội bộ vẫn là đường lùi.

    Nếu ``auto`` bỏ hẳn chế độ nội bộ thì chỉ cần khai ``SUPABASE_URL`` là mọi phiên nội bộ đang
    chạy bị khoá ra ngoài — đúng thứ đã xảy ra khi thêm biến này vào ``.env``.
    """
    monkeypatch.setenv("AUTH_PROVIDER", "auto")
    monkeypatch.setenv("SUPABASE_URL", "https://vi-du.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    get_settings.cache_clear()
    monkeypatch.setattr("src.api.auth.supabase_provider_ready", lambda: True)
    chain = provider_chain()
    assert isinstance(chain[0], SupabaseProvider)
    assert any(isinstance(provider, LocalProvider) for provider in chain)
    assert [provider.name for provider in chain] == ["supabase", "local"]


def test_auto_skips_supabase_when_the_library_is_missing(monkeypatch):
    """Thiếu PyJWT thì ``auto`` dùng chế độ nội bộ, thay vì dựng nhà cung cấp không chạy được."""
    monkeypatch.setenv("AUTH_PROVIDER", "auto")
    monkeypatch.setenv("SUPABASE_URL", "https://vi-du.supabase.co")
    get_settings.cache_clear()
    monkeypatch.setattr("src.api.auth.supabase_provider_ready", lambda: False)
    assert [provider.name for provider in provider_chain()] == ["local"]


def test_explicit_supabase_mode_is_not_a_fallback(monkeypatch):
    """Khai thẳng ``supabase`` ⇒ chỉ Supabase; thiếu thư viện là lỗi cấu hình, không hạ cấp."""
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://vi-du.supabase.co")
    get_settings.cache_clear()
    monkeypatch.setattr("src.api.auth.supabase_provider_ready", lambda: False)
    assert [provider.name for provider in provider_chain()] == ["supabase"]


def test_explicit_supabase_mode_reports_the_missing_library(monkeypatch):
    """Thiếu PyJWT ⇒ 503 nói rõ nguyên nhân, không phải 401 khiến người dùng tưởng sai mật khẩu."""
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://vi-du.supabase.co")
    get_settings.cache_clear()
    monkeypatch.setitem(sys.modules, "jwt", None)
    with pytest.raises(MvpError) as excinfo:
        SupabaseProvider()._decode("bat-ky")
    assert excinfo.value.status == 503
    assert excinfo.value.code == ErrorCode.UNAVAILABLE


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
async def test_the_legacy_token_needs_an_explicit_opt_in(provider_client: AsyncClient, monkeypatch):
    """Bỏ cờ bật thì khoá tĩnh cũ **không** chạy, dù môi trường chỉ là phát triển.

    Trước đây nhánh này chỉ chặn ở ``APP_ENV=production``: một bản triển khai quên đặt ``APP_ENV``
    mang mặc định ``development``, nên khoá dùng chung cũ tự sống lại. Nay phải bật tường minh.
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "khoa-tam")
    monkeypatch.setenv("VIGILENS_ALLOW_LEGACY_TOKENS", "0")
    get_settings.cache_clear()
    response = await provider_client.get(
        "/api/v1/investigations", headers={"X-API-Token": "khoa-tam"}
    )
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_the_legacy_token_works_when_it_is_deliberately_enabled(provider_client: AsyncClient, monkeypatch):
    """Bật cờ ở môi trường phát triển thì nhánh cũ vẫn dùng được — đây là đường chạy ngoại tuyến."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "khoa-tam")
    monkeypatch.setenv("VIGILENS_ALLOW_LEGACY_TOKENS", "1")
    get_settings.cache_clear()
    response = await provider_client.get(
        "/api/v1/investigations", headers={"X-API-Token": "khoa-tam"}
    )
    assert response.status_code == 200, response.text
    me = await provider_client.get("/api/v1/auth/me", headers={"X-API-Token": "khoa-tam"})
    assert me.json()["auth_method"] == "legacy_token"


def test_using_a_legacy_token_is_visible_in_the_log(caplog, monkeypatch):
    """Khoá dùng chung xác thực được một yêu cầu thì phải để lại cảnh báo, không im lặng."""
    import logging

    from src.api import auth as auth_module
    from src.api.auth import _legacy_static_token
    from src.config import get_settings

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "khoa-tam")
    monkeypatch.setenv("VIGILENS_ALLOW_LEGACY_TOKENS", "1")
    get_settings.cache_clear()
    auth_module._legacy_warning_emitted[0] = False  # noqa: SLF001 - cờ một lần, phải đặt lại để kiểm
    try:
        with caplog.at_level(logging.WARNING, logger="src.api.auth"):
            assert _legacy_static_token("khoa-tam") is not None
            assert _legacy_static_token("khong-khop") is None
        warnings = [r for r in caplog.records if "Khoá tĩnh dùng chung" in r.message]
        assert len(warnings) == 1, "cảnh báo chỉ một lần cho mỗi tiến trình"
    finally:
        get_settings.cache_clear()


def test_an_environment_that_is_not_development_is_treated_as_production():
    """``is_production_like`` là chốt chặn cuối: chỉ ``development``/``test`` mới là ngoài production."""
    from src.config import Settings

    assert Settings(app_env="development").is_production_like is False
    assert Settings(app_env="test").is_production_like is False
    assert Settings(app_env="production").is_production_like is True


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
