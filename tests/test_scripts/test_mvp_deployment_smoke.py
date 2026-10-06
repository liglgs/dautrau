import pytest
from fastapi.testclient import TestClient

from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app


def test_deployment_probe_checks_review_export_and_citation_after_reopen(monkeypatch, tmp_path):
    from scripts.mvp_deployment_smoke import (
        check_auth_hardening,
        check_investigation,
        check_new_investigation,
        role_headers,
    )

    monkeypatch.setenv("INVESTIGATOR_TOKEN", "smoke-investigator")
    monkeypatch.setenv("REVIEWER_TOKEN", "smoke-reviewer")
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "mvp.sqlite3"))
    get_settings.cache_clear()
    reset_mvp()
    try:
        with TestClient(app) as client:
            assert check_auth_hardening(client, "/api/v1", origin="http://testserver") == {
                "self_declared_role_rejected": True,
                "anonymous_read_rejected": True,
            }
            investigator = role_headers("smoke-investigator", origin="http://testserver")
            reviewer = role_headers("smoke-reviewer", origin="http://testserver")
            result = check_new_investigation(client, "/api/v1", investigator, reviewer, timeout=10)
            assert result["evidence_count"] >= 2
            assert result["export_bytes"] > 0
            reset_mvp()
            configure_mvp(str(tmp_path / "mvp.sqlite3"))
            assert check_investigation(client, "/api/v1", investigator, result["investigation_id"]) == result
            with pytest.raises(AssertionError, match="expected 200"):
                check_investigation(client, "/api/v1", {"X-API-Token": "wrong"}, result["investigation_id"])
    finally:
        reset_mvp()
        get_settings.cache_clear()


def test_role_headers_carry_the_static_token_and_the_origin():
    """AUTH-01: bộ kiểm tra triển khai không còn đăng nhập bằng vai tự khai."""
    from scripts.mvp_deployment_smoke import role_headers

    headers = role_headers("khoa-tinh", origin="http://127.0.0.1:3100")
    assert headers == {"X-API-Token": "khoa-tinh", "Origin": "http://127.0.0.1:3100"}


def test_auth_hardening_rejects_a_self_declared_role():
    from scripts.mvp_deployment_smoke import check_auth_hardening

    seen: list[tuple[str, object]] = []

    class FakeResponse:
        def __init__(self, status_code: int, payload=None):
            self.status_code = status_code
            self._payload = payload
            self.text = "{}"
            self.cookies: dict[str, str] = {}

        def json(self):
            return self._payload

    class FakeClient:
        def post(self, url, *, headers, json):
            seen.append((url, json))
            return FakeResponse(422)

        def get(self, url, *, headers):
            seen.append((url, None))
            return FakeResponse(401)

    result = check_auth_hardening(FakeClient(), "/api/v1", origin="http://proxy")
    assert result == {"self_declared_role_rejected": True, "anonymous_read_rejected": True}
    assert seen[0][1] == {"role": "reviewer"}
    assert seen[1][1] == {"token": "bat-ky", "username": "ke-gia-danh"}
    assert seen[2][0] == "/api/v1/investigations"
