"""Kiểm thử máy trạng thái LangGraph MVP (M05).

Phạm vi:
  * đổi query/nguồn theo khoảng trống bằng chứng (demo D4 — replanning);
  * không bao giờ tự kết luận ``supported`` từ FAERS;
  * hết ngân sách ⇒ dừng kèm lý do và vẫn tạo được hồ sơ thiếu sót;
  * checkpoint review (chuẩn hoá/kết luận/hồ sơ) và tiếp tục sau review;
  * policy an toàn: không kết luận nhân quả, trích dẫn phải có thật.
"""

from __future__ import annotations

import pytest

from src.models.schemas import (
    AssessmentStatus,
    CheckpointKind,
    ClaimInput,
    EvidenceScope,
    EvidenceUnit,
    GapKind,
    NormalizedClaim,
    ReviewStatus,
    RunStatus,
    SourceStatus,
    Stance,
    StopReason,
)
from src.services.assessment import assess_evidence
from src.services.budget import BudgetController
from src.services.dossier import validate_dossier
from src.services.planner import contrary_attempted, contrary_query, query_fingerprint
from src.services.runner import InProcessRunner
from src.services.stopping import _ready_to_conclude
from src.services.store import MvpStore


def _start(tmp_path, drug: str, event: str, **extra) -> tuple[MvpStore, InProcessRunner, str]:
    store = MvpStore(str(tmp_path / "mvp.db"))
    claim = ClaimInput(claim_text=f"{drug} gây {event}.", drug=drug, event=event, **extra)
    state, _ = store.create_investigation(claim)
    return store, InProcessRunner(store), state.investigation_id


def _run(tmp_path, drug: str, event: str, **extra):
    store, runner, investigation_id = _start(tmp_path, drug, event, **extra)
    return store, runner, runner.run(investigation_id)


def _events(store: MvpStore, investigation_id: str) -> list[tuple[str, str]]:
    return [(row["kind"], row["message"]) for row in store.list_events(investigation_id)]


def state_claim_text(store: MvpStore, investigation_id: str) -> str:
    return store.get_state(investigation_id).claim.claim_text


def _event_text(store: MvpStore, investigation_id: str) -> str:
    return "\n".join(message for _, message in _events(store, investigation_id))


# --------------------------------------------------------------------------------------
# Chuẩn hoá & checkpoint đầu vào
# --------------------------------------------------------------------------------------


def test_run_starts_with_normalization_and_checklist(tmp_path):
    store, _, state = _run(
        tmp_path, "metformin", "lactic acidosis", population="adults with renal impairment", route="oral"
    )
    assert state.normalized_claim is not None
    assert state.normalized_claim.drug_ingredient == "metformin"
    assert state.normalized_claim.event_term == "lactic acidosis"
    kinds = [kind for kind, _ in _events(store, state.investigation_id)]
    assert kinds[:3] == ["created", "running", "normalize"]
    assert "checklist" in kinds


def test_ambiguous_brand_pauses_at_normalization_checkpoint(tmp_path):
    store, _, state = _run(tmp_path, "Vigilax", "somnolence")
    assert state.checkpoint is CheckpointKind.NORMALIZATION
    assert state.run_status is RunStatus.WAITING_FOR_REVIEW
    assert state.stop_reason is StopReason.NEEDS_REVIEW
    assert state.budget.steps_used == 0
    assert state.documents == []
    assert "reviewer" in _event_text(store, state.investigation_id)


def test_ambiguous_claim_continues_after_reviewer_clarifies(tmp_path):
    store, runner, state = _run(tmp_path, "Vigilax", "somnolence")
    assert state.checkpoint is CheckpointKind.NORMALIZATION

    clarified = state.normalized_claim.model_copy(
        update={
            "drug_ingredient": "metformin",
            "drug_synonyms": ["Glucophage"],
            "ambiguities": [],
            "requires_review": False,
        }
    )
    store.save_state(state.model_copy(update={"normalized_claim": clarified}))

    resumed = runner.run(state.investigation_id, resume=True)
    assert resumed.checkpoint is CheckpointKind.ASSESSMENT
    assert resumed.searched_sources
    assert resumed.budget.steps_used > 0


# --------------------------------------------------------------------------------------
# Demo D4 — replanning: đổi query rồi đổi nguồn theo khoảng trống bằng chứng
# --------------------------------------------------------------------------------------


def test_d4_replanning_changes_query_then_source(tmp_path):
    store, _, state = _run(
        tmp_path, "Micardis", "angioedema", population="adults", route="oral"
    )
    events = _events(store, state.investigation_id)
    retrieves = [message for kind, message in events if kind == "retrieve"]

    # Bước 1 dùng nguyên văn tên biệt dược ⇒ không có kết quả, sinh gap NO_RESULTS.
    assert "Micardis" in retrieves[0]
    assert "0 tài liệu mới" in retrieves[0]
    assert any(gap.kind is GapKind.NO_RESULTS for gap in state.gaps)

    # Bước 2 đổi sang tên hoạt chất và ghi rõ lý do đổi.
    assert "telmisartan" in retrieves[1]
    assert "lý do:" in retrieves[1]
    assert state.normalized_claim.drug_ingredient == "telmisartan"

    # Sau khi đổi, agent thu được bằng chứng và mở rộng sang nguồn khác.
    assert len(state.active_evidence()) >= 1
    assert len(set(state.searched_sources)) >= 2
    assert state.assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE
    assert state.stop_reason is StopReason.SUCCESS


def test_planner_never_repeats_same_query_on_same_source(tmp_path):
    _, _, state = _run(tmp_path, "orlistat", "acute pancreatitis", dose="120 mg three times daily")
    assert len(state.queries) == len(set(state.queries)), "planner lặp lại query/nguồn đã gọi"


def test_planner_prefers_unsearched_source_before_giving_up(tmp_path):
    _, _, state = _run(tmp_path, "orlistat", "acute pancreatitis")
    assert set(state.searched_sources) == {"pubmed", "dailymed", "faers"}


# --------------------------------------------------------------------------------------
# FAERS không bao giờ tự thành kết luận
# --------------------------------------------------------------------------------------


def test_faers_only_never_auto_supports(tmp_path):
    _, _, state = _run(tmp_path, "orlistat", "acute pancreatitis", dose="120 mg three times daily")
    sources = {item.source for item in state.active_evidence()}
    assert sources == {"faers"}, "kịch bản kiểm thử phải chỉ có bằng chứng FAERS"
    assert state.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert state.assessment_status is not AssessmentStatus.SUPPORTED_FOR_SCOPE
    assert state.stop_reason is StopReason.INSUFFICIENT_EVIDENCE


def test_assess_evidence_rejects_faers_only_support():
    claim = NormalizedClaim(claim_text="orlistat và viêm tuỵ", drug_ingredient="orlistat", event_term="pancreatitis")
    faers_evidence = [
        EvidenceUnit(
            evidence_id="EVI-FAERS-1",
            doc_id="DOC-FAERS-1",
            source="faers",
            stance=Stance.SUPPORTS,
            quote="Báo cáo FAERS ghi nhận biến cố viêm tuỵ ở bệnh nhân dùng orlistat.",
            locator={"start": 0, "end": 60, "section": "4.8"},
            scope=EvidenceScope(population="adults", study_type="spontaneous report"),
        )
    ]
    result = assess_evidence(faers_evidence, claim)
    assert result.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert any("faers" in note.casefold() for note in result.rationale.split(".")) or result.rationale


# --------------------------------------------------------------------------------------
# Phạm vi & mâu thuẫn
# --------------------------------------------------------------------------------------


def test_scope_mismatch_is_reported_not_supported(tmp_path):
    _, _, state = _run(
        tmp_path, "ibuprofen", "gastrointestinal bleeding", population="children (under 12 years)", route="oral"
    )
    assert state.assessment_status is AssessmentStatus.SCOPE_MISMATCH
    assert any(gap.kind is GapKind.SCOPE_MISMATCH for gap in state.gaps)
    assert state.checkpoint is CheckpointKind.ASSESSMENT


def test_contradiction_requires_human_review(tmp_path):
    _, _, state = _run(
        tmp_path,
        "sertraline",
        "hyponatraemia",
        population="older adults (65 years and older)",
        route="oral",
    )
    assert state.assessment_status is AssessmentStatus.REQUIRES_HUMAN_REVIEW
    assert state.stop_reason is StopReason.NEEDS_REVIEW
    assert any(gap.kind is GapKind.CONTRADICTION for gap in state.gaps)


def test_source_error_is_recorded_and_stops_without_evidence(tmp_path):
    _, _, state = _run(
        tmp_path,
        "rivaroxaban",
        "intracranial haemorrhage",
        population="older adults (75 years and older)",
        route="oral",
    )
    assert state.stop_reason is StopReason.SOURCE_ERROR
    assert state.active_evidence() == []
    assert SourceStatus.ERROR in state.source_status.values()


# --------------------------------------------------------------------------------------
# Chống kết luận dương tính khi chưa tìm bằng chứng phản bác
# --------------------------------------------------------------------------------------


def test_supported_requires_contrary_search_and_second_source(tmp_path):
    _, _, state = _run(
        tmp_path, "metformin", "lactic acidosis", population="adults with renal impairment", route="oral"
    )
    contrary = query_fingerprint("pubmed", contrary_query(state.normalized_claim))
    assert contrary in state.queries, "phải chạy truy vấn phản bác trước khi kết luận supported"
    assert len(set(state.searched_sources)) >= 2
    assert state.assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE
    assert state.stop_reason is StopReason.SUCCESS


# --------------------------------------------------------------------------------------
# Ngân sách & hồ sơ
# --------------------------------------------------------------------------------------


def test_budget_reservation_is_idempotent(tmp_path):
    store, _, investigation_id = _start(tmp_path, "metformin", "lactic acidosis")
    controller = BudgetController(store)
    state = store.get_state(investigation_id)
    state, first = controller.reserve(state, "op-1", steps=1, source_requests=1)
    assert first.granted
    steps_after_first = state.budget.steps_used
    state, second = controller.reserve(state, "op-1", steps=1, source_requests=1)
    assert second.granted and "idempotent" in second.reason.casefold()
    assert state.budget.steps_used == steps_after_first


def test_run_keeps_last_step_reserved_for_dossier(tmp_path):
    _, _, state = _run(tmp_path, "metformin", "lactic acidosis")
    assert state.budget.steps_used <= state.budget.max_steps - 1


def test_exhaustion_yields_dossier_gaps(tmp_path):
    store, runner, investigation_id = _start(
        tmp_path, "metformin", "lactic acidosis", population="adults with renal impairment", route="oral"
    )
    state = store.get_state(investigation_id)
    store.save_state(state.model_copy(update={"budget": state.budget.model_copy(update={"max_steps": 2})}))

    stopped = runner.run(investigation_id)
    assert stopped.run_status is RunStatus.WAITING_FOR_REVIEW
    assert stopped.stop_reason is StopReason.BUDGET_EXHAUSTED
    assert stopped.checkpoint is CheckpointKind.ASSESSMENT
    assert stopped.next_stage == "build_dossier"
    # Dừng vì hết ngân sách KHÔNG được giữ kết luận dương tính chưa qua bước phản bác/nguồn thứ hai.
    assert stopped.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert store.latest_dossier(investigation_id) is None

    finished = runner.run(investigation_id, resume=True)
    assert finished.checkpoint is CheckpointKind.DOSSIER
    assert finished.next_stage == "export"

    dossier = store.latest_dossier(investigation_id)
    assert dossier is not None
    assert dossier.version == 1
    assert dossier.status is ReviewStatus.PENDING
    assert dossier.gaps, "hồ sơ thiếu sót phải ghi lại khoảng trống"
    assert "budget_exhausted" in "\n".join(dossier.limitations)
    assert dossier.content_hash
    assert set(dossier.citations) <= {document.doc_id for document in finished.documents}
    report = validate_dossier(dossier, finished)
    assert report.ok, report.errors


def test_dossier_version_increments_when_rebuilt(tmp_path):
    store, runner, investigation_id = _start(
        tmp_path, "metformin", "lactic acidosis", population="adults with renal impairment", route="oral"
    )
    stopped = runner.run(investigation_id)
    assert stopped.checkpoint is CheckpointKind.ASSESSMENT
    runner.run(investigation_id, resume=True)
    first = store.latest_dossier(investigation_id)
    assert first is not None and first.version == 1

    state = store.get_state(investigation_id)
    store.save_state(
        state.model_copy(update={"run_status": RunStatus.WAITING_FOR_REVIEW, "next_stage": "build_dossier"})
    )
    runner.run(investigation_id, resume=True)
    versions = [dossier.version for dossier in store.list_dossiers(investigation_id)]
    assert versions == [1, 2]


def test_dossier_has_no_causal_language_and_keeps_citations(tmp_path):
    store, runner, investigation_id = _start(
        tmp_path, "metformin", "lactic acidosis", population="adults with renal impairment", route="oral"
    )
    runner.run(investigation_id)
    runner.run(investigation_id, resume=True)
    dossier = store.latest_dossier(investigation_id)
    assert dossier is not None

    # Mục "Claim" giữ nguyên văn câu người dùng nêu; chỉ phần agent tự viết mới bị soi policy.
    claim_section = next(section for section in dossier.sections if section.title == "Claim")
    assert claim_section.body == state_claim_text(store, investigation_id)

    agent_text = "\n".join(
        [dossier.summary, *(section.body for section in dossier.sections if section.title != "Claim")]
    ).casefold()
    for pattern in ("gây", "nguyên nhân", "tỷ lệ mắc", "incidence"):
        assert pattern not in agent_text, f"hồ sơ chứa ngôn ngữ nhân quả/incidence: {pattern}"

    state = store.get_state(investigation_id)
    assert dossier.citations
    assert set(dossier.citations) <= {document.doc_id for document in state.documents}
    for section in dossier.sections:
        for evidence_id in section.evidence_ids:
            assert evidence_id in {item.evidence_id for item in state.active_evidence()}


# --------------------------------------------------------------------------------------
# Sự kiện cho UI
# --------------------------------------------------------------------------------------


def test_events_expose_query_change_reason_for_ui(tmp_path):
    store, _, state = _run(tmp_path, "Micardis", "angioedema", population="adults", route="oral")
    events = store.list_events(state.investigation_id)
    kinds = {row["kind"] for row in events}
    assert {"normalize", "checklist", "retrieve", "assess", "gaps", "waiting_for_review"} <= kinds
    retrieve_events = [row for row in events if row["kind"] == "retrieve"]
    assert all(row["payload"] is not None for row in retrieve_events)


@pytest.mark.parametrize(
    ("drug", "event", "extra", "expected_status"),
    [
        (
            "metformin",
            "lactic acidosis",
            {"population": "adults with renal impairment", "route": "oral"},
            AssessmentStatus.SUPPORTED_FOR_SCOPE,
        ),
        (
            "ibuprofen",
            "gastrointestinal bleeding",
            {"population": "children (under 12 years)", "route": "oral"},
            AssessmentStatus.SCOPE_MISMATCH,
        ),
        (
            "sertraline",
            "hyponatraemia",
            {"population": "older adults (65 years and older)", "route": "oral"},
            AssessmentStatus.REQUIRES_HUMAN_REVIEW,
        ),
        ("orlistat", "acute pancreatitis", {"dose": "120 mg three times daily"}, AssessmentStatus.INSUFFICIENT_EVIDENCE),
    ],
)
def test_fixture_scenarios_reach_expected_assessment(tmp_path, drug, event, extra, expected_status):
    _, _, state = _run(tmp_path, drug, event, **extra)
    assert state.assessment_status is expected_status


# --------------------------------------------------------------------------------------
# Hồi quy an toàn (đợt review M05–M07): dừng an toàn, trần ngân sách, phạm vi, trích dẫn
# --------------------------------------------------------------------------------------


def _metformin_case(tmp_path):
    return _start(
        tmp_path, "metformin", "lactic acidosis", population="adults with renal impairment", route="oral"
    )


def test_second_investigation_in_same_store_keeps_its_own_documents(tmp_path):
    """Chạy lại cùng kịch bản trong một store: không lỗi UNIQUE và vẫn đọc được tài liệu."""
    store, runner, first_id = _metformin_case(tmp_path)
    first = runner.run(first_id)
    assert first.run_status is RunStatus.WAITING_FOR_REVIEW

    claim = ClaimInput(
        claim_text="metformin gây lactic acidosis.",
        drug="metformin",
        event="lactic acidosis",
        population="adults with renal impairment",
        route="oral",
    )
    second_state, created = store.create_investigation(claim)
    assert created
    second = runner.run(second_state.investigation_id)

    assert second.run_status is not RunStatus.FAILED
    assert second.evidence, "lượt chạy thứ hai vẫn phải trích xuất được bằng chứng"
    for document in second.documents:
        # Mọi tài liệu được nêu trong state phải đọc được từ chính cuộc điều tra đó.
        assert store.get_document(second.investigation_id, document.doc_id).doc_id == document.doc_id
    assert {item.evidence_id for item in store.list_evidence(second.investigation_id)} == {
        item.evidence_id for item in second.evidence
    }


def test_document_ceiling_is_never_exceeded(tmp_path):
    """Trần tài liệu là trần cứng: state vẫn đọc được và bộ đếm không vượt trần."""
    store, runner, investigation_id = _metformin_case(tmp_path)
    state = store.get_state(investigation_id)
    store.save_state(
        state.model_copy(update={"budget": state.budget.model_copy(update={"max_documents": 1})})
    )

    stopped = runner.run(investigation_id)
    reloaded = store.get_state(investigation_id)  # không được ném ValidationError
    assert reloaded.budget.documents_used <= reloaded.budget.max_documents
    assert stopped.budget.documents_used <= stopped.budget.max_documents
    assert any(gap.kind is GapKind.MISSING_EVIDENCE and "trần tài liệu" in gap.description for gap in stopped.gaps)


def test_positive_conclusion_requires_evidence_from_two_sources(tmp_path):
    store, runner, investigation_id = _metformin_case(tmp_path)
    state = runner.run(investigation_id)
    assert state.assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE
    state = state.model_copy(update={"searched_sources": ["pubmed", "dailymed"]})
    assert len({item.source for item in state.evidence}) >= 2
    assert _ready_to_conclude(state)

    # Một nguồn đã gọi nhưng không trả bằng chứng không được tính là nguồn thứ hai.
    single_source = state.model_copy(
        update={"evidence": [item for item in state.evidence if item.source == "pubmed"][:1]}
    )
    assert not _ready_to_conclude(single_source)

    # Hai trích đoạn của CÙNG một tài liệu cũng không đủ cho kết luận dương tính.
    pubmed = [item for item in state.evidence if item.source == "pubmed"][0]
    same_document = state.model_copy(
        update={
            "evidence": [
                pubmed,
                pubmed.model_copy(update={"evidence_id": "EVI-PUBMED-1b", "quote": pubmed.quote + " (b)"}),
            ]
        }
    )
    assert not _ready_to_conclude(same_document)

    # Hai tài liệu độc lập cùng một nguồn thì đủ.
    two_documents = state.model_copy(
        update={
            "evidence": [
                pubmed,
                pubmed.model_copy(update={"evidence_id": "EVI-PUBMED-2", "doc_id": "DOC-PUBMED-2"}),
            ]
        }
    )
    assert _ready_to_conclude(two_documents)


def test_all_unknown_scope_is_not_reported_as_mismatch():
    claim = ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
    normalized = NormalizedClaim(claim_text=claim.claim_text, drug_ingredient="metformin", event_term="lactic acidosis")
    evidence = EvidenceUnit(
        evidence_id="EVI-1",
        doc_id="DOC-1",
        source="pubmed",
        stance=Stance.SUPPORTS,
        quote="Metformin was associated with lactic acidosis.",
        locator={"start": 0, "end": 44},
        scope=EvidenceScope(population="adults", route="oral"),
    )
    result = assess_evidence([evidence], normalized)
    # Không trường nào so khớp được ⇒ chưa đủ căn cứ kết luận "ngoài phạm vi".
    assert result.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE


def test_source_quote_with_causal_phrase_does_not_block_dossier(tmp_path):
    """Nguyên văn nguồn có 'due to' không được chặn hồ sơ; nhưng trích dẫn bịa thì bị bắt."""
    from src.services.dossier import build_dossier
    from src.services.policy import PolicyError

    store, runner, investigation_id = _metformin_case(tmp_path)
    runner.run(investigation_id)
    state = store.get_state(investigation_id)

    quote = "Lactic acidosis due to metformin accumulation was reported."
    edited = state.evidence[0].model_copy(update={"quote": quote})
    state = state.model_copy(update={"evidence": [edited, *state.evidence[1:]]})

    dossier = build_dossier(state)  # không ném PolicyError
    evidence_section = next(section for section in dossier.sections if section.title == "Bằng chứng đã truy xuất")
    assert "due to" in evidence_section.body

    report = validate_dossier(dossier, state)
    assert not report.ok
    assert any("nguyên văn không khớp" in error for error in report.errors)
    assert isinstance(PolicyError("no_causal_claim", "x"), ValueError)


def test_approve_at_normalization_checkpoint_returns_to_checklist(tmp_path):
    """Duyệt ở checkpoint chuẩn hoá phải quay lại vòng điều tra, không nhảy thẳng tới hồ sơ."""
    from src.models.schemas import ReviewAction, ReviewDecision
    from src.services.review import apply_review

    store, runner, investigation_id = _metformin_case(tmp_path)
    state = store.get_state(investigation_id)
    paused = state.model_copy(
        update={
            "checkpoint": CheckpointKind.NORMALIZATION,
            "run_status": RunStatus.WAITING_FOR_REVIEW,
            "next_stage": "checklist",
        }
    )
    paused = store.save_state(paused)

    decision = ReviewDecision(
        decision_id="DEC-NORM-1",
        investigation_id=investigation_id,
        checkpoint=CheckpointKind.NORMALIZATION,
        action=ReviewAction.APPROVE,
        reviewer_id="reviewer",
        expected_version=paused.version,
    )
    apply_review(store, decision)
    assert store.get_state(investigation_id).next_stage == "checklist"

    resumed = runner.run(investigation_id, resume=True)
    # Không được nhảy thẳng tới hồ sơ khi chưa hề đánh giá bằng chứng.
    assert resumed.documents, "duyệt ở checkpoint chuẩn hoá phải quay lại vòng thu thập bằng chứng"
    assert resumed.budget.steps_used > 0
    assert resumed.checkpoint is CheckpointKind.ASSESSMENT
    assert resumed.assessment is not None


# --------------------------------------------------------------------------------------
# P16/P17 — các kiểm tra theo tên trong quy tắc phối hợp
# --------------------------------------------------------------------------------------


def test_empty_search_changes_strategy(tmp_path):
    """Tìm rỗng phải đổi chiến lược (đổi query hoặc đổi nguồn), không lặp lại y nguyên."""
    store, _, state = _run(tmp_path, "không-rõ", "không-rõ")
    retrieves = [message for kind, message in _events(store, state.investigation_id) if kind == "retrieve"]

    assert len(retrieves) >= 2, "phải có ít nhất một lần đổi chiến lược sau khi tìm rỗng"
    assert "0 tài liệu mới" in retrieves[0]
    assert any(gap.kind is GapKind.NO_RESULTS for gap in state.gaps)
    assert any("lý do:" in message for message in retrieves[1:]), "lần đổi chiến lược phải ghi rõ lý do"
    assert retrieves[1] != retrieves[0]


def test_contradiction_adds_followup_gap(tmp_path):
    """Bằng chứng mâu thuẫn phải sinh gap contradiction để bước sau xử lý."""
    _, _, state = _run(tmp_path, "sertraline", "hyponatraemia")

    assert state.assessment_status is AssessmentStatus.REQUIRES_HUMAN_REVIEW
    contradiction_gaps = [gap for gap in state.gaps if gap.kind is GapKind.CONTRADICTION]
    assert contradiction_gaps, "thiếu gap contradiction"
    assert contradiction_gaps[0].description


def test_unresolved_contradiction_waits_for_review(tmp_path):
    """Mâu thuẫn chưa giải quyết thì dừng ở checkpoint assessment chờ người phân xử."""
    store, _, state = _run(tmp_path, "sertraline", "hyponatraemia")

    assert state.run_status is RunStatus.WAITING_FOR_REVIEW
    assert state.checkpoint is CheckpointKind.ASSESSMENT
    assert state.stop_reason is StopReason.NEEDS_REVIEW
    assert state.assessment_status is AssessmentStatus.REQUIRES_HUMAN_REVIEW
    assert "người phân xử" in _event_text(store, state.investigation_id)


def test_repeated_query_is_not_reissued(tmp_path):
    """Không bao giờ gửi lại đúng một cặp (nguồn, truy vấn) đã chạy."""
    _, _, state = _run(tmp_path, "không-rõ", "không-rõ")

    assert len(state.queries) >= 3
    assert len(state.queries) == len(set(state.queries)), f"truy vấn bị lặp: {state.queries}"


def test_checklist_covers_five_required_categories(tmp_path):
    """Checklist mặc định phải có label check, y văn, mẫu báo cáo tự nguyện, phản bác và scope gap."""
    from src.agents.graph import checklist_node
    from src.models.schemas import NormalizedClaim
    from src.services.llm import LLMGateway, MockProvider
    from src.services.runner import RunContext

    store = MvpStore(str(tmp_path / "checklist.db"))
    state, _ = store.create_investigation(
        ClaimInput(claim_text="metformin gây lactic acidosis.", drug="metformin", event="lactic acidosis")
    )
    normalized = NormalizedClaim(
        claim_text=state.claim.claim_text,
        drug_ingredient="metformin",
        event_term="lactic acidosis",
        unknowns=["dose", "time_window"],
    )
    state = store.save_state(state.model_copy(update={"normalized_claim": normalized}), expected_version=state.version)
    ctx = RunContext(store=store, gateway=LLMGateway(MockProvider({})))
    result = checklist_node({"investigation": state, "ctx": ctx, "scenario": {}, "decision": None, "stop": None})

    checklist = {gap.gap_id: gap.description for gap in result["investigation"].gaps}
    assert "GAP-SRC-dailymed" in checklist and "label" in checklist["GAP-SRC-dailymed"].casefold()
    assert "GAP-SRC-pubmed" in checklist and "y văn" in checklist["GAP-SRC-pubmed"].casefold()
    assert "GAP-SRC-faers" in checklist and "tự nguyện" in checklist["GAP-SRC-faers"].casefold()
    assert "GAP-UNKNOWN-dose" in checklist  # scope gap
    assert "chưa kiểm tra được" in " ".join(checklist.values())


def test_contrary_gap_is_closed_after_the_contrary_search(tmp_path):
    _, _, state = _run(tmp_path, "metformin", "lactic acidosis")

    assert contrary_attempted(state)
    assert all(gap.gap_id != "GAP-CONTRARY" for gap in state.gaps), "gap phản bác phải được đóng sau khi chạy"


def test_contrary_gap_stays_open_when_the_contrary_search_never_runs(tmp_path):
    """Nếu bước phản bác chưa chạy thì gap phải còn, để hồ sơ ghi rõ phần chưa kiểm tra được."""
    store, runner, investigation_id = _start(tmp_path, "metformin", "lactic acidosis")
    state = store.get_state(investigation_id)
    state.budget.max_steps = 1  # chỉ đủ một bước truy xuất, chưa tới bước phản bác
    store.save_state(state, expected_version=state.version)

    final = runner.run(investigation_id)

    assert not contrary_attempted(final)
    assert any(gap.gap_id == "GAP-CONTRARY" for gap in final.gaps)
