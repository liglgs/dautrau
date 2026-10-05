"""Check the local fixture deployment through the VigiLens server proxy; no LLM calls."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

CLAIM = {
    "claim_text": "Investigate metformin and lactic acidosis in adults with renal impairment.",
    "drug": "metformin",
    "event": "lactic acidosis",
    "population": "adults with renal impairment",
    "route": "oral",
}


def _request(client, prefix, method, path, headers, *, expected=200, **kwargs):
    response = client.request(method, prefix + path, headers=headers, **kwargs)
    assert response.status_code == expected, f"{method} {path}: expected {expected}, got {response.status_code}"
    return response


def session_headers(client, token, *, origin):
    """Log in through the proxy and keep each role's cookie independent of the jar."""
    response = _request(client, "/api/v1", "POST", "/auth/login", {"Origin": origin}, json={"token": token})
    cookie = response.cookies.get("session_id")
    assert cookie, "Login did not return a session cookie"
    return {"Cookie": f"session_id={cookie}", "Origin": origin}


def _checkpoint(client, prefix, headers, identifier, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = _request(client, prefix, "GET", f"/investigations/{identifier}", headers).json()
        if state["run_status"] in {"waiting_for_review", "completed", "failed", "interrupted"}:
            return state
        time.sleep(0.1)
    raise AssertionError("Timed out waiting for investigation checkpoint")


def check_investigation(client, prefix, investigator, identifier):
    """Verify approved output and every evidence quote against persisted source text."""
    base = f"/investigations/{identifier}"
    evidence = _request(client, prefix, "GET", base + "/evidence", investigator).json()["items"]
    assert len(evidence) >= 2, "Expected at least two fixture evidence units"
    dossier = _request(client, prefix, "GET", base + "/dossier", investigator).json()
    assert dossier["approved"] is not None and dossier["validation"]["ok"], "Expected valid approved dossier"
    exported = _request(client, prefix, "GET", base + "/export", investigator)
    assert exported.headers["content-type"].startswith("text/markdown"), "Expected Markdown export"
    for item in evidence:
        doc = _request(client, prefix, "GET", base + f"/documents/{item['doc_id']}", investigator).json()["document"]
        locator = item["locator"]
        assert doc["text"][locator["start"] : locator["end"]] == item["quote"], "Source quote mismatch"
        assert item["quote"] in exported.text, "Evidence quote missing from export"
    return {
        "investigation_id": identifier,
        "evidence_count": len(evidence),
        "export_bytes": len(exported.content),
        "export_sha256": hashlib.sha256(exported.content).hexdigest(),
        "synthetic": True,
    }


def check_new_investigation(client, prefix, investigator, reviewer, *, timeout=60):
    """Exercise both review gates, role enforcement, resume and approved export."""
    created = _request(
        client,
        prefix,
        "POST",
        "/investigations",
        {**investigator, "Idempotency-Key": uuid4().hex},
        expected=202,
        json=CLAIM,
    ).json()
    identifier = created["investigation_id"]
    base = f"/investigations/{identifier}"
    state = _checkpoint(client, prefix, investigator, identifier, timeout)
    assert state["checkpoint"] == "assessment" and state["assessment_status"] == "supported_for_scope"
    _request(client, prefix, "GET", base + "/export", investigator, expected=409)
    decision = {
        "decision_id": uuid4().hex,
        "action": "approve",
        "checkpoint": "assessment",
        "expected_version": state["version"],
    }
    _request(client, prefix, "POST", base + "/reviews", investigator, expected=403, json=decision)
    _request(client, prefix, "POST", base + "/reviews", reviewer, json=decision)
    _request(client, prefix, "GET", base + "/export", investigator, expected=409)
    _request(
        client,
        prefix,
        "POST",
        base + "/continue",
        {**investigator, "Idempotency-Key": uuid4().hex},
        expected=202,
        json={},
    )
    state = _checkpoint(client, prefix, investigator, identifier, timeout)
    assert state["checkpoint"] == "dossier"
    _request(
        client,
        prefix,
        "POST",
        base + "/reviews",
        reviewer,
        json={
            "decision_id": uuid4().hex,
            "action": "approve",
            "checkpoint": "dossier",
            "expected_version": state["version"],
        },
    )
    return check_investigation(client, prefix, investigator, identifier)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend", default="http://127.0.0.1:3100")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--verify-result", type=Path, help="Recheck the same approved investigation after restart/restore"
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    investigator_token = os.environ.get("INVESTIGATOR_TOKEN")
    reviewer_token = os.environ.get("REVIEWER_TOKEN")
    if not investigator_token or not reviewer_token:
        parser.error("Set INVESTIGATOR_TOKEN and REVIEWER_TOKEN to the tokens used by the deployment")
    frontend_url = urlsplit(args.frontend)
    origin = f"{frontend_url.scheme}://{frontend_url.netloc}"
    with httpx.Client(timeout=30, trust_env=False) as client:
        ready = client.get(args.backend.rstrip("/") + "/ready")
        assert ready.status_code == 200 and ready.json()["status"] == "ready", "Backend not ready"
        assert client.get(args.frontend).status_code == 200, "Frontend unavailable"
    with httpx.Client(base_url=args.frontend.rstrip("/") + "/api/backend", timeout=30, trust_env=False) as client:
        investigator = session_headers(client, investigator_token, origin=origin)
        reviewer = session_headers(client, reviewer_token, origin=origin)
        if args.verify_result:
            previous = json.loads(args.verify_result.read_text(encoding="utf-8"))
            result = check_investigation(client, "/api/v1", investigator, previous["investigation_id"])
            assert result == previous, "Persisted investigation changed after restart/restore"
        else:
            result = check_new_investigation(client, "/api/v1", investigator, reviewer, timeout=args.timeout)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
