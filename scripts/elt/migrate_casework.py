"""Nâng cấp lược đồ cho bảng lát cắt DI (WorkItem/Response/FollowUp) — chỉ thêm bảng.

Kho ELT chưa dùng Alembic; các bảng cũ do ``create_all`` dựng nên. Vì vậy bước nâng cấp
ở đây cũng chỉ **thêm** bảy bảng mới, không đụng tới bảng đang có:

    work_items, investigation_links, evidence_bundles, professional_responses,
    follow_ups, version_refs, review_refs

Cách dùng:

    python -m scripts.elt.migrate_casework             # xem kế hoạch rồi thực hiện
    python -m scripts.elt.migrate_casework --check     # chỉ kiểm tra, mã thoát 1 nếu thiếu
    python -m scripts.elt.migrate_casework --rollback --yes   # bỏ bảy bảng mới (mất dữ liệu DI)

An toàn: trước khi ghi, script đếm số dòng của mọi bảng cũ; sau khi ghi, đếm lại và so
sánh. Lệch thì báo lỗi rõ ràng (thực tế không thể lệch vì chỉ có ``CREATE TABLE``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.casework.store import CASEWORK_TABLES, ensure_casework_schema  # noqa: E402
from src.services.warehouse.db import get_warehouse_engine  # noqa: E402
from src.services.warehouse.models import WarehouseBase  # noqa: E402


def legacy_tables() -> list[str]:
    return sorted(name for name in WarehouseBase.metadata.tables if name not in CASEWORK_TABLES)


def inspect_state(engine: Engine) -> dict[str, list[str]]:
    existing = set(inspect(engine).get_table_names())
    return {
        "present_casework": sorted(name for name in CASEWORK_TABLES if name in existing),
        "missing_casework": sorted(name for name in CASEWORK_TABLES if name not in existing),
        "missing_legacy": sorted(name for name in legacy_tables() if name not in existing),
    }


def _row_counts(engine: Engine, names: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    existing = set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        for name in names:
            if name in existing:
                counts[name] = int(conn.execute(text(f'SELECT count(*) FROM "{name}"')).scalar_one())
    return counts


def migrate(engine: Engine) -> dict[str, object]:
    before_tables = set(inspect(engine).get_table_names())
    legacy_before = _row_counts(engine, legacy_tables())
    created = ensure_casework_schema(engine)
    legacy_after = _row_counts(engine, legacy_tables())
    drift = {name: (legacy_before[name], legacy_after[name]) for name in legacy_before if legacy_before[name] != legacy_after[name]}
    state = inspect_state(engine)
    return {
        "created_tables": created,
        "tables_before": len(before_tables),
        "tables_after": len(before_tables) + len(created),
        "legacy_rows_before": legacy_before,
        "legacy_rows_after": legacy_after,
        "legacy_drift": drift,
        "missing_casework": state["missing_casework"],
        "missing_legacy": state["missing_legacy"],
    }


def rollback(engine: Engine) -> list[str]:
    """Bỏ bảy bảng mới. Chỉ dùng khi thật sự muốn mất dữ liệu DI."""
    existing = set(inspect(engine).get_table_names())
    dropped: list[str] = []
    # Thứ tự ngược để bảng con đi trước bảng cha.
    with engine.begin() as conn:
        for name in reversed(CASEWORK_TABLES):
            if name in existing:
                conn.execute(text(f'DROP TABLE IF EXISTS "{name}"'))
                dropped.append(name)
    return dropped


def main() -> int:
    parser = argparse.ArgumentParser(description="Nâng cấp lược đồ bảng lát cắt DI (chỉ thêm bảng).")
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm tra, không ghi.")
    parser.add_argument("--rollback", action="store_true", help="Bỏ bảy bảng lát cắt DI.")
    parser.add_argument("--yes", action="store_true", help="Xác nhận cho --rollback.")
    parser.add_argument("--json", action="store_true", help="In kết quả dạng JSON.")
    parser.add_argument("--database-url", default="", help="Ghi đè địa chỉ kho (mặc định lấy từ cấu hình).")
    args = parser.parse_args()

    engine = get_warehouse_engine(args.database_url or None)
    state = inspect_state(engine)

    if args.check:
        payload = {"status": "ok" if not state["missing_casework"] else "missing", **state}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else _describe(state))
        return 0 if not state["missing_casework"] else 1

    if args.rollback:
        if not args.yes:
            print("Từ chối chạy: thêm --yes để xác nhận bỏ bảy bảng lát cắt DI.")
            return 2
        dropped = rollback(engine)
        print(f"Đã bỏ {len(dropped)} bảng: {', '.join(dropped) if dropped else '(không có bảng nào)'}.")
        return 0

    report = migrate(engine)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Bảng đã tạo: {', '.join(report['created_tables']) or '(không có bảng mới)'}.")
        print(f"Số bảng: {report['tables_before']} → {report['tables_after']}.")
        print(f"Bảng cũ còn thiếu: {', '.join(report['missing_legacy']) or '(không)'}.")
        print(f"Bảng DI còn thiếu: {', '.join(report['missing_casework']) or '(không)'}.")
        if report["legacy_drift"]:
            print(f"LỖI: số dòng bảng cũ thay đổi: {report['legacy_drift']}")
            return 1
        print(f"Bảng cũ không đổi số dòng ({len(report['legacy_rows_after'])} bảng đã đếm).")
    return 0 if not report["missing_casework"] and not report["legacy_drift"] else 1


def _describe(state: dict[str, list[str]]) -> str:
    if state["missing_casework"]:
        return "Thiếu bảng lát cắt DI: " + ", ".join(state["missing_casework"]) + "."
    return "Đủ bảy bảng lát cắt DI; bảng cũ không đổi."


if __name__ == "__main__":
    raise SystemExit(main())
