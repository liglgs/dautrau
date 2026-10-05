"""Test tích hợp M10: cắm connector Người 1 + node Người 3 vào graph qua ``RunContext``.

Các lớp giả lập dưới đây mô phỏng đúng hợp đồng trong ``docs/INTEGRATION_PLUG_POINTS.md``
(không dùng fixture, không dùng ``FixtureAdapter``/``FixtureExtractor``).
"""

from __future__ import annotations

from typing import Any

from src.agents.graph import run_investigation
from src.models.schemas import (
    AssessmentStatus,
    ClaimInput,
    EvidenceScope,
    EvidenceUnit,
    NormalizedClaim,
    PlannerDecision,
    QuoteLocator,
    RunStatus,
    SourceDocument,
    SourceSearchResult,
    SourceStatus,
    Stance,
)
from src.services.planner import query_fingerprint
from src.services.runner import InProcessRunner
from src.services.store import MvpStore

CLAIM = ClaimInput(
    claim_text="metformin gây lactic acidosis ở người suy thận.",
    drug="metformin",
    event="lactic acidosis",
    population="adults with renal impairment",
    route="oral",
)

TEXT_PUBMED = (
    "Metformin and lactic acidosis in renal impairment: a cohort study. "
    "Among adults with renal impairment, metformin exposure was associated with lactic acidosis."
)
TEXT_DAILYMED = (
    "Metformin label, section 5.1: lactic acidosis is a rare but serious metabolic complication "
    "that can occur in patients with renal impairment."
)


class RecordingConnector:
    """Connector kiểu thật: gọi API nguồn, trả SourceSearchResult, không ghi DB."""

    def __init__(self, source: str, documents: list[SourceDocument]) -> None:
        self.name = source
        self.documents = documents
        self.calls: list[str] = []

    def search(self, action: PlannerDecision, budget) -> SourceSearchResult:  # noqa: ANN001 - BudgetState
        query = action.query or ""
        self.calls.append(query)
        fingerprint = action.fingerprint or query_fingerprint(self.name, query)
        matched = [document for document in self.documents if document.source == self.name]
        if not matched:
            return SourceSearchResult(
                source=self.name,  # type: ignore[arg-type]
                query=query,
                fingerprint=fingerprint,
                status=SourceStatus.EMPTY,
            )
        return SourceSearchResult(
            source=self.name,  # type: ignore[arg-type]
            query=query,
            fingerprint=fingerprint,
            status=SourceStatus.OK,
            documents=matched,
            request_id=f"{self.name}-req-1",
        )


class RecordingExtractor:
    """Node trích xuất của Người 3: trả bằng chứng có trích dẫn nguyên văn từ tài liệu."""

    def __init__(self, quotes: dict[str, str]) -> None:
        self.quotes = quotes
        self.seen: list[str] = []

    def extract_evidence(self, document: SourceDocument, claim: NormalizedClaim) -> list[EvidenceUnit]:
        self.seen.append(document.doc_id)
        quote = self.quotes.get(document.doc_id)
        if quote is None or quote not in document.text:
            return []
        start = document.text.find(quote)
        return [
            EvidenceUnit(
                evidence_id=f"EVI-{document.source.upper()}-1",
                doc_id=document.doc_id,
                source=document.source,
                stance=Stance.SUPPORTS,
                quote=quote,
                locator=QuoteLocator(start=start, end=start + len(quote), section="results"),
                scope=EvidenceScope(population="adults with renal impairment", route="oral", study_type="cohort"),
                confidence=0.8,
            )
        ]


class RecordingNormalizer:
    """Node chuẩn hoá của Người 3 (không dùng fixture ``normalization``)."""

    def __init__(self) -> None:
        self.calls = 0

    def normalize_claim(self, claim: ClaimInput) -> NormalizedClaim:
        self.calls += 1
        return NormalizedClaim(
            claim_text=claim.claim_text,
            drug_ingredient=claim.drug.casefold(),
            drug_synonyms=["Glucophage"] if claim.drug.casefold() == "metformin" else [],
            event_term=claim.event.casefold(),
            population=claim.population,
            route=claim.route,
            unknowns=["dose", "time_window"],
        )


def _documents() -> list[SourceDocument]:
    return [
        SourceDocument(
            doc_id="DOC-PUBMED-PLUG",
            source="pubmed",
            source_id="pmid:90000001",
            title="Metformin and lactic acidosis in renal impairment",
            text=TEXT_PUBMED,
            hash="hash-pubmed-plug-0001",
        ),
        SourceDocument(
            doc_id="DOC-DAILYMED-PLUG",
            source="dailymed",
            source_id="setid:plug-1",
            title="Metformin label",
            text=TEXT_DAILYMED,
            hash="hash-dailymed-plug-001",
        ),
    ]


def _context(store: MvpStore, runner: InProcessRunner) -> tuple[Any, dict[str, RecordingConnector], RecordingExtractor, RecordingNormalizer]:
    connectors = {
        "pubmed": RecordingConnector("pubmed", _documents()),
        "dailymed": RecordingConnector("dailymed", _documents()),
        "faers": RecordingConnector("faers", []),
    }
    extractor = RecordingExtractor(
        {
            "DOC-PUBMED-PLUG": "metformin exposure was associated with lactic acidosis",
            "DOC-DAILYMED-PLUG": "lactic acidosis is a rare but serious metabolic complication",
        }
    )
    normalizer = RecordingNormalizer()
    ctx = runner.context()
    ctx.adapters = connectors
    ctx.extractor = extractor
    ctx.normalizer = normalizer
    return ctx, connectors, extractor, normalizer


def test_plugged_connectors_and_extractor_drive_the_run(tmp_path):
    store = MvpStore(str(tmp_path / "plug.db"))
    runner = InProcessRunner(store)
    state, _ = store.create_investigation(CLAIM)
    ctx, connectors, extractor, normalizer = _context(store, runner)

    result = run_investigation(store.get_state(state.investigation_id), ctx)

    assert normalizer.calls == 1, "graph phải dùng normalizer được cắm"
    assert connectors["pubmed"].calls, "adapter Người 1 phải được gọi"
    assert extractor.seen, "extractor Người 3 phải nhận tài liệu thật"
    assert result.run_status is RunStatus.WAITING_FOR_REVIEW
    assert result.checkpoint is not None

    evidence = result.active_evidence()
    assert {item.evidence_id for item in evidence} >= {"EVI-PUBMED-1"}
    assert all(item.doc_id.startswith("DOC-") for item in evidence)
    assert result.assessment_status in {
        AssessmentStatus.SUPPORTED_FOR_SCOPE,
        AssessmentStatus.INSUFFICIENT_EVIDENCE,
    }

    # Tài liệu do connector trả về phải đọc lại được từ store (không có tài liệu "ma").
    for document in result.documents:
        stored = store.get_document(state.investigation_id, document.doc_id)
        assert stored is not None
        assert stored.hash == document.hash
        assert document.text in stored.text


def test_plugged_connector_error_becomes_a_gap_not_a_crash(tmp_path):
    store = MvpStore(str(tmp_path / "plug-error.db"))
    runner = InProcessRunner(store)
    state, _ = store.create_investigation(CLAIM)
    ctx, connectors, _, _ = _context(store, runner)

    class BrokenConnector(RecordingConnector):
        def search(self, action: PlannerDecision, budget) -> SourceSearchResult:  # noqa: ANN001 - BudgetState
            self.calls.append(action.query or "")
            return SourceSearchResult(
                source=self.name,  # type: ignore[arg-type]
                query=action.query or "q",
                fingerprint=action.fingerprint or query_fingerprint(self.name, action.query or "q"),
                status=SourceStatus.ERROR,
                error="503 từ nguồn",
                retryable=True,
            )

    for source in ("pubmed", "dailymed", "faers"):
        connectors[source] = BrokenConnector(source, [])

    result = run_investigation(store.get_state(state.investigation_id), ctx)

    assert result.run_status in {RunStatus.WAITING_FOR_REVIEW, RunStatus.COMPLETED}
    assert any(gap.kind.value == "missing_source" for gap in result.gaps)
    assert result.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
