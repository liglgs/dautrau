"""Policy an toàn bắt buộc cho mọi output của agent (M01 — mục "policy không nhân quả").

Ba quy tắc cứng:
  1. Không kết luận nhân quả ("X gây Y", "caused by", "leads to", ...).
  2. Không suy diễn tỷ lệ mắc (incidence) từ FAERS hoặc từ báo cáo tự nguyện.
  3. Không dùng trích dẫn ngoài tập tài liệu đã truy xuất.

Module này được runner/validator gọi trước khi lưu hồ sơ hoặc trả output ra API.
"""

from __future__ import annotations

import re

from src.models.schemas import AssessmentStatus

#: Các cụm từ kết luận nhân quả bị cấm (tiếng Việt + tiếng Anh).
CAUSAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bgây\b", re.IGNORECASE),
    re.compile(r"\bdẫn đến\b", re.IGNORECASE),
    re.compile(r"\blà nguyên nhân\b", re.IGNORECASE),
    re.compile(r"\bnguyên nhân (?:là|do)\b", re.IGNORECASE),
    re.compile(r"\bcaused by\b", re.IGNORECASE),
    re.compile(r"\bcauses\b", re.IGNORECASE),
    re.compile(r"\bcausal(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\bleads? to\b", re.IGNORECASE),
    re.compile(r"\bresult(?:s|ed)? in\b", re.IGNORECASE),
    re.compile(r"\bdue to\b", re.IGNORECASE),
)

#: Các cụm từ suy diễn tỷ lệ mắc bị cấm khi nguồn chỉ có báo cáo tự nguyện.
INCIDENCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\btỷ lệ (?:mắc|gặp|phát hiện)\b", re.IGNORECASE),
    re.compile(r"\bincidence\b", re.IGNORECASE),
    re.compile(r"\brisk ratio\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:ca|trường hợp)\s*/\s*100", re.IGNORECASE),
)

#: Trạng thái kết luận được phép xuất bản.
ALLOWED_ASSESSMENT_STATUSES: frozenset[AssessmentStatus] = frozenset(AssessmentStatus)

#: Những nguồn không thể tự mình chống đỡ kết luận ``supported_for_scope``.
WEAK_SOURCES: frozenset[str] = frozenset({"faers"})


class PolicyError(ValueError):
    """Output vi phạm policy an toàn — không được lưu hay trả ra ngoài."""

    def __init__(self, rule: str, detail: str):
        self.rule = rule
        self.detail = detail
        super().__init__(f"{rule}: {detail}")


def find_causal_claims(text: str) -> list[str]:
    """Trả về các cụm từ nhân quả bị cấm xuất hiện trong ``text``."""
    return [pattern.pattern for pattern in CAUSAL_PATTERNS if pattern.search(text)]


def find_incidence_claims(text: str) -> list[str]:
    return [pattern.pattern for pattern in INCIDENCE_PATTERNS if pattern.search(text)]


def assert_no_causal_claim(text: str) -> None:
    hits = find_causal_claims(text)
    if hits:
        raise PolicyError("no_causal_claim", f"Phát hiện cụm từ nhân quả: {hits}")


def assert_no_incidence_inference(text: str, sources: set[str]) -> None:
    """Chỉ cho phép nói tới tỷ lệ khi có ít nhất một nguồn không phải báo cáo tự nguyện."""
    if sources and sources <= WEAK_SOURCES:
        hits = find_incidence_claims(text)
        if hits:
            raise PolicyError("no_incidence_from_spontaneous_reports", f"Phát hiện suy diễn tỷ lệ: {hits}")


def assert_citations_retrieved(citations: list[str], retrieved_doc_ids: set[str]) -> None:
    outside = [citation for citation in citations if citation not in retrieved_doc_ids]
    if outside:
        raise PolicyError("citations_must_be_retrieved", f"Trích dẫn ngoài tập đã truy xuất: {outside}")


def assert_supported_needs_strong_source(assessment_status: AssessmentStatus, sources: set[str]) -> None:
    """FAERS-only không bao giờ được tự động kết luận ``supported_for_scope``."""
    if assessment_status is AssessmentStatus.SUPPORTED_FOR_SCOPE and sources and sources <= WEAK_SOURCES:
        raise PolicyError("no_supported_from_faers_only", "Chỉ có FAERS thì không được kết luận supported")
