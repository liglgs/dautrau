"""Kiểm thử Replay Trace Hook và Trace API (Người 2)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from eval.baselines.keyword import BM25
from eval.contracts import Prediction
from eval.corpus import Corpus
from scripts.seed_demo import build
from src.api.mvp_runtime import configure_mvp, reset_mvp
from src.config import get_settings
from src.main import app
from src.services.eval_hook import replay_agent_prediction


@pytest_asyncio.fixture
async def api_client(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTIGATOR_TOKEN", "test-inv-token")
    monkeypatch.setenv("REVIEWER_TOKEN", "test-rev-token")
    get_settings.cache_clear()
    reset_mvp()
    configure_mvp(str(tmp_path / "trace_test.db"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    reset_mvp()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_investigation_trace_endpoint(api_client: AsyncClient):
    """Kiểm tra API GET /api/v1/investigations/{id}/trace trả về đúng metadata và sự kiện."""
    # Tạo một investigation
    create_res = await api_client.post(
        "/api/v1/investigations",
        json={"claim_text": "aspirin causes ulcer", "drug": "aspirin", "event": "ulcer"},
        headers={"X-API-Token": "test-inv-token"},
    )
    assert create_res.status_code == 202
    inv_id = create_res.json()["investigation_id"]

    # Gọi endpoint trace
    trace_res = await api_client.get(
        f"/api/v1/investigations/{inv_id}/trace",
        headers={"X-API-Token": "test-inv-token"},
    )
    assert trace_res.status_code == 200
    data = trace_res.json()
    assert data["investigation_id"] == inv_id
    assert "budget" in data
    assert "counters" in data
    assert "traces" in data
    assert isinstance(data["traces"], list)


def test_eval_hook_replay_agent_prediction(tmp_path):
    """Kiểm tra hàm replay_agent_prediction khớp hợp đồng Prediction cho module đánh giá."""
    build(tmp_path)
    manifest_path = tmp_path / "corpus_manifest.json"
    corpus = Corpus.load(manifest_path)
    index = BM25(corpus)

    claim = {
        "claim_id": "test-claim-1",
        "claim_text": "TestDrugB causes TestEventB",
        "drug": "TestDrugB",
        "event": "TestEventB",
    }
    config = {
        "manifest": str(manifest_path),
        "max_steps": 4,
        "max_documents": 10,
    }

    prediction = replay_agent_prediction(claim=claim, index=index, config=config)
    assert isinstance(prediction, Prediction)
    assert prediction.usage["model"] == "replay-agent"
    assert isinstance(prediction.retrieved_ids, list)
    assert isinstance(prediction.trace, list)

    # Đảm bảo Prediction.parse từ eval/contracts.py parse thành công mà không có lỗi
    allowed_ids = {unit.unit_id for unit in corpus.units}
    parsed = Prediction.parse(prediction.to_dict(), allowed_ids=allowed_ids)
    assert parsed.retrieved_ids == prediction.retrieved_ids
