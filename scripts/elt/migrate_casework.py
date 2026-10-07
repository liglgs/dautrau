"""Nâng cấp lược đồ cho bảng lát cắt DI (WorkItem/Response/FollowUp) — chỉ thêm bảng.

Kho ELT chưa dùng Alembic; các bảng cũ do ``create_all`` dựng nên. Vì vậy bước nâng cấp
ở đây cũng chỉ **thêm** 16 bảng mới (và chỉ mục duy nhất còn thiếu), không đụng tới bảng
đang có:

    work_items, investigation_links, evidence_bundles, professional_responses,
    follow_ups, version_refs, review_refs

Cách dùng:

    python -m scripts.elt.migrate_casework             # xem kế hoạch rồi thực hiện
    python -m scripts.elt.migrate_casework --check     # chỉ kiểm tra, mã thoát 1 nếu thiếu
    python -m scripts.elt.migrate_casework --rollback --yes   # bỏ 16 bảng mới (mất dữ liệu DI)

An toàn: trước khi ghi, script đếm số dòng của mọi bảng cũ; sau khi ghi, đếm lại và so
sánh. Lệch thì báo lỗi rõ ràng (thực tế không thể lệch vì chỉ có ``CREATE TABLE`` và
``CREATE UNIQUE INDEX``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

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


def casework_indexes() -> dict[str, dict[str, tuple[str, ...]]]:
    """Chỉ mục duy nhất phải có, kèm các cột — để kiểm cả *tính duy nhất*, không chỉ tên."""
    expected: dict[str, dict[str, tuple[str, ...]]] = {}
    for name in CASEWORK_TABLES:
        table = WarehouseBase.metadata.tables[name]
        indexes = {
            index.name: tuple(column.name for column in index.columns) for index in table.indexes if index.unique
        }
        if indexes:
            expected[name] = indexes
    return expected


def _index_predicate(index) -> str:
    """Mệnh đề WHERE của chỉ mục duy nhất một phần, đã dịch sang SQL của máy chủ.

    Chỉ mục ``uq_response_current`` chỉ áp cho các bản *chưa* bị thay thế; nếu bỏ mệnh đề
    này thì phép kiểm trùng sẽ báo nhầm mọi phiếu có nhiều hơn một phiên bản.
    """
    for dialect in ("postgresql", "sqlite"):
        options = index.dialect_options.get(dialect) or {}
        predicate = options.get("where")
        if predicate is not None:
            return str(predicate.compile(compile_kwargs={"literal_binds": True}))
    return ""


def duplicate_keys(engine: Engine) -> dict[str, list[list[Any]]]:
    """Nhóm khoá đang trùng trên các ràng buộc duy nhất của 16 bảng.

    Phải kiểm trước khi tạo chỉ mục duy nhất: bản cũ cho phép trùng, nên một máy đã chạy
    bản cũ có thể đang có dữ liệu làm `CREATE UNIQUE INDEX` nổ giữa đường.
    """
    existing = set(inspect(engine).get_table_names())
    duplicates: dict[str, list[list[Any]]] = {}
    with engine.connect() as conn:
        for name in CASEWORK_TABLES:
            if name not in existing:
                continue
            table = WarehouseBase.metadata.tables[name]
            for index in sorted(table.indexes, key=lambda item: item.name or ""):
                if not index.unique:
                    continue
                columns = [column.name for column in index.columns]
                listed = ", ".join(f'"{column}"' for column in columns)
                predicate = _index_predicate(index)
                where = f" WHERE {predicate}" if predicate else ""
                rows = conn.execute(
                    text(f'SELECT {listed} FROM "{name}"{where} GROUP BY {listed} HAVING count(*) > 1')
                ).fetchall()
                if rows:
                    duplicates[index.name] = [list(row) for row in rows]
    return duplicates


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
    """Chỉ mục còn thiếu *hoặc* đang tồn tại nhưng không duy nhất / sai cột."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    gaps: dict[str, list[str]] = {}
    for name, expected in casework_indexes().items():
        if name not in existing:
            continue
        actual = {
            index["name"]: tuple(index["column_names"]) for index in inspector.get_indexes(name) if index.get("unique")
        }
        problems = [
            f"{index_name} (cần duy nhất trên {', '.join(columns)})"
            for index_name, columns in expected.items()
            if actual.get(index_name) != columns
        ]
        if problems:
            gaps[name] = sorted(problems)
    return gaps


def inspect_state(engine: Engine) -> dict[str, object]:
    existing = set(inspect(engine).get_table_names())
    return {
        "present_casework": sorted(name for name in CASEWORK_TABLES if name in existing),
        "missing_casework": sorted(name for name in CASEWORK_TABLES if name not in existing),
        "missing_legacy": sorted(name for name in legacy_tables() if name not in existing),
        "missing_columns": _column_gaps(engine),
        "missing_indexes": _index_gaps(engine),
        "duplicate_keys": duplicate_keys(engine),
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
    """Tạo (hoặc dựng lại) chỉ mục duy nhất còn thiếu/sai của 16 bảng."""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    created: list[str] = []
    for name, expected in casework_indexes().items():
        if name not in existing:
            continue
        table = WarehouseBase.metadata.tables[name]
        actual = {
            index["name"]: tuple(index["column_names"]) for index in inspector.get_indexes(name) if index.get("unique")
        }
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            if index.name not in expected or actual.get(index.name) == expected[index.name]:
                continue
            if index.name in {item["name"] for item in inspector.get_indexes(name)}:
                # Có tên nhưng không duy nhất (hoặc sai cột): bỏ đi rồi dựng lại cho đúng.
                with engine.begin() as conn:
                    conn.execute(text(f'DROP INDEX IF EXISTS "{index.name}"'))
            index.create(engine, checkfirst=True)
            created.append(f"{name}.{index.name}")
    return created


def migrate(engine: Engine) -> dict[str, object]:
    before_tables = set(inspect(engine).get_table_names())
    legacy_before = _row_counts(engine, legacy_tables())
    created = ensure_casework_schema(engine)
    duplicates = duplicate_keys(engine)
    if duplicates:
        # Không tạo chỉ mục duy nhất trên dữ liệu đang trùng: `CREATE UNIQUE INDEX` sẽ nổ
        # và để lại lược đồ nửa vời. Dừng trước, in rõ nhóm nào trùng để người trực xử lý.
        return {
            "created_tables": created,
            "created_indexes": [],
            "tables_before": len(before_tables),
            "tables_after": len(before_tables) + len(created),
            "legacy_rows_before": legacy_before,
            "legacy_rows_after": _row_counts(engine, legacy_tables()),
            "legacy_drift": {},
            "duplicate_keys": duplicates,
            "blocked": True,
            **{key: value for key, value in inspect_state(engine).items() if key != "duplicate_keys"},
        }
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
        "duplicate_keys": state["duplicate_keys"],
    }


def rollback(engine: Engine) -> list[str]:
    """Bỏ 16 bảng mới. Chỉ dùng khi thật sự muốn mất dữ liệu DI."""
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
    """Điều kiện khiến `--check` trả mã thoát 1 (bảng cũ thiếu chỉ là cảnh báo)."""
    problems: list[str] = []
    if state.get("missing_casework"):
        problems.append("thiếu bảng: " + ", ".join(state["missing_casework"]))
    for table, columns in (state.get("missing_columns") or {}).items():
        problems.append(f"{table} thiếu cột: " + ", ".join(columns))
    for table, indexes in (state.get("missing_indexes") or {}).items():
        problems.append(f"{table} thiếu chỉ mục: " + ", ".join(indexes))
    for index_name, rows in (state.get("duplicate_keys") or {}).items():
        problems.append(f"{index_name} đang có khoá trùng: {rows}")
    return problems


def _warnings(state: dict[str, object]) -> list[str]:
    if state.get("missing_legacy"):
        return ["thiếu bảng kho ELT (chỉ là cảnh báo): " + ", ".join(state["missing_legacy"])]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Nâng cấp lược đồ bảng lát cắt DI (chỉ thêm bảng).")
    parser.add_argument("--check", action="store_true", help="Chỉ kiểm tra, không ghi.")
    parser.add_argument("--rollback", action="store_true", help="Bỏ 16 bảng lát cắt DI.")
    parser.add_argument("--yes", action="store_true", help="Xác nhận cho --rollback.")
    parser.add_argument("--json", action="store_true", help="In kết quả dạng JSON.")
    parser.add_argument("--database-url", default="", help="Ghi đè địa chỉ kho (mặc định lấy từ cấu hình).")
    args = parser.parse_args()

    engine = get_warehouse_engine(args.database_url or None)
    state = inspect_state(engine)

    if args.check:
        problems = _problems(state)
        warnings = _warnings(state)
        payload = {
            "status": "ok" if not problems else "missing",
            "problems": problems,
            "warnings": warnings,
            **state,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(_describe(problems))
            for warning in warnings:
                print("Cảnh báo: " + warning)
        return 0 if not problems else 1

    if args.rollback:
        if not args.yes:
            print("Từ chối chạy: thêm --yes để xác nhận bỏ 16 bảng lát cắt DI.")
            return 2
        dropped = rollback(engine)
        print(f"Đã bỏ {len(dropped)} bảng: {', '.join(dropped) if dropped else '(không có bảng nào)'}.")
        return 0

    report = migrate(engine)
    if report.get("blocked"):
        duplicates = report["duplicate_keys"]
        print("Từ chối tạo chỉ mục duy nhất: đang có khoá trùng.")
        for index_name, rows in duplicates.items():
            print(f"  {index_name}: {rows}")
        print("Sửa dữ liệu trùng rồi chạy lại. Chưa tạo chỉ mục nào.")
        return 1
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
    return "Đủ 16 bảng lát cắt DI (cột khớp, chỉ mục duy nhất đúng)."


if __name__ == "__main__":
    raise SystemExit(main())
