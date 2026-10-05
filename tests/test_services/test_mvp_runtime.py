"""M02 — Kiểm thử runtime: store bền vững, runner một-người-một-lúc, LLM gateway.

Nghiệm thu: ``python -m pytest tests/test_services/test_mvp_runtime.py -q``
"""

from __future__ import annotations

import threading

import pytest
from pydantic import BaseModel

from src.models.schemas import (
    CheckpointKind,
    ClaimInput,
    EvidenceGap,
    InvestigationState,
    RunStatus,
    SourceDocument,
    SourceSearchResult,
    SourceStatus,
)
from src.services.errors import MvpError
from src.services.llm import LLMGateway, MockProvider
from src.services.runner import InProcessRunner, RunContext
from src.services.snapshots import FileSnapshotStore
from src.services.store import MvpStore


def make_claim(text: str = "Metformin gây nhiễm toan lactic ở người suy thận.") -> ClaimInput:
    return ClaimInput(claim_text=text, drug="metformin", event="lactic acidosis", population="adults with renal impairment")


@pytest.fixture
def store(tmp_path) -> MvpStore:
    db = MvpStore(tmp_path / "mvp.db")
    yield db
    db.close()


def make_document(doc_id: str = "DOC-1", text: str = "nội dung nguồn") -> SourceDocument:
    import hashlib

    return SourceDocument(
        doc_id=doc_id,
        source="pubmed",
        source_id="PMID:1",
        title="Nghiên cứu mẫu",
        source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        text=text,
        hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


# --------------------------------------------------------------------------------------
# Store: tạo, idempotency, version, event
# --------------------------------------------------------------------------------------


def test_create_is_idempotent_by_key(store):
    first, created = store.create_investigation(make_claim(), idempotency_key="key-1")
    assert created is True
    second, created_again = store.create_investigation(make_claim(), idempotency_key="key-1")
    assert created_again is False
    assert second.investigation_id == first.investigation_id

    with pytest.raises(MvpError) as excinfo:
        store.create_investigation(make_claim("Claim khác hoàn toàn."), idempotency_key="key-1")
    assert excinfo.value.code == "idempotency_conflict"
    assert excinfo.value.status == 409


def test_events_timeline_supports_after_id(store):
    state, _ = store.create_investigation(make_claim())
    store.append_event(state.investigation_id, "step", "bước 1")
    store.append_event(state.investigation_id, "step", "bước 2")
    events = store.list_events(state.investigation_id)
    assert [event["message"] for event in events] == ["Tạo cuộc điều tra mới.", "bước 1", "bước 2"]
    tail = store.list_events(state.investigation_id, after_id=events[0]["id"])
    assert [event["message"] for event in tail] == ["bước 1", "bước 2"]


def test_stale_version_cannot_overwrite(store):
    state, _ = store.create_investigation(make_claim())
    updated = store.save_state(state.model_copy(update={"step_index": 1}), expected_version=state.version)
    assert updated.version == state.version + 1

    with pytest.raises(MvpError) as excinfo:
        store.save_state(state.model_copy(update={"step_index": 99}), expected_version=state.version)
    assert excinfo.value.code == "version_conflict"

    persisted = store.get_state(state.investigation_id)
    assert persisted.step_index == 1
    assert persisted.version == state.version + 1


def test_documents_are_immutable(store):
    state, _ = store.create_investigation(make_claim())
    assert store.save_document(state.investigation_id, make_document()) is True
    assert store.save_document(state.investigation_id, make_document()) is False
    with pytest.raises(MvpError) as excinfo:
        store.save_document(state.investigation_id, make_document(text="nội dung khác"))
    assert excinfo.value.code == "invalid_state"
    assert store.get_document(state.investigation_id, "DOC-1").text == "nội dung nguồn"


def test_state_reopens_after_restart(tmp_path):
    db_path = tmp_path / "restart.db"
    first = MvpStore(db_path)
    state, _ = first.create_investigation(make_claim())
    state = state.model_copy(update={"step_index": 3, "queries": ["pubmed:metformin lactic acidosis"]})
    state.budget.steps_used = 3
    state.budget.documents_used = 12
    saved = first.save_state(state, expected_version=state.version)
    first.close()

    reopened = MvpStore(db_path)
    restored = reopened.get_state(state.investigation_id)
    assert restored.step_index == 3
    assert restored.budget.steps_used == 3
    assert restored.budget.documents_used == 12
    assert restored.queries == ["pubmed:metformin lactic acidosis"]
    assert restored.version == saved.version
    assert restored.claim.drug == "metformin"
    reopened.close()


# --------------------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------------------


def test_only_one_runner_at_a_time(store):
    state, _ = store.create_investigation(make_claim())
    started = threading.Event()
    release = threading.Event()

    def blocking_executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        started.set()
        release.wait(timeout=5)
        return ctx.save(current.model_copy(update={"step_index": 1}), event=("step", "xong bước 1"))

    runner = InProcessRunner(store, executor=blocking_executor)
    runner.start_background(state.investigation_id)
    assert started.wait(timeout=5)

    other, _ = store.create_investigation(make_claim("Claim thứ hai."))
    with pytest.raises(MvpError) as excinfo:
        runner.run(other.investigation_id)
    assert excinfo.value.code == "runner_busy"
    assert excinfo.value.status == 429
    assert excinfo.value.details["current_investigation_id"] == state.investigation_id

    release.set()
    deadline = threading.Event()
    deadline.wait(timeout=0.3)
    assert runner.is_busy is False
    assert store.get_state(state.investigation_id).step_index == 1


def test_next_stage_saved_before_review_wait(store):
    state, _ = store.create_investigation(make_claim())

    def pausing_executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        current.budget.steps_used = 2
        current = ctx.save(current, event=("step", "hai bước đầu"))
        return ctx.pause_for_review(
            current,
            checkpoint=CheckpointKind.ASSESSMENT,
            next_stage="build_dossier",
            message="Chờ reviewer duyệt kết luận.",
        )

    runner = InProcessRunner(store, executor=pausing_executor)
    result = runner.run(state.investigation_id)
    assert result.run_status is RunStatus.WAITING_FOR_REVIEW
    assert result.checkpoint is CheckpointKind.ASSESSMENT
    assert result.next_stage == "build_dossier"
    assert result.budget.steps_used == 2

    persisted = store.get_state(state.investigation_id)
    assert persisted.next_stage == "build_dossier"
    assert persisted.budget.steps_used == 2


def test_resume_after_review_keeps_counters(store):
    state, _ = store.create_investigation(make_claim())
    state = state.model_copy(update={"run_status": RunStatus.WAITING_FOR_REVIEW, "next_stage": "build_dossier"})
    state.budget.steps_used = 4
    state.budget.llm_calls = 6
    state = store.save_state(state, expected_version=state.version)

    def resume_executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        assert current.budget.steps_used == 4
        assert current.budget.llm_calls == 6
        return ctx.save(current.model_copy(update={"run_status": RunStatus.COMPLETED}), event=("completed", "xong"))

    runner = InProcessRunner(store, executor=resume_executor)
    result = runner.run(state.investigation_id, resume=True)
    assert result.run_status is RunStatus.COMPLETED
    assert result.budget.steps_used == 4
    assert result.budget.llm_calls == 6


def test_recover_marks_running_as_interrupted(store):
    state, _ = store.create_investigation(make_claim())
    state = state.model_copy(
        update={"run_status": RunStatus.RUNNING, "checkpoint": CheckpointKind.ASSESSMENT, "step_index": 5}
    )
    state.budget.steps_used = 5
    state.budget.documents_used = 21
    state.budget.llm_calls = 7
    store.save_state(state, expected_version=state.version)

    runner = InProcessRunner(store)
    recovered = runner.recover_interrupted()
    assert recovered == [state.investigation_id]

    restored = store.get_state(state.investigation_id)
    assert restored.run_status is RunStatus.INTERRUPTED
    assert restored.checkpoint is CheckpointKind.ASSESSMENT
    assert restored.step_index == 5
    assert restored.budget.steps_used == 5
    assert restored.budget.documents_used == 21
    assert restored.budget.llm_calls == 7
    assert store.list_events(state.investigation_id)[-1]["kind"] == "interrupted"


def test_run_marks_failed_when_executor_raises(store):
    state, _ = store.create_investigation(make_claim())

    def exploding_executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        raise RuntimeError("lỗi giả lập")

    runner = InProcessRunner(store, executor=exploding_executor)
    with pytest.raises(RuntimeError):
        runner.run(state.investigation_id)
    assert store.get_state(state.investigation_id).run_status is RunStatus.FAILED
    assert runner.is_busy is False


def test_interrupted_run_can_be_resumed(store):
    state, _ = store.create_investigation(make_claim())
    state = state.model_copy(update={"run_status": RunStatus.INTERRUPTED, "step_index": 2})
    state.budget.steps_used = 2
    store.save_state(state, expected_version=state.version)

    seen: dict[str, int] = {}

    def executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        seen["steps"] = current.budget.steps_used
        return ctx.save(current.model_copy(update={"run_status": RunStatus.COMPLETED}))

    runner = InProcessRunner(store, executor=executor)
    result = runner.run(state.investigation_id)
    assert seen["steps"] == 2
    assert result.run_status is RunStatus.COMPLETED


# --------------------------------------------------------------------------------------
# LLM gateway
# --------------------------------------------------------------------------------------


class _Payload(BaseModel):
    answer: str
    confidence: float = 0.5


def test_gateway_uses_mock_provider_and_records_usage(store):
    provider = MockProvider({"normalize_claim": {"answer": "ok", "confidence": 0.8}})
    gateway = LLMGateway(provider)
    state, _ = store.create_investigation(make_claim())

    result = gateway.complete_model("normalize_claim", "chuẩn hoá claim", _Payload, budget=state.budget)
    assert result.answer == "ok"
    assert gateway.ledger.llm_calls == 1
    assert gateway.ledger.input_tokens > 0
    assert gateway.ledger.output_tokens > 0
    assert state.budget.llm_calls == 1
    assert state.budget.input_tokens == gateway.ledger.input_tokens


def test_gateway_repairs_invalid_output_once():
    provider = MockProvider({"plan": "đây không phải JSON", "plan:repair": {"answer": "đã sửa"}})
    gateway = LLMGateway(provider)
    result = gateway.complete_model("plan", "chọn hành động", _Payload)
    assert result.answer == "đã sửa"
    assert gateway.ledger.llm_calls == 2
    assert gateway.ledger.repairs == 1
    assert [call["task"] for call in provider.calls] == ["plan", "plan:repair"]


def test_gateway_fails_after_single_repair():
    provider = MockProvider({"plan": "vẫn không phải JSON", "plan:repair": "vẫn sai"})
    gateway = LLMGateway(provider)
    with pytest.raises(MvpError) as excinfo:
        gateway.complete_model("plan", "chọn hành động", _Payload)
    assert excinfo.value.code == "llm_format_error"
    assert gateway.ledger.llm_calls == 2
    assert len(provider.calls) == 2


def test_gateway_accepts_fenced_json():
    provider = MockProvider({"plan": '```json\n{"answer": "trong fence"}\n```'})
    gateway = LLMGateway(provider)
    assert gateway.complete_model("plan", "x", _Payload).answer == "trong fence"


def test_gateway_reserves_last_calls_for_dossier(store):
    provider = MockProvider({"plan": {"answer": "ok"}, "build_dossier": {"answer": "hồ sơ"}})
    gateway = LLMGateway(provider)
    state, _ = store.create_investigation(make_claim())
    state.budget.max_llm_calls = 4
    state.budget.llm_calls = 2  # còn 2 lượt, nhưng 2 lượt cuối được giữ dự phòng

    with pytest.raises(MvpError) as excinfo:
        gateway.complete_model("plan", "x", _Payload, budget=state.budget)
    assert excinfo.value.code == "budget_exhausted"
    assert provider.calls == []

    # Bước hồ sơ được phép dùng phần dự phòng.
    result = gateway.complete_model("build_dossier", "x", _Payload, budget=state.budget, reserve=False)
    assert result.answer == "hồ sơ"
    assert state.budget.llm_calls == 3


def test_gateway_blocks_when_calls_exhausted(store):
    provider = MockProvider({"plan": {"answer": "ok"}})
    gateway = LLMGateway(provider)
    state, _ = store.create_investigation(make_claim())
    state.budget.max_llm_calls = 2
    state.budget.llm_calls = 2
    with pytest.raises(MvpError) as excinfo:
        gateway.complete_model("plan", "x", _Payload, budget=state.budget, reserve=False)
    assert excinfo.value.code == "budget_exhausted"
    assert provider.calls == []


def test_gateway_offline_never_touches_network(store):
    """Test offline: provider mock không có kịch bản thì báo lỗi rõ, không gọi mạng."""
    gateway = LLMGateway(MockProvider({}))
    with pytest.raises(AssertionError):
        gateway.complete_model("unknown_task", "x", _Payload)


# --------------------------------------------------------------------------------------
# Snapshot store
# --------------------------------------------------------------------------------------


def test_snapshot_round_trip_is_hash_addressed(tmp_path):
    store = FileSnapshotStore(tmp_path / "snapshots")
    document = make_document()
    path = store.save(document)
    assert document.hash in path
    assert store.save(document) == path  # idempotent theo hash
    assert store.load(path) == document


def test_snapshot_does_not_cache_errors_as_empty_results(tmp_path):
    store = FileSnapshotStore(tmp_path / "snapshots")
    failed = SourceSearchResult(
        source="dailymed",
        query="metformin",
        fingerprint="dailymed:metformin",
        status=SourceStatus.ERROR,
        error="timeout after 10s",
    )
    assert store.save_search_result(failed) == []

    empty = SourceSearchResult(
        source="pubmed", query="metformin", fingerprint="pubmed:metformin", status=SourceStatus.EMPTY
    )
    assert store.save_search_result(empty) == []

    ok = SourceSearchResult(
        source="pubmed",
        query="metformin",
        fingerprint="pubmed:metformin",
        status=SourceStatus.OK,
        documents=[make_document()],
    )
    assert len(store.save_search_result(ok)) == 1


def test_runner_records_gap_events_in_timeline(store):
    state, _ = store.create_investigation(make_claim())

    def executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        current = current.model_copy(
            update={"gaps": [EvidenceGap(gap_id="GAP-1", kind="missing_source", description="Thiếu nhãn DailyMed")]}
        )
        current = ctx.save(current, event=("gap", "Phát hiện khoảng trống bằng chứng"))
        return ctx.pause_for_review(current, checkpoint=CheckpointKind.ASSESSMENT, next_stage="build_dossier")

    runner = InProcessRunner(store, executor=executor)
    runner.run(state.investigation_id)
    kinds = [event["kind"] for event in store.list_events(state.investigation_id)]
    assert "gap" in kinds
    assert kinds[-1] == "checkpoint"
    assert store.get_state(state.investigation_id).gaps[0].gap_id == "GAP-1"


def test_shared_document_is_readable_from_both_investigations(store):
    """Cùng một tài liệu được hai cuộc điều tra truy xuất: cả hai phải đọc được."""
    first, _ = store.create_investigation(make_claim())
    second, _ = store.create_investigation(make_claim("metformin gây toan lactic ở người suy thận."))
    assert first.investigation_id != second.investigation_id

    document = make_document()
    assert store.save_document(first.investigation_id, document) is True
    assert store.save_document(second.investigation_id, document) is True  # liên kết mới

    assert store.get_document(second.investigation_id, "DOC-1").doc_id == "DOC-1"
    assert [item.doc_id for item in store.list_documents(second.investigation_id)] == ["DOC-1"]
    assert store.get_document(first.investigation_id, "DOC-1").doc_id == "DOC-1"


def test_same_doc_id_with_different_content_is_rejected(store):
    state, _ = store.create_investigation(make_claim())
    assert store.save_document(state.investigation_id, make_document()) is True
    with pytest.raises(MvpError) as excinfo:
        store.save_document(state.investigation_id, make_document(doc_id="DOC-1", text="bài khác"))
    assert excinfo.value.code == "invalid_state"
    # Cùng doc_id nhưng khác (source, source_id, version): cũng phải bị chặn, không lỗi 500.
    other = make_document(doc_id="DOC-1", text="bài khác").model_copy(update={"source_id": "PMID:2"})
    with pytest.raises(MvpError) as taken:
        store.save_document(state.investigation_id, other)
    assert taken.value.code == "invalid_state"
    assert store.get_document(state.investigation_id, "DOC-1").text == "nội dung nguồn"


# --------------------------------------------------------------------------------------
# P16 — trần ngân sách và đặt trước đồng thời
# --------------------------------------------------------------------------------------


def test_budget_boundary_20_steps_100_documents(tmp_path):
    """Đúng trần cứng thì hợp lệ, vượt một đơn vị thì bị chặn; lượt chạy không vượt trần."""
    from src.models.schemas import HARD_MAX_DOCUMENTS, HARD_MAX_STEPS, validate_budget_ceiling

    validate_budget_ceiling(HARD_MAX_STEPS, HARD_MAX_DOCUMENTS)
    with pytest.raises(ValueError):
        validate_budget_ceiling(HARD_MAX_STEPS + 1, HARD_MAX_DOCUMENTS)
    with pytest.raises(ValueError):
        validate_budget_ceiling(HARD_MAX_STEPS, HARD_MAX_DOCUMENTS + 1)

    store = MvpStore(tmp_path / "boundary.db")
    claim = ClaimInput(claim_text="không rõ gây không rõ", drug="không rõ", event="không rõ")
    state, _ = store.create_investigation(claim)
    state.budget.max_steps = HARD_MAX_STEPS
    state.budget.max_documents = HARD_MAX_DOCUMENTS
    store.save_state(state, expected_version=state.version)

    final = InProcessRunner(store).run(state.investigation_id)

    assert final.budget.steps_used <= HARD_MAX_STEPS
    assert final.budget.documents_used <= HARD_MAX_DOCUMENTS
    assert final.budget.source_requests <= final.budget.max_source_requests


def test_concurrent_reservation_cannot_overspend(store):
    """Hai lần đặt trước trên cùng một state cũ: chỉ một thành công, tổng không vượt trần."""
    from src.services.budget import BudgetController

    state, _ = store.create_investigation(make_claim())
    state.budget.max_steps = 2
    store.save_state(state, expected_version=state.version)
    controller = BudgetController(store)

    first_copy = store.get_state(state.investigation_id)
    second_copy = store.get_state(state.investigation_id)  # cùng version

    saved, reservation = controller.reserve(first_copy, "op-A")
    assert reservation.granted

    with pytest.raises(MvpError) as excinfo:
        controller.reserve(second_copy, "op-B")
    assert excinfo.value.code == "version_conflict"

    current = store.get_state(state.investigation_id)
    assert sum(current.budget.reservations.values()) <= current.budget.max_steps

    # Cùng một operation_key gọi lại là idempotent, không cộng thêm lượt đặt trước.
    again, repeated = controller.reserve(saved, "op-A")
    assert repeated.granted and repeated.reason
    assert again.budget.reservations == {"op-A": 1}

    # Khi đã dùng hết trần bước thì lần đặt trước kế tiếp bị từ chối (không vượt ngân sách).
    spent = controller.commit(store.get_state(state.investigation_id), "op-A")
    spent.budget.steps_used = spent.budget.max_steps
    store.save_state(spent, expected_version=spent.version)
    _, refused = controller.reserve(store.get_state(state.investigation_id), "op-C")
    assert not refused.granted


def test_background_run_that_loses_the_lock_emits_a_queued_event(store):
    """Hai cuộc điều tra cùng lúc: cuộc thua khoá giữ nguyên ``queued`` và ghi sự kiện, không im lặng."""
    running, _ = store.create_investigation(make_claim())
    waiting, _ = store.create_investigation(make_claim("Ibuprofen gây xuất huyết tiêu hoá ở người lớn."))

    runner = InProcessRunner(store)
    runner.acquire(running.investigation_id)  # giả lập cuộc khác đang giữ khoá
    try:
        runner._run_guarded(waiting.investigation_id, False)
    finally:
        runner.release()

    events = store.list_events(waiting.investigation_id)
    assert events[-1]["kind"] == "queued"
    assert "bận" in events[-1]["message"]
    assert store.get_state(waiting.investigation_id).run_status is RunStatus.QUEUED
