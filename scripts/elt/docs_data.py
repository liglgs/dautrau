"""Sinh tài liệu mô tả dữ liệu trong ``docs/data`` từ báo cáo ELT thật.

Chạy: ``python -m scripts.elt.docs_data``

Mọi số liệu trong ``docs/data/bao-cao-chat-luong.md`` đều lấy từ:
- báo cáo chất lượng mới nhất trong ``data/elt/reports/*-quality.json``
- số bản ghi thật trong PostgreSQL (nếu kho đang chạy)

Không có số liệu nào được viết tay, nên tài liệu luôn khớp với lần chạy ELT gần nhất.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.elt.config import DATA, REPORTS, ROOT

DOCS_DATA = ROOT / "docs" / "data"
OUTPUT = DOCS_DATA / "bao-cao-chat-luong.md"

SOURCE_LABEL = {
    "pubmed": "PubMed (trích y văn)",
    "dailymed": "DailyMed (nhãn thuốc FDA)",
    "faers": "openFDA FAERS (báo cáo ADR tự nguyện)",
    "reference": "Tài liệu tham chiếu (không phải bằng chứng chính)",
}

CONTENT_LEVEL_LABEL = {
    "abstract_only": "chỉ có tóm tắt + siêu dữ liệu (không có toàn văn)",
    "label_sections": "các mục nhãn thuốc",
    "spontaneous_report": "báo cáo tự nguyện",
    "reference_material": "tài liệu tham chiếu",
    "national_pv_bulletin": "bản tin cảnh giác dược quốc gia",
    "national_pv_bulletin_index": "mục lục bản tin cảnh giác dược",
    "data_source_documentation": "tài liệu mô tả nguồn dữ liệu",
    "case_assessment_guidance": "hướng dẫn đánh giá ca",
}


def latest_quality_report() -> Path | None:
    files = sorted(REPORTS.glob("*-quality.json"))
    return files[-1] if files else None


def warehouse_counts() -> dict[str, int] | None:
    try:
        from src.services.warehouse.db import get_warehouse_engine, table_counts
    except Exception:  # noqa: BLE001 - thiếu phụ thuộc thì bỏ phần này
        return None
    try:
        return table_counts(get_warehouse_engine())
    except Exception:  # noqa: BLE001 - kho chưa chạy thì bỏ qua
        return None


def rag_stats() -> dict | None:
    try:
        from src.services.rag.build import index_stats

        from src.services.warehouse.db import get_warehouse_engine

        return index_stats(get_warehouse_engine())
    except Exception:  # noqa: BLE001
        return None


def render(report: dict, counts: dict[str, int] | None, rag: dict | None) -> str:
    stats = report["stats"]
    lines: list[str] = []
    lines.append("# Báo cáo chất lượng dữ liệu ELT (tự sinh)")
    lines.append("")
    lines.append(
        "Tài liệu này do `python -m scripts.elt.docs_data` sinh ra từ báo cáo ELT thật. "
        "Không sửa tay; chạy lại lệnh trên sau mỗi lần nạp dữ liệu."
    )
    lines.append("")
    lines.append(f"- Lần chạy: `{report['run_id']}` (profile `{report['profile']}`)")
    lines.append(f"- Thời điểm sinh báo cáo ELT: {report['generated_at']}")
    lines.append(f"- Thời điểm sinh tài liệu này: {datetime.now(UTC).isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## 1. Khối lượng theo nguồn")
    lines.append("")
    lines.append("| Nguồn | Số tài liệu | Mức nội dung |")
    lines.append("| --- | --- | --- |")
    for source, payload in sorted(stats["by_source"].items()):
        levels = ", ".join(
            f"{CONTENT_LEVEL_LABEL.get(level, level)} ({count})"
            for level, count in sorted(payload["content_levels"].items())
        )
        lines.append(f"| {SOURCE_LABEL.get(source, source)} | {payload['count']} | {levels} |")
    lines.append(f"| **Tổng** | **{stats['documents']}** | |")
    lines.append("")
    lines.append("## 2. Quyết định của cổng chất lượng")
    lines.append("")
    lines.append("| Quyết định | Số tài liệu | Ý nghĩa |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| keep | {stats['keep']} | đủ điều kiện vào kho và chỉ mục RAG |")
    lines.append(f"| quarantine | {stats['quarantine']} | vào kho nhưng bị gắn cờ, không dùng làm bằng chứng chính |")
    lines.append(f"| reject | {stats['rejected']} | bị loại, không nạp |")
    lines.append("")
    lines.append("## 3. Cấu trúc từng nguồn")
    lines.append("")
    pubmed = stats.get("pubmed", {})
    if pubmed:
        lines.append(
            f"- PubMed: {pubmed.get('records', 0)} bản ghi, {pubmed.get('with_abstract', 0)} có tóm tắt, "
            f"{pubmed.get('metadata_only', 0)} chỉ có siêu dữ liệu."
        )
    dailymed = stats.get("dailymed", {})
    if dailymed:
        lines.append(
            f"- DailyMed: {dailymed.get('labels', 0)} nhãn, {dailymed.get('single_ingredient', 0)} đơn hoạt chất, "
            f"{dailymed.get('oral', 0)} dùng đường uống."
        )
    faers = stats.get("faers", {})
    if faers:
        lines.append(
            f"- FAERS: {faers.get('reports', 0)} báo cáo, {faers.get('multi_drug_reports', 0)} báo cáo có nhiều thuốc, "
            f"{faers.get('drug_rows', 0)} dòng thuốc, {faers.get('drug_rows_missing_start_date', 0)} dòng thiếu ngày bắt đầu, "
            f"{faers.get('missing_age', 0)} báo cáo thiếu tuổi, {faers.get('missing_sex', 0)} thiếu giới tính, "
            f"văn bản dài nhất {faers.get('max_text_chars', 0):,} ký tự."
        )
    lines.append("")
    lines.append("## 4. Phát hiện theo mã kiểm tra")
    lines.append("")
    lines.append("| Mã kiểm tra | Số lần |")
    lines.append("| --- | --- |")
    for name, count in sorted(stats.get("finding_counts", {}).items()):
        lines.append(f"| `{name}` | {count} |")
    lines.append("")
    lines.append("## 5. Số bản ghi thật trong PostgreSQL")
    lines.append("")
    if counts:
        lines.append("| Bảng | Số bản ghi |")
        lines.append("| --- | --- |")
        for table, value in sorted(counts.items()):
            lines.append(f"| `{table}` | {value:,} |")
    else:
        lines.append("_Kho PostgreSQL chưa chạy khi sinh tài liệu — chạy `docker compose -f docker-compose.elt.yml up -d --wait` rồi chạy lại._")
    lines.append("")
    lines.append("## 6. Chỉ mục vector (ChromaDB)")
    lines.append("")
    if rag:
        lines.append(f"- Bộ sưu tập: `{rag['collection']}`")
        lines.append(f"- Mô hình nhúng: `{rag['embedding_model']}` (provider `{rag['embedding_provider']}`)")
        lines.append(f"- Số đoạn trong ChromaDB: {rag['chroma_chunks']:,}")
        lines.append(f"- Số đoạn trong PostgreSQL: {rag['postgres_chunks']:,}")
        drift = rag["chroma_chunks"] - rag["postgres_chunks"]
        lines.append(f"- Lệch: {drift} (0 nghĩa là hai kho khớp nhau)")
        lines.append(f"- Thư mục lưu: `{rag['persist_dir']}`")
    else:
        lines.append("_Chưa dựng chỉ mục vector._")
    lines.append("")
    lines.append("## 7. Cách chạy lại")
    lines.append("")
    lines.append("```bash")
    lines.append("# 1. Tải dữ liệu thô và ghi manifest (không cần mạng nếu đã có sẵn)")
    lines.append("python -m scripts.elt.run_elt --profile bundle")
    lines.append("# 2. Nạp kho PostgreSQL + dựng chỉ mục ChromaDB")
    lines.append("python -m scripts.elt.run_elt --profile all --reset-db")
    lines.append("# 3. Kiểm tra kho và sinh lại tài liệu này")
    lines.append("python -m scripts.elt.check_warehouse")
    lines.append("python -m scripts.elt.docs_data")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report_path = latest_quality_report()
    if report_path is None:
        print("Chưa có báo cáo chất lượng nào trong data/elt/reports — chạy run_elt trước.")
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(report, warehouse_counts(), rag_stats()), encoding="utf-8")
    print(f"Đã ghi {OUTPUT.relative_to(ROOT)} từ {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
