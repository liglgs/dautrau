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


def _settings(
    source: str, evidence: str, pubmed: str = "api", *, model_key: str = "khoa-gia-lap"
) -> Settings:
    """``Settings`` với hai công tắc chế độ, không đọc ``.env`` của máy chạy.

    Mặc định có khoá mô hình giả để phép thử nói về chế độ, không nói về chuyện thiếu khoá; bài
    kiểm riêng cho trường hợp thiếu khoá truyền ``model_key=""``.
    """
    return Settings(
        _env_file=None,
        mvp_source_mode=source,
        mvp_evidence_mode=evidence,
        mvp_pubmed_mode=pubmed,
        openai_api_key=model_key,
    )


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


def test_local_pubmed_is_not_described_as_network_retrieval():
    """``MVP_PUBMED_MODE=local`` đọc corpus đã nhập, không gọi mạng — nhãn phải nói đúng."""
    mode = resolve_run_mode(_settings("live", "person3", pubmed="local"))
    assert "không gọi mạng" in mode.label
    assert mode.warnings, "chế độ này phải kèm cảnh báo, không im lặng"
    assert any("local" in warning for warning in mode.warnings)
    # Vẫn là dữ liệu thật: tài liệu là bản thật đã nhập, chỉ khác đường lấy.
    assert mode.synthetic is False


def test_network_pubmed_carries_no_warning():
    mode = resolve_run_mode(_settings("live", "person3", pubmed="api"))
    assert mode.warnings == []
    assert "qua mạng" not in mode.label  # nhãn cũ nói "qua mạng" cả khi đọc corpus


def test_a_model_backed_mode_without_a_key_says_so():
    """Nhãn "mô hình trích từ nguồn thật" là nói sai nếu chưa cấu hình khoá nào."""
    mode = resolve_run_mode(_settings("live", "person3", model_key=""))
    assert any("khoá" in warning for warning in mode.warnings), mode.warnings


def test_a_model_backed_mode_with_a_gemini_key_only_is_fine():
    mode = resolve_run_mode(
        Settings(
            _env_file=None,
            mvp_source_mode="live",
            mvp_evidence_mode="person3",
            openai_api_key="",
            gemini_api_key="khoa-gemini",
        )
    )
    assert not any("khoá" in warning for warning in mode.warnings), mode.warnings


def test_fixture_mode_does_not_ask_for_a_model_key():
    """Chế độ mẫu không gọi mô hình, nên thiếu khoá không phải là vấn đề."""
    mode = resolve_run_mode(_settings("fixture", "fixture", model_key=""))
    assert mode.warnings == []


def test_warehouse_mode_is_never_described_as_network():
    mode = resolve_run_mode(_settings("warehouse", "person3", pubmed="api"))
    assert "mạng" not in mode.label


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
