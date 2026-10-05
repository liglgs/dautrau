"""Planner (M05): chọn hành động tiếp theo theo khoảng trống bằng chứng.

Quy tắc chiến lược (planMVPfinal §8 M05):
  * ít kết quả → đổi sang tên hoạt chất / thêm synonym;
  * nhiễu → thêm filter scope (quần thể/liều/đường dùng);
  * thiếu loại bằng chứng → đổi nguồn;
  * chống lặp bằng ``query_fingerprint``: không gọi lại cùng query trên cùng nguồn;
  * chủ động tìm bằng chứng phản bác (contrary evidence) trước khi kết luận.
"""

from __future__ import annotations

import hashlib

from src.models.schemas import (
    GapKind,
    InvestigationState,
    NormalizedClaim,
    PlannerActionKind,
    PlannerDecision,
    Stance,
)
from src.services.budget import can_spend

#: Thứ tự ưu tiên nguồn khi chưa có thông tin gì.
SOURCE_PRIORITY: tuple[str, ...] = ("pubmed", "dailymed", "faers")

#: Loại bằng chứng "mạnh" không thể chỉ đến từ FAERS.
STRONG_EVIDENCE_SOURCES: frozenset[str] = frozenset({"pubmed", "dailymed"})


def normalize_query(text: str) -> str:
    return " ".join(text.casefold().split())


def query_fingerprint(source: str, query: str) -> str:
    """Dấu vân tay chống lặp: cùng nguồn + cùng query (đã chuẩn hoá) ⇒ cùng fingerprint."""
    digest = hashlib.sha1(normalize_query(query).encode("utf-8")).hexdigest()[:16]
    return f"{source}:{digest}"


def ingredient_query(claim: NormalizedClaim) -> str:
    parts = [claim.drug_ingredient, claim.event_term]
    for synonym in claim.drug_synonyms[:2]:
        if synonym.casefold() != claim.drug_ingredient.casefold():
            parts.append(synonym)
            break
    return " ".join(parts)


def scope_query(claim: NormalizedClaim) -> str:
    parts = [claim.drug_ingredient, claim.event_term]
    for value in (claim.population, claim.dose, claim.route):
        if value:
            parts.append(value)
    return " ".join(parts)


def contrary_query(claim: NormalizedClaim) -> str:
    return f"{claim.drug_ingredient} {claim.event_term} no association not associated"


def label_query(claim: NormalizedClaim) -> str:
    return f"{claim.drug_ingredient} label {claim.event_term}"


def _allowed_sources(state: InvestigationState) -> list[str]:
    return getattr(state.config, "sources", None) or list(SOURCE_PRIORITY)


def _last_source(state: InvestigationState) -> str:
    allowed = _allowed_sources(state)
    for src in reversed(state.searched_sources):
        if src in allowed:
            return src
    return allowed[0] if allowed else SOURCE_PRIORITY[0]


def _candidates(state: InvestigationState) -> list[tuple[str, str, str, str]]:
    """Danh sách ứng viên (source, query, lý do, gap_id) theo thứ tự ưu tiên."""
    claim = state.normalized_claim
    if claim is None:  # pragma: no cover - planner luôn chạy sau normalize
        return []
    candidates: list[tuple[str, str, str, str]] = []
    allowed = _allowed_sources(state)
    first_source = allowed[0] if allowed else SOURCE_PRIORITY[0]

    # 0. Chủ động tìm bằng chứng phản bác ngay khi đã có bằng chứng ủng hộ.
    if _has_supporting_evidence(state) and not contrary_attempted(state):
        candidates.append(("pubmed", contrary_query(claim), "Chủ động tìm bằng chứng phản bác", ""))

    # 0b. Bước đầu tiên dùng nguyên văn tên người dùng cung cấp (kể cả tên thương mại).
    if not state.searched_sources and state.claim.drug.strip().casefold() != claim.drug_ingredient.casefold():
        candidates.append(
            (
                first_source,
                f"{state.claim.drug} {claim.event_term}",
                "Bắt đầu bằng tên người dùng cung cấp",
                "",
            )
        )

    # 1. Khoảng trống ưu tiên cao nhất trước.
    for gap in sorted(state.gaps, key=lambda item: -item.priority):
        if gap.kind is GapKind.NO_RESULTS:
            candidates.append((_last_source(state), ingredient_query(claim), "Ít kết quả → đổi sang tên hoạt chất/synonym", gap.gap_id))
            candidates.append(("dailymed", label_query(claim), "Ít kết quả → đổi nguồn sang nhãn DailyMed", gap.gap_id))
        elif gap.kind is GapKind.MISSING_SOURCE:
            source = gap.field or _next_unsearched_source(state)
            candidates.append((source, ingredient_query(claim), f"Thiếu nguồn {source}", gap.gap_id))
        elif gap.kind is GapKind.MISSING_EVIDENCE:
            if gap.field in {"population", "dose", "route", "time_window"}:
                candidates.append((_last_source(state), scope_query(claim), f"Thiếu thông tin {gap.field} → thêm filter scope", gap.gap_id))
            else:
                source = _next_unsearched_source(state)
                candidates.append((source, ingredient_query(claim), f"Thiếu loại bằng chứng → đổi nguồn {source}", gap.gap_id))
        elif gap.kind is GapKind.SCOPE_MISMATCH:
            candidates.append((_last_source(state), scope_query(claim), "Nhiễu/khác phạm vi → thêm filter scope", gap.gap_id))
        elif gap.kind is GapKind.CONTRADICTION:
            candidates.append(("pubmed", contrary_query(claim), "Cần bằng chứng phản bác để phân xử mâu thuẫn", gap.gap_id))

    # 2. Nguồn chưa từng được gọi.
    for source in allowed:
        if source not in state.searched_sources:
            candidates.append((source, ingredient_query(claim), f"Chưa truy xuất nguồn {source}", ""))

    allowed_set = set(allowed)
    return [c for c in candidates if c[0] in allowed_set]


def _next_unsearched_source(state: InvestigationState) -> str:
    for source in _allowed_sources(state):
        if source not in state.searched_sources:
            return source
    return _last_source(state)


def _has_supporting_evidence(state: InvestigationState) -> bool:
    return any(item.stance is Stance.SUPPORTS for item in state.active_evidence())


def contrary_attempted(state: InvestigationState) -> bool:
    """Truy vấn phản bác đã được chạy chưa (đối chiếu vân tay truy vấn đã lưu)."""
    claim = state.normalized_claim
    if claim is None:
        return False
    return query_fingerprint("pubmed", contrary_query(claim)) in state.queries


def choose_next_action(state: InvestigationState) -> PlannerDecision:
    """Chọn một hành động chưa từng thực hiện; hết chiến lược ⇒ dừng."""
    claim = state.normalized_claim
    if claim is None:  # pragma: no cover
        return PlannerDecision(action=PlannerActionKind.STOP, reason="Claim chưa được chuẩn hoá.")

    if claim.ambiguities:
        return PlannerDecision(
            action=PlannerActionKind.STOP,
            reason="Claim còn mơ hồ (thương mại khớp nhiều hoạt chất) — cần reviewer chốt trước khi truy xuất.",
        )

    ok, reason = can_spend(state.budget, steps=1)
    if not ok:
        return PlannerDecision(action=PlannerActionKind.STOP, reason=f"{reason} — dừng để tạo hồ sơ/abstain.")

    tried = set(state.queries)
    for source, query, why, gap_id in _candidates(state):
        fingerprint = query_fingerprint(source, query)
        if fingerprint in tried:
            continue
        action = PlannerActionKind.SEARCH_SOURCE
        if state.searched_sources:
            action = PlannerActionKind.CHANGE_QUERY if source == _last_source(state) else PlannerActionKind.CHANGE_SOURCE
        return PlannerDecision(
            action=action,
            source=source,
            query=query,
            fingerprint=fingerprint,
            gap_id=gap_id or None,
            reason=why,
        )

    return PlannerDecision(
        action=PlannerActionKind.STOP,
        reason="Đã thử hết query/nguồn khả dụng mà không thu thêm bằng chứng mới.",
    )
