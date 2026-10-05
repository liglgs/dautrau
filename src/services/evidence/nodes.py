"""Person 3 extract/assess node, independent of LangGraph's orchestration package."""

from hashlib import sha256

from src.models.schemas import AssessmentStatus, ErrorCode, EvidenceGap, GapKind, RunStatus, StopDecision, StopReason
from src.services.errors import MvpError
from src.services.evidence.citations import text_hash, validate_evidence_citation


def extract_assess_person3(gstate):
    state, ctx = gstate["investigation"], gstate["ctx"]
    claim = state.normalized_claim
    if claim is None:
        raise ValueError("Normalize the claim before extracting evidence")
    extractor = ctx.extractor
    extractor.bind(state.budget, state.investigation_id)
    evidence = list(state.evidence)
    documents = {document.doc_id: document for document in state.documents}
    # Revalidate saved observations before assessing a changed claim or source.
    for index, item in enumerate(evidence):
        if item.excluded:
            continue
        document = documents.get(item.doc_id)
        if document is None or validate_evidence_citation(document, item).errors:
            excluded = item.model_copy(update={"excluded": True, "version": item.version + 1})
            ctx.store.save_evidence(state.investigation_id, excluded)
            evidence[index] = excluded
    known = {item.evidence_id for item in evidence}
    gaps = [gap for gap in state.gaps if not gap.gap_id.startswith("GAP-P3-")]
    stop = None
    call_start = len(ctx.gateway.ledger.records)
    for document in state.documents:
        suffix = sha256(document.doc_id.encode("utf-8")).hexdigest()[:20]
        if document.hash != text_hash(document.text):
            gaps.append(EvidenceGap(
                gap_id=f"GAP-P3-HASH-{suffix}", kind=GapKind.MISSING_EVIDENCE, field="provenance",
                description=f"Document hash mismatch: {document.doc_id}; extraction blocked.", priority=5,
            ))
            continue
        try:
            units = extractor.extract_evidence(document, claim)
        except MvpError as error:
            if error.code not in {ErrorCode.BUDGET_EXHAUSTED, ErrorCode.LLM_FORMAT_ERROR, ErrorCode.MODEL_UNAVAILABLE}:
                raise
            gaps.append(EvidenceGap(
                gap_id=f"GAP-P3-EXTRACT-{suffix}", kind=GapKind.MISSING_EVIDENCE, field="extraction",
                description=f"{document.doc_id}: {error.code}; no fabricated fallback evidence.", priority=5,
            ))
            stop = StopDecision(
                should_stop=True,
                reason=StopReason.BUDGET_EXHAUSTED if error.code is ErrorCode.BUDGET_EXHAUSTED else StopReason.NEEDS_REVIEW,
                run_status=RunStatus.WAITING_FOR_REVIEW,
                assessment_status=AssessmentStatus.INSUFFICIENT_EVIDENCE,
                message=f"Extraction stopped: {error.code}",
            )
            # Preserve validated observations from completed windows before a
            # later call hits its budget or fails; never fabricate a fallback.
            units = extractor.partial_units.get(document.doc_id, [])
        for item in units:
            if item.evidence_id in known:
                continue
            known.add(item.evidence_id)
            ctx.store.save_evidence(state.investigation_id, item)
            evidence.append(item)
            if item.excluded:
                gaps.append(EvidenceGap(
                    gap_id=f"GAP-P3-CITATION-{item.evidence_id}", kind=GapKind.MISSING_EVIDENCE,
                    field="citation", description=f"Excluded invalid citation: {item.evidence_id}", priority=4,
                ))
        coverage = extractor.coverage.get(document.doc_id, {})
        if not coverage.get("complete", False):
            gaps.append(EvidenceGap(
                gap_id=f"GAP-P3-TRUNCATED-{suffix}", kind=GapKind.MISSING_EVIDENCE,
                field="document", description=(f"{document.doc_id}: examined {coverage.get('examined_chars', 0)}"
                    f"/{len(document.text)} characters in selected windows; unexamined text remains."), priority=3,
            ))
        if stop:
            break
    analysis = ctx.evidence_analyzer.analyze(evidence, claim)
    assessment = analysis.assessment
    if stop:
        assessment = assessment.model_copy(update={
            "assessment_status": AssessmentStatus.INSUFFICIENT_EVIDENCE,
            "rationale": stop.message, "evidence_ids": [],
        })
    gaps.extend(analysis.gaps)
    gaps = [gap.model_copy(update={"created_step": state.step_index}) if gap.gap_id.startswith("GAP-P3-") else gap
            for gap in gaps]
    state = state.model_copy(update={"evidence": evidence, "assessment": assessment,
                                     "assessment_status": assessment.assessment_status, "gaps": gaps})
    saved = ctx.save(state, event=("assess", f"Person 3: {assessment.assessment_status}; {len(evidence)} evidence units"))
    for record in ctx.gateway.ledger.records[call_start:]:
        ctx.emit(saved.investigation_id, "llm", "Person 3 extraction call", record.model_dump())
    result = {"investigation": saved}
    if stop:
        result["stop"] = stop
    return result
