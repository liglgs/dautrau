"""API-04: số đo thật thay cho hằng số 0 trong API (thời gian chạy, trạng thái bản băm).

Trước đây:

* giao diện luôn hiện ``0 ms`` vì API không trả trường thời gian nào;
* giao diện luôn gắn nhãn "chưa đối chiếu" cho bản băm vì ``real.ts`` viết cứng ``"unchecked"``,
  kể cả khi tài liệu có sẵn bản băm gốc để đối chiếu.

Bộ kiểm thử này khoá cả hai: trường phải có thật trong phản hồi, và giá trị phải đổi theo dữ liệu.
"""

from __future__ import annotations

import hashlib
import time

from src.api.investigations import _document_summary
from src.models.schemas import SourceDocument


def _document(*, metadata: dict | None = None, text: str = "nội dung nguồn") -> SourceDocument:
    return SourceDocument(
        doc_id="DOC-1",
        source="pubmed",
        source_id="PMID:1",
        title="Nghiên cứu mẫu",
        source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        text=text,
        hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        metadata=metadata or {},
    )


# ------------------------------------------------------------------ API-04b: trạng thái bản băm


def test_document_without_a_raw_hash_is_reported_as_unchecked():
    """Nguồn chỉ trả văn bản: bản băm dùng để phát hiện văn bản đổi, không chứng minh gì thêm."""
    summary = _document_summary(_document())
    assert summary["hash_status"] == "unchecked"


def test_document_with_a_raw_hash_is_reported_as_verified():
    """Có bản băm gốc ⇒ ta đối chiếu lại được từ chính dữ liệu đang có."""
    summary = _document_summary(_document(metadata={"raw_hash": "a" * 64, "parsed_hash": "b" * 64}))
    assert summary["hash_status"] == "verified"


def test_hash_status_is_never_mismatch_from_the_summary():
    """Lệch bản băm bị chặn lúc nạp tài liệu, nên API không bao giờ tự bịa ra ``mismatch``."""
    summary = _document_summary(_document(metadata={"raw_hash": "", "parsed_hash": "b" * 64}))
    assert summary["hash_status"] == "unchecked"


def test_summary_still_carries_the_hash_and_metadata():
    document = _document(metadata={"raw_hash": "a" * 64})
    summary = _document_summary(document)
    assert summary["hash"] == document.hash
    assert summary["metadata"] == document.metadata


# ------------------------------------------------------------------ API-04a: thời gian chạy


def test_state_exposes_elapsed_ms_defaulting_to_zero():
    """Hồ sơ cũ (ghi trước khi có trường) phải đọc được, không vỡ."""
    from src.models.schemas import ClaimInput, InvestigationState

    state = InvestigationState(
        investigation_id="INV-1",
        claim=ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis"),
    )
    assert state.elapsed_ms == 0
    assert "elapsed_ms" in state.model_dump()


def test_run_accumulates_real_elapsed_time(tmp_path):
    """Số phải là thời gian đo được, không phải hằng số."""
    from src.models.schemas import CheckpointKind, ClaimInput, InvestigationState
    from src.services.runner import InProcessRunner, RunContext
    from src.services.store import MvpStore

    store = MvpStore(tmp_path / "api04.sqlite3")
    state, _ = store.create_investigation(
        ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
    )

    def executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        time.sleep(0.05)
        return ctx.pause_for_review(current, checkpoint=CheckpointKind.ASSESSMENT, next_stage="build_dossier")

    InProcessRunner(store, executor=executor).run(state.investigation_id)
    saved = store.get_state(state.investigation_id)
    assert saved.elapsed_ms >= 40, saved.elapsed_ms


def test_elapsed_time_adds_up_across_resumed_runs(tmp_path):
    """Chạy tiếp không được xoá thời gian đã tiêu ở lượt trước."""
    from src.models.schemas import CheckpointKind, ClaimInput, InvestigationState, RunStatus
    from src.services.runner import InProcessRunner, RunContext
    from src.services.store import MvpStore

    store = MvpStore(tmp_path / "api04b.sqlite3")
    state, _ = store.create_investigation(
        ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
    )

    def first(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        time.sleep(0.05)
        return ctx.pause_for_review(current, checkpoint=CheckpointKind.ASSESSMENT, next_stage="build_dossier")

    InProcessRunner(store, executor=first).run(state.investigation_id)
    after_first = store.get_state(state.investigation_id).elapsed_ms

    def second(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        time.sleep(0.05)
        return current.model_copy(update={"run_status": RunStatus.COMPLETED})

    InProcessRunner(store, executor=second).run(state.investigation_id, resume=True)
    after_second = store.get_state(state.investigation_id).elapsed_ms
    assert after_second >= after_first + 40, (after_first, after_second)


def test_elapsed_time_is_zero_when_the_context_was_not_started_by_the_runner(tmp_path):
    """Node gọi trực tiếp (không qua runner) không được tự bịa thời gian chạy."""
    from src.models.schemas import ClaimInput
    from src.services.runner import RunContext
    from src.services.store import MvpStore

    store = MvpStore(tmp_path / "api04c.sqlite3")
    state, _ = store.create_investigation(
        ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
    )
    ctx = RunContext(store=store, gateway=None)  # type: ignore[arg-type]
    saved = ctx.save(state, event=("normalize", "Chuẩn hoá xong"))
    assert saved.elapsed_ms == 0
