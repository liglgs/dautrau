"""``scripts/mvp_seed_users.py`` — tài khoản khởi động cho stack docker compose.

Vì sao phải có bài kiểm thử này: sau AUTH-01, nếu script nạp tài khoản im lặng làm sai thì
``docker compose up`` cho ra một giao diện **không ai đăng nhập được**, mà lỗi lại không hiện ở
đâu cả. Ba điều phải đúng:

1. Chạy idempotent — chạy lại không ghi đè mật khẩu đang dùng.
2. Từ chối chạy ở ``APP_ENV=production``.
3. Không nạp tài khoản nào khi biến môi trường chưa được đặt.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _module():
    spec = importlib.util.spec_from_file_location("mvp_seed_users", ROOT / "scripts" / "mvp_seed_users.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mvp_seed_users"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def seeded(monkeypatch, tmp_path):
    """Store SQLite riêng cho mỗi bài, không đụng ``data/mvp.sqlite3`` của máy phát triển."""
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "seed.sqlite3"))
    monkeypatch.setenv("APP_ENV", "development")
    from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp

    reset_mvp()
    configure_mvp(str(tmp_path / "seed.sqlite3"))
    try:
        yield get_mvp_store()
    finally:
        reset_mvp()


def _set(monkeypatch, role: str, email: str, password: str) -> None:
    prefix = f"MVP_BOOTSTRAP_{role.upper()}"
    monkeypatch.setenv(f"{prefix}_EMAIL", email)
    monkeypatch.setenv(f"{prefix}_PASSWORD", password)


def test_creates_the_three_accounts_with_hashed_passwords(monkeypatch, seeded):
    module = _module()
    _set(monkeypatch, "investigator", "dieutra@benhvien.vn", "mat-khau-dieu-tra")
    _set(monkeypatch, "reviewer", "duyet@benhvien.vn", "mat-khau-duyet")
    _set(monkeypatch, "admin", "quantri@benhvien.vn", "mat-khau-quan-tri")

    assert module.main([]) == 0

    from src.api.auth import _verify_password

    expected = (
        ("usr_dieu_tra", "investigator", "mat-khau-dieu-tra"),
        ("usr_duyet", "reviewer", "mat-khau-duyet"),
        ("usr_quan_tri", "admin", "mat-khau-quan-tri"),
    )
    for user_id, role, password in expected:
        user = seeded.get_user(user_id)
        assert user is not None, user_id
        assert user["role"] == role
        assert user["status"] == "active"
        assert user["password_hash"] != password
        assert _verify_password(password, user["password_hash"])


def test_is_idempotent_and_does_not_overwrite_a_changed_password(monkeypatch, seeded):
    module = _module()
    _set(monkeypatch, "reviewer", "duyet@benhvien.vn", "mat-khau-ban-dau")
    assert module.main([]) == 0

    from src.api.auth import _verify_password, hash_password

    seeded.update_user("usr_duyet", password_hash=hash_password("mat-khau-doi-sau"))
    _set(monkeypatch, "reviewer", "duyet@benhvien.vn", "mat-khau-ban-dau")
    assert module.main([]) == 0

    user = seeded.get_user("usr_duyet")
    assert _verify_password("mat-khau-doi-sau", user["password_hash"])
    assert not _verify_password("mat-khau-ban-dau", user["password_hash"])
    assert len([row for row in seeded.list_users() if row["role"] == "reviewer"]) == 1


def test_creates_nothing_when_no_variable_is_set(monkeypatch, seeded):
    module = _module()
    assert module.main([]) == 0
    assert seeded.list_users() == []


def test_refuses_production(monkeypatch, seeded):
    module = _module()
    monkeypatch.setenv("APP_ENV", "production")
    from src.config import get_settings

    get_settings.cache_clear()
    _set(monkeypatch, "reviewer", "duyet@benhvien.vn", "mat-khau-duyet")
    try:
        assert module.main([]) == 2
        assert seeded.list_users() == []
    finally:
        get_settings.cache_clear()


def test_refuses_a_half_configured_role(monkeypatch, seeded):
    module = _module()
    monkeypatch.setenv("MVP_BOOTSTRAP_REVIEWER_EMAIL", "duyet@benhvien.vn")
    monkeypatch.delenv("MVP_BOOTSTRAP_REVIEWER_PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        module.main([])
    assert seeded.list_users() == []


def test_empty_strings_count_as_unset(monkeypatch, seeded):
    module = _module()
    monkeypatch.setenv("MVP_BOOTSTRAP_REVIEWER_EMAIL", "")
    monkeypatch.setenv("MVP_BOOTSTRAP_REVIEWER_PASSWORD", "")
    assert module.main([]) == 0
    assert seeded.list_users() == []


def test_never_reads_the_legacy_static_tokens(monkeypatch, seeded):
    """Khoá tĩnh cũ không được dùng làm mật khẩu khởi động — chúng không phải mật khẩu của ai."""
    module = _module()
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "dev-investigator")
    monkeypatch.setenv("REVIEWER_TOKEN", "dev-reviewer")
    assert module.main([]) == 0
    assert seeded.list_users() == []


def test_password_never_comes_from_the_command_line(monkeypatch, seeded):
    """Mật khẩu chỉ đọc từ biến môi trường: tham số dòng lệnh lọt vào lịch sử shell."""
    module = _module()
    source = (ROOT / "scripts" / "mvp_seed_users.py").read_text()
    assert 'add_argument("--password' not in source
    assert module.main([]) == 0


def test_environment_variable_names_match_the_compose_file(monkeypatch, seeded):
    """Tên biến phải khớp ``docker-compose.mvp.yml``, nếu không stack dựng lên sẽ trống tài khoản."""
    compose = (ROOT / "docker-compose.mvp.yml").read_text()
    for prefix, _, _ in _module().ROLES:
        assert f"{prefix}_EMAIL" in compose, prefix
        assert f"{prefix}_PASSWORD" in compose, prefix
