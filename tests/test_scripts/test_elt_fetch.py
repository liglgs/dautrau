"""Offline retry behavior for the ELT fetcher."""

from __future__ import annotations

from pathlib import Path

import httpx

from scripts.elt.fetch import Fetcher
from scripts.elt.manifest import RunManifest


def test_network_error_after_retry_does_not_keep_stale_http_status(tmp_path: Path, monkeypatch) -> None:
    request = httpx.Request("GET", "https://example.test/catalog")

    class Client:
        responses = [
            httpx.Response(503, request=request),
            httpx.ConnectError("connection lost", request=request),
        ]

        def get(self, *_args, **_kwargs):
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    fetcher = Fetcher(tmp_path / "raw", RunManifest("test", "test", tmp_path))
    fetcher._client = Client()
    monkeypatch.setattr(fetcher, "_throttle", lambda _host: None)
    monkeypatch.setattr("scripts.elt.fetch.time.sleep", lambda _seconds: None)

    result = fetcher.get("test", "catalog", str(request.url), retries=1)

    assert result.status is None
    assert result.error and result.error.startswith("network:")
    assert fetcher.manifest.artifacts[-1]["status"] is None
