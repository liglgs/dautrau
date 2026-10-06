"""Nạp tài khoản khởi động cho môi trường chạy bằng docker compose.

Vì sao cần: sau AUTH-01, cầu nối giao diện **không còn** đường "trình duyệt khai vai rồi máy chủ
gắn token vai trò". Nếu dựng stack bằng `docker-compose.mvp.yml` mà không nạp tài khoản nào thì
không ai đăng nhập được, kể cả để xem thử.

Script này chỉ tạo tài khoản ở môi trường **không phải production** và chỉ khi biến môi trường
tương ứng được đặt. Mật khẩu đọc từ biến môi trường, không ghi vào mã nguồn, không in ra màn hình.

    MVP_BOOTSTRAP_INVESTIGATOR_EMAIL / MVP_BOOTSTRAP_INVESTIGATOR_PASSWORD
    MVP_BOOTSTRAP_REVIEWER_EMAIL     / MVP_BOOTSTRAP_REVIEWER_PASSWORD

Chạy idempotent: tài khoản đã tồn tại thì bỏ qua (và báo rõ), không ghi đè mật khẩu.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROLES = (
    ("MVP_BOOTSTRAP_INVESTIGATOR", "investigator", "usr_dieu_tra"),
    ("MVP_BOOTSTRAP_REVIEWER", "reviewer", "usr_duyet"),
    ("MVP_BOOTSTRAP_ADMIN", "admin", "usr_quan_tri"),
)


def _settings(prefix: str) -> tuple[str, str] | None:
    email = os.environ.get(f"{prefix}_EMAIL", "").strip()
    password = os.environ.get(f"{prefix}_PASSWORD", "")
    if not email and not password:
        return None
    if not email or not password:
        raise SystemExit(f"{prefix}_EMAIL và {prefix}_PASSWORD phải được đặt cùng nhau.")
    return email, password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Cho phép chạy khi APP_ENV=production (mặc định: từ chối).",
    )
    args = parser.parse_args(argv)

    from src.config import get_settings

    settings = get_settings()
    if settings.app_env == "production" and not args.allow_production:
        print(
            "APP_ENV=production: từ chối nạp tài khoản khởi động. Dùng `scripts/auth_cli.py create-user`.",
            file=sys.stderr,
        )
        return 2

    from src.api.auth import hash_password
    from src.api.mvp_runtime import get_mvp_store

    store = get_mvp_store()
    created = 0
    for prefix, role, user_id in ROLES:
        credentials = _settings(prefix)
        if credentials is None:
            continue
        email, password = credentials
        if store.get_user(user_id) is not None:
            print(f"Bỏ qua {user_id}: đã tồn tại.")
            continue
        store.create_user(
            user_id=user_id,
            email=email,
            role=role,
            display_name=email,
            password_hash=hash_password(password),
            created_by="bootstrap",
        )
        print(f"Đã tạo {user_id} (vai {role}, email {email}).")
        created += 1

    if created == 0:
        print("Không có tài khoản nào được nạp. Đặt biến MVP_BOOTSTRAP_* nếu cần đăng nhập.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
