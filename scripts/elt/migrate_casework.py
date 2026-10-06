"""Nâng cấp lược đồ cho bảng lát cắt DI (WorkItem/Response/FollowUp) — chỉ thêm bảng.

Kho ELT chưa dùng Alembic; các bảng cũ do ``create_all`` dựng nên. Vì vậy bước nâng cấp
ở đây cũng chỉ **thêm** bảy bảng mới (và chỉ mục duy nhất còn thiếu), không đụng tới bảng
đang có:

    work_items, investigation_links, evidence_bundles, professional_responses,
    follow_ups, version_refs, review_refs

Cách dùng:

    python -m scripts.elt.migrate_casework             # xem kế hoạch rồi thực hiện
    python -m scripts.elt.migrate_casework --check     # chỉ kiểm tra, mã thoát 1 nếu thiếu
    python -m scripts.elt.migrate_casework --rollback --yes   # bỏ bảy bảng mới (mất dữ liệu DI)

An toàn: trước khi ghi, script đếm số dòng của mọi bảng cũ; sau khi ghi, đếm lại và so
sánh. Lệch thì báo lỗi rõ ràng (thực tế không thể lệch vì chỉ có ``CREATE TABLE`` và
``CREATE UNIQUE INDEX``).
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


def casework_indexes() -> dict[str, list[str]]:
    """Chỉ mục duy nhất phải có cho từng bảng lát cắt DI."""
    expected: dict[str, list[str]] = {}
    for name in CASEWORK_TABLES:
        table = WarehouseBase.metadata.tables[name]
        expected[name] = sorted(index.name for index in table.indexes if index.unique)
    return {name: names for name, names in expected.items() if names}


def _column_names(engine: Engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _index_names(engine: Engine, table: str) -> set[str]:
    return {index["name"] for index in inspect(engine).get_indexes(table)}


def _column_gaps(engine: Engine) -> dict[str, list[str]]:
    """Cột của bảng lát cắt DI còn thiếu so với mô hình (bảng chưa có tính là thiếu hết)."""
    existing = set(inspect(engine).get_table_names())
    gaps: dict[str, list[str]] = {}
    for name in CASEWORK_TABLES:
        if name not in existing:
            continue
        expected = {column.name for column in WarehouseBase.metadata.tables[name].columns}
        missing = sorted(expected - _column_names(engine, name))
        if missing:
            gaps[name] = missing
    return gaps


def _index_gaps(engine: Engine) -> dict[str, list[str]]:
    existing = set(inspect(engine).get_table_names())
    gaps: dict[str, list[str]] = {}
    for name, expected in casework_indexes().items():
        if name not in existing:
            continue
        missing = sorted(set(expected) - _index_names(engine, name))
        if missing:
            gaps[name] = missing
    return gaps


def inspect_state(engine: Engine) -> dict[str, object]:
    existing = set(inspect(engine).get_table_names())
    return {
        "present_casework": sorted(name for name in CASEWORK_TABLES if name in existing),
        "missing_casework": sorted(name for name in CASEWORK_TABLES if name not in existing),
        "missing_legacy": sorted(name for name in legacy_tables() if name not in existing),
        "missing_columns": _column_gaps(engine),
        "missing_indexes": _index_gaps(engine),
    }


def _row_counts(engine: Engine, names: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    existing = set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        for name in names:
            if name in existing:
                counts[name] = int(conn.execute(text(f'SELECT count(*) FROM "{name}"')).scalar_one())
    return counts


def create_missing_indexes(engine: Engine) -> list[str]:
    """Tạo chỉ mục duy nhất còn thiếu của bảy bảng (bảng đã có từ bản nâng cấp trước)."""
    existing = set(inspect(engine).get_table_names())
    created: list[str] = []
    for name, expected in casework_indexes().items():
        if name not in existing:
            continue
        table = WarehouseBase.metadata.tables[name]
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            if index.name not in expected or index.name in _index_names(engine, name):
                continue
            index.create(engine, checkfirst=True)
            created.append(f"{name}.{index.name}")
    return created


def migrate(engine: Engine) -> dict[str, object]:
    before_tables = set(inspect(engine).get_table_names())
    legacy_before = _row_counts(engine, legacy_tables())
    created = ensure_casework_schema(engine)
    created_indexes = create_missing_indexes(engine)
    legacy_after = _row_counts(engine, legacy_tables())
    drift = {
        name: (legacy_before[name], legacy_after[name])
        for name in legacy_before
        if legacy_before[name] != legacy_after[name]
    }
    state = inspect_state(engine)
    return {
        "created_tables": created,
        "created_indexes": created_indexes,
        "tables_before": len(before_tables),
        "tables_after": len(before_tables) + len(created),
        "legacy_rows_before": legacy_before,
        "legacy_rows_after": legacy_after,
        "legacy_drift": drift,
        "missing_casework": state["missing_casework"],
        "missing_legacy": state["missing_legacy"],
        "missing_columns": state["missing_columns"],
        "missing_indexes": state["missing_indexes"],
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


def _problems(state: dict[str, object]) -> list[str]:
    problems: list[str] = []
    if state["missing_casework"]:
        problems.append("thiếu bảng: " + ", ".join(state["missing_casework"]))
    if state["missing_legacy"]:
        problems.append("thiếu bảng cũ: " + ", ".join(state["missing_legacy"]))
    for table, columns in state["missing_columns"].items():
        problems.append(f"{table} thiếu cột: " + ", ".join(columns))
    for table, indexes in state["missing_indexes"].items():
        problems.append(f"{table} thiếu chỉ mục: " + ", ".join(indexes))
    return problems


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
        problems = _problems(state)
        payload = {"status": "ok" if not problems else "missing", "problems": problems, **state}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else _describe(problems))
        return 0 if not problems else 1

    if args.rollback:
        if not args.yes:
            print("Từ chối chạy: thêm --yes để xác nhận bỏ bảy bảng lát cắt DI.")
            return 2
        dropped = rollback(engine)
        print(f"Đã bỏ {len(dropped)} bảng: {', '.join(dropped) if dropped else '(không có bảng nào)'}.")
        return 0

    report = migrate(engine)
    problems = _problems(
        {
            "missing_casework": report["missing_casework"],
            "missing_legacy": report["missing_legacy"],
            "missing_columns": report["missing_columns"],
            "missing_indexes": report["missing_indexes"],
        }
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Bảng đã tạo: {', '.join(report['created_tables']) or '(không có bảng mới)'}.")
        print(f"Chỉ mục đã tạo: {', '.join(report['created_indexes']) or '(không có chỉ mục mới)'}.")
        print(f"Số bảng: {report['tables_before']} → {report['tables_after']}.")
        if report["legacy_drift"]:
            print(f"LỖI: số dòng bảng cũ thay đổi: {report['legacy_drift']}")
            return 1
        print(f"Bảng cũ không đổi số dòng ({len(report['legacy_rows_after'])} bảng đã đếm).")
        print("Còn thiếu: " + ("; ".join(problems) if problems else "(không)"))
    return 1 if problems or report["legacy_drift"] else 0


def _describe(problems: list[str]) -> str:
    if problems:
        return "Chưa đạt: " + "; ".join(problems) + "."
    return "Đủ bảy bảng lát cắt DI (cột và chỉ mục khớp); bảng cũ không đổi."


if __name__ == "__main__":
    raise SystemExit(main())
