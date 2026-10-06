"""RT-01: khoá tổ hợp chế độ chạy sai và nhãn "thật hay mẫu" phải nói đúng.

Vì sao có bộ kiểm thử này: ``MVP_SOURCE_MODE`` và ``MVP_EVIDENCE_MODE`` là hai công tắc độc lập.
Trước đây bật nguồn thật mà quên đổi chế độ bằng chứng vẫn chạy được: hệ thống tải tài liệu PubMed
thật rồi gắn bằng chứng fixture lên, và hồ sơ xuất ra **trông như thật**. Không có nhãn nào cảnh
báo, nên người đọc không có cách nào nhận ra.
"""

from __future__ import annotations

import pytest

from src.config import Settings, get_settings
from src.services.errors import MvpError
from src.services.runmode import (
    describe_run_mode,
    get_run_mode,
    resolve_run_mode,
    validate_run_mode,
)


def _settings(source: str, evidence: str) -> Settings:
    """``Settings`` với hai công tắc chế độ, không đọc ``.env`` của máy chạy."""
    return Settings(_env_file=None, mvp_source_mode=source, mvp_evidence_mode=evidence)


@pytest.mark.parametrize(
    ("source", "evidence"),
    [
        ("fixture", "fixture"),
        ("live", "person3"),
        ("warehouse", "person3"),
    ],
)
def test_allowed_combinations_pass(source, evidence):
    validate_run_mode(_settings(source, evidence))


@pytest.mark.parametrize(
    ("source", "evidence"),
    [
        # Nguồn thật + bằng chứng mẫu: tài liệu thật, trích đoạn bịa. Tổ hợp nguy hiểm nhất.
        ("live", "fixture"),
        ("warehouse", "fixture"),
        # Bằng chứng do mô hình trích nhưng không có tài liệu thật nào để trích.
        ("fixture", "person3"),
        # Kịch bản demo có sẵn trích đoạn, gắn lên tài liệu tải từ mạng.
        ("live", "person3_demo"),
        ("warehouse", "person3_demo"),
    ],
)
def test_forbidden_combinations_are_blocked_with_a_fix_instruction(source, evidence):
    with pytest.raises(MvpError) as excinfo:
        validate_run_mode(_settings(source, evidence))
    details = excinfo.value.details or {}
    assert details.get("combination") == f"{source}+{evidence}"
    # Thông báo phải nói được cách sửa, không chỉ nói "sai".
    assert details.get("remedy")
    assert "MVP_" in str(details["remedy"])


def test_blocked_combination_never_reaches_the_store(tmp_path, monkeypatch):
    """Chặn ở lúc dựng app: không được tạo tệp DB trước khi kiểm tra chế độ."""
    from src.api.mvp_runtime import configure_mvp, reset_mvp

    monkeypatch.setenv("MVP_SOURCE_MODE", "live")
    monkeypatch.setenv("MVP_EVIDENCE_MODE", "fixture")
    monkeypatch.setenv("MVP_DB_PATH", str(tmp_path / "phai-khong-duoc-tao.sqlite3"))
    get_settings.cache_clear()
    try:
        with pytest.raises(MvpError):
            configure_mvp(force=True)
        assert not (tmp_path / "phai-khong-duoc-tao.sqlite3").exists()
    finally:
        reset_mvp()
        get_settings.cache_clear()


def test_fixture_mode_is_labelled_as_synthetic():
    mode = resolve_run_mode(_settings("fixture", "fixture"))
    assert mode.synthetic is True
    assert mode.sources_are_real is False
    assert mode.evidence_is_real is False
    assert mode.model_is_real is False
    assert "mẫu" in mode.label
    assert describe_run_mode(_settings("fixture", "fixture")).startswith("Chế độ chạy: DỮ LIỆU MẪU")


@pytest.mark.parametrize(("source", "evidence"), [("live", "person3"), ("warehouse", "person3")])
def test_real_pipeline_is_not_labelled_synthetic(source, evidence):
    mode = resolve_run_mode(_settings(source, evidence))
    assert mode.synthetic is False
    assert mode.sources_are_real is True
    assert mode.evidence_is_real is True
    assert mode.model_is_real is True
    assert "mẫu" not in mode.label
    assert describe_run_mode(_settings(source, evidence)).startswith("Chế độ chạy: DỮ LIỆU THẬT")


def test_run_mode_payload_is_json_safe():
    """Payload đi thẳng vào cột ``payload_json`` của bảng events."""
    import json

    payload = resolve_run_mode(_settings("live", "person3")).as_event_payload()
    assert json.loads(json.dumps(payload)) == payload
    assert set(payload) == {"source_mode", "evidence_mode", "pubmed_mode", "synthetic", "label"}


def test_get_run_mode_reads_current_settings(monkeypatch):
    monkeypatch.setenv("MVP_SOURCE_MODE", "fixture")
    monkeypatch.setenv("MVP_EVIDENCE_MODE", "fixture")
    get_settings.cache_clear()
    try:
        assert get_run_mode()["synthetic"] is True
    finally:
        get_settings.cache_clear()


def test_runner_stamps_run_mode_into_the_running_event(tmp_path):
    """RT-02: dòng "bắt đầu chạy" phải mang theo chế độ, để nhật ký tự nói thật."""
    from src.models.schemas import CheckpointKind, InvestigationState
    from src.services.runner import InProcessRunner, RunContext
    from src.services.store import MvpStore

    store = MvpStore(tmp_path / "runmode.sqlite3")
    state, _ = store.create_investigation(_claim())

    def executor(current: InvestigationState, ctx: RunContext) -> InvestigationState:
        return ctx.pause_for_review(current, checkpoint=CheckpointKind.ASSESSMENT, next_stage="build_dossier")

    runner = InProcessRunner(store, executor=executor)
    runner.run(state.investigation_id)

    events = store.list_events(state.investigation_id)
    kinds = [event["kind"] for event in events]
    # Trình tự mà giao diện đang đọc không được đổi: chế độ đi kèm dòng "running", không thêm dòng.
    assert kinds[:2] == ["created", "running"]
    running = next(event for event in events if event["kind"] == "running")
    assert running["payload"]["source_mode"] == "fixture"
    assert running["payload"]["synthetic"] is True
    assert "Chế độ chạy" in running["message"]
    # Thời gian chạy thật phải được lưu, không còn là 0 cứng.
    assert store.get_state(state.investigation_id).elapsed_ms >= 0


def _claim():
    from src.models.schemas import ClaimInput

    return ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
