import json

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app


def test_deployment_probe_checks_review_export_and_citation_after_reopen(monkeypatch, tmp_path):
    from scripts.mvp_deployment_smoke import check_investigation, check_new_investigation, session_headers

    monkeypatch.setenv("INVESTIGATOR_TOKEN", "smoke-investigator")
    monkeypatch.setenv("REVIEWER_TOKEN", "smoke-reviewer")
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "mvp.sqlite3"))
    get_settings.cache_clear()
    reset_mvp()
    try:
        with TestClient(app) as client:
            investigator = session_headers(client, "smoke-investigator", origin="http://testserver")
            reviewer = session_headers(client, "smoke-reviewer", origin="http://testserver")
            result = check_new_investigation(client, "/api/v1", investigator, reviewer, timeout=10)
            assert result["evidence_count"] >= 2
            assert result["export_bytes"] > 0
            reset_mvp()
            configure_mvp(str(tmp_path / "mvp.sqlite3"))
            assert check_investigation(client, "/api/v1", investigator, result["investigation_id"]) == result
            client.cookies.clear()
            with pytest.raises(AssertionError, match="expected 200"):
                check_investigation(client, "/api/v1", {"X-API-Token": "wrong"}, result["investigation_id"])
    finally:
        reset_mvp()
        get_settings.cache_clear()


def test_proxy_sessions_keep_roles_separate_and_send_origin():
    from scripts.mvp_deployment_smoke import session_headers

    def handle(request):
        assert request.headers["Origin"] == "http://127.0.0.1:3100"
        if request.url.path.endswith("/auth/login"):
            role = json.loads(request.content)["token"]
            return httpx.Response(200, headers={"Set-Cookie": f"session_id={role}; Path=/; HttpOnly"})
        return httpx.Response(200, json={"cookie": request.headers["Cookie"]})

    with httpx.Client(base_url="http://127.0.0.1:3100/api/backend", transport=httpx.MockTransport(handle)) as client:
        investigator = session_headers(client, "investigator", origin="http://127.0.0.1:3100")
        reviewer = session_headers(client, "reviewer", origin="http://127.0.0.1:3100")
        assert client.get("/api/v1/auth/me", headers=investigator).json()["cookie"] == "session_id=investigator"
        assert client.get("/api/v1/auth/me", headers=reviewer).json()["cookie"] == "session_id=reviewer"


def test_proxy_login_requires_a_session_cookie():
    from scripts.mvp_deployment_smoke import session_headers

    with httpx.Client(base_url="http://proxy", transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        with pytest.raises(AssertionError, match="session cookie"):
            session_headers(client, "token", origin="http://proxy")
