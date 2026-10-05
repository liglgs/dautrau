"""Bộ điều khiển ngân sách (M05).

Quy tắc (planMVPfinal §4.3, QUY_TAC §6):
  * mặc định 8 bước / 50 tài liệu, trần cứng 20 bước / 100 tài liệu;
  * một bước nghiệp vụ = một quyết định truy xuất (cache hit vẫn tính);
  * tài liệu chỉ được đếm một lần theo ``(source, source_id, version)`` hoặc ``hash``;
  * trần kỹ thuật: 80 request nguồn, 80 lượt gọi LLM, 150k token vào, 25k token ra;
  * **giữ dự phòng** 1 bước + 2 lượt gọi LLM cho bước tạo hồ sơ/abstain;
  * đặt trước (reserve) theo ``operation_key`` là idempotent: gọi lại không trừ thêm.
"""

from __future__ import annotations

from src.models.schemas import (
    RESERVED_STEPS_FOR_DOSSIER,
    BudgetReservation,
    BudgetState,
    InvestigationState,
    SourceDocument,
)
from src.services.errors import budget_exhausted, invalid_state
from src.services.store import MvpStore


def dossier_step_available(budget: BudgetState) -> bool:
    """Còn ít nhất 1 bước dành cho hồ sơ/abstain?"""
    return budget.steps_used + RESERVED_STEPS_FOR_DOSSIER <= budget.max_steps


def can_spend(
    budget: BudgetState,
    *,
    steps: int = 0,
    documents: int = 0,
    source_requests: int = 0,
    keep_dossier_reserve: bool = True,
) -> tuple[bool, str]:
    """Kiểm tra còn ngân sách cho một thao tác (không thay đổi gì)."""
    step_limit = budget.max_steps - (RESERVED_STEPS_FOR_DOSSIER if keep_dossier_reserve else 0)
    if budget.steps_used + steps > step_limit:
        return False, f"Hết ngân sách bước ({budget.steps_used}+{steps}>{step_limit})"
    if budget.documents_used + documents > budget.max_documents:
        return False, f"Hết ngân sách tài liệu ({budget.documents_used}+{documents}>{budget.max_documents})"
    if budget.source_requests + source_requests > budget.max_source_requests:
        return False, f"Hết ngân sách request nguồn ({budget.source_requests}+{source_requests})"
    return True, ""


def count_new_documents(state: InvestigationState, documents: list[SourceDocument]) -> int:
    """Đếm tài liệu MỚI (chưa từng đếm) theo doc_id và theo hash."""
    seen_ids = {document.doc_id for document in state.documents}
    seen_hashes = {document.hash for document in state.documents}
    counted: set[str] = set()
    fresh = 0
    for document in documents:
        if document.doc_id in seen_ids or document.hash in seen_hashes or document.hash in counted:
            continue
        counted.add(document.hash)
        fresh += 1
    return fresh


class BudgetController:
    """Đặt trước / cam kết / giải phóng ngân sách, lưu bền vững cùng state."""

    def __init__(self, store: MvpStore):
        self.store = store

    def reserve(
        self,
        state: InvestigationState,
        operation_key: str,
        *,
        steps: int = 1,
        documents: int = 0,
        source_requests: int = 1,
        keep_dossier_reserve: bool = True,
    ) -> tuple[InvestigationState, BudgetReservation]:
        """Đặt trước ngân sách; idempotent theo ``operation_key``."""
        budget = state.budget
        existing = budget.reservations.get(operation_key)
        if existing is not None:
            return state, BudgetReservation(
                operation_key=operation_key,
                granted=True,
                amounts={"steps": existing},
                remaining={"steps": budget.steps_remaining, "documents": budget.documents_remaining},
                reason="Đã đặt trước trước đó (idempotent).",
            )
        ok, reason = can_spend(
            budget,
            steps=steps,
            documents=documents,
            source_requests=source_requests,
            keep_dossier_reserve=keep_dossier_reserve,
        )
        if not ok:
            return state, BudgetReservation(
                operation_key=operation_key,
                granted=False,
                amounts={"steps": steps, "documents": documents, "source_requests": source_requests},
                remaining={"steps": budget.steps_remaining, "documents": budget.documents_remaining},
                reason=reason,
            )
        budget.reservations[operation_key] = steps
        saved = self.store.save_state(state, expected_version=state.version)
        return saved, BudgetReservation(
            operation_key=operation_key,
            granted=True,
            amounts={"steps": steps, "documents": documents, "source_requests": source_requests},
            remaining={"steps": budget.steps_remaining, "documents": budget.documents_remaining},
            reason="",
        )

    def commit(
        self,
        state: InvestigationState,
        operation_key: str,
        *,
        documents: int = 0,
        source_requests: int = 0,
    ) -> InvestigationState:
        """Chuyển đặt trước thành đã dùng và cộng tài liệu/request thực tế."""
        reserved = state.budget.reservations.pop(operation_key, None)
        if reserved is None:
            raise invalid_state(
                "Không có đặt trước ngân sách cho thao tác này.", {"operation_key": operation_key}
            )
        budget = state.budget
        budget.steps_used += reserved
        budget.documents_used += documents
        budget.source_requests += source_requests
        if budget.steps_used > budget.max_steps:
            raise budget_exhausted("Vượt trần bước sau khi cam kết ngân sách.", {"steps_used": budget.steps_used})
        if budget.documents_used > budget.max_documents:
            # Vượt trần tài liệu làm state không còn đọc được (BudgetState từ chối) ⇒ chặn trước khi lưu.
            raise budget_exhausted(
                "Vượt trần tài liệu sau khi cam kết ngân sách.",
                {"documents_used": budget.documents_used, "max_documents": budget.max_documents},
            )
        return self.store.save_state(state, expected_version=state.version)

    def release(self, state: InvestigationState, operation_key: str) -> InvestigationState:
        if state.budget.reservations.pop(operation_key, None) is None:
            return state
        return self.store.save_state(state, expected_version=state.version)
