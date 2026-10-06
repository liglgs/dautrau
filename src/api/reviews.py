"""Endpoint quyết định của reviewer (M07).

Tách riêng khỏi ``investigations.py`` để ranh giới quyền rõ ràng: mọi route ở đây đều
yêu cầu quyền ``review:decide`` (403 nếu tài khoản không có quyền đó). Danh tính reviewer
luôn lấy từ phiên ở server — body không được phép khai báo ``reviewer_id``, và người tạo
ca không được tự duyệt ca của mình.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.api.auth import Principal, actor_for, assert_can_decide, require_reviewer
from src.api.investigations import StoreDep, _state
from src.models.schemas import (
    MIN_REVIEW_REASON,
    CheckpointKind,
    ReviewAction,
    ReviewDecision,
    ReviewResult,
)
from src.services.errors import invalid_request
from src.services.review import apply_review

router = APIRouter(prefix="/investigations", tags=["mvp-review"])

ReviewerDep = Annotated[Principal, Depends(require_reviewer)]


class ReviewRequest(BaseModel):
    """Body của reviewer; ``reviewer_id`` do server gán từ token."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=120)
    action: ReviewAction
    checkpoint: CheckpointKind
    expected_version: int = Field(ge=1)
    reason: str = Field(max_length=2000)
    target_evidence_id: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason")
    @classmethod
    def _reason_length_matches_ui(cls, value: str) -> str:
        """RV-04: cùng ngưỡng với giao diện, tính trên phần đã bỏ khoảng trắng hai đầu."""
        if len(value.strip()) < MIN_REVIEW_REASON:
            raise ValueError(f"lý do phải có ít nhất {MIN_REVIEW_REASON} ký tự")
        return value


@router.post("/{investigation_id}/reviews", response_model=ReviewResult)
async def submit_review(
    investigation_id: str,
    payload: ReviewRequest,
    store: StoreDep,
    user: ReviewerDep,
) -> ReviewResult:
    """Gửi quyết định của reviewer; danh tính lấy từ phiên ở server."""
    state = _state(store, investigation_id)
    # B1.5 — người tạo ca không được tự duyệt ca của mình, kể cả khi có quyền ``review:decide``.
    assert_can_decide(state, user)
    try:
        decision = ReviewDecision(
            decision_id=payload.decision_id,
            investigation_id=investigation_id,
            checkpoint=payload.checkpoint,
            action=payload.action,
            reviewer_id=actor_for(user),
            expected_version=payload.expected_version,
            reason=payload.reason,
            target_evidence_id=payload.target_evidence_id,
            payload=payload.payload,
        )
    except ValidationError as exc:
        # Chỉ giữ phần JSON-able: ``errors()`` có thể chứa ``ctx.error`` là Exception.
        details = [
            {"loc": list(item.get("loc", ())), "msg": item.get("msg", ""), "type": item.get("type", "")}
            for item in exc.errors()
        ]
        raise invalid_request("Quyết định review không hợp lệ.", {"errors": details}) from exc
    return apply_review(store, decision, actor_role=str(user.role))
