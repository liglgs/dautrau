"""Exercise five development claims through HTTP, review checkpoints and Markdown export.

Temporary database and explicit test reviewer only. Does not approve production
investigations, label clinical gold or evaluate the held-out families.
"""

import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
runtime = ROOT / ".local-preview/python-runtime"
if runtime.is_dir():
    sys.path.insert(0, str(runtime))


async def run():
    os.environ.update({"INVESTIGATOR_TOKEN": "corpus-flow-test-investigator", "REVIEWER_TOKEN": "corpus-flow-test-reviewer",
                       # Khoá tĩnh cũ mặc định tắt (B1.7); bài chạy tại chỗ này bật tường minh.
                       "VIGILENS_ALLOW_LEGACY_TOKENS": "1",
                       "MVP_EVIDENCE_MODE": "fixture", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"})
    from src.config import get_settings
    get_settings.cache_clear()
    from src.main import app
    from src.api.mvp_runtime import configure_mvp, reset_mvp
    from src.services.runner import configure_runner
    from src.services.evidence.corpus_runtime import make_corpus_runtime
    from httpx import ASGITransport, AsyncClient
    rows = [json.loads(l) for l in (ROOT / "data/benchmark/mvp_claims.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["split"] == "development"]
    investigator = {"X-API-Token": os.environ["INVESTIGATOR_TOKEN"]}
    reviewer = {"X-API-Token": os.environ["REVIEWER_TOKEN"]}
    results = []
    @contextmanager
    def temporary_runtime():
        with tempfile.TemporaryDirectory(prefix="person3-real-source-flow-") as temp:
            try:
                yield temp
            finally:
                reset_mvp()  # close SQLite before Windows removes the directory
    async def state_at_checkpoint(client, base):
        for _ in range(300):
            response = await client.get(base, headers=investigator)
            assert response.status_code == 200, response.text
            state = response.json()
            assert state["run_status"] not in {"failed", "interrupted"}, state
            if state["checkpoint"]:
                return state
            await asyncio.sleep(0.02)
        raise AssertionError("Checkpoint timeout")
    try:
        with temporary_runtime() as temp:
            store = configure_mvp(str(Path(temp) / "flow.db"), force=True)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                for row in rows:
                    executor, gateway = make_corpus_runtime(row["family_id"])
                    configure_runner(store, executor=executor, gateway=gateway)
                    created = await client.post("/api/v1/investigations", headers=investigator, json=row["claim"])
                    assert created.status_code == 202, created.text
                    base = "/api/v1/investigations/" + created.json()["investigation_id"]
                    state = await state_at_checkpoint(client, base)
                    if state["checkpoint"] == "normalization":
                        assert row["case_category"] == "technical_ambiguity"
                        assert state["counters"]["documents"] == 0 and state["counters"]["evidence"] == 0
                        results.append({"claim_id": row["claim_id"], "checkpoint": "normalization", "requires_human_mapping": True, "pass": True})
                        continue
                    assert state["checkpoint"] == "assessment", state
                    evidence = (await client.get(base + "/evidence", headers=investigator)).json()["items"]
                    assert state["assessment_status"] == "insufficient_evidence", state
                    assert evidence
                    for item in evidence:
                        document = (await client.get(base + "/documents/" + item["doc_id"], headers=investigator)).json()["document"]
                        assert document["text"][item["locator"]["start"]:item["locator"]["end"]] == item["quote"]
                    assert (await client.get(base + "/export", headers=investigator)).status_code == 409
                    for checkpoint in ["assessment", "dossier"]:
                        decision = await client.post(base + "/reviews", headers=reviewer, json={
                            "decision_id": uuid4().hex, "action": "approve", "checkpoint": checkpoint,
                            "expected_version": state["version"],
                            "reason": "Temporary technical test of abstaining output; no clinical approval or gold label."})
                        assert decision.status_code == 200, decision.text
                        if checkpoint == "assessment":
                            continuation = await client.post(base + "/continue", headers=investigator,
                                                             json={"expected_version": state["version"] + 1})
                            assert continuation.status_code == 202, continuation.text
                            state = await state_at_checkpoint(client, base)
                            assert state["checkpoint"] == "dossier"
                            dossier = (await client.get(base + "/dossier", headers=investigator)).json()
                            assert dossier["validation"]["ok"], dossier
                            assert (await client.get(base + "/export", headers=investigator)).status_code == 409
                    exported = await client.get(base + "/export", headers=investigator)
                    assert exported.status_code == 200, exported.text
                    assert "Offline lexical quotation suggestions" in exported.text
                    results.append({"claim_id": row["claim_id"], "pass": True, "assessment": state["assessment_status"],
                        "evidence": len(evidence), "documents": state["counters"]["documents"], "two_review_checkpoints": True,
                        "markdown_export": True, "live_model": False, "clinical_approval": False})
    finally:
        reset_mvp()
        get_settings.cache_clear()
    report = {"source_mode": "real_frozen_candidates", "provider": "offline_lexical_candidates", "temporary_database": True,
              "clinical_gold": False, "heldout_evaluated": False, "results": results}
    output = ROOT / "eval/person3/corpus/development-api-flow.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Real-source development HTTP flow: {len(results)}/{len(rows)} PASS; gold remains pending.")


if __name__ == "__main__":
    asyncio.run(run())
