"""Chuẩn hoá kết quả nguồn cho runner/extractor mà không đổi contract MVP hiện có.

``SourceSearchResult`` tiếp tục là interface runtime cũ. ``SourceResult`` là payload
additive cho connector, replay và UI: nó giữ phân loại lỗi/coverage và provenance
thay vì suy lỗi thành "không có kết quả".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from src.models.schemas import SourceSearchResult, SourceStatus

Outcome = Literal["ok", "empty", "timeout", "http_error", "rate_limited", "partial"]


@dataclass(frozen=True)
class SourceResult:
    source: str
    outcome: Outcome
    documents: tuple[Any, ...] = ()
    retryable: bool = False
    source_gap: bool = False
    error: str | None = None
    http_status: int | None = None
    coverage: str = "complete"
    version: str | int | None = None
    published_date: str | None = None
    effective_time: str | None = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.outcome in {"ok", "empty", "partial"}

    def to_dict(self) -> dict[str, Any]:
        """Payload JSON-friendly while preserving the source adapter's document content."""
        return {
            "source": self.source,
            "outcome": self.outcome,
            "documents": [
                document.model_dump(mode="json") if hasattr(document, "model_dump") else document
                for document in self.documents
            ],
            "retryable": self.retryable,
            "source_gap": self.source_gap,
            "error": self.error,
            "http_status": self.http_status,
            "coverage": self.coverage,
            "version": self.version,
            "published_date": self.published_date,
            "effective_time": self.effective_time,
            "retrieved_at": self.retrieved_at,
            "provenance": self.provenance,
        }


def _metadata(result: SourceSearchResult) -> dict[str, Any]:
    if not result.documents:
        return {}
    return dict(result.documents[0].metadata or {})


def _outcome_from_error(error: str | None) -> Outcome:
    code = (error or "").casefold()
    if "timeout" in code:
        return "timeout"
    if "rate_limited" in code or "429" in code:
        return "rate_limited"
    return "http_error"


def source_result_from_search(result: SourceSearchResult) -> SourceResult:
    """Ánh xạ contract runtime cũ sang payload mở rộng, giữ nguyên tài liệu và error cũ."""

    metadata = _metadata(result)
    partial = any("truncated" in str(item) for doc in result.documents for item in doc.metadata.get("warnings", []))
    if result.status is SourceStatus.ERROR:
        outcome = _outcome_from_error(result.error)
        return SourceResult(
            source=result.source,
            outcome=outcome,
            documents=tuple(result.documents),
            error=result.error,
            retryable=result.retryable,
            coverage="unavailable",
            provenance={"query": result.query, "fingerprint": result.fingerprint, "requests_used": result.requests_used},
        )
    if result.status is SourceStatus.EMPTY:
        return SourceResult(
            source=result.source,
            outcome="empty",
            coverage="empty",
            provenance={"query": result.query, "fingerprint": result.fingerprint, "requests_used": result.requests_used},
        )
    return SourceResult(
        source=result.source,
        outcome="partial" if partial else "ok",
        documents=tuple(result.documents),
        coverage="partial" if partial else "complete",
        version=metadata.get("version") or metadata.get("source_record_version") or result.documents[0].version,
        published_date=metadata.get("published_date"),
        effective_time=metadata.get("effective_time"),
        retrieved_at=result.documents[0].retrieved_at.isoformat() if result.documents else datetime.now(UTC).isoformat(),
        provenance={"query": result.query, "fingerprint": result.fingerprint, "requests_used": result.requests_used},
    )


def source_result_from_fetch(fetch_result: Any, *, partial: bool = False, metadata: dict[str, Any] | None = None) -> SourceResult:
    """Ánh xạ ``scripts.elt.fetch.FetchResult`` mà không tạo phụ thuộc ngược vào ELT.

    HTTP 404 luôn là ``http_error`` và ``source_gap=True``. Vì vậy 404 không bị hiển
    thị như ``empty`` hay như một kết luận "không có bằng chứng".
    """

    metadata = metadata or {}
    error = getattr(fetch_result, "error", None)
    status = getattr(fetch_result, "status", None)
    body = getattr(fetch_result, "body", b"")
    if error:
        outcome = _outcome_from_error(error)
    elif status == 200:
        outcome = "partial" if partial else ("empty" if not body else "ok")
    else:
        outcome = "http_error"
    return SourceResult(
        source=str(getattr(fetch_result, "source", "")),
        outcome=outcome,
        retryable=outcome in {"timeout", "rate_limited"} or (status is not None and status >= 500),
        source_gap=status == 404 or str(error or "").casefold().startswith("http_404"),
        error=error,
        http_status=status,
        coverage="partial" if outcome == "partial" else ("empty" if outcome == "empty" else "unavailable" if not body else "complete"),
        version=metadata.get("version"),
        published_date=metadata.get("published_date"),
        effective_time=metadata.get("effective_time"),
        retrieved_at=metadata.get("retrieved_at") or datetime.now(UTC).isoformat(),
        provenance={
            "url": getattr(fetch_result, "url", ""),
            "params": getattr(fetch_result, "params", {}),
            "sha256": getattr(fetch_result, "sha256", ""),
            "path": getattr(fetch_result, "path", ""),
        },
    )
