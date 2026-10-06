"""Kiểm tra kho ELT và chỉ mục RAG sau khi chạy pipeline.

Trả mã thoát 0 khi kho có tài liệu và chỉ mục khớp số đoạn trong PostgreSQL; ngược lại trả 1.
"""

from __future__ import annotations

import argparse
import json
import sys

from sqlalchemy import text

from src.services.warehouse import db as wh_db
from src.services.warehouse.queries import warehouse_overview


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kiểm tra kho ELT (PostgreSQL) và chỉ mục ChromaDB")
    parser.add_argument("--skip-rag", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        engine = wh_db.get_warehouse_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"KHÔNG kết nối được PostgreSQL: {exc.__class__.__name__}: {exc}")
        print(f"Địa chỉ đang dùng: {wh_db.elt_database_url()}")
        print("Gợi ý: docker compose -f docker-compose.elt.yml up -d --wait")
        return 1

    counts = wh_db.table_counts(engine)
    overview = warehouse_overview(engine)
    report: dict = {
        "database_url": wh_db.elt_database_url(),
        "table_counts": counts,
        "documents_by_source": overview["documents_by_source"],
        "documents_by_quality_status": overview["documents_by_quality_status"],
        "quality_findings": overview["quality_findings"],
    }

    problems: list[str] = []
    if counts.get("documents", 0) == 0:
        problems.append("Bảng documents trống: hãy chạy python -m scripts.elt.run_elt --profile bundle")

    if not args.skip_rag:
        from src.services.rag import build as rag_build

        try:
            stats = rag_build.index_stats(engine)
        except Exception as exc:
            stats = {"error": f"{exc.__class__.__name__}: {exc}"}
        report["rag"] = stats
        if isinstance(stats, dict) and stats.get("error") is None:
            if stats.get("chroma_chunks", 0) == 0:
                problems.append("ChromaDB trống: hãy chạy bước build-index (mặc định có trong run_elt)")
            elif stats.get("chroma_chunks") != stats.get("postgres_chunks"):
                problems.append(
                    f"Lệch số đoạn: Chroma={stats.get('chroma_chunks')} PostgreSQL={stats.get('postgres_chunks')}"
                )
        elif isinstance(stats, dict):
            problems.append(f"Không đọc được chỉ mục RAG: {stats.get('error')}")

    with wh_db.read_session(engine) as conn:
        from sqlalchemy import select

        from src.services.warehouse.models import EltRun, IngestionEvent

        runs = conn.execute(select(EltRun).order_by(EltRun.started_at.desc()).limit(5)).scalars().all()
        events = conn.execute(
            select(IngestionEvent).order_by(IngestionEvent.created_at.desc()).limit(5)
        ).scalars().all()
    report["recent_runs"] = [
        {"run_id": r.run_id, "profile": r.profile, "status": r.status,
         "started_at": r.started_at.isoformat() if r.started_at else None,
         "documents": (r.stats or {}).get("documents")}
        for r in runs
    ]
    report["recent_ingestion_events"] = [
        {"event_id": e.event_id, "kind": e.kind, "status": e.status, "title": e.title,
         "created_at": e.created_at.isoformat() if e.created_at else None}
        for e in events
    ]
    report["problems"] = problems
    report["ok"] = not problems

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"PostgreSQL: {report['database_url']}")
        print("Bảng:", json.dumps(counts, ensure_ascii=False))
        for source in report["documents_by_source"]:
            print(f"  - {source['source']}: {source['documents']} tài liệu "
                  f"(mức nội dung: {source['by_content_level']})")
        print("Trạng thái chất lượng:", json.dumps(report["documents_by_quality_status"], ensure_ascii=False))
        if "rag" in report:
            print("Chỉ mục RAG:", json.dumps(report["rag"], ensure_ascii=False))
        for run in report["recent_runs"]:
            print(f"  lần chạy: {run['run_id']} | {run['profile']} | {run['status']}")
        if problems:
            print("VẤN ĐỀ:")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print("KẾT LUẬN: kho và chỉ mục đạt yêu cầu kiểm tra.")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
