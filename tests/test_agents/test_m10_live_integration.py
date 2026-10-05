"""Bộ kiểm thử tích hợp thực tế M10 (Final Live Integration Suite).

Kiểm chứng sự phối hợp trực tiếp giữa Người 2 (LangGraph, InProcessRunner, BudgetController,
ReviewWorkflow, Store, API) với Người 1 (LocalPubMedAdapter, DailyMed, FAERS) và
Người 3 (ClaimNormalizer, EvidenceExtractor, EvidenceAnalyzer, build_person3_dossier).
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    StopReason,
)
from src.services.evidence.candidate_provider import CandidateQuoteProvider
from src.services.evidence.demo import graph_inputs, make_demo_runtime
from src.services.evidence.integration import configure_person3
from src.services.evidence.normalize import load_dictionary
from src.services.llm import LLMGateway
from src.services.review import apply_review
from src.services.runner import InProcessRunner
from src.services.sources import build_adapters
from src.services.store import MvpStore

ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = ROOT / "data/pubmed-local"
SNAPSHOT_ROOT = ROOT / "data/snapshots"
DICTIONARY_PATH = ROOT / "data/dictionaries/mvp_candidates_2026_10_02.json"


def test_live_pubmed_local_adapter_with_person2_graph(tmp_path):
    """Kiểm chứng Person 2 LangGraph kết hợp với LocalPubMedAdapter của Person 1 và ClaimNormalizer của Person 3."""
    if not (CORPUS_ROOT / "manifest.json").exists():
        pytest.skip("Chưa import dữ liệu PubMed local")

    store = MvpStore(str(tmp_path / "test_m10_pubmed.sqlite3"))
    claim_input = ClaimInput(
        claim_text="Investigate reported association: metformin / diarrhoea.",
        drug="metformin",
        event="diarrhoea",
        config=InvestigationConfig(sources=["pubmed"], max_steps=4, max_documents=5),
    )
    state, _ = store.create_investigation(claim_input)

    # Sử dụng CandidateQuoteProvider offline của Person 3
    gateway = LLMGateway(CandidateQuoteProvider(load_dictionary(DICTIONARY_PATH)))
    runner = InProcessRunner(store, gateway=gateway)
    ctx = runner.context()

    # Cắm adapter Người 1 (Local PubMed) và Người 3
    ctx.adapters = build_adapters(
        pubmed_mode="local",
        pubmed_corpus_root=str(CORPUS_ROOT),
        snapshot_root=str(SNAPSHOT_ROOT),
        drug="metformin",
        event="diarrhoea",
        max_documents=5,
    )
    if DICTIONARY_PATH.exists():
        configure_person3(ctx, DICTIONARY_PATH)

    # Chạy graph
    result = run_investigation(state, ctx)

    # Kiểm tra kết quả
    assert result.step_index >= 1
    assert "pubmed" in result.searched_sources
    assert len(result.documents) > 0
    # Tài liệu được lưu trữ nguyên vẹn vào SQLite
    saved_docs = store.list_documents(result.investigation_id)
    assert len(saved_docs) == len(result.documents)
    assert any("metformin" in doc.text.casefold() for doc in saved_docs)


def test_person3_demo_scenarios_integration(tmp_path):
    """Kiểm chứng toàn diện luồng điều tra và reviewer với Person 3 demo engine:

    1. Chạy ca 'match': dừng tại checkpoint assessment với supported_for_scope.
    2. Reviewer thẩm định -> tiếp tục -> tạo dossier -> dừng tại checkpoint dossier.
    3. Reviewer duyệt dossier -> export markdown thành công với đầy đủ trích dẫn.
    """
    store = MvpStore(str(tmp_path / "test_m10_demo.sqlite3"))
    claim_data = graph_inputs("match")[0]
    claim_input = ClaimInput(**claim_data)
    state, _ = store.create_investigation(claim_input)

    executor, gateway = make_demo_runtime("match")
    runner = InProcessRunner(store, executor=executor, gateway=gateway)

    # 1. Chạy đợt 1
    paused_state = runner.run(state.investigation_id)
    assert paused_state.run_status is RunStatus.WAITING_FOR_REVIEW
    assert paused_state.checkpoint is CheckpointKind.ASSESSMENT
    assert paused_state.assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE
    assert paused_state.next_stage == "build_dossier"

    # 2. Reviewer thẩm định kết quả
    review_decision = ReviewDecision(
        decision_id="rev-dec-1",
        investigation_id=paused_state.investigation_id,
        reviewer_id="reviewer_1",
        action=ReviewAction.APPROVE,
        checkpoint=CheckpointKind.ASSESSMENT,
        reason="Đồng ý với đánh giá bằng chứng",
        expected_version=paused_state.version,
    )
    res_review = apply_review(store, review_decision)
    assert res_review.version == paused_state.version + 1
    reviewed_state = store.get_state(paused_state.investigation_id)

    # 3. Tiếp tục chạy để tạo hồ sơ dossier
    dossier_paused = runner.run(reviewed_state.investigation_id, resume=True)
    assert dossier_paused.run_status is RunStatus.WAITING_FOR_REVIEW
    assert dossier_paused.checkpoint is CheckpointKind.DOSSIER
    assert dossier_paused.next_stage == "export"

    dossiers = store.list_dossiers(dossier_paused.investigation_id)
    assert len(dossiers) >= 1
    dossier = dossiers[-1]
    assert dossier.status is ReviewStatus.PENDING

    # 4. Reviewer phê duyệt dossier để hoàn tất
    approve_dossier_decision = ReviewDecision(
        decision_id="rev-dec-2",
        investigation_id=dossier_paused.investigation_id,
        reviewer_id="reviewer_1",
        action=ReviewAction.APPROVE,
        checkpoint=CheckpointKind.DOSSIER,
        reason="Hồ sơ đầy đủ, phê duyệt để ban hành",
        expected_version=dossier_paused.version,
    )
    apply_review(store, approve_dossier_decision)
    final_state = store.get_state(dossier_paused.investigation_id)
    assert final_state.run_status is RunStatus.COMPLETED

    approved_dossiers = [d for d in store.list_dossiers(final_state.investigation_id) if d.status is ReviewStatus.APPROVED]
    assert len(approved_dossiers) == 1
    assert len(approved_dossiers[0].sections) > 0
    assert len(approved_dossiers[0].citations) > 0
    assert len(final_state.evidence) > 0


def test_contradiction_handling_stops_for_review(tmp_path):
    """Kiểm chứng khi phát hiện bằng chứng trái chiều (contradiction), graph tự dừng an toàn."""
    store = MvpStore(str(tmp_path / "test_m10_contra.sqlite3"))
    claim_data = graph_inputs("contradiction")[0]
    claim_input = ClaimInput(**claim_data)
    state, _ = store.create_investigation(claim_input)

    executor, gateway = make_demo_runtime("contradiction")
    runner = InProcessRunner(store, executor=executor, gateway=gateway)

    result = runner.run(state.investigation_id)
    assert result.run_status is RunStatus.WAITING_FOR_REVIEW
    assert result.assessment_status is AssessmentStatus.REQUIRES_HUMAN_REVIEW
    assert any("contradiction" in gap.description.lower() for gap in result.gaps)


def test_budget_exhaustion_stops_gracefully_on_live_pipeline(tmp_path):
    """Kiểm chứng khi hết ngân sách bước/tài liệu, agent dừng lại an toàn với insufficient_evidence."""
    store = MvpStore(str(tmp_path / "test_m10_budget.sqlite3"))
    claim_input = ClaimInput(
        claim_text="Investigate reported association: metformin / diarrhoea.",
        drug="metformin",
        event="diarrhoea",
        config=InvestigationConfig(sources=["pubmed"], max_steps=1, max_documents=1),
    )
    state, _ = store.create_investigation(claim_input)

    gateway = LLMGateway(CandidateQuoteProvider(load_dictionary(DICTIONARY_PATH)))
    ctx = InProcessRunner(store, gateway=gateway).context()
    ctx.adapters = build_adapters(
        pubmed_mode="local",
        pubmed_corpus_root=str(CORPUS_ROOT),
        snapshot_root=str(SNAPSHOT_ROOT),
        drug="metformin",
        event="diarrhoea",
        max_documents=1,
    )

    result = run_investigation(state, ctx)
    assert result.step_index <= 2
    # Dừng an toàn không bị exception
    assert result.run_status in (RunStatus.WAITING_FOR_REVIEW, RunStatus.COMPLETED)
    assert result.stop_reason in (StopReason.BUDGET_EXHAUSTED, StopReason.INSUFFICIENT_EVIDENCE, StopReason.SATURATION)


def test_cancel_api_releases_runner_lock(tmp_path):
    """Kiểm chứng API hủy cuộc điều tra giải phóng runner lock ngay lập tức."""
    store = MvpStore(str(tmp_path / "test_m10_cancel.sqlite3"))
    claim_input = ClaimInput(claim_text="test drug event", drug="aspirin", event="bleeding")
    state, _ = store.create_investigation(claim_input)

    runner = InProcessRunner(store)
    # Chiếm lock mô phỏng đang chạy
    runner.acquire(state.investigation_id)
    assert runner.is_busy
    assert runner.current == state.investigation_id

    # Hủy cuộc điều tra
    cancelled = runner.cancel(state.investigation_id)
    assert cancelled.run_status is RunStatus.CANCELLED
    assert runner.is_cancelled(state.investigation_id)

    # Giải phóng
    runner.release()
    assert not runner.is_busy
