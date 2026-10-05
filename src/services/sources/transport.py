"""Bounded HTTP transport. A request is charged before any network side effect."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from threading import Lock

import httpx

from src.models.schemas import BudgetState

ALLOWED_HOSTS = {"eutils.ncbi.nlm.nih.gov", "dailymed.nlm.nih.gov", "api.fda.gov"}


class SourceError(Exception):
    def __init__(self, code: str, *, retryable: bool = False):
        super().__init__(code)
        self.retryable = retryable


class RequestBudget:
    def __init__(self, budget: BudgetState, on_request: Callable[[], None] | None = None):
        self.remaining = budget.max_source_requests - budget.source_requests
        self.used = 0
        self.on_request = on_request

    def charge(self):
        if self.used >= self.remaining:
            raise SourceError("budget_exhausted")
        if self.on_request:
            self.on_request()
        self.used += 1


class SourceTransport:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        interval: float = 0.4,
        timeout: float = 15,
        max_bytes: int = 4_000_000,
    ):
        self.client = client
        self.interval = interval
        self.timeout = timeout
        self.max_bytes = max_bytes
        self._lock = Lock()
        self._last: dict[str, float] = {}

    def get(self, url: str, params: dict, budget: RequestBudget | BudgetState) -> bytes:
        target = httpx.URL(url)
        if target.scheme != "https" or target.host not in ALLOWED_HOSTS or target.port not in (None, 443):
            raise SourceError("invalid_query: host not allowed")
        meter = RequestBudget(budget) if isinstance(budget, BudgetState) else budget
        for attempt in range(2):
            with self._lock:
                delay = self.interval - (time.monotonic() - self._last.get(target.host, 0))
                if delay > 0:
                    time.sleep(delay)
                meter.charge()
                self._last[target.host] = time.monotonic()
                try:
                    if self.client is None:
                        with httpx.Client(timeout=self.timeout, follow_redirects=False, trust_env=False) as client:
                            return self._read(client, url, params)
                    return self._read(self.client, url, params)
                except httpx.DecodingError:
                    failure = SourceError("parse_error: invalid response encoding")
                except httpx.RequestError as exc:
                    failure = SourceError(
                        "timeout" if isinstance(exc, httpx.TimeoutException) else "unavailable", retryable=True
                    )
                except SourceError as exc:
                    failure = exc
            if not failure.retryable or attempt == 1:
                raise failure
            time.sleep(min(self.interval, 1))
        raise SourceError("unavailable")  # pragma: no cover

    def _read(self, client, url, params):
        with client.stream("GET", url, params=params, timeout=self.timeout, follow_redirects=False) as response:
            if 300 <= response.status_code < 400:
                raise SourceError("invalid_query: redirect rejected")
            if response.status_code == 429:
                raise SourceError("rate_limited", retryable=True)
            if response.status_code >= 500:
                raise SourceError("unavailable", retryable=True)
            # openFDA represents an empty search as a typed 404 JSON response.
            if response.status_code == 404 and response.request.url.host == "api.fda.gov":
                raw = self._bounded(response)
                try:
                    error = json.loads(raw).get("error", {})
                except (ValueError, AttributeError):
                    error = {}
                if error.get("code") == "NOT_FOUND" and error.get("message") == "No matches found!":
                    return b'{"results": []}'
            if response.status_code >= 400:
                raise SourceError("invalid_query" if response.status_code == 400 else "unavailable")
            content_type = response.headers.get("content-type", "").split(";")[0].strip()
            if content_type not in {"application/json", "application/xml", "text/xml"}:
                raise SourceError("parse_error: unexpected content type")
            return self._bounded(response)

    def _bounded(self, response):
        data = bytearray()
        for chunk in response.iter_bytes():
            if len(data) + len(chunk) > self.max_bytes:
                raise SourceError("parse_error: response too large")
            data.extend(chunk)
        return bytes(data)
