"""Run the Person 3 preparation kit offline and create a synthetic draft.

This is a technical preview, not an agent run or an official dossier export.
"""

import argparse
import json
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from string import Template

TASK_ROOT = Path(__file__).resolve().parents[1]
if str(TASK_ROOT) not in sys.path:
    sys.path.insert(0, str(TASK_ROOT))

from src.services.evidence.citations import text_hash, validate_citation  # noqa: E402
from src.services.evidence.contradiction import compare_evidence  # noqa: E402
from src.services.evidence.drafts import CitationDraft, DocumentDraft, EvidenceDraft, scope_from_dict  # noqa: E402
from src.services.evidence.normalize import load_dictionary, normalize_claim  # noqa: E402
from src.services.evidence.scope import assess_scope  # noqa: E402

FIXTURE_PATH = TASK_ROOT / "tests/fixtures/mvp/person3/cases.json"
DICTIONARY_PATH = TASK_ROOT / "data/dictionaries/person3_synthetic.json"


def changed_scope(base: dict, changes: dict):
    result = deepcopy(base)
    result.update(changes)
    return scope_from_dict(result)


def fixture_document(payload: dict) -> tuple[DocumentDraft, CitationDraft]:
    document = DocumentDraft(
        document_id=payload["document_id"], source_id=payload["source_id"],
        source_version=payload["source_version"], source_url=payload["source_url"],
        text=payload["text"], content_hash=text_hash(payload["text"]), mode="synthetic",
    )
    start = document.text.index(payload["quote"])
    citation = CitationDraft(
        document.document_id, document.source_id, document.source_version, document.source_url,
        document.content_hash, payload["quote"], start, start + len(payload["quote"]),
    )
    return document, citation


def run_preparation() -> dict:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if payload["mode"] != "synthetic":
        raise ValueError("This preview is only for explicitly synthetic fixtures")
    dictionary = load_dictionary(DICTIONARY_PATH)
    rows = []
    for case in payload["scope_cases"]:
        result = assess_scope(
            changed_scope(payload["base_scope"], case["evidence_changes"]),
            changed_scope(payload["base_scope"], case["claim_changes"]),
        )
        statuses = {item.field: item.status for item in result.fields}
        expected = case["expected"]
        passed = result.eligible_as_direct_evidence == expected["eligible"] and all(
            statuses[name] == status for name, status in expected["field_statuses"].items()
        )
        rows.append({"id": case["id"], "task": "scope", "expected": expected, "actual": asdict(result), "passed": passed})
    for case in payload["normalization_cases"]:
        result = normalize_claim(case["drug"], case["event"], dictionary, allow_synthetic=True)
        expected = case["expected"]
        passed = (
            list(result.ingredient_candidates) == expected["ingredients"]
            and list(result.event_candidates) == expected["events"]
            and result.requires_review == expected["requires_review"]
        )
        rows.append({"id": case["id"], "task": "normalization", "expected": expected, "actual": asdict(result), "passed": passed})
    left = EvidenceDraft("SYN-E-LEFT", scope_from_dict(payload["base_scope"]), "support", "pubmed", "low", "increase")
    for case in payload["contradiction_cases"]:
        right = EvidenceDraft(
            "SYN-E-RIGHT", changed_scope(payload["base_scope"], case["right_scope_changes"]),
            "contradict", case["right_source"], case["right_uncertainty"], case["right_direction"],
        )
        result = compare_evidence(left, right)
        rows.append({
            "id": case["id"], "task": "contradiction", "expected": case["expected_kind"],
            "actual": asdict(result), "passed": result.kind == case["expected_kind"],
        })
    document, base_citation = fixture_document(payload["document"])
    for case in payload["citation_cases"]:
        result = validate_citation(document, replace(base_citation, **case["changes"]))
        rows.append({
            "id": case["id"], "task": "citation_integrity", "expected": case["expected_errors"],
            "actual": asdict(result), "passed": sorted(result.errors) == sorted(case["expected_errors"]),
        })
    return {
        "mode": "synthetic", "contract_status": "draft_pending_M01",
        "scope": "development technical verification; not clinical evaluation",
        "fixture_hash": text_hash(FIXTURE_PATH.read_text(encoding="utf-8")),
        "dictionary_version": dictionary["version"],
        "total": len(rows), "passed": sum(row["passed"] for row in rows), "results": rows,
    }


def write_preview(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "technical-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    document, citation = fixture_document(payload["document"])
    template = Template((TASK_ROOT / "data/templates/dossier.synthetic.md").read_text(encoding="utf-8"))
    rendered = template.substitute(
        investigation_id="SYN-PERSON3-PREVIEW",
        document_label="NHÁP SYNTHETIC — dữ liệu giả lập, chưa được chuyên viên duyệt",
        mode="synthetic (offline)", dossier_version="draft-0.1", review_status="pending",
        claim_summary="Nhận định kỹ thuật giả lập về ingredient_alpha / event_alpha. Tuổi 18–65, oral, 10 mg/day, 0–30 days. Các giá trị không mô tả thuốc thật.",
        proposed_assessment_status="requires_human_review (minh họa; không phải output của Agent)",
        assessment_status="null — chưa có assessment review",
        stop_reason="Preview kết thúc sau kiểm tra kỹ thuật; chưa có truy xuất nguồn thật hoặc đánh giá chuyên môn.",
        search_strategy="Không có truy vấn live. Đọc fixture đã lưu trong tests/fixtures/mvp/person3/cases.json.",
        evidence_table="| ID | Nguồn | Stance | Citation |\n|---|---|---|---|\n| SYN-E-001 | Synthetic excerpt | background | SYN-SOURCE-001 v1; entailment pending |",
        scope_and_contradictions="Các ca S01–S08/C01–C04 có output trong technical-results.json. Đây là các tình huống độc lập, không phải bằng chứng của cùng một cuộc điều tra.",
        gaps_and_limitations="- Chưa có corpus thật, LLM extraction, gateway hoặc gold chuyên môn.\n- Quote/hash đúng chỉ xác nhận vị trí; statement entailment vẫn pending.\n- Dictionary hoàn toàn synthetic.\n- Không có approval hoặc export chính thức.",
        citations=(
            f"SYN-SOURCE-001 v1 · synthetic_excerpt · document {document.document_id}\n\n"
            f"> {citation.quoted_span}\n\n"
            f"Locator: Unicode offsets [{citation.start}, {citation.end}).\n\n"
            f"Parsed-text SHA-256: `{document.content_hash}`.\n\n"
            "Source URL: `https://example.invalid/synthetic/person3/SYN-SOURCE-001` — placeholder synthetic, không phải nguồn đã truy xuất."
        ),
        review_decisions="Chưa có quyết định. Không gán reviewer giả hoặc trạng thái approved.",
        audit_reference="technical-results.json lưu fixture hash, dictionary version và output từng ca. Đây là trace kiểm tra kỹ thuật, chưa phải audit log của Agent.",
    )
    (output_dir / "dossier-synthetic-draft.md").write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=TASK_ROOT / "eval/person3")
    args = parser.parse_args()
    report = run_preparation()
    write_preview(report, args.output_dir)
    print(f"Synthetic technical cases: {report['passed']}/{report['total']} passed")
    print("Created: technical-results.json, dossier-synthetic-draft.md")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
