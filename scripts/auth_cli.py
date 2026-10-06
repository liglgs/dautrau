"""Quản trị danh tính VigiLens từ dòng lệnh (B1.4, B1.9).

Hai việc:

* ``issue-token`` — cấp khoá máy cho tài khoản ``service``. Khoá thô chỉ in **một lần**; trong
  cơ sở dữ liệu chỉ có bản băm SHA-256.
* ``migrate-legacy`` — đọc bảng ``users`` của ngăn xếp VMEC cũ, ghi sang ``app_users``, và in bảng
  đối chiếu số dòng trước/sau theo vai. Chạy lại phải **không đổi gì** (idempotent).

Mật khẩu băm của VMEC **không** chuyển sang: băm không xuất được. Người dùng cũ đăng nhập bằng
cách đặt lại mật khẩu; tài khoản được tạo ở trạng thái chưa có mật khẩu.

Ví dụ::

    python -m scripts.auth_cli issue-token --user-id svc_etl --label "nạp định kỳ"
    python -m scripts.auth_cli list-users
    python -m scripts.auth_cli migrate-legacy --dry-run
    python -m scripts.auth_cli migrate-legacy
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Cho phép chạy thẳng `python scripts/auth_cli.py ...` như tài liệu hướng dẫn, không chỉ `-m`.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Ánh xạ vai VMEC cũ → vai mới (B1.1).
LEGACY_ROLE_MAP = {
    "responder": "investigator",
    "reviewer": "reviewer",
    "clinician": "reviewer",
}

#: Ai đã chạy công cụ này. Nhật ký phải trả lời được "ai cấp vai này", mà "system" thì không trả
#: lời được gì; tên đăng nhập hệ điều hành là thông tin có thật duy nhất ở đây.
ACTOR = f"cli:{getpass.getuser()}"


def _store():
    """Store MVP trên đúng tệp cơ sở dữ liệu mà máy chủ đang dùng."""
    from src.api.mvp_runtime import get_mvp_store

    return get_mvp_store()


def _role_counts(rows) -> Counter:
    return Counter(row["role"] for row in rows)


def _print_role_table(title: str, counts: Counter) -> None:
    print(f"\n{title}")
    if not counts:
        print("  (không có dòng nào)")
        return
    for role in sorted(counts):
        print(f"  {role:<14} {counts[role]}")
    print(f"  {'TỔNG':<14} {sum(counts.values())}")


def cmd_issue_token(args: argparse.Namespace) -> int:
    from src.services.identity import generate_token

    store = _store()
    user = store.get_user(args.user_id)
    if user is None:
        print(f"Không có tài khoản {args.user_id!r}. Tạo trước bằng `create-user`.", file=sys.stderr)
        return 2
    if user["role"] != "service":
        print(
            f"Tài khoản {args.user_id!r} có vai {user['role']!r}; khoá máy chỉ cấp cho vai 'service'.",
            file=sys.stderr,
        )
        return 2

    raw = generate_token()
    store.issue_token(user_id=args.user_id, raw_token=raw, label=args.label, expires_at=args.expires_at)
    print("Khoá máy dưới đây chỉ hiện MỘT lần. Sao chép ngay và cất trong kho bí mật:")
    print()
    print(f"  {raw}")
    print()
    print(f"Đã lưu bản băm cho {args.user_id} (nhãn: {args.label or 'không có'}).")
    return 0


def cmd_create_user(args: argparse.Namespace) -> int:
    from src.api.auth import hash_password

    store = _store()
    if store.get_user(args.user_id) is not None:
        print(f"Tài khoản {args.user_id!r} đã tồn tại.", file=sys.stderr)
        return 2
    password_hash = hash_password(args.password) if args.password else None
    store.create_user(
        user_id=args.user_id,
        email=args.email,
        role=args.role,
        display_name=args.display_name or args.email,
        password_hash=password_hash,
        created_by=args.created_by,
        actor_role="cli",
    )
    print(f"Đã tạo {args.user_id} (vai {args.role}, email {args.email}).")
    if password_hash is None:
        print("Chưa có mật khẩu: tài khoản này chỉ dùng được bằng khoá máy.")
    return 0


def cmd_list_users(args: argparse.Namespace) -> int:
    store = _store()
    rows = store.list_users(limit=args.limit)
    if not rows:
        print("Chưa có tài khoản nào trong app_users.")
        return 0
    print(f"{'user_id':<24} {'vai':<14} {'trạng thái':<10} email")
    for row in rows:
        print(f"{row['user_id']:<24} {row['role']:<14} {row['status']:<10} {row['email']}")
    _print_role_table("Số tài khoản theo vai:", _role_counts(rows))
    return 0


def _legacy_rows():
    """Đọc bảng ``users`` của VMEC. Trả ``None`` khi ngăn xếp cũ chưa dựng."""
    from sqlalchemy import select

    from src.db import SessionLocal, User

    session = SessionLocal()
    try:
        # ``session.execute(select(User))`` trả về ``Row`` bọc thực thể (khoá ``"User"``) trong
        # SQLAlchemy 2.x, nên ``row.id`` ném AttributeError; ``scalars`` trả thẳng thực thể.
        return [
            {"id": user.id, "name": user.name, "role": user.role}
            for user in session.scalars(select(User))
        ]
    except Exception as exc:  # noqa: BLE001 - thiếu bảng/chưa cấu hình đều quy về một thông báo
        print(f"Không đọc được bảng users của VMEC: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return None
    finally:
        session.close()


def cmd_migrate_legacy(args: argparse.Namespace) -> int:
    store = _store()
    legacy = _legacy_rows()
    if legacy is None:
        return 2

    before = _role_counts(store.list_users(limit=10000))
    _print_role_table("Trước khi di trú — app_users:", before)
    print(f"\nNguồn: bảng users của VMEC có {len(legacy)} dòng.")
    unmapped = sorted({row["role"] for row in legacy if row["role"] not in LEGACY_ROLE_MAP})
    if unmapped:
        print(f"Vai không có trong bảng ánh xạ (bỏ qua): {', '.join(unmapped)}")

    created, skipped, remapped = 0, 0, 0
    for row in legacy:
        role = LEGACY_ROLE_MAP.get(row["role"])
        if role is None:
            skipped += 1
            continue
        existing = store.get_user(row["id"])
        if existing is not None:
            if existing["role"] != role and not args.dry_run:
                store.update_user(row["id"], role=role, actor=ACTOR, actor_role="cli")
                remapped += 1
            skipped += 1
            continue
        if args.dry_run:
            created += 1
            continue
        # Email phải duy nhất; dùng mã người làm email tạm để không chặn di trú.
        store.create_user(
            user_id=row["id"],
            email=f"{row['id']}@di-tru-cho-dat-lai.local",
            role=role,
            display_name=row["name"],
            created_by=ACTOR,
            actor_role="cli",
        )
        created += 1

    after = _role_counts(store.list_users(limit=10000))
    _print_role_table("Sau khi di trú — app_users:", after)
    print(f"\nTạo mới: {created}   Đã có (bỏ qua): {skipped}   Đổi vai: {remapped}")
    if args.dry_run:
        print("Chế độ --dry-run: chưa ghi gì.")
    else:
        print("Chạy lại lệnh này phải cho Tạo mới: 0 — đó là phép thử tính idempotent.")
        print("Hoàn tác: xoá các dòng vừa tạo trong app_users; bảng users cũ không bị đụng tới.")
    print("Mật khẩu băm KHÔNG được chuyển; người dùng cũ phải đặt lại mật khẩu.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    issue = sub.add_parser("issue-token", help="Cấp khoá máy cho một tài khoản vai service")
    issue.add_argument("--user-id", required=True)
    issue.add_argument("--label", default="")
    issue.add_argument("--expires-at", default=None, help="Dấu thời gian ISO-8601; bỏ trống là không hết hạn")
    issue.set_defaults(func=cmd_issue_token)

    create = sub.add_parser("create-user", help="Tạo tài khoản người")
    create.add_argument("--user-id", required=True)
    create.add_argument("--email", required=True)
    create.add_argument(
        "--role", required=True, choices=["investigator", "reviewer", "admin", "service", "auditor"]
    )
    create.add_argument("--display-name", default="")
    create.add_argument("--password", default=None, help="Bỏ trống nếu chỉ dùng khoá máy")
    create.add_argument("--created-by", default=ACTOR, help="Ai cấp tài khoản; ghi vào nhật ký")
    create.set_defaults(func=cmd_create_user)

    listing = sub.add_parser("list-users", help="Liệt kê tài khoản và số lượng theo vai")
    listing.add_argument("--limit", type=int, default=200)
    listing.set_defaults(func=cmd_list_users)

    migrate = sub.add_parser("migrate-legacy", help="Chuyển bảng users của VMEC sang app_users")
    migrate.add_argument("--dry-run", action="store_true", help="Chỉ đếm, không ghi")
    migrate.set_defaults(func=cmd_migrate_legacy)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
