"""LangGraph state machine cho MVP điều tra an toàn thuốc (M05).

Chu trình::

    [entry] normalize → checklist → plan → retrieve → extract/assess → update_gaps
              → stop_or_continue → (plan | END chờ reviewer)
    [resume] next_stage=build_dossier → build_dossier → END chờ duyệt hồ sơ

Entry Dispatcher phân biệt **chạy mới** với **tiếp tục từ checkpoint review** và không bao giờ
reset bộ đếm ngân sách.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.mock_runtime import FixtureAdapter, FixtureExtractor, FixtureNormalizer, scenario_for_claim
from src.agents.state import MvpGraphState
from src.models.schemas import (
    AssessmentStatus,
    CheckpointKind,
    EvidenceGap,
    EvidenceUnit,
    GapKind,
    InvestigationState,
    PlannerActionKind,
    RunStatus,
    SourceDocument,
    SourceSearchResult,
    SourceStatus,
    StopDecision,
    StopReason,
)
from src.services.assessment import assess_evidence
from src.services.budget import BudgetController, can_spend, count_new_documents
from src.services.dossier import build_dossier, content_hash
from src.services.planner import SOURCE_PRIORITY, choose_next_action, contrary_query, query_fingerprint
from src.services.policy import PolicyError, assert_supported_needs_strong_source
from src.services.stopping import evaluate_stop

#: Giới hạn đệ quy kỹ thuật của LangGraph — KHÔNG phải ngân sách nghiệp vụ.
#: Mỗi bước truy xuất đi qua ~5 node; trần cứng 20 bước ⇒ cần >100 bước graph.
RECURSION_LIMIT = 160

#: Nhãn checklist mặc định theo từng nguồn (label check / y văn / mẫu báo cáo tự nguyện).
CHECKLIST_LABELS: dict[str, str] = {
    "dailymed": "Kiểm tra nhãn thuốc (label check, DailyMed)",
    "pubmed": "Đối chiếu y văn phù hợp (PubMed)",
    "faers": "Kiểm tra mẫu báo cáo tự nguyện (spontaneous pattern, FAERS)",
}


# --------------------------------------------------------------------------------------
# Node: normalize
# --------------------------------------------------------------------------------------


def normalize_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    scenario = gstate.get("scenario") or {}
    normalizer = ctx.normalizer or FixtureNormalizer(scenario)
    claim = normalizer.normalize_claim(state.claim)
    state = state.model_copy(update={"normalized_claim": claim})

    if claim.ambiguities or claim.requires_review:
        state = state.model_copy(update={"stop_reason": StopReason.NEEDS_REVIEW})
        saved = ctx.pause_for_review(
            state,
            checkpoint=CheckpointKind.NORMALIZATION,
            next_stage="checklist",
            message="Claim mơ hồ — chờ reviewer chốt hoạt chất trước khi truy xuất.",
        )
        stop = StopDecision(
            should_stop=True,
            reason=StopReason.NEEDS_REVIEW,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            message="Cần reviewer chốt hoạt chất.",
        )
        return {"investigation": saved, "stop": stop}

    saved = ctx.save(
        state,
        event=("normalize", f"Chuẩn hoá claim: {claim.drug_ingredient} / {claim.event_term}"),
    )
    return {"investigation": saved, "stop": None}


# --------------------------------------------------------------------------------------
# Node: checklist (xác định khoảng trống bằng chứng ban đầu)
# --------------------------------------------------------------------------------------


def checklist_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    claim = state.normalized_claim
    gaps: list[EvidenceGap] = []

    allowed_sources = getattr(state.config, "sources", None) or list(SOURCE_PRIORITY)
    for source in allowed_sources:
        if source in CHECKLIST_LABELS and source not in state.searched_sources:
            gaps.append(
                EvidenceGap(
                    gap_id=f"GAP-SRC-{source}",
                    kind=GapKind.MISSING_SOURCE,
                    field=source,
                    description=f"{CHECKLIST_LABELS[source]} — chưa kiểm tra được (nguồn chưa chạy).",
                    priority=3 if source in ("pubmed", "dailymed") else 2,
                    created_step=state.step_index,
                )
            )
    if "pubmed" in allowed_sources:
        gaps.append(
            EvidenceGap(
                gap_id="GAP-CONTRARY",
                kind=GapKind.MISSING_EVIDENCE,
                field="contrary",
                description="Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.",
                priority=3,
                created_step=state.step_index,
            )
        )
    if claim is not None:
        for ambiguity in claim.ambiguities:
            gaps.append(
                EvidenceGap(
                    gap_id=f"GAP-AMBIGUITY-{len(gaps)}",
                    kind=GapKind.AMBIGUITY,
                    field="normalized_claim",
                    description=f"Claim còn mơ hồ (chưa chốt): {ambiguity}",
                    priority=5,
                    created_step=state.step_index,
                )
            )
        for field in claim.unknowns:
            if field in {"population", "dose", "route", "time_window"}:
                gaps.append(
                    EvidenceGap(
                        gap_id=f"GAP-UNKNOWN-{field}",
                        kind=GapKind.MISSING_EVIDENCE,
                        field=field,
                        description=f"Claim chưa xác định {field}; không được suy rộng.",
                        priority=1,
                        created_step=state.step_index,
                    )
                )

    state = state.model_copy(update={"gaps": gaps})
    saved = ctx.save(state, event=("checklist", f"Xác định {len(gaps)} khoảng trống bằng chứng ban đầu."))
    return {"investigation": saved, "gaps_before": len(gaps)}


# --------------------------------------------------------------------------------------
# Node: plan
# --------------------------------------------------------------------------------------


def plan_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    decision = choose_next_action(state)
    if decision.action is PlannerActionKind.STOP:
        ctx = gstate["ctx"]
        state = ctx.save(state, event=("plan", f"Dừng lập kế hoạch: {decision.reason}"))
        step_ok, _ = can_spend(state.budget, steps=1)
        stop = StopDecision(
            should_stop=True,
            reason=StopReason.BUDGET_EXHAUSTED if not step_ok else StopReason.INSUFFICIENT_EVIDENCE,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            # Hết chiến lược ⇒ không có kết luận mới; giữ nguyên mức thận trọng thay vì
            # tái sử dụng kết luận cũ (có thể là dương tính chưa đủ điều kiện).
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            message=decision.reason,
        )
        return {"investigation": state, "decision": None, "stop": stop}
    return {"decision": decision}


def route_after_plan(gstate: MvpGraphState) -> str:
    return "retrieve" if gstate.get("decision") else "stop_or_continue"


# --------------------------------------------------------------------------------------
# Node: retrieve
# --------------------------------------------------------------------------------------


def retrieve_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    decision = gstate["decision"]
    assert decision is not None

    budget = BudgetController(ctx.store)
    operation_key = f"step-{state.step_index + 1}-{decision.fingerprint}"
    if not ctx.adapters and ctx.source_factory is not None and state.normalized_claim is not None:
        ctx.adapters = ctx.source_factory(state.normalized_claim)
    adapter = ctx.adapters.get(decision.source)
    # Metered adapters charge each actual HTTP call; local/cache hits need no HTTP reservation.
    reserved_requests = 0 if hasattr(adapter, "search_with_budget") else 1
    state, reservation = budget.reserve(state, operation_key, steps=1, source_requests=reserved_requests)
    if not reservation.granted:
        stop = StopDecision(
            should_stop=True,
            reason=StopReason.BUDGET_EXHAUSTED,
            run_status=RunStatus.WAITING_FOR_REVIEW,
            assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
            message=reservation.reason,
        )
        return {"investigation": state, "stop": stop}

    requests_to_commit = 1
    if adapter is None:  # pragma: no cover - planner chỉ chọn nguồn hợp lệ
        result_documents: list[SourceDocument] = []
        result = SourceSearchResult(
            source=decision.source,  # type: ignore[arg-type]
            query=decision.query or "",
            fingerprint=decision.fingerprint or "",
            status=SourceStatus.ERROR,
            error=f"Chưa có adapter cho nguồn {decision.source}",
        )
    else:
        if hasattr(adapter, "search_with_budget"):
            def charge_request() -> None:
                nonlocal state
                updated_budget = state.budget.model_copy(update={
                    "source_requests": state.budget.source_requests + 1,
                })
                state = ctx.save(state.model_copy(update={"budget": updated_budget}))

            result = adapter.search_with_budget(decision, state.budget, charge_request)
            requests_to_commit = 0  # HTTP calls are already durably charged, including failures/retries.
        else:
            result = adapter.search(decision, state.budget)
            requests_to_commit = result.requests_used
        result_documents = list(result.documents)

    fresh_documents = count_new_documents(state, result_documents)
    allowed = max(0, state.budget.max_documents - state.budget.documents_used)
    dropped_documents = 0
    if fresh_documents > allowed:
        # Trần cứng tài liệu: chỉ nhận phần còn ngân sách; phần dư ghi thành gap để không
        # bao giờ đẩy bộ đếm vượt trần (vượt trần làm state không đọc được nữa).
        kept: list[SourceDocument] = []
        kept_hashes = {document.hash for document in state.documents}
        for document in result_documents:
            if len(kept) >= allowed:
                break
            if document.hash in kept_hashes:
                continue
            kept.append(document)
            kept_hashes.add(document.hash)
        dropped_documents = fresh_documents - len(kept)
        result_documents = kept
        fresh_documents = len(kept)
    state = budget.commit(state, operation_key, documents=fresh_documents, source_requests=requests_to_commit)

    known_ids = {document.doc_id for document in state.documents}
    appended = [document for document in result_documents if document.doc_id not in known_ids]
    for document in appended:
        ctx.store.save_document(state.investigation_id, document)

    contrary_done = (
        state.normalized_claim is not None
        and decision.fingerprint == query_fingerprint(decision.source, contrary_query(state.normalized_claim))
    )
    gaps = [
        gap
        for gap in state.gaps
        if not (gap.kind is GapKind.MISSING_SOURCE and gap.field == decision.source)
        and not (gap.gap_id == "GAP-CONTRARY" and contrary_done)
    ]
    if result.status is SourceStatus.EMPTY and not appended:
        gaps.append(
            EvidenceGap(
                gap_id=f"GAP-EMPTY-{decision.fingerprint}",
                kind=GapKind.NO_RESULTS,
                field=decision.source,
                description=f"Nguồn {decision.source} không trả kết quả cho query '{decision.query}'.",
                priority=4,
                created_step=state.step_index + 1,
            )
        )
    if result.status is SourceStatus.ERROR:
        gaps.append(
            EvidenceGap(
                gap_id=f"GAP-ERROR-{decision.fingerprint}",
                kind=GapKind.MISSING_SOURCE,
                field=decision.source,
                description=f"Nguồn {decision.source} lỗi: {result.error}",
                priority=4,
                created_step=state.step_index + 1,
            )
        )
    if dropped_documents:
        gaps.append(
            EvidenceGap(
                gap_id=f"GAP-BUDGET-{decision.fingerprint}",
                kind=GapKind.MISSING_EVIDENCE,
                field=decision.source,
                description=(
                    f"Đã chạm trần tài liệu ({state.budget.max_documents}); bỏ qua {dropped_documents} "
                    f"tài liệu mới từ {decision.source}."
                ),
                priority=5,
                created_step=state.step_index + 1,
            )
        )

    searched = list(dict.fromkeys([*state.searched_sources, decision.source]))
    state = state.model_copy(
        update={
            "step_index": state.step_index + 1,
            "documents": [*state.documents, *appended],
            "queries": [*state.queries, decision.fingerprint or result.fingerprint],
            "searched_sources": searched,
            "source_status": {**state.source_status, decision.source: result.status},
            "gaps": gaps,
        }
    )
    saved = ctx.save(
        state,
        event=(
            "retrieve",
            f"{decision.source} · '{decision.query}' → {len(appended)} tài liệu mới ({result.status})"
            + (f" · lý do: {decision.reason}" if decision.reason else ""),
        ),
    )
    return {
        "investigation": saved,
        "decision": None,
        "evidence_before": len(saved.active_evidence()),
        "gaps_before": len(saved.gaps),
    }


# --------------------------------------------------------------------------------------
# Node: extract/assess
# --------------------------------------------------------------------------------------


def extract_assess_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    if ctx.evidence_analyzer is not None:
        from src.services.evidence.nodes import extract_assess_person3

        return extract_assess_person3(gstate)
    scenario = gstate.get("scenario") or {}
    extractor = ctx.extractor or FixtureExtractor(scenario)
    claim = state.normalized_claim
    assert claim is not None

    evidence: list[EvidenceUnit] = list(state.evidence)
    known = {item.evidence_id for item in evidence}
    for document in state.documents:
        for item in extractor.extract_evidence(document, claim):
            if item.evidence_id in known:
                continue
            known.add(item.evidence_id)
            evidence.append(item)
            ctx.store.save_evidence(state.investigation_id, item)

    assessment = assess_evidence(evidence, claim)
    try:
        assert_supported_needs_strong_source(
            assessment.assessment_status, {item.source for item in evidence if not item.excluded}
        )
    except PolicyError as exc:
        assessment = assessment.model_copy(
            update={
                "assessment_status": AssessmentStatus.INSUFFICIENT_EVIDENCE,
                "rationale": f"Policy chặn kết luận: {exc.detail}",
            }
        )

    gaps = list(state.gaps)
    if any(item.stance == "contradicts" and not item.excluded for item in evidence):
        if not any(gap.kind is GapKind.CONTRADICTION for gap in gaps):
            gaps.append(
                EvidenceGap(
                    gap_id="GAP-CONTRADICTION",
                    kind=GapKind.CONTRADICTION,
                    description="Có bằng chứng trái chiều cần người phân xử.",
                    priority=5,
                    created_step=state.step_index,
                )
            )
    if assessment.assessment_status is AssessmentStatus.SCOPE_MISMATCH:
        if not any(gap.kind is GapKind.SCOPE_MISMATCH for gap in gaps):
            gaps.append(
                EvidenceGap(
                    gap_id="GAP-SCOPE",
                    kind=GapKind.SCOPE_MISMATCH,
                    description="Bằng chứng lệch phạm vi claim: " + "; ".join(assessment.scope_notes),
                    priority=4,
                    created_step=state.step_index,
                )
            )

    state = state.model_copy(
        update={
            "evidence": evidence,
            "assessment": assessment,
            "assessment_status": assessment.assessment_status,
            "gaps": gaps,
        }
    )
    saved = ctx.save(
        state,
        event=("assess", f"Kết luận tạm thời: {assessment.assessment_status} ({len(evidence)} đơn vị bằng chứng)"),
    )
    return {"investigation": saved}


# --------------------------------------------------------------------------------------
# Node: update_gaps (bão hoà)
# --------------------------------------------------------------------------------------


def update_gaps_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    grew = len(state.active_evidence()) > gstate.get("evidence_before", 0)
    narrowed = len(state.gaps) < gstate.get("gaps_before", len(state.gaps))
    streak = 0 if (grew or narrowed) else state.no_progress_streak + 1
    state = state.model_copy(update={"no_progress_streak": streak})
    saved = ctx.save(
        state,
        event=("gaps", f"Cập nhật khoảng trống: {len(state.gaps)} gap, chuỗi không tiến triển = {streak}"),
    )
    # RT-02: đây là node cuối của mỗi lượt, nên đây là chỗ duy nhất ghi được một dòng nhật ký
    # trọn vẹn cho lượt đó — nguồn đã tìm, số lượt, ngân sách đã tiêu và chế độ đang chạy.
    ctx.emit(
        saved.investigation_id,
        "turn",
        f"Lượt {saved.step_index}: {len(saved.searched_sources)} nguồn, "
        f"{len(saved.active_evidence())} bằng chứng, {len(saved.gaps)} khoảng trống",
        _turn_log_payload(saved),
    )
    return {"investigation": saved}


def _turn_log_payload(state: InvestigationState) -> dict[str, Any]:
    """Dòng nhật ký của một lượt điều tra: nguồn, số lượt, ngân sách, chế độ chạy."""
    from src.config import get_settings
    from src.services.runmode import resolve_run_mode

    mode = resolve_run_mode(get_settings())
    return {
        "turn": state.step_index,
        "searched_sources": list(state.searched_sources),
        "source_status": {key: str(value) for key, value in state.source_status.items()},
        "evidence_active": len(state.active_evidence()),
        "gaps": len(state.gaps),
        "no_progress_streak": state.no_progress_streak,
        # Lấy nguyên ``BudgetState.model_dump()`` để trường ngân sách mới tự vào nhật ký, không
        # phải sửa tay ở đây (bản liệt kê tay trước đây thiếu ``max_llm_calls``,
        # ``max_input_tokens`` và ``max_output_tokens``).
        "budget": state.budget.model_dump(),
        "mode": mode.as_event_payload(),
    }


# --------------------------------------------------------------------------------------
# Node: stop_or_continue
# --------------------------------------------------------------------------------------


def stop_or_continue_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    stop = gstate.get("stop")
    if stop is None or not stop.should_stop:
        stop = evaluate_stop(state)

    if not stop.should_stop:
        return {"investigation": state, "stop": stop}

    checkpoint = (
        CheckpointKind.NORMALIZATION
        if state.checkpoint is CheckpointKind.NORMALIZATION
        else CheckpointKind.ASSESSMENT
    )
    next_stage = "build_dossier" if checkpoint is CheckpointKind.ASSESSMENT else "checklist"
    # Chỉ giữ kết luận đã tính khi dừng vì **đủ bằng chứng** (success). Mọi lý do dừng khác
    # (bão hoà, hết ngân sách, lỗi nguồn) đều hạ kết luận xuống mức của quyết định dừng, để hồ sơ
    # không bao giờ trình bày một kết luận dương tính chưa qua bước tìm phản bác/nguồn thứ hai.
    assessment_status = state.assessment_status or stop.assessment_status
    if stop.reason is not StopReason.SUCCESS:
        assessment_status = stop.assessment_status or AssessmentStatus.INSUFFICIENT_EVIDENCE
    state = state.model_copy(
        update={
            "assessment_status": assessment_status,
            "stop_reason": stop.reason,
        }
    )
    saved = ctx.pause_for_review(
        state,
        checkpoint=checkpoint,
        next_stage=next_stage,
        message=stop.message or f"Chờ reviewer tại {checkpoint}.",
    )
    return {"investigation": saved, "stop": stop}


def route_after_stop(gstate: MvpGraphState) -> str:
    stop = gstate.get("stop")
    return END if (stop is not None and stop.should_stop) else "plan"


# --------------------------------------------------------------------------------------
# Node: build_dossier (nhánh resume sau khi reviewer duyệt kết luận)
# --------------------------------------------------------------------------------------


def build_dossier_node(gstate: MvpGraphState) -> dict[str, Any]:
    state = gstate["investigation"]
    ctx = gstate["ctx"]
    state = ctx.resume(state, next_stage="export")
    builder = ctx.dossier_builder or build_dossier
    dossier = builder(state)
    existing = ctx.store.list_dossiers(state.investigation_id)
    dossier = dossier.model_copy(update={"version": len(existing) + 1, "content_hash": ""})
    # Băm lại sau khi tăng phiên bản để ``content_hash`` luôn khớp bản ghi được lưu.
    dossier = dossier.model_copy(update={"content_hash": content_hash(dossier)})
    ctx.store.save_dossier(dossier)
    saved = ctx.pause_for_review(
        state,
        checkpoint=CheckpointKind.DOSSIER,
        next_stage="export",
        message="Hồ sơ đã tạo — chờ reviewer duyệt để export.",
    )
    ctx.emit(
        saved.investigation_id,
        "dossier",
        f"Tạo hồ sơ phiên bản {dossier.version}",
        {"dossier_id": dossier.dossier_id, "version": dossier.version, "status": str(dossier.status)},
    )
    return {"investigation": saved}


# --------------------------------------------------------------------------------------
# Entry dispatcher
# --------------------------------------------------------------------------------------


def entry_router(gstate: MvpGraphState) -> str:
    """Chạy mới hay tiếp tục từ checkpoint — không reset bộ đếm ngân sách."""
    state = gstate["investigation"]
    if state.next_stage == "build_dossier":
        return "build_dossier"
    if state.normalized_claim is None:
        return "normalize"
    return "checklist"


def route_after_normalize(gstate: MvpGraphState) -> str:
    stop = gstate.get("stop")
    return END if (stop is not None and stop.should_stop) else "checklist"


# --------------------------------------------------------------------------------------
# Graph builder
# --------------------------------------------------------------------------------------


def build_mvp_graph():
    graph = StateGraph(MvpGraphState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("checklist", checklist_node)
    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("extract_assess", extract_assess_node)
    graph.add_node("update_gaps", update_gaps_node)
    graph.add_node("stop_or_continue", stop_or_continue_node)
    graph.add_node("build_dossier", build_dossier_node)

    graph.set_conditional_entry_point(
        entry_router, {"normalize": "normalize", "checklist": "checklist", "build_dossier": "build_dossier"}
    )
    graph.add_conditional_edges("normalize", route_after_normalize, {"checklist": "checklist", END: END})
    graph.add_edge("checklist", "plan")
    graph.add_conditional_edges("plan", route_after_plan, {"retrieve": "retrieve", "stop_or_continue": "stop_or_continue"})
    graph.add_edge("retrieve", "extract_assess")
    graph.add_edge("extract_assess", "update_gaps")
    graph.add_edge("update_gaps", "stop_or_continue")
    graph.add_conditional_edges("stop_or_continue", route_after_stop, {"plan": "plan", END: END})
    graph.add_edge("build_dossier", END)
    return graph.compile()


_MVP_GRAPH = None


def mvp_graph():
    global _MVP_GRAPH
    if _MVP_GRAPH is None:
        _MVP_GRAPH = build_mvp_graph()
    return _MVP_GRAPH


def run_investigation(state: InvestigationState, ctx) -> InvestigationState:  # noqa: ANN001 - RunContext
    """Executor cho ``InProcessRunner``: chạy graph tới khi dừng."""
    scenario = ctx.scenario if ctx.scenario is not None else scenario_for_claim(state.claim.drug, state.claim.event)
    if not ctx.adapters and ctx.source_factory is None:
        ctx.adapters = {source: FixtureAdapter(source, scenario) for source in SOURCE_PRIORITY}
    payload: MvpGraphState = {
        "investigation": state,
        "ctx": ctx,
        "scenario": scenario,
        "decision": None,
        "stop": None,
    }
    result = mvp_graph().invoke(payload, {"recursion_limit": RECURSION_LIMIT})
    return result["investigation"]


# --------------------------------------------------------------------------------------
# Graph mẫu của template (giữ để tương thích ngược)
# --------------------------------------------------------------------------------------

from langgraph.graph import StateGraph as _LegacyStateGraph  # noqa: E402

from src.agents.nodes.example_node import analyze_node, respond_node  # noqa: E402
from src.agents.state import AgentState  # noqa: E402


def should_continue(state: AgentState) -> str:
    """Route based on whether an error occurred during analysis."""
    if state.get("error"):
        return END
    return "respond"


def build_graph() -> _LegacyStateGraph:
    graph = _LegacyStateGraph(AgentState)
    graph.add_node("analyze", analyze_node)
    graph.add_node("respond", respond_node)
    graph.set_entry_point("analyze")
    graph.add_conditional_edges("analyze", should_continue)
    graph.add_edge("respond", END)
    return graph.compile()


agent = build_graph()
