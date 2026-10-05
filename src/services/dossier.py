"""Tổng hợp và kiểm tra hồ sơ (dossier) — M05/M06.

Hồ sơ chỉ chứa: claim đã chuẩn hoá, phạm vi áp dụng, bằng chứng kèm trích dẫn,
khoảng trống, hạn chế và kết luận trong phạm vi. Không bao giờ kết luận nhân quả.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from src.models.schemas import (
    AssessmentStatus,
    Dossier,
    DossierSection,
    InvestigationState,
    ReviewStatus,
    ValidationReport,
)
from src.services.errors import dossier_invalid, dossier_not_approved
from src.services.policy import (
    PolicyError,
    assert_citations_retrieved,
    assert_no_causal_claim,
    assert_no_incidence_inference,
    assert_supported_needs_strong_source,
)
from src.services.store import MvpStore

STATUS_LABEL = {
    AssessmentStatus.SUPPORTED_FOR_SCOPE: "Có bằng chứng ủng hộ trong đúng phạm vi claim.",
    AssessmentStatus.CONTRADICTED_FOR_SCOPE: "Có bằng chứng phản bác trong cùng phạm vi.",
    AssessmentStatus.INSUFFICIENT_EVIDENCE: "Chưa đủ bằng chứng để kết luận.",
    AssessmentStatus.SCOPE_MISMATCH: "Bằng chứng hiện có nằm ngoài phạm vi claim.",
    AssessmentStatus.OUT_OF_SCOPE: "Claim nằm ngoài phạm vi hệ thống hỗ trợ.",
    AssessmentStatus.REQUIRES_HUMAN_REVIEW: "Cần người có chuyên môn phân xử.",
}


def _truncate_text(text: str, max_chars: int = 7900) -> str:
    """Cắt ngắn nội dung nếu vượt quá giới hạn ký tự tối đa của schema hồ sơ."""
    if len(text) <= max_chars:
        return text
    truncation_note = "\n... [nội dung đã được rút gọn để đảm bảo kích thước hồ sơ]"
    cutoff = max(0, max_chars - len(truncation_note))
    return text[:cutoff] + truncation_note


def _scope_line(state: InvestigationState) -> str:
    claim = state.claim
    parts = [
        f"thuốc: {claim.drug}",
        f"biến cố: {claim.event}",
        f"quần thể: {claim.population or 'không xác định'}",
        f"liều: {claim.dose or 'không xác định'}",
        f"đường dùng: {claim.route or 'không xác định'}",
        f"cửa sổ thời gian: {claim.time_window or 'không xác định'}",
    ]
    return "; ".join(parts)


def build_dossier(state: InvestigationState, *, actor: str = "agent") -> Dossier:
    """Sinh hồ sơ từ state; nội dung đã qua policy an toàn."""
    evidence = state.active_evidence()
    status = state.assessment_status or AssessmentStatus.INSUFFICIENT_EVIDENCE

    evidence_lines = []
    for item in evidence:
        scope_bits = [f"{key}={value}" for key, value in item.scope.model_dump().items() if value]
        evidence_lines.append(
            f"[{item.evidence_id}] {item.source} · {item.stance} · {item.quote.strip()} "
            f"(nguồn: {item.doc_id}; phạm vi: {', '.join(scope_bits) or 'không xác định'})"
        )

    strategy_lines = [
        f"Nguồn đã truy xuất: {', '.join(state.searched_sources) or 'chưa truy xuất nguồn nào'}",
        f"Số bước đã dùng: {state.budget.steps_used}/{state.budget.max_steps}",
        f"Số truy vấn đã chạy: {len(state.queries)}",
    ]
    strategy_lines.extend(f"- {query}" for query in state.queries)

    sections = [
        DossierSection(title="Claim", body=_truncate_text(state.claim.claim_text), evidence_ids=[]),
        DossierSection(title="Phạm vi áp dụng", body=_truncate_text(_scope_line(state)), evidence_ids=[]),
        DossierSection(
            title="Chiến lược truy xuất",
            body=_truncate_text("\n".join(strategy_lines)),
            evidence_ids=[],
        ),
        DossierSection(
            title="Bằng chứng đã truy xuất",
            body=_truncate_text("\n".join(evidence_lines) if evidence_lines else "Không có bằng chứng nào được truy xuất."),
            evidence_ids=[item.evidence_id for item in evidence],
        ),
        DossierSection(
            title="Khoảng trống bằng chứng",
            body=_truncate_text("\n".join(f"- [{gap.kind}] {gap.description}" for gap in state.gaps) or "Không ghi nhận khoảng trống."),
            evidence_ids=[],
        ),
        DossierSection(
            title="Kết luận trong phạm vi claim",
            body=_truncate_text(STATUS_LABEL.get(status, str(status))),
            evidence_ids=[item.evidence_id for item in evidence],
        ),
    ]

    limitations = [f"Khoảng trống: {gap.description}" for gap in state.gaps]
    if not evidence:
        limitations.append("Chưa thu được bằng chứng nào.")
    if state.stop_reason:
        limitations.append(f"Lý do dừng: {state.stop_reason}")

    summary = _truncate_text(
        f"Kết luận trong phạm vi: {STATUS_LABEL.get(status, str(status))}\n"
        f"Nhật ký kiểm toán: cuộc điều tra {state.investigation_id} (bảng audit_events + review_decisions)\n"
        f"Số đơn vị bằng chứng đang hoạt động: {len(evidence)}; "
        f"bước đã dùng: {state.budget.steps_used}/{state.budget.max_steps}; "
        f"tài liệu đã dùng: {state.budget.documents_used}/{state.budget.max_documents}."
    )

    citations = sorted({item.doc_id for item in evidence})
    dossier = Dossier(
        dossier_id=f"DOS-{uuid4().hex[:10]}",
        investigation_id=state.investigation_id,
        version=1,
        status=ReviewStatus.PENDING,
        assessment_status=status,
        summary=summary,
        sections=sections,
        limitations=limitations,
        gaps=[gap.description for gap in state.gaps],
        citations=citations,
    )
    _assert_policy(dossier, state)
    return dossier.model_copy(update={"content_hash": content_hash(dossier)})


def content_hash(dossier: Dossier) -> str:
    payload = dossier.model_dump_json(exclude={"content_hash", "created_at", "approved_at", "approved_by", "status"})
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


#: Tiêu đề mục chứa nguyên văn claim của người dùng hoặc nguyên văn trích dẫn nguồn.
VERBATIM_SECTION_TITLES = ("Claim", "Phạm vi áp dụng", "Bằng chứng đã truy xuất")


def _assert_policy(dossier: Dossier, state: InvestigationState) -> None:
    # Chỉ soi ngôn ngữ nhân quả ở phần agent tự viết. Claim của người dùng và nguyên văn
    # nguồn (bài báo/nhãn thuốc thường có "due to", "caused by") được giữ nguyên — nếu soi
    # cả phần này thì mọi hồ sơ trích bài báo thật đều bị chặn oan.
    agent_text = "\n".join(
        [dossier.summary, *(section.body for section in dossier.sections if section.title not in VERBATIM_SECTION_TITLES)]
    )
    assert_no_causal_claim(agent_text)
    # Cùng lý do với luật nhân quả: số liệu tỷ lệ nằm trong nguyên văn nguồn là dữ liệu thật
    # của bài báo/nhãn thuốc, không phải suy diễn của agent.
    assert_no_incidence_inference(agent_text, {item.source for item in state.active_evidence()})
    assert_supported_needs_strong_source(dossier.assessment_status, {item.source for item in state.active_evidence()})
    assert_citations_retrieved(dossier.citations, {document.doc_id for document in state.documents})


TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "data" / "templates" / "dossier.md"


def _section_body(section: DossierSection) -> str:
    refs = [ref for statement in section.statements for ref in statement.evidence_refs]
    citations = "\n".join(
        f"- [{ref.evidence_id} v{ref.evidence_version}]({ref.source_url}) "
        f"source={ref.doc_id} v{ref.document_version}; sha256={ref.document_hash}"
        for ref in refs
    )
    return section.body + (f"\n\n{citations}" if citations else "")


def render_markdown(dossier: Dossier) -> str:
    """Sinh Markdown chính thức từ hồ sơ đã duyệt (không gọi LLM).

    Dùng mẫu ``data/templates/dossier.md`` khi có; nếu thiếu mẫu thì rơi về bản dựng
    trong mã để không bao giờ mất dữ liệu.
    """
    if TEMPLATE_PATH.exists():
        sections = "\n\n".join(
            f"## {section.title}\n{_section_body(section)}"
            + (f"\n\nBằng chứng: {', '.join(section.evidence_ids)}" if section.evidence_ids else "")
            for section in dossier.sections
        )
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        return (
            template.replace("{{investigation_id}}", dossier.investigation_id)
            .replace("{{version}}", str(dossier.version))
            .replace("{{status}}", str(dossier.status))
            .replace(
                "{{assessment_status}}",
                STATUS_LABEL.get(dossier.assessment_status, str(dossier.assessment_status)),
            )
            .replace("{{approved_by}}", dossier.approved_by or "chưa duyệt")
            .replace("{{content_hash}}", dossier.content_hash)
            .replace("{{summary}}", dossier.summary)
            .replace("{{sections}}", sections)
            .replace("{{limitations}}", "\n".join(f"- {item}" for item in dossier.limitations))
        )

    lines = [
        f"# Hồ sơ điều tra {dossier.investigation_id} (bản {dossier.version})",
        "",
        f"- Trạng thái: {dossier.status}",
        f"- Kết luận trong phạm vi: {STATUS_LABEL.get(dossier.assessment_status, str(dossier.assessment_status))}",
        f"- Duyệt bởi: {dossier.approved_by or 'chưa duyệt'}",
        f"- Thời điểm duyệt: {dossier.approved_at.isoformat() if dossier.approved_at else '—'}",
        f"- Mã nội dung: `{dossier.content_hash}`",
        "",
        dossier.summary,
        "",
    ]
    for section in dossier.sections:
        lines.append(f"## {section.title}")
        lines.append(_section_body(section))
        if section.evidence_ids:
            lines.append("")
            lines.append(f"Bằng chứng: {', '.join(section.evidence_ids)}")
        lines.append("")
    if dossier.limitations:
        lines.append("## Hạn chế")
        lines.extend(f"- {item}" for item in dossier.limitations)
        lines.append("")
    if dossier.gaps:
        lines.append("## Khoảng trống bằng chứng")
        lines.extend(f"- {item}" for item in dossier.gaps)
        lines.append("")
    if dossier.citations:
        lines.append("## Trích dẫn nguồn")
        lines.extend(f"- {item}" for item in dossier.citations)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_markdown(store: MvpStore, investigation_id: str) -> str:
    """Export Markdown — chỉ khi có phiên bản hồ sơ đã được duyệt **và** còn hợp lệ.

    Kiểm tra lại lần cuối trước khi trả nội dung: nếu bằng chứng/trích dẫn đã đổi so với
    lúc duyệt (ví dụ state bị sửa ngoài luồng review) thì từ chối export.
    """
    dossier = store.approved_dossier(investigation_id)
    if dossier is None:
        raise dossier_not_approved(investigation_id)
    report = validate_dossier(dossier, store.get_state(investigation_id))
    if report.errors:
        raise dossier_invalid(investigation_id, report.errors)
    return render_markdown(dossier)


def validate_dossier(dossier: Dossier, state: InvestigationState) -> ValidationReport:
    """Kiểm tra hồ sơ trước khi cho phép export."""
    errors: list[str] = []
    warnings: list[str] = []
    documents = {document.doc_id: document for document in state.documents}
    retrieved = set(documents)
    active_ids = {item.evidence_id for item in state.active_evidence()}

    try:
        _assert_policy(dossier, state)
    except PolicyError as exc:
        errors.append(f"{exc.rule}: {exc.detail}")

    missing_citations = [citation for citation in dossier.citations if citation not in retrieved]
    if missing_citations:
        errors.append(f"Trích dẫn ngoài tập đã truy xuất: {missing_citations}")

    unknown_evidence = [
        evidence_id
        for section in dossier.sections
        for evidence_id in section.evidence_ids
        if evidence_id not in active_ids
    ]
    if unknown_evidence:
        errors.append(f"Bằng chứng không còn hoạt động: {unknown_evidence}")

    if dossier.assessment_status is AssessmentStatus.INSUFFICIENT_EVIDENCE:
        warnings.append("Hồ sơ kết luận chưa đủ bằng chứng — chỉ dùng như bản ghi nhận khoảng trống.")
    if dossier.gaps:
        warnings.append(f"Hồ sơ còn {len(dossier.gaps)} khoảng trống chưa giải quyết.")
    if not dossier.sections:
        errors.append("Hồ sơ không có nội dung.")

    for item in state.active_evidence():
        document = documents.get(item.doc_id)
        if document is None:
            continue
        if document.text[item.locator.start : item.locator.end] == item.quote:
            continue
        if item.quote in document.text:
            warnings.append(
                f"Bằng chứng {item.evidence_id}: vị trí trích dẫn lệch nhưng nguyên văn vẫn có trong tài liệu."
            )
            continue
        errors.append(
            f"Bằng chứng {item.evidence_id}: nguyên văn không khớp tài liệu nguồn {item.doc_id}."
        )

    if dossier.dossier_id.startswith("DOS-P3-") or any(section.statements for section in dossier.sections):
        from src.services.evidence.dossier import validate_person3_statements

        errors.extend(validate_person3_statements(dossier, state))

    return ValidationReport(ok=not errors, errors=errors, warnings=warnings)
