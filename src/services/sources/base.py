"""Synchronous MVP adapter contract; HTTP is injected for offline tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

from src.models.schemas import SourceSearchResult, SourceStatus
from src.services.planner import query_fingerprint
from src.services.sources.transport import RequestBudget, SourceError, SourceTransport


class SourceAdapter:
    name: str

    def __init__(
        self,
        *,
        transport: SourceTransport,
        snapshot_root: str | Path,
        drug: str = "",
        event: str = "",
        max_documents: int = 5,
    ):
        self.transport = transport
        self.root = Path(snapshot_root)
        self.drug = drug
        self.event = event
        self.max_documents = max_documents
        self._cache: dict[str, SourceSearchResult] = {}

    def search(self, action, budget):
        return self.search_with_budget(action, budget)

    def search_with_budget(self, action, budget, on_request=None):
        query = action.query or ""
        fingerprint = query_fingerprint(self.name, query)
        key = f"{fingerprint}:{self.drug}:{self.event}:{self.max_documents}"
        meter = RequestBudget(budget, on_request)
        try:
            if key in self._cache:
                cached = self._cache[key]
                for item in cached.documents:
                    raw_hash = item.metadata["raw_hash"]
                    raw_path = self.root / self.name / f"{raw_hash}.raw"
                    if hashlib.sha256(raw_path.read_bytes()).hexdigest() != raw_hash:
                        raise SourceError("parse_error: corrupt snapshot")
                return cached.model_copy(deep=True, update={"requests_used": 0})
            documents = self.fetch(action, meter)
            result = SourceSearchResult(
                source=self.name,
                query=query,
                fingerprint=fingerprint,
                documents=documents,
                requests_used=meter.used,
                status=SourceStatus.OK if documents else SourceStatus.EMPTY,
            )
            self._cache[key] = result.model_copy(deep=True)
            return result
        except (SourceError, ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            code = (
                str(exc) if isinstance(exc, SourceError) else "parse_error: invalid source response or snapshot failure"
            )
            return SourceSearchResult(
                source=self.name,
                query=query,
                fingerprint=fingerprint,
                status=SourceStatus.ERROR,
                error=code[:1000],
                requests_used=meter.used,
                retryable=isinstance(exc, SourceError) and exc.retryable,
            )

    def get(self, url, params, meter):
        return self.transport.get(url, params, meter)

    def snapshot(self, document, raw):
        digest = hashlib.sha256(raw).hexdigest()
        folder = self.root / self.name
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{digest}.raw"
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise SourceError("parse_error: corrupt snapshot")
        else:
            temporary = folder / f".{uuid4().hex}.tmp"
            try:
                temporary.write_bytes(raw)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        document.metadata["raw_ref"] = str(path)
        return document

    def json(self, raw):
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise SourceError("parse_error: invalid JSON") from exc
        if not isinstance(value, dict):
            raise SourceError("parse_error: expected object")
        return value
