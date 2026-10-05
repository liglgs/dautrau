"""Hợp đồng giao tiếp giữa các thành phần (M01 — QUY_TAC §7).

Các ``Protocol`` dưới đây là điểm cắm (seam) để Người 1 (connectors/snapshot),
Người 3 (extraction/scope/contradiction) và Người 2 (runner/graph/dossier) làm việc độc lập.
Mock của mỗi bên chỉ cần thoả mãn protocol tương ứng.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.models.schemas import (
    BudgetState,
    Dossier,
    EvidenceGap,
    EvidenceUnit,
    InvestigationState,
    NormalizedClaim,
    PlannerDecision,
    ScopeAssessment,
    SourceDocument,
    SourceSearchResult,
)


@runtime_checkable
class SourceAdapter(Protocol):
    """Adapter nguồn ngoài (PubMed, DailyMed, openFDA FAERS) — Người 1."""

    name: str

    def search(self, action: PlannerDecision, budget: BudgetState) -> SourceSearchResult:
        """Thực hiện đúng một hành động tìm kiếm trong ngân sách cho phép."""
        ...


@runtime_checkable
class SnapshotStore(Protocol):
    """Lưu snapshot thô bất biến theo ``(source, source_id, version)``."""

    def save(self, document: SourceDocument) -> str:
        """Trả về đường dẫn/khóa snapshot sinh từ ID và hash (không từ tên file người dùng)."""
        ...


@runtime_checkable
class DocumentParser(Protocol):
    """Chuẩn hoá văn bản nguồn thành ``SourceDocument``."""

    def parse_document(self, raw: bytes, metadata: dict) -> SourceDocument: ...


@runtime_checkable
class ClaimNormalizer(Protocol):
    """Chuẩn hoá claim và phát hiện mơ hồ (Người 3)."""

    def normalize_claim(self, claim: object) -> NormalizedClaim: ...


@runtime_checkable
class EvidenceExtractor(Protocol):
    """Trích xuất bằng chứng kèm trích dẫn kiểm chứng được (Người 3)."""

    def extract_evidence(self, document: SourceDocument, claim: NormalizedClaim) -> list[EvidenceUnit]: ...


@runtime_checkable
class ScopeMatcher(Protocol):
    """So khớp phạm vi bằng chứng với claim (Người 3)."""

    def assess_scope(self, evidence: list[EvidenceUnit], claim: NormalizedClaim) -> ScopeAssessment: ...


@runtime_checkable
class ContradictionAnalyzer(Protocol):
    """Phát hiện mâu thuẫn trực tiếp (Người 3)."""

    def analyze_contradictions(self, evidence: list[EvidenceUnit], claim: NormalizedClaim) -> list[EvidenceGap]: ...


@runtime_checkable
class DossierBuilder(Protocol):
    """Tổng hợp hồ sơ từ state đã được duyệt (Người 2)."""

    def build_dossier(self, state: InvestigationState) -> Dossier: ...


@runtime_checkable
class EvaluationRunner(Protocol):
    """Chạy bộ đánh giá chất lượng (Người 3/4 dùng chung)."""

    def run_evaluation(self, dataset: str) -> dict: ...
