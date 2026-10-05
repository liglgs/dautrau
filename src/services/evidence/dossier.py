"""Deterministic dossier fallback with evidence/version references and strict validation."""

from __future__ import annotations

from uuid import uuid4

from src.models.schemas import (
    AssessmentStatus,
    Dossier,
    DossierSection,
    DossierStatement,
    EvidenceReference,
    GapKind,
    InvestigationState,
    ReviewStatus,
)
from src.services.evidence.analysis import EvidenceAnalyzer, duplicate_report_candidates
from src.services.evidence.citations import validate_evidence_citation


def build_person3_dossier(state: InvestigationState) -> Dossier:
    from src.services.dossier import STATUS_LABEL, content_hash

    status = state.assessment_status or AssessmentStatus.INSUFFICIENT_EVIDENCE
    documents = {item.doc_id: item for item in state.documents}
    sections = [
        DossierSection(title="Claim", body=state.claim.claim_text),
        DossierSection(title="Phạm vi áp dụng", body="\n".join(
            f"{key}: {value or 'unknown'}" for key, value in state.claim.model_dump().items()
            if key != "claim_text"
        )),
        DossierSection(title="Chiến lược truy xuất", body=(
            f"Sources: {', '.join(state.searched_sources) or 'none'}\n"
            f"Steps: {state.budget.steps_used}/{state.budget.max_steps}\n"
            f"LLM calls: {state.budget.llm_calls}/{state.budget.max_llm_calls}\n"
            + "\n".join(state.queries)
        )[:8000]),
    ]
    for item in state.active_evidence():
        document = documents.get(item.doc_id)
        if document is None:
            raise ValueError(f"Missing source document: {item.doc_id}")
        checked = validate_evidence_citation(document, item)
        if checked.errors:
            raise ValueError(f"Invalid citation {item.evidence_id}: {checked.errors}")
        reference = EvidenceReference(
            evidence_id=item.evidence_id, evidence_version=item.version, doc_id=document.doc_id,
            document_version=document.version, document_hash=document.hash, source_url=document.source_url,
        )
        sections.append(DossierSection(
            title="Bằng chứng đã truy xuất", body=item.quote, evidence_ids=[item.evidence_id],
            statements=[DossierStatement(kind="quote", text=item.quote, evidence_refs=[reference])],
        ))
    if not state.active_evidence():
        sections.append(DossierSection(title="Bằng chứng đã truy xuất", body="No usable evidence retrieved."))
    analysis = EvidenceAnalyzer().analyze(state.evidence, state.normalized_claim) if state.normalized_claim else None
    pairs = [gap for gap in (analysis.gaps if analysis else [])
             if gap.kind in {GapKind.CONTRADICTION, GapKind.SCOPE_MISMATCH}]
    sections.extend([
        DossierSection(title="Phạm vi và mâu thuẫn", body=(
            "\n".join([*(analysis.scope.notes if analysis else []), *(gap.description for gap in pairs)])
            or "No comparable contradiction established."
        )[:8000]),
        DossierSection(title="Khoảng trống bằng chứng", body=(
            "\n".join(gap.description for gap in state.gaps) or "No recorded gaps."
        )[:8000]),
        DossierSection(title="Kết luận trong phạm vi claim", body=STATUS_LABEL[status],
                       evidence_ids=list(state.assessment.evidence_ids) if state.assessment else []),
    ])
    limitations = [f"Stop reason: {state.stop_reason or 'not recorded'}", "Semantic interpretation requires reviewer approval."]
    limitations.extend(f"Excluded evidence retained for audit: {item.evidence_id}" for item in state.evidence if item.excluded)
    for item in state.active_evidence():
        if item.source == "faers":
            limitations.append(f"{item.evidence_id}: spontaneous reports are background; no incidence inference.")
    limitations.extend(f"Possible duplicate FAERS reports (retained): {', '.join(ids)}"
                       for ids in duplicate_report_candidates(state.documents))
    for document in state.documents:
        if document.metadata.get("content_level") == "abstract_only":
            limitations.append(f"{document.doc_id}: abstract only; full study context has not been examined.")
        if document.metadata.get("version_semantics") == "local_collection_version_not_verified_PubMed_revision":
            limitations.append(f"{document.doc_id}: local snapshot version; PubMed record revision is unverified.")
    dossier = Dossier(
        dossier_id=f"DOS-P3-{uuid4().hex[:12]}", investigation_id=state.investigation_id,
        status=ReviewStatus.PENDING, assessment_status=status,
        summary=f"{STATUS_LABEL[status]}\nAudit: {state.investigation_id} / audit_events / review_decisions.",
        sections=sections, limitations=limitations, gaps=[gap.description for gap in state.gaps],
        citations=sorted({item.doc_id for item in state.active_evidence()}),
    )
    return dossier.model_copy(update={"content_hash": content_hash(dossier)})


def validate_person3_statements(dossier: Dossier, state: InvestigationState) -> list[str]:
    """Used by the shared validator at both approval and export, without LLM calls."""
    from src.services.dossier import content_hash

    errors = []
    documents = {item.doc_id: item for item in state.documents}
    evidence = {item.evidence_id: item for item in state.active_evidence()}
    if dossier.investigation_id != state.investigation_id:
        errors.append("Dossier belongs to another investigation")
    if dossier.content_hash != content_hash(dossier):
        errors.append("Dossier content hash mismatch")
    if dossier.assessment_status != state.assessment_status:
        errors.append("Dossier assessment is stale")
    referenced = set()
    for section in dossier.sections:
        if section.evidence_ids and not section.statements and section.title == "Bằng chứng đã truy xuất":
            errors.append("Evidence section needs typed statements with version references")
        if section.statements and section.body != "\n".join(statement.text for statement in section.statements):
            errors.append("Section body differs from its typed statements")
        section_refs = set()
        for statement in section.statements:
            if not statement.evidence_refs:
                errors.append("Statement has no citation")
            if statement.kind != "quote":
                errors.append("Semantic statements require a separate entailment review; only exact quotes supported in this version")
            for ref in statement.evidence_refs:
                item = evidence.get(ref.evidence_id)
                document = documents.get(ref.doc_id)
                section_refs.add(ref.evidence_id)
                referenced.add(ref.doc_id)
                if item is None or document is None or item.doc_id != ref.doc_id:
                    errors.append(f"Citation outside active investigation evidence: {ref.evidence_id}")
                    continue
                if item.version != ref.evidence_version or document.version != ref.document_version or document.hash != ref.document_hash:
                    errors.append(f"Stale evidence/document version: {ref.evidence_id}")
                if ref.source_url != document.source_url:
                    errors.append(f"Source URL mismatch: {ref.evidence_id}")
                if statement.text != item.quote:
                    errors.append(f"Statement is not the cited quote: {ref.evidence_id}")
                checked = validate_evidence_citation(document, item)
                errors.extend(f"{ref.evidence_id}: {issue}" for issue in checked.errors)
        if section.statements and section_refs != set(section.evidence_ids):
            errors.append("Section evidence IDs differ from typed statement references")
    if referenced != set(dossier.citations):
        errors.append("Dossier citations differ from typed statement references")
    if state.normalized_claim and dossier.assessment_status in {
        AssessmentStatus.SUPPORTED_FOR_SCOPE, AssessmentStatus.CONTRADICTED_FOR_SCOPE,
    }:
        analysis = EvidenceAnalyzer().analyze(state.evidence, state.normalized_claim)
        if analysis.assessment.assessment_status != dossier.assessment_status:
            errors.append("Dossier overclaims the applicable evidence")
    return list(dict.fromkeys(errors))
