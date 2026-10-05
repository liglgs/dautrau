"""Kiểm thử tính năng Cancel API và Runtime Config (Người 2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.agents.graph import run_investigation
from src.models.schemas import (
    HARD_MAX_DOCUMENTS,
    HARD_MAX_STEPS,
    ClaimInput,
    InvestigationConfig,
    RunStatus,
)
from src.services.errors import MvpError
from src.services.runner import InProcessRunner
from src.services.store import MvpStore


@pytest.fixture
def store(tmp_path):
    mvp_store = MvpStore(str(tmp_path / "cancel_config.db"))
    yield mvp_store
    mvp_store.close()


@pytest.fixture
def runner(store):
    return InProcessRunner(store=store, executor=run_investigation)


def test_runtime_config_validation():
    """Kiểm tra validation của InvestigationConfig."""
    # Nguồn hợp lệ
    cfg = InvestigationConfig(sources=["pubmed", "dailymed"], max_steps=5, max_documents=20)
    assert cfg.sources == ["pubmed", "dailymed"]
    assert cfg.max_steps == 5
    assert cfg.max_documents == 20

    # Nguồn rỗng -> lỗi
    with pytest.raises(ValidationError):
        InvestigationConfig(sources=[])

    # Nguồn lạ -> lỗi
    with pytest.raises(ValidationError):
        InvestigationConfig(sources=["google_search"])

    # Vượt trần cứng -> lỗi
    with pytest.raises(ValidationError):
        InvestigationConfig(max_steps=HARD_MAX_STEPS + 1)

    with pytest.raises(ValidationError):
        InvestigationConfig(max_documents=HARD_MAX_DOCUMENTS + 1)


def test_cancel_queued_investigation(store, runner):
    """Hủy cuộc điều tra ở trạng thái QUEUED."""
    claim = ClaimInput(
        claim_text="metformin causes lactic acidosis",
        drug="metformin",
        event="lactic acidosis",
    )
    state, created = store.create_investigation(claim)
    assert created
    assert state.run_status == RunStatus.QUEUED

    cancelled = runner.cancel(state.investigation_id)
    assert cancelled.run_status == RunStatus.CANCELLED

    # Kiểm tra store đã lưu và ghi event
    reloaded = store.get_state(state.investigation_id)
    assert reloaded.run_status == RunStatus.CANCELLED
    events = store.list_events(state.investigation_id)
    assert any(e["kind"] == "cancelled" for e in events)


def test_cannot_cancel_terminal_investigation(store, runner):
    """Không thể hủy cuộc điều tra đã hoàn tất hoặc đã bị hủy."""
    claim = ClaimInput(
        claim_text="metformin causes lactic acidosis",
        drug="metformin",
        event="lactic acidosis",
    )
    state, _ = store.create_investigation(claim)
    runner.cancel(state.investigation_id)

    # Thử hủy lại lần nữa
    with pytest.raises(MvpError) as exc_info:
        runner.cancel(state.investigation_id)
    assert "không thể hủy" in str(exc_info.value.message)


def test_runtime_config_sources_filtering(store, runner):
    """Cấu hình runtime chỉ tìm kiếm nguồn DailyMed."""
    claim = ClaimInput(
        claim_text="metformin causes lactic acidosis",
        drug="metformin",
        event="lactic acidosis",
        config=InvestigationConfig(sources=["dailymed"], max_steps=4, max_documents=10),
    )
    state, _ = store.create_investigation(claim)
    assert state.config.sources == ["dailymed"]
    assert state.budget.max_steps == 4
    assert state.budget.max_documents == 10

    # Chạy runner
    result = runner.run(state.investigation_id)

    # Xác nhận các nguồn đã tìm kiếm chỉ nằm trong tập được cho phép
    for searched in result.searched_sources:
        assert searched == "dailymed"

    # Xác nhận checklist không sinh gap thiếu nguồn ngoài dailymed
    for gap in result.gaps:
        if gap.gap_id.startswith("GAP-SRC-"):
            assert gap.field == "dailymed"


def test_cancel_running_investigation_releases_lock(store):
    """Hủy cuộc điều tra đang chạy phải ngắt luồng và giải phóng lock runner."""
    executed_nodes = []

    def mock_executor(state, ctx):
        executed_nodes.append("node1")
        # Giả lập runner nhận lệnh cancel giữa chừng
        ctx.runner._cancelled_ids.add(state.investigation_id)
        # Bước lưu tiếp theo sẽ phát hiện hủy và ném ngoại lệ
        return ctx.save(state, event=("step", "Testing cancel"))

    runner = InProcessRunner(store=store, executor=mock_executor)

    claim = ClaimInput(
        claim_text="metformin causes lactic acidosis",
        drug="metformin",
        event="lactic acidosis",
    )
    state, _ = store.create_investigation(claim)

    result = runner.run(state.investigation_id)
    assert result.run_status == RunStatus.CANCELLED
    assert not runner.is_busy
    assert runner.current is None


def test_cancel_during_state_save_preserves_cancelled_status(store, monkeypatch):
    original_save = store.save_state

    def cancel_before_save(state, **kwargs):
        if kwargs.get("event", (None,))[0] == "step":
            runner.cancel(state.investigation_id)
        return original_save(state, **kwargs)

    monkeypatch.setattr(store, "save_state", cancel_before_save)
    runner = InProcessRunner(store, executor=lambda state, ctx: ctx.save(state, event=("step", "Saving node")))
    state, _ = store.create_investigation(ClaimInput(claim_text="Drug causes event", drug="Drug", event="event"))
    result = runner.run(state.investigation_id)
    assert result.run_status is RunStatus.CANCELLED
    assert store.get_state(state.investigation_id).run_status is RunStatus.CANCELLED
    assert not any(event["kind"] == "failed" for event in store.list_events(state.investigation_id))
    assert not runner.is_busy
    assert not runner.is_cancelled(state.investigation_id)
