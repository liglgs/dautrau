"""Endpoint quyết định của reviewer (M07).

Tách riêng khỏi ``investigations.py`` để ranh giới quyền rõ ràng: mọi route ở đây đều
yêu cầu role ``reviewer`` (403 nếu chỉ có token investigator). Danh tính reviewer luôn
lấy từ token ở server — body không được phép khai báo ``reviewer_id``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.api.auth import Role, actor_for, require_reviewer
from src.api.investigations import StoreDep, _state
from src.models.schemas import CheckpointKind, ReviewAction, ReviewDecision
from src.services.errors import invalid_request
from src.services.review import apply_review

router = APIRouter(prefix="/investigations", tags=["mvp-review"])

ReviewerDep = Annotated[Role, Depends(require_reviewer)]


class ReviewRequest(BaseModel):
    """Body của reviewer; ``reviewer_id`` do server gán từ token."""

    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=120)
    action: ReviewAction
    checkpoint: CheckpointKind
    expected_version: int = Field(ge=1)
    reason: str = Field(default="", max_length=2000)
    target_evidence_id: str | None = Field(default=None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/{investigation_id}/reviews")
async def submit_review(
    investigation_id: str,
    payload: ReviewRequest,
    store: StoreDep,
    role: ReviewerDep,
) -> dict[str, Any]:
    """Gửi quyết định của reviewer; danh tính lấy từ token ở server."""
    _state(store, investigation_id)
    try:
        decision = ReviewDecision(
            decision_id=payload.decision_id,
            investigation_id=investigation_id,
            checkpoint=payload.checkpoint,
            action=payload.action,
            reviewer_id=actor_for(role),
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
    result = apply_review(store, decision)
    return result.model_dump()
