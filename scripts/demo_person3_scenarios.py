"""Show actual Person 3 service outputs for synthetic scenarios, using the shared gateway/store."""

import argparse
import json
import tempfile
from pathlib import Path

from src.models.schemas import (
    AssessmentResult, AssessmentStatus, CheckpointKind, ClaimInput, EvidenceGap,
    GapKind, ReviewAction, ReviewDecision, RunStatus, SourceDocument,
)
from src.services.dossier import export_markdown, render_markdown, validate_dossier
from src.services.errors import MvpError
from src.services.evidence.citations import text_hash
from src.services.evidence.integration import configure_person3
from src.services.evidence.nodes import extract_assess_person3
from src.services.llm import LLMGateway, MockProvider
from src.services.review import apply_review
from src.services.runner import RunContext
from src.services.store import MvpStore

ROOT = Path(__file__).resolve().parents[1]
from src.services.evidence.demo import SCENARIOS, build_inputs


def demonstrate_review(store, state, dossier):
    """Controlled synthetic review decisions in the temporary test DB only."""
    store.save_dossier(dossier)
    state = store.save_state(state.model_copy(update={
        "checkpoint": CheckpointKind.DOSSIER, "run_status": RunStatus.WAITING_FOR_REVIEW,
    }))

    def can_export():
        try:
            export_markdown(store, state.investigation_id)
            return True
        except MvpError:
            return False

    before = can_export()
    apply_review(store, ReviewDecision(
        decision_id="SYNTHETIC-APPROVE", investigation_id=state.investigation_id,
        checkpoint=CheckpointKind.DOSSIER, action=ReviewAction.APPROVE,
        reviewer_id="synthetic-test-reviewer", expected_version=state.version,
    ))
    approved = can_export()
    state = store.get_state(state.investigation_id)
    state = store.save_state(state.model_copy(update={
        "checkpoint": CheckpointKind.ASSESSMENT, "run_status": RunStatus.WAITING_FOR_REVIEW,
    }))
    apply_review(store, ReviewDecision(
        decision_id="SYNTHETIC-EDIT", investigation_id=state.investigation_id,
        checkpoint=CheckpointKind.ASSESSMENT, action=ReviewAction.EDIT_EVIDENCE,
        reviewer_id="synthetic-test-reviewer", expected_version=state.version,
        target_evidence_id=state.evidence[0].evidence_id, payload={"quote": "Event Alpha"},
    ))
    edited = can_export()
    return {"before_approval": before, "after_synthetic_approval": approved, "after_evidence_edit": edited}


def run_scenario(name, folder):
    claim, inputs = build_inputs(name)
    responses = {document["doc_id"]: response for document, response in inputs}

    def respond(prompt, system):
        for identifier, response in responses.items():
            if identifier in prompt:
                return response
        raise ValueError("No synthetic response for this document")

    store = MvpStore(str(folder / f"{name}.sqlite3"))
    try:
        state, _ = store.create_investigation(ClaimInput(**claim))
        ctx = configure_person3(
            RunContext(store=store, gateway=LLMGateway(MockProvider({"extract_evidence": respond}))),
            ROOT / "data/dictionaries/person3_synthetic.json", allow_synthetic=True,
        )
        normalized = ctx.normalizer.normalize_claim(state.claim)
        documents = [SourceDocument(**document, hash=text_hash(document["text"])) for document, _ in inputs]
        for document in documents:
            store.save_document(state.investigation_id, document)
        budget = state.budget.model_copy(update={"documents_used": len(documents)})
        state = store.save_state(state.model_copy(update={
            "normalized_claim": normalized, "documents": documents, "budget": budget,
            "searched_sources": sorted({document.source for document in documents}),
        }))
        if normalized.requires_review:
            assessment = AssessmentResult(
                assessment_status=AssessmentStatus.REQUIRES_HUMAN_REVIEW,
                rationale="Claim target is ambiguous: " + "; ".join(normalized.ambiguities),
            )
            state = store.save_state(state.model_copy(update={
                "assessment_status": assessment.assessment_status, "assessment": assessment,
                "gaps": [EvidenceGap(gap_id="GAP-P3-AMBIGUITY", kind=GapKind.AMBIGUITY,
                                     description=assessment.rationale, priority=5)],
            }))
        else:
            state = extract_assess_person3({"investigation": state, "ctx": ctx})["investigation"]
        dossier = ctx.dossier_builder(state)
        validation = validate_dossier(dossier, state)
        report = {
            "scenario": name, "title": SCENARIOS[name][0], "mode": "synthetic",
            "expected_technical_status": SCENARIOS[name][1], "actual_status": state.assessment_status,
            "passed": state.assessment_status == SCENARIOS[name][1] and validation.ok,
            "input_claim": claim, "normalized_claim": normalized.model_dump(mode="json"),
            "source_documents": [document.model_dump(mode="json") for document in documents],
            "evidence": [item.model_dump(mode="json") for item in state.evidence],
            "assessment": state.assessment.model_dump(mode="json"),
            "gaps": [gap.model_dump(mode="json") for gap in state.gaps],
            "budget": state.budget.model_dump(mode="json"), "validation": validation.model_dump(mode="json"),
            "dossier_markdown": render_markdown(dossier), "approved_dossier": False,
        }
        if name == "match":
            report["review_demo"] = demonstrate_review(store, state, dossier)
            report["passed"] &= report["review_demo"] == {
                "before_approval": False, "after_synthetic_approval": True, "after_evidence_edit": False,
            }
        return report
    finally:
        store.close()


def write_report(reports, directory):
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["# Thử phần Người 3 qua các kịch bản", "",
             "> Dữ liệu hư cấu. Code Python Người 3, gateway và SQLite/review của Người 2 được gọi thật; model/nguồn được giả lập. Đây là thử các dịch vụ, chưa chạy toàn LangGraph/API/UI.", "",
             "| Kịch bản | Kết quả code trả về | Đối chiếu fixture |", "|---|---|---|"]
    for report in reports:
        name = report["scenario"]
        (directory / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (directory / f"{name}-dossier.md").write_text("> SYNTHETIC DRAFT — chưa duyệt, không phải bằng chứng y khoa.\n\n" + report["dossier_markdown"], encoding="utf-8")
        lines.append(f"| {report['title']} | `{report['actual_status']}` | {'Đạt' if report['passed'] else 'Không đạt'} |")
    lines.extend(["", "## Cách đọc kết quả", "",
                  "Mỗi file JSON chứa input, claim chuẩn hóa, văn bản nguồn, evidence/quote/locator, scope, lý do đánh giá, gaps và ngân sách. File dossier đi kèm là đầu ra nháp.", ""])
    for report in reports:
        name = report["scenario"]
        excluded = sum(item["excluded"] for item in report["evidence"])
        lines.extend([f"## {report['title']}", "",
                      f"- Claim: `{report['input_claim']['drug']}` / `{report['input_claim']['event']}`; route `{report['input_claim']['route']}`.",
                      f"- Kết quả: `{report['actual_status']}`.",
                      f"- Evidence: {len(report['evidence'])}; bị loại: {excluded}; LLM mock calls: {report['budget']['llm_calls']}.",
                      f"- [Input và output đầy đủ]({name}.json) · [Dossier nháp]({name}-dossier.md).", ""])
        if report.get("review_demo"):
            lines.extend(["**Thử duyệt hồ sơ bằng SQLite tạm:** trước duyệt export bị chặn; sau quyết định duyệt giả lập export được; sửa evidence thì export bị chặn lại. Không phải quyết định duyệt của người dùng.", ""])
    (directory / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "eval/person3/scenarios")
    args = parser.parse_args()
    names = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    with tempfile.TemporaryDirectory(prefix="p066-person3-scenarios-") as folder:
        reports = [run_scenario(name, Path(folder)) for name in names]
    write_report(reports, args.output_dir)
    for report in reports:
        print(f"{report['scenario']}: {report['actual_status']} | {'PASS' if report['passed'] else 'FAIL'}")
    print("Results: eval/person3/scenarios/README.md and per-case JSON/dossier files")
    return 0 if all(report["passed"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
