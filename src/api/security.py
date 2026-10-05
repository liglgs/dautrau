import hashlib
import secrets
from datetime import UTC, timedelta

from fastapi import Depends, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import LoginSession, User, get_db, now
from src.vmec import DomainError

password_hash = PasswordHash.recommended()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(36)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=now() + timedelta(hours=8)))
    return token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("medreview_session")
    session = db.get(LoginSession, token_hash(token)) if token else None
    if not session or session.expires_at.replace(tzinfo=UTC) < now():
        raise DomainError(401, "SESSION_REQUIRED", "Cần đăng nhập.")
    user = db.get(User, session.user_id)
    if user is None:
        raise DomainError(401, "SESSION_REQUIRED", "Phiên không hợp lệ.")
    return user


def reviewer(user: User):
    if user.role not in ("reviewer", "clinician"):
        raise DomainError(403, "FORBIDDEN", "Chỉ người rà soát được thao tác.")


def clinician(user: User):
    if user.role != "clinician":
        raise DomainError(403, "FORBIDDEN", "Chỉ người duyệt được thao tác.")


def check_origin(request: Request):
    origin = request.headers.get("origin")
    settings = get_settings()
    allowed = set(settings.cors_origins.split(","))
    if settings.app_env == "development":
        allowed.update({"http://127.0.0.1:5173", "http://localhost:5173"})
    if origin and origin not in allowed:
        raise DomainError(403, "INVALID_ORIGIN", "Nguồn yêu cầu không hợp lệ.")
