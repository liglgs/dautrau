"""Demo D4 (M10): chạy kịch bản replanning và in timeline cho buổi demo.

Kịch bản: claim dùng tên biệt dược ``Micardis`` ⇒ nguồn đầu không có kết quả ⇒ agent đổi query
sang hoạt chất ``telmisartan`` rồi mở rộng nguồn ⇒ thu được bằng chứng và dừng ở checkpoint
assessment để reviewer duyệt.

    python scripts/demo_d4_replanning.py            # in timeline + kiểm tra kỳ vọng của fixture
    python scripts/demo_d4_replanning.py --keep-db  # giữ file DB để xem lại bằng API

Script chỉ dùng fixture M01 và store SQLite tạm; không gọi mạng, không gọi LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents.graph import run_investigation  # noqa: E402
from src.agents.mock_runtime import FixtureAdapter, FixtureExtractor, FixtureNormalizer  # noqa: E402
from src.models.schemas import ClaimInput  # noqa: E402
from src.services.runner import InProcessRunner  # noqa: E402
from src.services.store import MvpStore  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "mvp" / "replanning_fixture.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy kịch bản demo D4 (replanning).")
    parser.add_argument("--keep-db", action="store_true", help="giữ file SQLite để xem lại")
    parser.add_argument("--db", default="", help="đường dẫn DB (mặc định: thư mục tạm)")
    args = parser.parse_args()

    scenario = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = scenario.get("expected", {})

    tmpdir = None
    if args.db:
        db_path = args.db
    elif args.keep_db:
        db_path = str(ROOT / "data" / "demo-d4.sqlite3")
    else:
        tmpdir = tempfile.TemporaryDirectory()
        db_path = str(Path(tmpdir.name) / "demo-d4.sqlite3")

    store = MvpStore(db_path)
    runner = InProcessRunner(store)
    claim = ClaimInput.model_validate(scenario["claim"])
    state, _ = store.create_investigation(claim)

    print(f"Claim: {claim.claim_text!r} (drug={claim.drug!r}, event={claim.event!r})")
    print(f"DB: {db_path}\n")

    ctx = runner.context()
    ctx.scenario = scenario
    ctx.adapters = {source: FixtureAdapter(source, scenario) for source in ("pubmed", "dailymed", "faers")}
    ctx.extractor = FixtureExtractor(scenario)
    ctx.normalizer = FixtureNormalizer(scenario)

    result = run_investigation(state, ctx)

    print("TIMELINE")
    print("-" * 88)
    for row in store.list_events(state.investigation_id):
        payload = json.loads(row["payload_json"]) if row.get("payload_json") else {}
        suffix = f" · {payload}" if payload else ""
        print(f"  [{row['id']:>3}] {row['kind']:<20} {row['message']}{suffix}")

    print("\nTRUY VẤN ĐÃ CHẠY")
    for fingerprint in result.queries:
        print(f"  - {fingerprint}")

    print("\nBẰNG CHỨNG")
    for item in result.active_evidence():
        print(f"  - {item.evidence_id} · {item.source} · {item.doc_id} · stance={item.stance}")
        print(f"      trích dẫn: {item.quote[:90]}…")

    print("\nKẾT QUẢ")
    print(f"  run_status={result.run_status} · checkpoint={result.checkpoint} · next_stage={result.next_stage}")
    print(f"  assessment_status={result.assessment_status} · stop_reason={result.stop_reason}")
    print(f"  ngân sách: bước={result.budget.steps_used}/{result.budget.max_steps} · "
          f"tài liệu={result.budget.documents_used}/{result.budget.max_documents} · "
          f"nguồn={result.budget.source_requests}/{result.budget.max_source_requests}")
    print(f"  khoảng trống: {[gap.gap_id for gap in result.gaps]}")

    failures: list[str] = []
    if expected:
        if str(result.assessment_status) != expected.get("assessment_status"):
            failures.append(f"assessment_status={result.assessment_status} (kỳ vọng {expected.get('assessment_status')})")
        if str(result.stop_reason) != expected.get("stop_reason"):
            failures.append(f"stop_reason={result.stop_reason} (kỳ vọng {expected.get('stop_reason')})")
        if str(result.checkpoint) != expected.get("checkpoint"):
            failures.append(f"checkpoint={result.checkpoint} (kỳ vọng {expected.get('checkpoint')})")
        if str(result.run_status) != expected.get("run_status_at_stop"):
            failures.append(f"run_status={result.run_status} (kỳ vọng {expected.get('run_status_at_stop')})")

    retrieves = [row["message"] for row in store.list_events(state.investigation_id) if row["kind"] == "retrieve"]
    if len(retrieves) < 2:
        failures.append("chưa thấy bước đổi truy vấn/nguồn (cần ≥2 lượt retrieve)")

    if failures:
        print("\nKẾT QUẢ DEMO: KHÔNG ĐẠT")
        for item in failures:
            print(f"  ✗ {item}")
        return 1

    print("\nKẾT QUẢ DEMO: ĐẠT — đổi query rồi mở rộng nguồn, có bằng chứng, dừng chờ reviewer.")
    if tmpdir is not None:
        store.close()
        tmpdir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
