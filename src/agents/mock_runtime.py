"""Mock runtime cho graph M05: adapter nguồn và extractor chạy trên fixture M01.

Dùng để chạy trơn tru LangGraph trước khi có connector thật của Người 1 và node thật của Người 3.
Mọi fixture đều gắn nhãn ``synthetic``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models.schemas import (
    BudgetState,
    EvidenceUnit,
    NormalizedClaim,
    PlannerDecision,
    SourceDocument,
    SourceSearchResult,
    SourceStatus,
)
from src.services.planner import query_fingerprint

#: Thư mục fixture M01 (dữ liệu tổng hợp, gắn nhãn synthetic).
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "mvp"

FIXTURE_NAMES: tuple[str, ...] = (
    "supported",
    "insufficient",
    "scope_mismatch",
    "contradiction",
    "source_error",
    "ambiguous_brand",
    "replanning",
)


def load_fixture(name: str) -> dict[str, Any]:
    """Đọc fixture theo tên; thiếu file thì trả kịch bản rỗng (không bịa dữ liệu)."""
    path = FIXTURE_DIR / f"{name}_fixture.json"
    if name not in FIXTURE_NAMES or not path.exists():
        return dict(EMPTY_SCENARIO)
    return json.loads(path.read_text(encoding="utf-8"))

#: Từ khoá nhận diện kịch bản theo (thuốc, biến cố).
SCENARIO_HINTS: dict[str, tuple[str, str]] = {
    "supported": ("metformin", "lactic acidosis"),
    "insufficient": ("orlistat", "pancreatitis"),
    "scope_mismatch": ("ibuprofen", "gastrointestinal bleeding"),
    "contradiction": ("sertraline", "hyponatraemia"),
    "source_error": ("rivaroxaban", "intracranial haemorrhage"),
    "ambiguous_brand": ("vigilax", "somnolence"),
    "replanning": ("micardis", "angioedema"),
}

EMPTY_SCENARIO: dict[str, Any] = {
    "name": "empty",
    "synthetic": True,
    "description": "Không có kịch bản mẫu cho claim này — mọi nguồn trả rỗng.",
    "claim": {},
    "source_results": [],
    "documents": [],
    "evidence": [],
    "expected": {"assessment_status": "insufficient_evidence", "stop_reason": "saturation", "checkpoint": "assessment"},
}


def detect_scenario(drug: str, event: str) -> str | None:
    drug_key = drug.casefold()
    event_key = event.casefold()
    for name, (drug_hint, event_hint) in SCENARIO_HINTS.items():
        if drug_hint in drug_key and event_hint in event_key:
            return name
    return None


def scenario_for_claim(drug: str, event: str) -> dict[str, Any]:
    name = detect_scenario(drug, event)
    return load_fixture(name) if name else dict(EMPTY_SCENARIO)


class FixtureAdapter:
    """Adapter nguồn chạy trên fixture: khớp ``query_contains`` rồi tới stage mặc định."""

    def __init__(self, source: str, scenario: dict[str, Any]):
        self.name = source
        self.scenario = scenario
        self._used: set[int] = set()
        self.calls: list[str] = []

    def _documents(self, doc_ids: list[str]) -> list[SourceDocument]:
        by_id = {item["doc_id"]: item for item in self.scenario.get("documents", [])}
        return [SourceDocument.model_validate(by_id[doc_id]) for doc_id in doc_ids if doc_id in by_id]

    def search(self, action: PlannerDecision, budget: BudgetState) -> SourceSearchResult:
        query = action.query or ""
        self.calls.append(query)
        fingerprint = action.fingerprint or query_fingerprint(self.name, query)
        stages = [
            (index, stage)
            for index, stage in enumerate(self.scenario.get("source_results", []))
            if stage.get("source") == self.name
        ]
        for index, stage in stages:
            if index in self._used:
                continue
            needle = stage.get("query_contains")
            if needle and needle.casefold() in query.casefold():
                self._used.add(index)
                return self._result(stage, query, fingerprint)
        for index, stage in stages:
            if index in self._used or stage.get("query_contains"):
                continue
            self._used.add(index)
            return self._result(stage, query, fingerprint)
        return SourceSearchResult(
            source=self.name,  # type: ignore[arg-type]
            query=query,
            fingerprint=fingerprint,
            status=SourceStatus.EMPTY,
        )

    def _result(self, stage: dict[str, Any], query: str, fingerprint: str) -> SourceSearchResult:
        status = SourceStatus(stage.get("status", "empty"))
        return SourceSearchResult(
            source=self.name,  # type: ignore[arg-type]
            query=query,
            fingerprint=fingerprint,
            status=status,
            documents=self._documents(stage.get("doc_ids", [])) if status is SourceStatus.OK else [],
            error=stage.get("error"),
            retryable=status is SourceStatus.ERROR,
        )


class FixtureExtractor:
    """Extractor mock: trả bằng chứng đã soạn trong fixture cho từng ``doc_id``."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario

    def extract_evidence(self, document: SourceDocument, claim: NormalizedClaim) -> list[EvidenceUnit]:
        return [
            EvidenceUnit.model_validate(item)
            for item in self.scenario.get("evidence", [])
            if item["doc_id"] == document.doc_id
        ]


class FixtureNormalizer:
    """Chuẩn hoá claim tối thiểu: dùng phần ``normalization`` của fixture nếu có."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario = scenario

    def normalize_claim(self, claim) -> NormalizedClaim:  # noqa: ANN001 - ClaimInput
        preset = self.scenario.get("normalization")
        if preset:
            return NormalizedClaim(
                claim_text=claim.claim_text,
                drug_ingredient=preset.get("drug_ingredient") or claim.drug.casefold(),
                drug_synonyms=preset.get("drug_synonyms", []),
                event_term=preset.get("event_term") or claim.event.casefold(),
                population=claim.population,
                dose=claim.dose,
                route=claim.route,
                time_window=claim.time_window,
                unknowns=preset.get("unknowns", []),
                ambiguities=preset.get("ambiguities", []),
                requires_review=preset.get("requires_review", False),
            )
        return NormalizedClaim(
            claim_text=claim.claim_text,
            drug_ingredient=claim.drug.casefold().strip(),
            drug_synonyms=[],
            event_term=claim.event.casefold().strip(),
            population=claim.population,
            dose=claim.dose,
            route=claim.route,
            time_window=claim.time_window,
            unknowns=[field for field in ("population", "dose", "route", "time_window") if getattr(claim, field) is None],
        )
