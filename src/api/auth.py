"""Xác thực bằng token và session cookie cho API MVP (M07).

Hỗ trợ 2 phương thức xác thực song song:
  1. Cookie session: ``session_id`` (HttpOnly) phục vụ Web Frontend/SPA;
  2. Static token: ``INVESTIGATOR_TOKEN`` và ``REVIEWER_TOKEN`` (qua ``X-API-Token`` hoặc ``Bearer``).

Token/Session quyết định **role**, và role quyết định hành động được phép:
  * ``investigator`` — tạo cuộc điều tra, hủy/chạy tiếp ca của mình, đọc dữ liệu;
  * ``reviewer``     — duyệt/từ chối/sửa; toàn quyền trên mọi cuộc điều tra.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from src.config import get_settings
from src.models.schemas import InvestigationState
from src.services.errors import forbidden, unauthorized

SESSION_COOKIE_NAME = "session_id"


class Role(StrEnum):
    INVESTIGATOR = "investigator"
    REVIEWER = "reviewer"


#: Danh tính mặc định gắn với từng token.
ROLE_ACTOR: dict[Role, str] = {
    Role.INVESTIGATOR: "investigator",
    Role.REVIEWER: "reviewer",
}

#: Header ưu tiên; vẫn chấp nhận ``Authorization: Bearer <token>`` cho tiện dụng cụ.
TOKEN_HEADER = "X-API-Token"


class UserSession(BaseModel):
    """Thông tin phiên người dùng xác thực."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=120)
    role: Role


class LoginRequest(BaseModel):
    """Yêu cầu đăng nhập hoặc khởi tạo phiên."""

    model_config = ConfigDict(extra="ignore")

    token: str | None = None
    username: str | None = None
    password: str | None = None
    role: Role | None = None


def _token_from_request(request: Request) -> str | None:
    token = request.headers.get(TOKEN_HEADER)
    if token:
        return token.strip()
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _role_for_token(token: str) -> Role | None:
    settings = get_settings()
    candidates = {
        Role.INVESTIGATOR: settings.investigator_token,
        Role.REVIEWER: settings.reviewer_token,
    }
    for role, configured in candidates.items():
        if configured and token == configured:
            return role
    return None


def current_user(request: Request) -> UserSession:
    """Dependency: lấy UserSession hiện tại từ cookie hoặc token; 401 nếu không hợp lệ."""
    # 1. Kiểm tra session cookie
    cookie_session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_session_id:
        from src.api.mvp_runtime import get_mvp_store

        store = get_mvp_store()
        session_data = store.get_session(cookie_session_id)
        if session_data is not None:
            return UserSession(user_id=session_data["user_id"], role=Role(session_data["role"]))

    # 2. Fallback sang header token
    token = _token_from_request(request)
    if token:
        role = _role_for_token(token)
        if role is not None:
            return UserSession(user_id=ROLE_ACTOR[role], role=role)
        raise unauthorized("Token không hợp lệ.")

    raise unauthorized(f"Thiếu thông tin xác thực ({SESSION_COOKIE_NAME} cookie, {TOKEN_HEADER} hoặc Authorization: Bearer).")


def current_role(request: Request) -> Role:
    """Dependency: trả role hợp lệ hoặc 401 (tương thích ngược 100%)."""
    return current_user(request).role


def require_reviewer(request: Request) -> Role:
    """Dependency: chỉ reviewer được gửi quyết định duyệt."""
    user = current_user(request)
    if user.role is not Role.REVIEWER:
        raise forbidden("Chỉ reviewer được thực hiện hành động này.")
    return user.role


def check_ownership(state: InvestigationState, user: UserSession) -> None:
    """Kiểm tra quyền sở hữu cuộc điều tra: Reviewer có toàn quyền; Investigator chỉ thao tác ca của mình."""
    if user.role is Role.REVIEWER:
        return
    if state.created_by in ("anonymous", user.user_id):
        return
    raise forbidden("Bạn không có quyền thao tác trên cuộc điều tra này.")


def actor_for(role: Role) -> str:
    """Danh tính ghi vào audit/review decision."""
    return ROLE_ACTOR[role]


# --------------------------------------------------------------------------------------
# Router xác thực /auth
# --------------------------------------------------------------------------------------

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest, response: Response) -> dict[str, str]:
    """Đăng nhập bằng token hoặc username/role và cấp cookie session HttpOnly."""
    from src.api.mvp_runtime import get_mvp_store

    store = get_mvp_store()
    role = payload.role
    user_id = payload.username

    if payload.token:
        matched_role = _role_for_token(payload.token)
        if matched_role is None:
            raise unauthorized("Token không hợp lệ.")
        role = matched_role
        user_id = user_id or ROLE_ACTOR[role]
    elif role is not None:
        user_id = user_id or f"{role}-user"
    elif user_id in (Role.INVESTIGATOR.value, Role.REVIEWER.value):
        role = Role(user_id)
    else:
        raise unauthorized("Cần cung cấp token hoặc role để đăng nhập.")

    session_id = store.create_session(user_id=user_id, role=str(role))
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=86400,
    )
    return {
        "user_id": user_id,
        "role": str(role),
        "session_id": session_id,
    }


@router.post("/logout")
async def logout(response: Response, session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None) -> dict[str, bool]:
    """Đăng xuất, xóa session khỏi store và hủy cookie."""
    if session_id:
        from src.api.mvp_runtime import get_mvp_store

        get_mvp_store().delete_session(session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/me")
async def me(user: Annotated[UserSession, Depends(current_user)]) -> dict[str, str]:
    """Trả thông tin người dùng và vai trò của phiên hiện tại."""
    return {
        "user_id": user.user_id,
        "role": str(user.role),
    }
