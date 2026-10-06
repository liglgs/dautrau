"""``scripts/auth_cli.py`` — cấp khoá máy và di trú tài khoản cũ (B1.4, B1.9)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from src.api.auth import SESSION_COOKIE_NAME
from src.api.mvp_runtime import configure_mvp, get_mvp_store, reset_mvp
from src.config import get_settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli_store(monkeypatch, tmp_path):
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "auth_cli.db"))
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "auth_cli.db"))
    yield get_mvp_store()
    reset_mvp()
    get_settings.cache_clear()


def _run(*argv: str) -> int:
    from scripts.auth_cli import main

    return main(list(argv))


def test_issue_token_prints_the_raw_key_once_and_stores_only_the_hash(cli_store, capsys):
    """Khoá thô chỉ hiện một lần; trong cơ sở dữ liệu chỉ có bản băm."""
    cli_store.create_user(user_id="svc_etl", email="etl@benhvien.test", role="service")

    assert _run("issue-token", "--user-id", "svc_etl", "--label", "nạp định kỳ") == 0
    printed = capsys.readouterr().out
    raw = next(line.strip() for line in printed.splitlines() if line.strip().startswith("vln_"))
    assert raw.startswith("vln_")

    with cli_store._lock:  # noqa: SLF001 - khẳng định đúng điều quan trọng: không có khoá thô
        stored = [
            row[0]
            for row in cli_store._conn.execute("SELECT token_hash FROM api_tokens").fetchall()  # noqa: SLF001
        ]
    assert stored and raw not in stored
    assert cli_store.resolve_token(raw)["user_id"] == "svc_etl"
    assert cli_store.resolve_token(raw + "x") is None


def test_issue_token_refuses_a_non_service_account(cli_store, capsys):
    cli_store.create_user(user_id="usr_bs", email="bs@benhvien.test", role="reviewer")
    assert _run("issue-token", "--user-id", "usr_bs") == 2
    assert "chỉ cấp cho vai 'service'" in capsys.readouterr().err


def test_issue_token_refuses_an_unknown_account(cli_store, capsys):
    assert _run("issue-token", "--user-id", "khong-ton-tai") == 2
    assert "Không có tài khoản" in capsys.readouterr().err


def test_create_user_can_hash_a_password(cli_store, capsys):
    from src.api.auth import _verify_password

    assert (
        _run(
            "create-user",
            "--user-id",
            "usr_moi",
            "--email",
            "moi@benhvien.test",
            "--role",
            "investigator",
            "--password",
            "mat-khau-rat-dai",
        )
        == 0
    )
    user = cli_store.get_user("usr_moi")
    assert user["role"] == "investigator"
    assert _verify_password("mat-khau-rat-dai", user["password_hash"])
    assert not _verify_password("sai", user["password_hash"])


def test_create_user_refuses_a_duplicate(cli_store, capsys):
    cli_store.create_user(user_id="usr_trung", email="trung@benhvien.test", role="reviewer")
    assert _run("create-user", "--user-id", "usr_trung", "--email", "khac@benhvien.test", "--role", "reviewer") == 2
    assert "đã tồn tại" in capsys.readouterr().err


def test_list_users_prints_the_role_table(cli_store, capsys):
    cli_store.create_user(user_id="usr_a", email="a@benhvien.test", role="investigator")
    cli_store.create_user(user_id="usr_b", email="b@benhvien.test", role="investigator")
    cli_store.create_user(user_id="usr_c", email="c@benhvien.test", role="reviewer")
    assert _run("list-users") == 0
    printed = capsys.readouterr().out
    assert "Số tài khoản theo vai" in printed
    assert "investigator" in printed and "reviewer" in printed


def test_migrate_legacy_maps_roles_and_is_idempotent(cli_store, monkeypatch, capsys):
    """Ánh xạ ``responder``/``clinician`` → ``investigator``/``reviewer``, và chạy lại không đổi gì."""
    legacy = [
        {"id": "u1", "name": "Người một", "role": "responder"},
        {"id": "u2", "name": "Người hai", "role": "clinician"},
        {"id": "u3", "name": "Người ba", "role": "reviewer"},
        {"id": "u4", "name": "Người bốn", "role": "vai-la"},
    ]
    monkeypatch.setattr("scripts.auth_cli._legacy_rows", lambda: legacy)

    assert _run("migrate-legacy") == 0
    first = capsys.readouterr().out
    assert "Tạo mới: 3" in first
    assert "Vai không có trong bảng ánh xạ (bỏ qua): vai-la" in first
    assert cli_store.get_user("u1")["role"] == "investigator"
    assert cli_store.get_user("u2")["role"] == "reviewer"
    assert cli_store.get_user("u3")["role"] == "reviewer"
    assert cli_store.get_user("u4") is None
    # Băm mật khẩu không xuất được ⇒ không tài khoản di trú nào có mật khẩu.
    assert all(cli_store.get_user(user_id)["password_hash"] is None for user_id in ("u1", "u2", "u3"))

    assert _run("migrate-legacy") == 0
    second = capsys.readouterr().out
    assert "Tạo mới: 0" in second
    assert len(cli_store.list_users(limit=100)) == 3


def test_migrate_legacy_dry_run_writes_nothing(cli_store, monkeypatch, capsys):
    monkeypatch.setattr(
        "scripts.auth_cli._legacy_rows",
        lambda: [{"id": "u1", "name": "Người một", "role": "responder"}],
    )
    assert _run("migrate-legacy", "--dry-run") == 0
    printed = capsys.readouterr().out
    assert "Tạo mới: 1" in printed
    assert "Chế độ --dry-run" in printed
    assert cli_store.list_users(limit=100) == []


def test_migrate_legacy_reports_an_unreadable_source(cli_store, monkeypatch, capsys):
    monkeypatch.setattr("scripts.auth_cli._legacy_rows", lambda: None)
    assert _run("migrate-legacy") == 2
    assert cli_store.list_users(limit=100) == []


def test_session_cookie_name_is_stable(cli_store):
    """Tên cookie là một phần giao kèo với cầu nối frontend; đổi tên là đổi giao kèo."""
    assert SESSION_COOKIE_NAME == "session_id"


def test_runs_as_a_file_path_not_only_as_a_module(tmp_path):
    """Tài liệu hướng dẫn gọi ``python scripts/auth_cli.py ...``; dạng đó phải chạy được.

    Trước đây chỉ ``python -m scripts.auth_cli`` mới chạy, còn dạng tệp thì lỗi
    ``ModuleNotFoundError: No module named 'src'`` — đúng dạng mà tài liệu bảo người vận hành dùng.
    """
    import subprocess

    env = {
        **os.environ,
        "APP_ENV": "development",
        "MVP_DB_PATH": str(tmp_path / "cli-path.sqlite3"),
        "AUTH_PROVIDER": "local",
        "SUPABASE_URL": "",
    }
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "auth_cli.py"), "list-users"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "ModuleNotFoundError" not in result.stderr
    assert "app_users" in result.stdout


# --------------------------------------------------------------------------------------
# B1.7 mục 3 — thao tác qua CLI cũng phải truy được ai làm
# --------------------------------------------------------------------------------------


def _rows(store, action: str) -> list[dict]:
    return [row for row in store.list_audit(limit=500) if row["action"] == action]


def test_create_user_is_audited_with_the_cli_identity(cli_store, capsys):
    """Tài khoản do CLI tạo không được mang nhãn ``legacy_actor`` — đây là bản ghi mới, không phải dữ liệu cũ."""
    assert _run("create-user", "--user-id", "usr_cli", "--email", "cli@benhvien.test", "--role", "reviewer") == 0
    rows = _rows(cli_store, "user_created")
    assert rows, "tạo tài khoản qua CLI phải để lại vết"
    assert rows[-1]["actor"].startswith("cli:")
    assert rows[-1]["actor_role"] == "cli"
    assert rows[-1]["legacy_actor"] is False
    assert rows[-1]["payload"]["user_id"] == "usr_cli"
