"""Xác thực và phân quyền cho API VigiLens (R2-2-07 / B1).

Ba lỗ hổng đã bịt ở đây:

* **AUTH-01** — không còn nhánh "tự khai vai". Danh tính chỉ đến từ :class:`IdentityProvider`;
  gọi thẳng cổng backend mà không có credential hợp lệ thì 401, và đổi header vai ở trình duyệt
  không đổi được quyền.
* **AUTH-02** — mọi tuyến đọc/ghi ca đều đi qua :func:`require_investigation_access`; không có
  quyền thì trả **404** (không phải 403) để không tiết lộ ca có tồn tại hay không.
* **AUTH-03** — :func:`actor_for` trả **mã người**, không trả chuỗi vai.

Chuỗi xác thực: ``cookie phiên`` → ``khoá máy (api_tokens)`` → ``khoá tĩnh cũ (ngoài production)``
→ ``X-Test-User (chỉ khi bật cờ)``. Không nhánh nào nhận vai do người gọi khai.
"""

from __future__ import annotations

import secrets
from typing import Annotated, Any, Protocol

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from src.config import get_settings
from src.models.schemas import InvestigationState
from src.services.errors import MvpError, forbidden, not_found, unauthorized
from src.services.identity import (
    ROLE_LABELS,
    Permission,
    Role,
    looks_like_token,
    permissions_for,
)

SESSION_COOKIE_NAME = "session_id"

#: Header ưu tiên; vẫn chấp nhận ``Authorization: Bearer <token>`` cho tiện dụng cụ.
TOKEN_HEADER = "X-API-Token"

#: Mã lỗi riêng cho tách biệt nhiệm vụ (B1.5) — nằm trong ``details`` để không phải mở rộng enum.
SELF_REVIEW_FORBIDDEN = "SELF_REVIEW_FORBIDDEN"

#: Ca tạo trước khi có xác thực mang mã này; không ai "sở hữu" nó.
LEGACY_ANONYMOUS = "anonymous"


class Principal(BaseModel):
    """Danh tính đã xác minh. Thay cho ``UserSession`` cũ (giữ tên cũ làm bí danh)."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=120)
    email: str = ""
    display_name: str = ""
    role: Role
    #: ``local_session`` | ``api_token`` | ``legacy_token`` | ``supabase`` | ``test``
    auth_method: str = "local"

    def has(self, permission: Permission) -> bool:
        return permission in permissions_for(self.role)

    def has_any(self, *permissions: Permission) -> bool:
        return any(self.has(permission) for permission in permissions)


#: Tương thích ngược: mã cũ gọi lớp này là ``UserSession``.
UserSession = Principal


# --------------------------------------------------------------------------------------
# Nhà cung cấp danh tính
# --------------------------------------------------------------------------------------


class IdentityProvider(Protocol):
    """Một hàm duy nhất: ``verify(request) -> Principal``, ném 401 khi không xác minh được."""

    name: str

    def verify(self, request: Request) -> Principal: ...


def _token_from_request(request: Request) -> str | None:
    token = request.headers.get(TOKEN_HEADER)
    if token:
        return token.strip()
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _principal_from_row(row: Any, *, auth_method: str) -> Principal:
    return Principal(
        user_id=row["user_id"],
        email=row["email"] or "",
        display_name=row["display_name"] or "",
        role=Role(row["role"]),
        auth_method=auth_method,
    )


def _legacy_static_token(token: str) -> Principal | None:
    """``INVESTIGATOR_TOKEN``/``REVIEWER_TOKEN`` — khoá tạm, **khai tử ở production**.

    Giữ lại một thời gian chỉ để chạy thử ngoại tuyến. Ánh xạ sang tài khoản cố định và đánh dấu
    ``auth_method="legacy_token"`` để nhật ký ghi rõ đây là khoá tạm, không phải danh tính thật.
    """
    settings = get_settings()
    if settings.app_env == "production":
        return None
    candidates = {
        Role.INVESTIGATOR: settings.investigator_token,
        Role.REVIEWER: settings.reviewer_token,
    }
    for role, configured in candidates.items():
        if configured and secrets.compare_digest(token, configured):
            return Principal(
                user_id=f"legacy-{role.value}",
                email="",
                display_name=f"Khoá tạm ({ROLE_LABELS[role]})",
                role=role,
                auth_method="legacy_token",
            )
    return None


class LocalProvider:
    """Chế độ nội bộ: phiên cookie, khoá máy trong ``api_tokens``, và khoá tĩnh cũ ngoài production."""

    name = "local"

    def verify(self, request: Request) -> Principal:
        from src.api.mvp_runtime import get_mvp_store

        store = get_mvp_store()

        # 1. Phiên nội bộ. Vai **không** lấy từ bản ghi phiên: đọc lại từ ``app_users`` để đổi vai
        #    hoặc khoá tài khoản có hiệu lực ngay, không phải chờ phiên hết hạn.
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if session_id:
            session = store.get_session(session_id)
            if session is not None:
                user = store.get_user(session["user_id"])
                if user is not None and user["status"] == "active":
                    return _principal_from_row(user, auth_method="local_session")

        # 2. Khoá máy.
        token = _token_from_request(request)
        if token:
            if looks_like_token(token):
                row = store.resolve_token(token)
                if row is not None:
                    return _principal_from_row(row, auth_method="api_token")
                raise unauthorized("Khoá máy không hợp lệ, đã thu hồi hoặc hết hạn.")
            legacy = _legacy_static_token(token)
            if legacy is not None:
                return legacy
            raise unauthorized("Token không hợp lệ.")

        raise unauthorized(
            f"Thiếu thông tin xác thực ({SESSION_COOKIE_NAME} cookie, {TOKEN_HEADER} hoặc Authorization: Bearer)."
        )


class SupabaseProvider:
    """Chế độ Supabase: kiểm chữ ký JWT bằng JWKS của dự án, vai tra từ ``app_users``.

    Không gọi mạng trong bài kiểm thử: chế độ này chỉ được chọn khi có ``SUPABASE_URL``.
    """

    name = "supabase"

    def __init__(self) -> None:
        self._jwks: dict[str, Any] | None = None
        self._jwks_at: float = 0.0

    def _load_jwks(self) -> dict[str, Any]:
        import json
        import time
        import urllib.request

        settings = get_settings()
        # Đệm 5 phút: JWKS gần như không đổi, mà gọi mỗi request thì chậm và dễ bị chặn.
        if self._jwks is not None and (time.monotonic() - self._jwks_at) < 300:
            return self._jwks
        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - URL do cấu hình, không do người dùng
            payload = json.loads(response.read().decode("utf-8"))
        self._jwks, self._jwks_at = payload, time.monotonic()
        return payload

    def _decode(self, token: str) -> dict[str, Any]:
        import jwt  # PyJWT; nhập muộn để chế độ local không cần thư viện này

        settings = get_settings()
        jwks = self._load_jwks()
        keys = {key.get("kid"): key for key in jwks.get("keys", [])}
        header = jwt.get_unverified_header(token)
        key = keys.get(header.get("kid"))
        if key is None:
            raise unauthorized("Khoá ký của Supabase không nhận ra được.")

        # Supabase dùng khoá bất đối xứng (ES256/RS256) từ JWKS. Chỉ nhận đúng họ khoá của
        # ``kty`` trong JWKS — không tin ``alg`` trong header để tránh tấn công đổi thuật toán.
        if key.get("kty") == "EC":
            from jwt.algorithms import ECAlgorithm

            signing_key = ECAlgorithm.from_jwk(key)
        else:
            from jwt.algorithms import RSAAlgorithm

            signing_key = RSAAlgorithm.from_jwk(key)

        return jwt.decode(
            token,
            signing_key,
            algorithms=[str(header.get("alg", "ES256"))],
            audience=settings.supabase_jwt_audience,
            options={"verify_exp": True},
        )

    def verify(self, request: Request) -> Principal:
        token = _token_from_request(request)
        if not token:
            raise unauthorized("Thiếu Authorization: Bearer <access_token> của Supabase.")
        try:
            claims = self._decode(token)
        except MvpError:
            raise
        except Exception as exc:  # noqa: BLE001 - mọi lỗi giải mã đều là 401
            raise unauthorized(f"Access token của Supabase không hợp lệ: {exc}") from exc

        user_id = str(claims.get("sub") or "")
        if not user_id:
            raise unauthorized("Access token thiếu trường ``sub``.")

        from src.api.mvp_runtime import get_mvp_store

        user = get_mvp_store().get_user(user_id)
        if user is None or user["status"] != "active":
            raise unauthorized("Tài khoản chưa được cấp quyền trong hệ thống hoặc đã bị khoá.")
        return _principal_from_row(user, auth_method="supabase")


class TestProvider:
    """Chỉ trong bộ kiểm thử: ``X-Test-User: <user_id>[:<role>]`` khi bật ``VIGILENS_TEST_AUTH=1``.

    Tuyệt đối không bật ở production — kiểm tra ``app_env`` trước khi đọc header.
    """

    name = "test"
    HEADER = "X-Test-User"

    def verify(self, request: Request) -> Principal:
        settings = get_settings()
        if settings.app_env == "production":
            raise unauthorized("Xác thực thử nghiệm bị chặn ở production.")
        if not settings.vigilens_test_auth:
            raise unauthorized("Xác thực thử nghiệm chưa bật (VIGILENS_TEST_AUTH=1).")
        raw = (request.headers.get(self.HEADER) or "").strip()
        if not raw:
            raise unauthorized(f"Thiếu header {self.HEADER}.")

        from src.api.mvp_runtime import get_mvp_store

        user_id, _, role_value = raw.partition(":")
        if role_value:
            try:
                role = Role(role_value)
            except ValueError as exc:
                raise unauthorized(f"Vai không hợp lệ trong {self.HEADER}: {role_value}") from exc
        else:
            role = Role.INVESTIGATOR

        store = get_mvp_store()
        user = store.get_user(user_id)
        if user is None:
            user = store.create_user(
                user_id=user_id,
                email=f"{user_id}@test.local",
                role=str(role),
                display_name=user_id,
                created_by="test-provider",
            )
        elif role_value and user["role"] != str(role):
            user = store.update_user(user_id, role=str(role))
        if user is None or user["status"] != "active":
            raise unauthorized("Tài khoản thử nghiệm đang bị khoá.")
        return _principal_from_row(user, auth_method="test")


def provider_chain() -> list[IdentityProvider]:
    """Chuỗi nhà cung cấp theo cấu hình. Thử lần lượt; cái đầu tiên xác minh được thì thắng."""
    settings = get_settings()
    mode = settings.auth_provider
    chain: list[IdentityProvider] = []
    if mode == "supabase" or (mode == "auto" and settings.supabase_url):
        chain.append(SupabaseProvider())
    elif mode == "test":
        pass
    else:
        chain.append(LocalProvider())
    if settings.vigilens_test_auth and settings.app_env != "production":
        chain.append(TestProvider())
    return chain


def current_principal(request: Request) -> Principal:
    """Dependency: danh tính đã xác minh; 401 nếu không nhà cung cấp nào xác minh được."""
    last: MvpError | None = None
    for provider in provider_chain():
        try:
            return provider.verify(request)
        except MvpError as exc:
            if exc.status != 401:
                raise
            last = exc
    if last is not None:
        raise last
    raise unauthorized("Không có nhà cung cấp danh tính nào được cấu hình.")


#: Tương thích ngược với tên cũ.
def current_user(request: Request) -> Principal:
    return current_principal(request)


def current_role(request: Request) -> Role:
    """Dependency: trả vai hợp lệ hoặc 401."""
    return current_principal(request).role


def require_permission(permission: Permission):
    """Dependency factory: đòi đúng một quyền."""

    def dependency(request: Request) -> Principal:
        principal = current_principal(request)
        if not principal.has(permission):
            raise forbidden(f"Vai {principal.role} không có quyền {permission}.")
        return principal

    return dependency


def require_reviewer(request: Request) -> Principal:
    """Dependency: chỉ vai có ``review:decide`` được gửi quyết định duyệt."""
    principal = current_principal(request)
    if not principal.has(Permission.REVIEW_DECIDE):
        raise forbidden("Chỉ người duyệt được thực hiện hành động này.")
    return principal


# --------------------------------------------------------------------------------------
# Quyền theo từng cuộc điều tra
# --------------------------------------------------------------------------------------

#: Ba hành động trên một ca, mỗi hành động có cặp quyền ``own``/``any``.
_INVESTIGATION_ACTIONS: dict[str, tuple[Permission, Permission]] = {
    "read": (Permission.INVESTIGATION_READ_OWN, Permission.INVESTIGATION_READ_ANY),
    "run": (Permission.INVESTIGATION_RUN_OWN, Permission.INVESTIGATION_RUN_ANY),
    "export": (Permission.INVESTIGATION_EXPORT_OWN, Permission.INVESTIGATION_EXPORT_ANY),
}


def can_access_investigation(principal: Principal, state: InvestigationState, action: str = "read") -> bool:
    """Quyền ``:any`` cho mọi ca; quyền ``:own`` chỉ cho ca do chính người gọi tạo."""
    try:
        own, any_ = _INVESTIGATION_ACTIONS[action]
    except KeyError as exc:  # pragma: no cover - lỗi lập trình, không phải lỗi người dùng
        raise ValueError(f"Hành động không biết: {action}") from exc
    if principal.has(any_):
        return True
    if principal.has(own) and state.created_by == principal.user_id:
        return True
    return False


def require_investigation_access(
    principal: Principal,
    state: InvestigationState,
    action: str = "read",
) -> None:
    """Ném **404** khi không có quyền — không tiết lộ ca có tồn tại hay không.

    AUTH-02: trước đây bảy tuyến đọc chỉ kiểm "đã đăng nhập", nên mọi vai đọc được mọi ca.
    """
    if can_access_investigation(principal, state, action):
        return
    raise not_found("cuộc điều tra", state.investigation_id)


def check_ownership(state: InvestigationState, user: Principal) -> None:
    """Tương thích ngược: kiểm quyền chạy ca. Dùng ``require_investigation_access`` cho mã mới."""
    require_investigation_access(user, state, "run")


def assert_can_decide(state: InvestigationState, principal: Principal) -> None:
    """Tách biệt nhiệm vụ (B1.5): người tạo ca không được quyết định duyệt chính ca đó.

    Ca tạo trước khi có xác thực (``created_by='anonymous'``) vẫn cho qua, nhưng đánh dấu để
    nhật ký ghi rõ đây là ca cũ — không âm thầm bỏ qua.
    """
    if not principal.has(Permission.REVIEW_DECIDE):
        raise forbidden("Chỉ người duyệt được ra quyết định.")
    if state.created_by == LEGACY_ANONYMOUS:
        return
    if state.created_by == principal.user_id:
        raise MvpError(
            403,
            "forbidden",
            "Người tạo cuộc điều tra không được tự duyệt ca của mình.",
            {"code": SELF_REVIEW_FORBIDDEN, "investigation_id": state.investigation_id},
        )


def actor_for(principal: Principal) -> str:
    """Danh tính ghi vào audit/review decision — **mã người**, không phải chuỗi vai (AUTH-03)."""
    return principal.user_id


# --------------------------------------------------------------------------------------
# Router xác thực /auth
# --------------------------------------------------------------------------------------

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Đăng nhập nội bộ: email + mật khẩu. Không nhận vai hay mã người do người gọi khai."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def _verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    from pwdlib import PasswordHash

    return PasswordHash.recommended().verify(password, password_hash)


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng argon2 (cùng cách ``src/api/security.py`` đang dùng)."""
    from pwdlib import PasswordHash

    return PasswordHash.recommended().hash(password)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
    """Đăng nhập nội bộ bằng email + mật khẩu; cấp cookie phiên HttpOnly.

    AUTH-01: trước đây chỉ cần khai ``role`` là có phiên. Nay phải có credential hợp lệ, và
    ``session_id`` **không** còn nằm trong thân phản hồi.
    """
    from src.api.mvp_runtime import get_mvp_store

    settings = get_settings()
    store = get_mvp_store()
    user = store.get_user_by_email(payload.email)
    if user is None or user["status"] != "active" or not _verify_password(payload.password, user["password_hash"]):
        # Một thông báo duy nhất cho mọi trường hợp: không tiết lộ email nào có trong hệ thống.
        raise unauthorized("Email hoặc mật khẩu không đúng.")
    if user["role"] == str(Role.SERVICE):
        raise unauthorized("Tài khoản máy không đăng nhập bằng mật khẩu.")

    session_id = store.create_session(user_id=user["user_id"], role=user["role"])
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=43200,
        secure=settings.session_cookie_secure,
    )
    store.audit(
        None,
        user["user_id"],
        "login",
        {"method": "local_password"},
        actor_role=user["role"],
        request_id=getattr(request.state, "request_id", None),
    )
    return {"user_id": user["user_id"], "role": user["role"], "display_name": user["display_name"] or ""}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    session_id: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> dict[str, bool]:
    """Thu hồi phiên của chính mình và huỷ cookie."""
    from src.api.mvp_runtime import get_mvp_store

    if session_id:
        get_mvp_store().revoke_session(session_id)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"logged_out": True}


@router.get("/me")
async def me(user: Annotated[Principal, Depends(current_principal)]) -> dict[str, str]:
    """Thông tin danh tính và vai trò của phiên hiện tại."""
    return {
        "user_id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": str(user.role),
        "auth_method": user.auth_method,
    }
