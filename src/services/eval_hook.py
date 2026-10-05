"""Replay trace hook cho module đánh giá (Người 4 / eval CLI).

Cung cấp hàm hook chuẩn ``replay_agent_prediction`` để cắm vào ``eval/run_evaluation.py``
thông qua đối số ``--agent-hook src.services.eval_hook:replay_agent_prediction``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from eval.baselines.keyword import BM25
from eval.contracts import ASSESSMENTS, Prediction
from eval.replay import ReplayAdapter
from src.agents.graph import run_investigation
from src.models.schemas import (
    AssessmentStatus,
    ClaimInput,
    InvestigationConfig,
)
from src.services.llm import LLMGateway
from src.services.planner import SOURCE_PRIORITY
from src.services.runner import RunContext
from src.services.store import MvpStore


def replay_agent_prediction(
    claim: dict[str, Any],
    index: BM25,
    config: dict[str, Any],
) -> Prediction:
    """Hàm hook thi hành cuộc điều tra dưới chế độ replay BM25 corpus và trả về Prediction."""
    import sys

    manifest_path: Path | None = None
    if "manifest" in config and Path(config["manifest"]).exists():
        manifest_path = Path(config["manifest"])
    elif "--manifest" in sys.argv:
        try:
            idx = sys.argv.index("--manifest")
            if idx + 1 < len(sys.argv) and Path(sys.argv[idx + 1]).exists():
                manifest_path = Path(sys.argv[idx + 1])
        except (ValueError, IndexError):
            pass

    if manifest_path is None or not manifest_path.exists():
        for cand in [
            Path("data/benchmark/corpus_manifest.json"),
            Path("data/benchmark/mvp_manifest.json"),
        ]:
            if cand.exists():
                manifest_path = cand
                break

    if manifest_path is None or not manifest_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy manifest cho replay index (manifest_hash={index.corpus.manifest_hash})."
        )

    max_steps = int(config.get("max_steps", 8))
    max_documents = int(config.get("max_documents", 50))
    cutoff = claim.get("cutoff")

    # 1. Khởi tạo adapter replay cho từng nguồn dựa vào BM25 corpus đã đóng băng
    adapters = {
        source: ReplayAdapter(source, index, manifest_path, cutoff=cutoff)
        for source in SOURCE_PRIORITY
    }

    # 2. Khởi tạo store tạm thời
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "eval_replay.sqlite3")
        store = MvpStore(db_path)
        try:
            claim_input = ClaimInput(
                claim_text=claim.get("claim_text", f"{claim['drug']} {claim['event']}"),
                drug=claim["drug"],
                event=claim["event"],
                population=claim.get("population"),
                dose=claim.get("dose"),
                route=claim.get("route"),
                time_window=claim.get("time_window"),
                config=InvestigationConfig(
                    sources=list(SOURCE_PRIORITY),
                    max_steps=max_steps,
                    max_documents=max_documents,
                ),
            )
            state, _ = store.create_investigation(claim_input)

            # 3. Tạo RunContext với adapters replay
            gateway = LLMGateway()
            ctx = RunContext(
                store=store,
                gateway=gateway,
                adapters=adapters,
            )

            # 4. Chạy graph điều tra
            state = run_investigation(state, ctx)

            # 5. Thu thập bằng chứng được truy xuất từ corpus
            visible_units = index.corpus.visible(cutoff)
            visible_ids = {unit.unit_id for unit in visible_units}
            doc_to_units: dict[str, list[str]] = {}
            for unit in visible_units:
                doc_to_units.setdefault(unit.doc_id, []).append(unit.unit_id)

            retrieved_ids: list[str] = []
            seen_ids: set[str] = set()
            for doc in state.documents:
                for uid in doc_to_units.get(doc.doc_id, []):
                    if uid in visible_ids and uid not in seen_ids:
                        seen_ids.add(uid)
                        retrieved_ids.append(uid)

            # 6. Xác định assessment_status và abstained
            status_str: str | None = None
            if state.assessment_status is not None:
                raw_status = str(state.assessment_status)
                if raw_status in ASSESSMENTS:
                    status_str = raw_status

            abstained = (
                state.assessment_status
                in (
                    AssessmentStatus.INSUFFICIENT_EVIDENCE,
                    AssessmentStatus.OUT_OF_SCOPE,
                    AssessmentStatus.REQUIRES_HUMAN_REVIEW,
                )
                or status_str is None
            )

            # 7. Trích xuất trace & usage
            events = store.list_events(state.investigation_id, limit=200)
            trace = [
                {
                    "step": event.get("id"),
                    "kind": event.get("kind"),
                    "message": event.get("message"),
                    "created_at": event.get("created_at"),
                }
                for event in events
            ]

            usage = {
                "steps": state.step_index,
                "documents": len(state.documents),
                "queries": len(state.queries),
                "llm_calls": state.budget.llm_calls,
                "input_tokens": state.budget.input_tokens,
                "output_tokens": state.budget.output_tokens,
                "model": "replay-agent",
            }

            return Prediction(
                retrieved_ids=retrieved_ids,
                assessment_status=status_str,
                abstained=abstained,
                scope_mismatches=[],
                contradictions=[],
                statements=[],
                usage=usage,
                trace=trace,
            )
        finally:
            store.close()
