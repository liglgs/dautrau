"""Hợp đồng dữ liệu Pydantic cho MVP "AI Agent điều tra an toàn thuốc" (P-066).

Người 2 (Core Backend & Agent Orchestration) — mốc M01.

File này là nguồn sự thật duy nhất (single source of truth) cho:
  * models trao đổi giữa Người 1 (connectors), Người 2 (runner/graph/API),
    Người 3 (extraction/scope/contradiction) và Người 4 (frontend);
  * enum trạng thái chạy, trạng thái kết luận, trạng thái duyệt, checkpoint;
  * giới hạn ngân sách (budget caps) và danh mục mã lỗi chuẩn.

Tài liệu mô tả hợp đồng: ``docs/mvp-contracts.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --------------------------------------------------------------------------------------
# Giới hạn ngân sách (budget) — xem docs/planMVPfinal.md §4.3 và QUY_TAC §6
# --------------------------------------------------------------------------------------

DEFAULT_MAX_STEPS = 8
DEFAULT_MAX_DOCUMENTS = 50
HARD_MAX_STEPS = 20
HARD_MAX_DOCUMENTS = 100

MAX_SOURCE_REQUESTS = 80
MAX_LLM_CALLS = 80
MAX_INPUT_TOKENS = 150_000
MAX_OUTPUT_TOKENS = 25_000

# Dự phòng cho bước tạo hồ sơ (dossier) và phương án abstain.
RESERVED_STEPS_FOR_DOSSIER = 1
RESERVED_LLM_CALLS_FOR_DOSSIER = 2

SOURCE_NAMES: tuple[str, ...] = ("pubmed", "dailymed", "faers")

#: RV-04 — ngưỡng lý do duyệt tối thiểu, dùng chung cho giao diện và máy chủ.
#: Giao diện đã đòi 15 ký tự từ trước; máy chủ chỉ cần khác rỗng, nên gọi thẳng API là lách được
#: yêu cầu ghi lý do. Giao diện giữ cùng con số ở ``frontend/lib/review-rules.ts``.
MIN_REVIEW_REASON = 15

UNKNOWN_TOKENS: frozenset[str] = frozenset(
    {
        "",
        "unknown",
        "n/a",
        "na",
        "none",
        "not specified",
        "unspecified",
        "not reported",
        "không rõ",
        "khong ro",
        "chưa rõ",
    }
)

# --------------------------------------------------------------------------------------
# Enum trạng thái
# --------------------------------------------------------------------------------------


class RunStatus(StrEnum):
    """Vòng đời một cuộc điều tra."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_REVIEW = "waiting_for_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


class AssessmentStatus(StrEnum):
    """Kết luận an toàn thuốc được phép.

    Lưu ý: ``causal`` (kết luận nhân quả) KHÔNG nằm trong enum này — agent không bao giờ
    được phép tự kết luận quan hệ nhân quả.
    """

    SUPPORTED_FOR_SCOPE = "supported_for_scope"
    CONTRADICTED_FOR_SCOPE = "contradicted_for_scope"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    SCOPE_MISMATCH = "scope_mismatch"
    OUT_OF_SCOPE = "out_of_scope"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class CheckpointKind(StrEnum):
    NORMALIZATION = "normalization"
    ASSESSMENT = "assessment"
    DOSSIER = "dossier"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT_CLAIM = "edit_claim"
    EDIT_EVIDENCE = "edit_evidence"
    EXCLUDE_EVIDENCE = "exclude_evidence"
    REQUEST_MORE = "request_more"


class Stance(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNCERTAIN = "uncertain"


class ScopeOutcome(StrEnum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class StopReason(StrEnum):
    SUCCESS = "success"
    SATURATION = "saturation"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BUDGET_EXHAUSTED = "budget_exhausted"
    SOURCE_ERROR = "source_error"


class PlannerActionKind(StrEnum):
    SEARCH_SOURCE = "search_source"
    CHANGE_QUERY = "change_query"
    CHANGE_SOURCE = "change_source"
    STOP = "stop"


class GapKind(StrEnum):
    NO_RESULTS = "no_results"
    MISSING_EVIDENCE = "missing_evidence"
    MISSING_SOURCE = "missing_source"
    SCOPE_MISMATCH = "scope_mismatch"
    CONTRADICTION = "contradiction"
    AMBIGUITY = "ambiguity"


class EvidenceType(StrEnum):
    RCT = "rct"
    OBSERVATIONAL = "observational"
    CASE_REPORT = "case_report"
    LABEL = "label"
    FAERS_REPORT = "faers_report"
    REVIEW = "review"
    OTHER = "other"


class SourceStatus(StrEnum):
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"
    SKIPPED = "skipped"


class ErrorCode(StrEnum):
    """Danh mục mã lỗi chuẩn của MVP (envelope: {"error": {code, message, details, request_id}})."""

    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    VERSION_CONFLICT = "version_conflict"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RUNNER_BUSY = "runner_busy"
    INVALID_STATE = "invalid_state"
    BUDGET_EXHAUSTED = "budget_exhausted"
    DOSSIER_NOT_APPROVED = "dossier_not_approved"
    DOSSIER_INVALID = "dossier_invalid"
    SOURCE_ERROR = "source_error"
    LLM_FORMAT_ERROR = "llm_format_error"
    MODEL_UNAVAILABLE = "model_unavailable"


# --------------------------------------------------------------------------------------
# Models: input & claim
# --------------------------------------------------------------------------------------


class InvestigationConfig(BaseModel):
    """Cấu hình nguồn và ngân sách runtime cho một cuộc điều tra."""

    model_config = ConfigDict(extra="forbid")

    sources: list[str] = Field(default_factory=lambda: list(SOURCE_NAMES))
    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1, le=HARD_MAX_STEPS)
    max_documents: int = Field(default=DEFAULT_MAX_DOCUMENTS, ge=1, le=HARD_MAX_DOCUMENTS)

    @field_validator("sources")
    @classmethod
    def _validate_sources(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("sources không được để trống")
        invalid = [s for s in v if s not in SOURCE_NAMES]
        if invalid:
            raise ValueError(f"Nguồn không hợp lệ: {invalid}. Nguồn hợp lệ: {list(SOURCE_NAMES)}")
        return list(dict.fromkeys(v))


class ClaimInput(BaseModel):
    """Yêu cầu điều tra thô từ người dùng (API ``POST /api/v1/investigations``)."""

    model_config = ConfigDict(extra="forbid")

    claim_text: str = Field(min_length=1, max_length=5000)
    drug: str = Field(min_length=1, max_length=200)
    event: str = Field(min_length=1, max_length=200)
    population: str | None = Field(default=None, max_length=200)
    dose: str | None = Field(default=None, max_length=120)
    route: str | None = Field(default=None, max_length=120)
    time_window: str | None = Field(default=None, max_length=120)
    config: InvestigationConfig | None = Field(default=None)

    @field_validator("claim_text", "drug", "event")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """IN-05: chuỗi chỉ gồm khoảng trắng không phải là nội dung.

        Giao diện đã chặn từ trước, nhưng gọi thẳng API thì lọt: ``min_length=1`` để ``"   "``
        đi qua, và ca đó chạy hết ngân sách rồi trả về hồ sơ rỗng.
        """
        if not value.strip():
            raise ValueError("không được chỉ gồm khoảng trắng")
        return value

    @field_validator("population", "dose", "route", "time_window")
    @classmethod
    def _blank_optional_is_absent(cls, value: str | None) -> str | None:
        """Trường tuỳ chọn gửi lên toàn khoảng trắng được coi như không khai."""
        if value is None:
            return None
        return value.strip() or None


class NormalizedClaim(BaseModel):
    """Claim sau bước chuẩn hóa; giữ rõ các trường chưa biết và điểm mơ hồ."""

    claim_text: str = Field(min_length=1, max_length=5000)
    drug_ingredient: str = Field(min_length=1, max_length=200)
    drug_synonyms: list[str] = Field(default_factory=list)
    event_term: str = Field(min_length=1, max_length=200)
    population: str | None = Field(default=None, max_length=200)
    dose: str | None = Field(default=None, max_length=120)
    route: str | None = Field(default=None, max_length=120)
    time_window: str | None = Field(default=None, max_length=120)
    unknowns: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    requires_review: bool = False
    version: int = Field(default=1, ge=1)

    @field_validator("drug_synonyms", "unknowns", "ambiguities")
    @classmethod
    def _dedupe(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item and item.strip()))


# --------------------------------------------------------------------------------------
# Models: nguồn & bằng chứng (hợp đồng với Người 1 và Người 3)
# --------------------------------------------------------------------------------------


class SourceDocument(BaseModel):
    """Tài liệu gốc do adapter nguồn (Người 1) trả về và được lưu bất biến."""

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1, max_length=120)
    source: Literal["pubmed", "dailymed", "faers"]
    source_id: str = Field(min_length=1, max_length=200)
    version: int = Field(default=1, ge=1)
    title: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=1000)
    text: str = Field(min_length=1, max_length=200_000)
    hash: str = Field(min_length=8, max_length=128)
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuoteLocator(BaseModel):
    """Vị trí trích dẫn trong tài liệu gốc (bắt buộc để kiểm chứng trích dẫn)."""

    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    section: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _ordered(self) -> QuoteLocator:
        if self.end <= self.start:
            raise ValueError("locator.end phải lớn hơn locator.start")
        return self


class EvidenceScope(BaseModel):
    """Phạm vi áp dụng của một đơn vị bằng chứng (dùng cho so khớp scope)."""

    model_config = ConfigDict(extra="forbid")

    population: str | None = Field(default=None, max_length=200)
    dose: str | None = Field(default=None, max_length=120)
    route: str | None = Field(default=None, max_length=120)
    time_window: str | None = Field(default=None, max_length=120)
    study_type: str | None = Field(default=None, max_length=120)


class ScopeComparison(BaseModel):
    """Kết quả so khớp một trường scope giữa claim và bằng chứng.

    Quy tắc bắt buộc: nếu một bên là ``unknown`` thì kết quả KHÔNG BAO GIỜ là ``match``.
    """

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=60)
    claim_value: str | None = None
    evidence_value: str | None = None
    outcome: ScopeOutcome

    @classmethod
    def compare(cls, field: str, claim_value: str | None, evidence_value: str | None) -> ScopeComparison:
        if is_unknown(claim_value) or is_unknown(evidence_value):
            outcome = ScopeOutcome.UNKNOWN
        elif _normalize_value(claim_value) == _normalize_value(evidence_value):
            outcome = ScopeOutcome.MATCH
        else:
            outcome = ScopeOutcome.MISMATCH
        return cls(field=field, claim_value=claim_value, evidence_value=evidence_value, outcome=outcome)

    @model_validator(mode="after")
    def _unknown_never_matches(self) -> ScopeComparison:
        if self.outcome is ScopeOutcome.MATCH and (is_unknown(self.claim_value) or is_unknown(self.evidence_value)):
            raise ValueError("Trường unknown không được gộp thành match")
        return self


class SourceSearchResult(BaseModel):
    """Kết quả một lượt tìm kiếm của adapter nguồn (hợp đồng với Người 1).

    ``SourceAdapter.search(action, budget) -> SourceSearchResult``
    """

    model_config = ConfigDict(extra="forbid")

    source: Literal["pubmed", "dailymed", "faers"]
    query: str = Field(min_length=1, max_length=500)
    fingerprint: str = Field(min_length=1, max_length=200)
    status: SourceStatus = SourceStatus.OK
    documents: list[SourceDocument] = Field(default_factory=list)
    error: str | None = Field(default=None, max_length=1000)
    retryable: bool = False
    request_id: str = Field(default="", max_length=120)
    requests_used: int = Field(default=1, ge=0, le=MAX_SOURCE_REQUESTS)


class ScopeAssessment(BaseModel):
    """Kết quả so khớp phạm vi của một tập bằng chứng với claim.

    ``assess_scope(evidence, claim) -> ScopeAssessment``
    """

    model_config = ConfigDict(extra="forbid")

    outcome: ScopeOutcome
    comparisons: list[ScopeComparison] = Field(default_factory=list)
    matched_evidence_ids: list[str] = Field(default_factory=list)
    mismatched_evidence_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class EvidenceUnit(BaseModel):
    """Bằng chứng do node trích xuất (Người 3) tạo ra, gắn với một tài liệu gốc."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=120)
    doc_id: str = Field(min_length=1, max_length=120)
    source: Literal["pubmed", "dailymed", "faers"]
    stance: Stance
    quote: str = Field(min_length=1, max_length=2000)
    locator: QuoteLocator
    scope: EvidenceScope = Field(default_factory=EvidenceScope)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_type: EvidenceType = EvidenceType.OTHER
    version: int = Field(default=1, ge=1)
    excluded: bool = False
    notes: str = Field(default="", max_length=1000)


class AssessmentResult(BaseModel):
    """Kết luận của agent cho một claim (không bao giờ là nhân quả)."""

    model_config = ConfigDict(extra="forbid")

    assessment_status: AssessmentStatus
    rationale: str = Field(min_length=1, max_length=4000)
    evidence_ids: list[str] = Field(default_factory=list)
    scope_notes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


# --------------------------------------------------------------------------------------
# Models: khoảng trống bằng chứng, ngân sách, trạng thái điều tra
# --------------------------------------------------------------------------------------


class EvidenceGap(BaseModel):
    """Khoảng trống bằng chứng mà planner phải xử lý ở bước tiếp theo."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str = Field(min_length=1, max_length=120)
    kind: GapKind
    field: str | None = Field(default=None, max_length=60)
    description: str = Field(min_length=1, max_length=1000)
    priority: int = Field(default=1, ge=1, le=5)
    created_step: int = Field(default=0, ge=0)


class BudgetState(BaseModel):
    """Bộ đếm ngân sách của một cuộc điều tra (được lưu cùng state)."""

    model_config = ConfigDict(extra="forbid")

    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1, le=HARD_MAX_STEPS)
    max_documents: int = Field(default=DEFAULT_MAX_DOCUMENTS, ge=1, le=HARD_MAX_DOCUMENTS)
    max_source_requests: int = Field(default=MAX_SOURCE_REQUESTS, ge=1, le=MAX_SOURCE_REQUESTS)
    max_llm_calls: int = Field(default=MAX_LLM_CALLS, ge=1, le=MAX_LLM_CALLS)
    max_input_tokens: int = Field(default=MAX_INPUT_TOKENS, ge=1, le=MAX_INPUT_TOKENS)
    max_output_tokens: int = Field(default=MAX_OUTPUT_TOKENS, ge=1, le=MAX_OUTPUT_TOKENS)

    steps_used: int = Field(default=0, ge=0)
    documents_used: int = Field(default=0, ge=0)
    source_requests: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)

    reservations: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _counters_within_limits(self) -> BudgetState:
        for used, maximum, label in (
            (self.steps_used, self.max_steps, "steps"),
            (self.documents_used, self.max_documents, "documents"),
            (self.source_requests, self.max_source_requests, "source_requests"),
            (self.llm_calls, self.max_llm_calls, "llm_calls"),
            (self.input_tokens, self.max_input_tokens, "input_tokens"),
            (self.output_tokens, self.max_output_tokens, "output_tokens"),
        ):
            if used > maximum:
                raise ValueError(f"Vượt trần ngân sách: {label} {used} > {maximum}")
        return self

    @property
    def steps_remaining(self) -> int:
        return max(0, self.max_steps - self.steps_used)

    @property
    def documents_remaining(self) -> int:
        return max(0, self.max_documents - self.documents_used)


class InvestigationState(BaseModel):
    """Trạng thái xuyên suốt của agent trong LangGraph (lưu sau mỗi node)."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str = Field(min_length=1, max_length=120)
    claim: ClaimInput
    normalized_claim: NormalizedClaim | None = None
    run_status: RunStatus = RunStatus.QUEUED
    assessment_status: AssessmentStatus | None = None
    assessment: AssessmentResult | None = None
    budget: BudgetState = Field(default_factory=BudgetState)
    step_index: int = Field(default=0, ge=0, le=HARD_MAX_STEPS)
    gaps: list[EvidenceGap] = Field(default_factory=list)
    evidence: list[EvidenceUnit] = Field(default_factory=list)
    documents: list[SourceDocument] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    next_stage: str | None = Field(default=None, max_length=60)
    checkpoint: CheckpointKind | None = None
    stop_reason: StopReason | None = None
    no_progress_streak: int = Field(default=0, ge=0)
    searched_sources: list[str] = Field(default_factory=list)
    source_status: dict[str, SourceStatus] = Field(default_factory=dict)
    config: InvestigationConfig = Field(default_factory=InvestigationConfig)
    created_by: str = Field(default="anonymous", max_length=120)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def active_evidence(self) -> list[EvidenceUnit]:
        """Bằng chứng chưa bị reviewer loại bỏ."""
        return [item for item in self.evidence if not item.excluded]

    def has_document(self, doc_id: str) -> bool:
        return any(document.doc_id == doc_id for document in self.documents)


# --------------------------------------------------------------------------------------
# Models: quyết định của reviewer & hồ sơ
# --------------------------------------------------------------------------------------


class ReviewDecision(BaseModel):
    """Quyết định của reviewer.

    ``reviewer_id`` do server xác định từ token, KHÔNG bao giờ lấy từ body request.
    """

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=120)
    investigation_id: str = Field(min_length=1, max_length=120)
    checkpoint: CheckpointKind
    action: ReviewAction
    reviewer_id: str = Field(min_length=1, max_length=120)
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)
    target_evidence_id: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _action_requirements(self) -> ReviewDecision:
        if self.action in (ReviewAction.REJECT, ReviewAction.REQUEST_MORE) and not self.reason.strip():
            raise ValueError("Hành động reject/request_more phải kèm lý do")
        if self.action in (ReviewAction.EDIT_EVIDENCE, ReviewAction.EXCLUDE_EVIDENCE) and not self.target_evidence_id:
            raise ValueError("Hành động chỉnh sửa/loại bằng chứng phải kèm target_evidence_id")
        return self


class EvidenceReference(BaseModel):
    """Evidence and source versions pinned by a dossier statement (M06)."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=120)
    evidence_version: int = Field(ge=1)
    doc_id: str = Field(min_length=1, max_length=120)
    document_version: int = Field(ge=1)
    document_hash: str = Field(min_length=8, max_length=128)
    source_url: str = Field(min_length=1, max_length=1000)


class DossierStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["quote", "fact", "inference", "hypothesis"]
    text: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)


class DossierSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=8000)
    evidence_ids: list[str] = Field(default_factory=list)
    statements: list[DossierStatement] = Field(default_factory=list)


class Dossier(BaseModel):
    """Hồ sơ tổng hợp; chỉ phiên bản đã duyệt mới được export."""

    model_config = ConfigDict(extra="forbid")

    dossier_id: str = Field(min_length=1, max_length=120)
    investigation_id: str = Field(min_length=1, max_length=120)
    version: int = Field(default=1, ge=1)
    status: ReviewStatus = ReviewStatus.PENDING
    assessment_status: AssessmentStatus
    summary: str = Field(min_length=1, max_length=8000)
    sections: list[DossierSection] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_at: datetime | None = None
    approved_by: str | None = None
    content_hash: str = Field(default="", max_length=128)


# --------------------------------------------------------------------------------------
# Models: quyết định của planner/stopping, đặt trước ngân sách, kết quả review
# --------------------------------------------------------------------------------------


class PlannerDecision(BaseModel):
    """Hành động tiếp theo do planner chọn (một bước nghiệp vụ)."""

    model_config = ConfigDict(extra="forbid")

    action: PlannerActionKind
    source: str | None = Field(default=None, max_length=40)
    query: str | None = Field(default=None, max_length=500)
    fingerprint: str | None = Field(default=None, max_length=200)
    gap_id: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def _search_needs_target(self) -> PlannerDecision:
        if self.action in (
            PlannerActionKind.SEARCH_SOURCE,
            PlannerActionKind.CHANGE_QUERY,
            PlannerActionKind.CHANGE_SOURCE,
        ):
            if not self.source or not self.query:
                raise ValueError("Hành động tìm kiếm phải kèm source và query")
        return self


class StopDecision(BaseModel):
    """Kết quả đánh giá dừng/tiếp tục của agent."""

    model_config = ConfigDict(extra="forbid")

    should_stop: bool
    reason: StopReason | None = None
    run_status: RunStatus = RunStatus.RUNNING
    assessment_status: AssessmentStatus | None = None
    message: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _stop_has_reason(self) -> StopDecision:
        if self.should_stop and self.reason is None:
            raise ValueError("Quyết định dừng phải kèm lý do")
        return self


class BudgetReservation(BaseModel):
    """Kết quả đặt trước ngân sách cho một thao tác (idempotent theo operation_key)."""

    model_config = ConfigDict(extra="forbid")

    operation_key: str = Field(min_length=1, max_length=200)
    granted: bool
    amounts: dict[str, int] = Field(default_factory=dict)
    remaining: dict[str, int] = Field(default_factory=dict)
    reason: str = Field(default="", max_length=500)


class ReviewResult(BaseModel):
    """Kết quả áp dụng một quyết định review."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    version: int = Field(ge=1)
    run_status: RunStatus
    review_status: ReviewStatus
    invalidated: list[str] = Field(default_factory=list)
    message: str = Field(default="", max_length=1000)


class ValidationReport(BaseModel):
    """Báo cáo kiểm tra tính hợp lệ của hồ sơ trước khi cho phép export."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CancelResponse(BaseModel):
    """Phản hồi sau khi yêu cầu hủy cuộc điều tra."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    run_status: RunStatus
    cancelled: bool
    message: str = ""


# --------------------------------------------------------------------------------------
# Mô hình phản hồi HTTP (API-01)
#
# Trước đây các điểm cuối dưới đây khai ``-> dict[str, Any]`` nên OpenAPI chỉ ghi ``object``:
# hợp đồng không nói được trường nào tồn tại, và giao diện phải đoán. Phần bao ngoài được mô
# hình hoá chặt; các khối JSON sâu bên trong (claim, ngân sách, bằng chứng) vẫn để dạng dict vì
# chúng được đọc thẳng từ bản ghi cũ và không nên bị lọc lại khi trả về.
# --------------------------------------------------------------------------------------


class CreateInvestigationResponse(BaseModel):
    """202 khi tạo cuộc điều tra mới."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    created: bool
    started: bool
    run_status: str
    version: int = Field(ge=1)
    events_url: str


class InvestigationSummary(BaseModel):
    """Một dòng trong danh sách cuộc điều tra."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    run_status: str
    assessment_status: str | None = None
    checkpoint: str | None = None
    next_stage: str | None = None
    version: int = Field(ge=1)
    drug: str | None = None
    event: str | None = None
    review_status: str | None = None
    last_review: dict[str, Any] | None = None
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class InvestigationListResponse(BaseModel):
    """Danh sách có phân trang; ``scope`` nói rõ đang nhìn thấy ca của ai."""

    model_config = ConfigDict(extra="forbid")

    items: list[InvestigationSummary]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
    scope: Literal["own", "any"]


class InvestigationDetailResponse(BaseModel):
    """Trạng thái đầy đủ để giao diện polling."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    created_at: str | None = None
    updated_at: str | None = None
    claim: dict[str, Any]
    normalized_claim: dict[str, Any] | None = None
    run_status: str
    assessment_status: str | None = None
    assessment: dict[str, Any] | None = None
    stop_reason: str | None = None
    checkpoint: str | None = None
    next_stage: str | None = None
    review_status: str | None = None
    last_review: dict[str, Any] | None = None
    version: int = Field(ge=1)
    budget: dict[str, Any]
    step_index: int = Field(ge=0)
    searched_sources: list[str] = Field(default_factory=list)
    source_status: dict[str, str] = Field(default_factory=dict)
    counters: dict[str, int] = Field(default_factory=dict)
    gaps: list[dict[str, Any]] = Field(default_factory=list)


class EventListResponse(BaseModel):
    """Timeline tiến trình cho polling."""

    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, Any]] = Field(default_factory=list)
    last_id: int = Field(ge=0)


class EvidenceListResponse(BaseModel):
    """Bằng chứng kèm tài liệu nguồn và kết quả so khớp phạm vi."""

    model_config = ConfigDict(extra="forbid")

    items: list[dict[str, Any]] = Field(default_factory=list)
    active_count: int = Field(ge=0)


class DocumentResponse(BaseModel):
    """Nội dung tài liệu gốc + locator để đối chiếu trích dẫn."""

    model_config = ConfigDict(extra="forbid")

    document: SourceDocument
    locators: list[dict[str, Any]] = Field(default_factory=list)


class DossierResponse(BaseModel):
    """Hồ sơ nháp hoặc đã duyệt gần nhất, kèm báo cáo kiểm tra."""

    model_config = ConfigDict(extra="forbid")

    dossier: Dossier | None = None
    approved: Dossier | None = None
    validation: ValidationReport | None = None


class ContinueResponse(BaseModel):
    """202 khi chạy tiếp; ``resumed=False`` nghĩa là yêu cầu trùng đã được xử lý."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    run_status: str
    resumed: bool
    detail: str | None = None


class TraceResponse(BaseModel):
    """Vết suy luận, các bước chạy LLM và tình trạng ngân sách."""

    model_config = ConfigDict(extra="forbid")

    investigation_id: str
    run_status: str
    step_index: int = Field(ge=0)
    budget: dict[str, Any]
    counters: dict[str, int] = Field(default_factory=dict)
    traces: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Tiện ích dùng chung
# --------------------------------------------------------------------------------------


def _normalize_value(value: str) -> str:
    return " ".join(value.casefold().split())


def is_unknown(value: str | None) -> bool:
    """True nếu giá trị trống/không xác định (không được coi là match)."""
    if value is None:
        return True
    return _normalize_value(value) in UNKNOWN_TOKENS


def compare_scope(claim: NormalizedClaim | ClaimInput, evidence: EvidenceScope) -> list[ScopeComparison]:
    """So khớp các trường scope giữa claim và bằng chứng."""
    pairs = (
        ("population", getattr(claim, "population", None), evidence.population),
        ("dose", getattr(claim, "dose", None), evidence.dose),
        ("route", getattr(claim, "route", None), evidence.route),
        ("time_window", getattr(claim, "time_window", None), evidence.time_window),
    )
    return [ScopeComparison.compare(field, claim_value, evidence_value) for field, claim_value, evidence_value in pairs]


def validate_budget_ceiling(max_steps: int, max_documents: int) -> None:
    """Chặn cấu hình vượt trần cứng 20 steps / 100 docs."""
    if max_steps > HARD_MAX_STEPS:
        raise ValueError(f"max_steps vượt trần cứng {HARD_MAX_STEPS}")
    if max_documents > HARD_MAX_DOCUMENTS:
        raise ValueError(f"max_documents vượt trần cứng {HARD_MAX_DOCUMENTS}")


# --------------------------------------------------------------------------------------
# Models của template cũ (giữ để tương thích ngược)
# --------------------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")
