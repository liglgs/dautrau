"""Endpoint quản trị mức tối thiểu cho Đợt 1 (AUTH-03).

Hiện chỉ có nhật ký kiểm toán — thứ cần để trả lời câu hỏi "ai đã duyệt hồ sơ này". Các trang
quản trị còn lại (tài khoản, ngân sách, chính sách) thuộc Đợt 2 và sẽ thêm vào cùng tiền tố.

Quyền: ``audit:read:own`` xem được nhật ký ca của mình và hành động của chính mình;
``audit:read:any`` (quản trị, kiểm toán) xem được toàn bộ.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from src.api.auth import Principal, current_principal
from src.api.investigations import StoreDep
from src.services.identity import Permission

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_audit_read(principal: Principal) -> bool:
    """Trả ``True`` nếu được đọc toàn bộ; ném 403 nếu không có quyền đọc nào."""
    from src.services.errors import forbidden

    if principal.has(Permission.AUDIT_READ_ANY):
        return True
    if principal.has(Permission.AUDIT_READ_OWN):
        return False
    raise forbidden(f"Vai {principal.role} không có quyền đọc nhật ký.")


@router.get("/audit")
async def read_audit(
    store: StoreDep,
    user: Annotated[Principal, Depends(current_principal)],
    investigation_id: str | None = Query(default=None),
    actor: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    format: str = Query(default="json", pattern="^(json|jsonl)$"),
) -> Any:
    """Nhật ký append-only, lọc được theo ca và theo người.

    ``format=jsonl`` trả mỗi bản ghi một dòng — dạng dùng để đối chiếu ngoài hệ thống.
    """
    see_all = _require_audit_read(user)
    if see_all:
        rows = store.list_audit(investigation_id, limit=limit, actor=actor)
    else:
        rows = store.list_audit_scoped(
            user_id=user.user_id, limit=limit, investigation_id=investigation_id, actor=actor
        )
    if format == "jsonl":
        body = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        return Response(content=f"{body}\n" if body else "", media_type="application/x-ndjson")
    return {"items": rows, "count": len(rows), "scope": "any" if see_all else "own"}
