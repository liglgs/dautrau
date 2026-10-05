"""Kịch bản nghiệm thu toàn diện công việc Người 2 (Core Backend & Agent Orchestrator).

Chạy qua 5 cặp ứng viên lâm sàng trong tập dữ liệu 50 mẫu:
  1. metformin / diarrhoea
  2. amoxicillin / rash
  3. atorvastatin / myalgia
  4. ibuprofen / gastrointestinal haemorrhage
  5. lisinopril / cough

Xác minh:
  - Chuẩn hóa claim (ClaimNormalizer Người 3)
  - Lập kế hoạch và điều phối (Planner & Budget Người 2)
  - Truy xuất tài liệu local (LocalPubMedAdapter Người 1)
  - Trích xuất bằng chứng (CandidateQuoteProvider / EvidenceExtractor Người 3)
  - Đánh giá và dừng an toàn (Stopping / Assessment Người 2 & 3)
  - Quy trình Human-in-the-loop: Thẩm định -> Duyệt -> Tạo Dossier -> Phê duyệt -> Xuất Markdown
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# Đảm bảo import được src và eval
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.graph import run_investigation
from src.models.schemas import (
    AssessmentStatus,
    CheckpointKind,
    ClaimInput,
    InvestigationConfig,
    ReviewAction,
    ReviewDecision,
    ReviewStatus,
    RunStatus,
)
from src.services.dossier import export_markdown
from src.services.evidence.candidate_provider import CandidateQuoteProvider
from src.services.evidence.integration import configure_person3
from src.services.evidence.normalize import load_dictionary
from src.services.llm import LLMGateway
from src.services.review import apply_review
from src.services.runner import InProcessRunner
from src.services.sources import build_adapters
from src.services.store import MvpStore

PAIRS = [
    {"drug": "metformin", "event": "diarrhoea", "population": "adults", "route": "oral"},
    {"drug": "amoxicillin", "event": "rash", "population": None, "route": "oral"},
    {"drug": "atorvastatin", "event": "myalgia", "population": "adults", "route": "oral"},
    {"drug": "ibuprofen", "event": "gastrointestinal haemorrhage", "population": None, "route": "oral"},
    {"drug": "lisinopril", "event": "cough", "population": "adults", "route": "oral"},
]

CORPUS_ROOT = ROOT / "data/pubmed-local"
SNAPSHOT_ROOT = ROOT / "data/snapshots"
DICTIONARY_PATH = ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json"


def verify_pair(store: MvpStore, pair_info: dict, index: int) -> dict:
    drug = pair_info["drug"]
    event = pair_info["event"]
    population = pair_info.get("population")
    route = pair_info.get("route")

    claim_input = ClaimInput(
        claim_text=f"Investigate reported association: {drug} / {event}.",
        drug=drug,
        event=event,
        population=population,
        route=route,
        config=InvestigationConfig(sources=["pubmed"], max_steps=4, max_documents=5),
    )
    state, _ = store.create_investigation(claim_input)

    gateway = LLMGateway(CandidateQuoteProvider(load_dictionary(DICTIONARY_PATH)))
    runner = InProcessRunner(store, gateway=gateway)
    ctx = runner.context()
    ctx.adapters = build_adapters(
        pubmed_mode="local",
        pubmed_corpus_root=str(CORPUS_ROOT),
        snapshot_root=str(SNAPSHOT_ROOT),
        drug=drug,
        event=event,
        max_documents=5,
    )
    configure_person3(ctx, DICTIONARY_PATH)

    # 1. Chạy điều tra
    paused_state = run_investigation(state, ctx)
    assert paused_state.run_status is RunStatus.WAITING_FOR_REVIEW
    assert paused_state.checkpoint is CheckpointKind.ASSESSMENT

    docs = store.list_documents(paused_state.investigation_id)

    # 2. Reviewer thẩm định kết quả
    review_decision = ReviewDecision(
        decision_id=f"rev-dec-pair-{index}-1",
        investigation_id=paused_state.investigation_id,
        reviewer_id="reviewer_senior",
        action=ReviewAction.APPROVE,
        checkpoint=CheckpointKind.ASSESSMENT,
        reason=f"Phê duyệt đánh giá lâm sàng cho {drug} / {event}",
        expected_version=paused_state.version,
    )
    apply_review(store, review_decision)
    resumed_state = store.get_state(paused_state.investigation_id)

    # 3. Chạy tiếp để tạo dossier
    dossier_paused = runner.run(resumed_state.investigation_id, resume=True)
    assert dossier_paused.checkpoint is CheckpointKind.DOSSIER

    dossiers = store.list_dossiers(dossier_paused.investigation_id)
    assert len(dossiers) >= 1
    dossier = dossiers[-1]

    # 4. Reviewer phê duyệt dossier để hoàn tất
    approve_decision = ReviewDecision(
        decision_id=f"rev-dec-pair-{index}-2",
        investigation_id=dossier_paused.investigation_id,
        reviewer_id="reviewer_senior",
        action=ReviewAction.APPROVE,
        checkpoint=CheckpointKind.DOSSIER,
        reason=f"Phê duyệt hồ sơ chính thức cho {drug} / {event}",
        expected_version=dossier_paused.version,
    )
    apply_review(store, approve_decision)
    final_state = store.get_state(dossier_paused.investigation_id)
    assert final_state.run_status is RunStatus.COMPLETED

    approved_dossiers = [d for d in store.list_dossiers(final_state.investigation_id) if d.status is ReviewStatus.APPROVED]
    assert len(approved_dossiers) == 1
    approved = approved_dossiers[0]

    # 5. Xuất báo cáo Markdown qua API export của hệ thống
    md_content = export_markdown(store, final_state.investigation_id)
    assert len(md_content) > 100
    assert drug in md_content.lower()

    return {
        "drug": drug,
        "event": event,
        "investigation_id": final_state.investigation_id,
        "docs_count": len(docs),
        "assessment": str(final_state.assessment_status.value if final_state.assessment_status else "n/a"),
        "dossier_sections": len(approved.sections),
        "citations": len(approved.citations),
        "status": "PASS",
    }


def main() -> int:
    print("=" * 80)
    print("  KIỂM CHỨNG TOÀN DIỆN NGƯỜI 2: 5 CẶP ỨNG VIÊN DỮ LIỆU THỰC TẾ")
    print("=" * 80)

    if not (CORPUS_ROOT / "manifest.json").exists():
        print(f"[ERROR] Không tìm thấy {CORPUS_ROOT}/manifest.json. Vui lòng import PubMed trước.", file=sys.stderr)
        return 1

    if not DICTIONARY_PATH.exists():
        print(f"[ERROR] Không tìm thấy từ điển {DICTIONARY_PATH}.", file=sys.stderr)
        return 1

    tmp_dir = tempfile.mkdtemp(prefix="p066-verify-person2-")
    try:
        db_path = str(Path(tmp_dir) / "verify_person2.sqlite3")
        store = MvpStore(db_path)
        try:
            results = []
            for i, pair in enumerate(PAIRS, 1):
                print(f"[{i}/5] Đang kiểm chứng: {pair['drug']} / {pair['event']} ...", end=" ", flush=True)
                res = verify_pair(store, pair, i)
                results.append(res)
                print(f"[OK] (Docs: {res['docs_count']}, Sections: {res['dossier_sections']}, Citations: {res['citations']})")

            print("\n" + "=" * 80)
            print("                      BẢNG TỔNG HỢP KẾT QUẢ NGHIỆM THU")
            print("=" * 80)
            print(f"{'CẶP THUỐC / BIẾN CỐ':<40} | {'SỐ TÀI LIỆU':<12} | {'KẾT LUẬN':<20} | {'KẾT QUẢ':<8}")
            print("-" * 80)
            for r in results:
                pair_name = f"{r['drug']} / {r['event']}"
                print(f"{pair_name:<40} | {r['docs_count']:<12} | {r['assessment']:<20} | {r['status']:<8}")
            print("=" * 80)
            print("  XÁC NHẬN: TOÀN BỘ 5/5 CẶP ỨNG VIÊN ĐÃ CHẠY HOÀN HẢO QUA GRAPH, REVIEWER & DOSSIER!")
            print("=" * 80 + "\n")
        finally:
            store.close()
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
