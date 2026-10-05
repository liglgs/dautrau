"""Trạng thái LangGraph cho MVP điều tra an toàn thuốc (M05)."""

from __future__ import annotations

from typing import Any, TypedDict

from src.models.schemas import InvestigationState, PlannerDecision, StopDecision
from src.services.runner import RunContext


class AgentState(TypedDict, total=False):
    """State schema cho LangGraph agent.

    Mỗi node đọc và ghi vào state này.
    total=False cho phép tất cả fields là optional.
    """

    query: str
    context: str
    analysis: str
    response: str
    error: str
    metadata: dict


class MvpGraphState(TypedDict, total=False):
    """State của graph MVP.

    ``investigation`` là state nghiệp vụ bền vững (được lưu sau mỗi node);
    ``ctx`` là bối cảnh chạy (store, gateway, adapter) — chỉ sống trong một lượt chạy.
    """

    investigation: InvestigationState
    ctx: RunContext
    scenario: dict[str, Any]
    decision: PlannerDecision | None
    stop: StopDecision | None
    evidence_before: int
    gaps_before: int
