"""Tầng Quality: cổng kiểm định dữ liệu trước khi nạp kho và dựng RAG.

Ba mức quyết định:
  * ``reject``     — loại khỏi kho (sai định danh, thiếu nội dung, báo cáo quá lớn, trùng lặp);
  * ``quarantine`` — giữ trong kho nhưng không đưa vào chỉ mục RAG (thiếu trường, lệch phạm vi);
  * ``keep``       — đủ điều kiện cho RAG, kèm cờ cảnh báo (không phải "đã xác thực chuyên môn").

Cổng kiểm tra chạy trên bản ghi chuẩn và bản thô, tất định, không dùng mô hình.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.elt.parse import ParsedDocument

TEXT_MIN_CHARS = 40
FAERS_MAX_TEXT = 200_000


@dataclass
class Finding:
    doc_id: str
    pair_id: str | None
    source: str
    check_name: str
    severity: str  # info | warn | error
    decision: str  # keep | quarantine | reject | note
    detail: str


@dataclass
class DocVerdict:
    decision: str = "keep"
    flags: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def add(self, doc: ParsedDocument, check: str, severity: str, decision: str, detail: str) -> None:
        if decision == "reject":
            self.decision = "reject"
        elif decision == "quarantine" and self.decision != "reject":
            self.decision = "quarantine"
        if check not in self.flags:
            self.flags.append(check)
        self.findings.append(Finding(doc.doc_id, doc.pair_id, doc.source, check, severity, decision, detail))


def _check_pubmed(doc: ParsedDocument, verdict: DocVerdict) -> None:
    if doc.structured.get("has_abstract"):
        verdict.add(doc, "has_abstract", "info", "keep", "Có tóm tắt (abstract).")
    else:
        verdict.add(doc, "missing_abstract", "warn", "quarantine",
                    "Chỉ có metadata, không có tóm tắt; không dùng làm bằng chứng nội dung.")
    types = [t.lower() for t in doc.structured.get("publication_types", [])]
    if any("retracted" in t for t in types):
        verdict.add(doc, "retracted_publication", "error", "reject", "Bài báo đã bị rút.")
    if any("comment" in t or "editorial" in t or "letter" in t for t in types):
        verdict.add(doc, "not_primary_evidence", "warn", "quarantine",
                    "Loại bài không phải nghiên cứu gốc (thư/ý kiến/biên tập).")
    if not doc.structured.get("doi"):
        verdict.add(doc, "missing_doi", "info", "note", "Không có DOI trong bản ghi.")
    if doc.structured.get("journal"):
        verdict.add(doc, "has_journal", "info", "keep", "Có tên tạp chí.")


def _check_dailymed(doc: ParsedDocument, verdict: DocVerdict) -> None:
    structured = doc.structured
    if not structured.get("single_ingredient"):
        verdict.add(doc, "multi_ingredient", "warn", "quarantine",
                    "Nhãn nhiều hoạt chất; cần xác minh sản phẩm trước khi dùng.")
    routes = [str(r).upper() for r in structured.get("routes", []) if r]
    if not routes:
        verdict.add(doc, "missing_route", "warn", "quarantine", "Nhãn thiếu thông tin đường dùng.")
    elif not any("ORAL" in r or "MOUTH" in r for r in routes):
        verdict.add(doc, "route_not_oral", "warn", "quarantine",
                    f"Đường dùng không phải uống: {', '.join(routes)}.")
    if not structured.get("effective_time"):
        verdict.add(doc, "missing_effective_time", "warn", "quarantine", "Nhãn thiếu ngày hiệu lực.")
    if int(structured.get("n_sections") or 0) == 0:
        verdict.add(doc, "missing_sections", "error", "reject", "Nhãn không có mục nội dung nào.")
    if int(structured.get("n_sections") or 0) < 3:
        verdict.add(doc, "few_sections", "info", "note",
                    f"Nhãn chỉ có {structured.get('n_sections')} mục.")


def _check_faers(doc: ParsedDocument, verdict: DocVerdict) -> None:
    structured = doc.structured
    if int(structured.get("n_reactions") or 0) == 0:
        verdict.add(doc, "no_reactions", "error", "reject", "Báo cáo không có phản ứng nào.")
    if int(structured.get("n_drugs") or 0) == 0:
        verdict.add(doc, "no_drugs", "error", "reject", "Báo cáo không có thuốc nào.")
    if len(doc.text) > FAERS_MAX_TEXT:
        verdict.add(doc, "report_too_large", "error", "reject",
                    f"Báo cáo dài {len(doc.text)} ký tự, vượt giới hạn {FAERS_MAX_TEXT}.")
    if not structured.get("patient_age"):
        verdict.add(doc, "missing_age", "warn", "quarantine", "Thiếu tuổi bệnh nhân.")
    if not structured.get("patient_sex"):
        verdict.add(doc, "missing_sex", "warn", "quarantine", "Thiếu giới tính bệnh nhân.")
    if int(structured.get("n_drugs") or 0) > 1:
        verdict.add(doc, "multiple_drugs", "info", "note",
                    f"Báo cáo có {structured.get('n_drugs')} thuốc; quan hệ thuốc–biến cố chưa chắc chắn.")
    drugs = structured.get("drugs") or []
    # Thiếu ngày/đường dùng là tình trạng phổ biến của FAERS: ghi cờ nhưng vẫn dùng được văn bản.
    if drugs and not any(d.get("start_date") for d in drugs):
        verdict.add(doc, "missing_drug_start_date", "warn", "note",
                    "Không có ngày bắt đầu dùng thuốc cho bất kỳ dòng thuốc nào.")
    if drugs and not any(d.get("route") for d in drugs):
        verdict.add(doc, "missing_drug_route", "warn", "note", "Thiếu đường dùng của thuốc.")
    if not structured.get("receivedate"):
        verdict.add(doc, "missing_receivedate", "warn", "quarantine", "Thiếu ngày FDA nhận báo cáo.")
    verdict.add(doc, "suspicion_not_causality", "info", "note",
                "Báo cáo nghi ngờ; không kết luận nhân quả và không dùng làm tỷ lệ mắc.")


def _check_common(doc: ParsedDocument, verdict: DocVerdict) -> None:
    if not doc.title.strip():
        verdict.add(doc, "no_title", "error", "reject", "Thiếu tiêu đề.")
    if len(doc.text.strip()) < TEXT_MIN_CHARS:
        verdict.add(doc, "text_too_short", "error", "reject", f"Văn bản chỉ {len(doc.text)} ký tự.")
    if not doc.raw_sha256:
        verdict.add(doc, "raw_hash_missing", "error", "reject", "Không xác định được băm bản thô.")
    if "<" in doc.text[:200] and ">" in doc.text[:200] and doc.source != "faers":
        verdict.add(doc, "possible_markup", "warn", "note", "Văn bản có ký tự giống thẻ HTML.")


def evaluate_document(doc: ParsedDocument) -> DocVerdict:
    verdict = DocVerdict()
    _check_common(doc, verdict)
    if doc.source == "pubmed":
        _check_pubmed(doc, verdict)
    elif doc.source == "dailymed":
        _check_dailymed(doc, verdict)
    elif doc.source == "faers":
        _check_faers(doc, verdict)
    return verdict


def evaluate_all(documents: list[ParsedDocument]) -> list[tuple[ParsedDocument, DocVerdict]]:
    """Chấm điểm từng tài liệu **một lần** và gắn cổng trùng định danh trong cùng lần chạy."""
    results: list[tuple[ParsedDocument, DocVerdict]] = []
    seen: set[tuple[str, str, int]] = set()
    for doc in documents:
        verdict = evaluate_document(doc)
        key = (doc.source, doc.source_id, doc.version)
        if key in seen:
            verdict.add(doc, "duplicate_in_run", "error", "reject", "Trùng định danh trong cùng lần chạy.")
        seen.add(key)
        results.append((doc, verdict))
    return results


def verdict_map(results: list[tuple[ParsedDocument, DocVerdict]]) -> dict[str, DocVerdict]:
    """Bảng tra ``doc_id → verdict`` cho bước ghi staging/báo cáo."""
    return {doc.doc_id: verdict for doc, verdict in results}


def partition(
    results: list[tuple[ParsedDocument, DocVerdict]],
) -> tuple[list[ParsedDocument], list[ParsedDocument], list[ParsedDocument]]:
    """Chia tài liệu thành ba nhóm theo quyết định đã chấm."""
    keep: list[ParsedDocument] = []
    quarantine: list[ParsedDocument] = []
    rejected: list[ParsedDocument] = []
    for doc, verdict in results:
        if verdict.decision == "reject":
            rejected.append(doc)
        elif verdict.decision == "quarantine":
            quarantine.append(doc)
        else:
            keep.append(doc)
    return keep, quarantine, rejected


def apply_gates(documents: list[ParsedDocument]) -> tuple[list[ParsedDocument], list[ParsedDocument], list[ParsedDocument]]:
    """Trả về (giữ cho RAG, cách ly, bị loại)."""
    return partition(evaluate_all(documents))


def dataset_stats(documents: list[ParsedDocument], findings: list[Finding]) -> dict:
    """Thống kê tổng hợp phục vụ báo cáo chất lượng và ghi chú tái lập."""
    stats: dict = {"documents": len(documents), "by_source": {}, "pairs": {}}
    for doc in documents:
        bucket = stats["by_source"].setdefault(doc.source, {"count": 0, "content_levels": {}})
        bucket["count"] += 1
        level = doc.content_level or "unknown"
        bucket["content_levels"][level] = bucket["content_levels"].get(level, 0) + 1
        pair = stats["pairs"].setdefault(doc.pair_id or "reference", {"pubmed": 0, "dailymed": 0, "faers": 0})
        pair[doc.source] = pair.get(doc.source, 0) + 1
    faers = [d for d in documents if d.source == "faers"]
    if faers:
        stats["faers"] = {
            "reports": len(faers),
            "multi_drug_reports": sum(1 for d in faers if int(d.structured.get("n_drugs") or 0) > 1),
            "missing_age": sum(1 for d in faers if not d.structured.get("patient_age")),
            "missing_sex": sum(1 for d in faers if not d.structured.get("patient_sex")),
            "drug_rows": sum(int(d.structured.get("n_drugs") or 0) for d in faers),
            "drug_rows_missing_start_date": sum(
                1 for d in faers for row in (d.structured.get("drugs") or []) if not row.get("start_date")
            ),
            "max_text_chars": max(len(d.text) for d in faers),
            "over_size_limit": sum(1 for d in faers if len(d.text) > FAERS_MAX_TEXT),
        }
    pubmed = [d for d in documents if d.source == "pubmed"]
    if pubmed:
        stats["pubmed"] = {
            "records": len(pubmed),
            "with_abstract": sum(1 for d in pubmed if d.structured.get("has_abstract")),
            "metadata_only": sum(1 for d in pubmed if not d.structured.get("has_abstract")),
        }
    dailymed = [d for d in documents if d.source == "dailymed"]
    if dailymed:
        stats["dailymed"] = {
            "labels": len(dailymed),
            "single_ingredient": sum(1 for d in dailymed if d.structured.get("single_ingredient")),
            "oral": sum(1 for d in dailymed if any("ORAL" in str(r).upper() for r in d.structured.get("routes", []))),
        }
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.check_name] = counts.get(finding.check_name, 0) + 1
    stats["finding_counts"] = dict(sorted(counts.items()))
    return stats


def render_markdown(stats: dict, findings: list[Finding], verdicts: dict[str, str], run_id: str) -> str:
    lines = [f"# Báo cáo chất lượng dữ liệu ELT — {run_id}", ""]
    lines.append(f"- Số tài liệu đã phân tích: {stats.get('documents', 0)}")
    for source, bucket in sorted(stats.get("by_source", {}).items()):
        lines.append(f"- {source}: {bucket['count']} tài liệu, mức nội dung {bucket['content_levels']}")
    lines.append("")
    lines.append("## Quyết định cổng chất lượng")
    for decision in ("keep", "quarantine", "reject"):
        names = sorted(doc_id for doc_id, value in verdicts.items() if value == decision)
        lines.append(f"- {decision}: {len(names)}")
        for name in names[:40]:
            lines.append(f"  - {name}")
    lines.append("")
    lines.append("## Phát hiện theo mã kiểm tra")
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.check_name] = counts.get(finding.check_name, 0) + 1
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {name}: {count}")
    lines.append("")
    lines.append("## Thống kê nguồn")
    for key in ("pubmed", "dailymed", "faers"):
        if key in stats:
            lines.append(f"### {key}")
            for name, value in stats[key].items():
                lines.append(f"- {name}: {value}")
    return "\n".join(lines) + "\n"
