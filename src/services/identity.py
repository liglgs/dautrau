"""Vai, quyền và khoá máy cho VigiLens (R2-2-07).

Một chỗ duy nhất định nghĩa *ai được làm gì*:

* :class:`Role` — năm vai. Vai **không** nằm trong Supabase Auth; Supabase chỉ giữ danh tính
  (mã người dùng + email), còn vai đọc từ bảng ``app_users`` trong kho của mình. Nhờ vậy đổi vai
  không cần đụng tới Supabase, và bài kiểm thử ngoại tuyến gán vai được mà không cần mạng.
* :class:`Permission` — mười sáu chuỗi quyền dạng ``tài-nguyên:hành-động:phạm-vi``.
* :data:`ROLE_PERMISSIONS` — ánh xạ vai → tập quyền, **cố định trong mã** (không lưu trong cơ sở
  dữ liệu ở bước này). Lý do: ít vai, ít thay đổi; đổi vai là đổi tập quyền ngay, không cần khởi
  động lại.

Quy tắc ghép quyền ở tầng API: một tuyến đòi một quyền; vai nào có quyền đó thì qua. Quyền có
phạm vi ``:own`` chỉ áp dụng cho ca do chính người gọi tạo; ``:any`` áp dụng cho mọi ca.
"""

from __future__ import annotations

import hashlib
import secrets
from enum import StrEnum

#: Tiền tố khoá máy, để nhìn là biết ngay đây là khoá của VigiLens chứ không phải khoá khác.
TOKEN_PREFIX = "vln_"


class Role(StrEnum):
    """Năm vai của hệ thống."""

    INVESTIGATOR = "investigator"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    SERVICE = "service"
    AUDITOR = "auditor"


#: Nhãn tiếng Việt để hiện trên giao diện và trong nhật ký.
ROLE_LABELS: dict[Role, str] = {
    Role.INVESTIGATOR: "Người điều tra",
    Role.REVIEWER: "Người duyệt",
    Role.ADMIN: "Quản trị",
    Role.SERVICE: "Tài khoản máy",
    Role.AUDITOR: "Người kiểm toán",
}


class Permission(StrEnum):
    """Mười sáu chuỗi quyền."""

    INVESTIGATION_CREATE = "investigation:create"
    INVESTIGATION_READ_OWN = "investigation:read:own"
    INVESTIGATION_READ_ANY = "investigation:read:any"
    INVESTIGATION_RUN_OWN = "investigation:run:own"
    INVESTIGATION_RUN_ANY = "investigation:run:any"
    INVESTIGATION_EXPORT_OWN = "investigation:export:own"
    INVESTIGATION_EXPORT_ANY = "investigation:export:any"
    REVIEW_DECIDE = "review:decide"
    QUEUE_ASSIGN = "queue:assign"
    WAREHOUSE_READ = "warehouse:read"
    WAREHOUSE_INGEST = "warehouse:ingest"
    ADMIN_USERS = "admin:users"
    ADMIN_POLICY = "admin:policy"
    AUDIT_READ_OWN = "audit:read:own"
    AUDIT_READ_ANY = "audit:read:any"
    SERVICE_RUN = "service:run"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.INVESTIGATOR: frozenset(
        {
            Permission.INVESTIGATION_CREATE,
            Permission.INVESTIGATION_READ_OWN,
            Permission.INVESTIGATION_RUN_OWN,
            Permission.INVESTIGATION_EXPORT_OWN,
            Permission.WAREHOUSE_READ,
            Permission.AUDIT_READ_OWN,
        }
    ),
    Role.REVIEWER: frozenset(
        {
            Permission.INVESTIGATION_CREATE,
            Permission.INVESTIGATION_READ_OWN,
            Permission.INVESTIGATION_READ_ANY,
            Permission.INVESTIGATION_RUN_OWN,
            Permission.INVESTIGATION_RUN_ANY,
            Permission.INVESTIGATION_EXPORT_OWN,
            Permission.INVESTIGATION_EXPORT_ANY,
            Permission.REVIEW_DECIDE,
            Permission.QUEUE_ASSIGN,
            Permission.WAREHOUSE_READ,
            Permission.WAREHOUSE_INGEST,
            Permission.ADMIN_POLICY,
            Permission.AUDIT_READ_OWN,
        }
    ),
    Role.ADMIN: frozenset(
        {
            Permission.INVESTIGATION_CREATE,
            Permission.INVESTIGATION_READ_OWN,
            Permission.INVESTIGATION_READ_ANY,
            Permission.INVESTIGATION_RUN_OWN,
            Permission.INVESTIGATION_RUN_ANY,
            Permission.INVESTIGATION_EXPORT_OWN,
            Permission.INVESTIGATION_EXPORT_ANY,
            Permission.QUEUE_ASSIGN,
            Permission.WAREHOUSE_READ,
            Permission.WAREHOUSE_INGEST,
            Permission.ADMIN_USERS,
            Permission.ADMIN_POLICY,
            Permission.AUDIT_READ_OWN,
            Permission.AUDIT_READ_ANY,
        }
    ),
    Role.SERVICE: frozenset(
        {
            Permission.INVESTIGATION_CREATE,
            Permission.INVESTIGATION_READ_OWN,
            Permission.INVESTIGATION_READ_ANY,
            Permission.INVESTIGATION_RUN_OWN,
            Permission.INVESTIGATION_RUN_ANY,
            Permission.INVESTIGATION_EXPORT_OWN,
            Permission.INVESTIGATION_EXPORT_ANY,
            Permission.WAREHOUSE_READ,
            Permission.WAREHOUSE_INGEST,
            Permission.AUDIT_READ_OWN,
            Permission.SERVICE_RUN,
        }
    ),
    Role.AUDITOR: frozenset(
        {
            Permission.INVESTIGATION_READ_OWN,
            Permission.INVESTIGATION_READ_ANY,
            Permission.INVESTIGATION_EXPORT_ANY,
            Permission.WAREHOUSE_READ,
            Permission.ADMIN_POLICY,
            Permission.AUDIT_READ_OWN,
            Permission.AUDIT_READ_ANY,
        }
    ),
}

#: Quyền của một vai, tra nhanh và không bao giờ ném lỗi với vai hợp lệ.
def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


# --------------------------------------------------------------------------------------
# Khoá máy
# --------------------------------------------------------------------------------------


def generate_token() -> str:
    """Sinh khoá thô cho tài khoản máy. Chỉ in **một lần** lúc tạo."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_token(raw: str) -> str:
    """Băm khoá để lưu. Khoá thô **không** bao giờ nằm trong cơ sở dữ liệu."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def looks_like_token(raw: str) -> bool:
    """Khoá máy phải đúng tiền tố; giúp phân biệt với mật khẩu/chuỗi lạ trước khi băm."""
    return raw.startswith(TOKEN_PREFIX) and len(raw) > len(TOKEN_PREFIX) + 16
