"""So sánh snapshot bất biến theo đoạn và tạo payload review có provenance.

Service này chỉ tạo ``ChangeSet``. Nó không tạo FollowUp/WorkItem; tầng đó chỉ được
nối sau khi contract casework được chốt. Cùng nội dung (cùng hash) không tạo việc.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Literal


@dataclass(frozen=True)
class VersionedDocument:
    source: str
    source_id: str
    version: int
    text: str
    text_sha256: str
    source_url: str = ""
    retrieved_at: str | None = None
    published_date: str | None = None
    effective_time: str | None = None


@dataclass(frozen=True)
class ParagraphChange:
    kind: Literal["added", "removed", "changed"]
    old_paragraph: str | None
    new_paragraph: str | None
    old_index: int | None
    new_index: int | None


@dataclass(frozen=True)
class ChangeSet:
    source: str
    source_id: str
    old_version: int
    new_version: int
    old_hash: str
    new_hash: str
    changed: bool
    requires_review: bool
    review_key: str | None
    reason: str
    changes: tuple[ParagraphChange, ...] = ()
    provenance: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text.strip()) if paragraph.strip()]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate(document: VersionedDocument) -> None:
    if not document.source or not document.source_id:
        raise ValueError("source và source_id là bắt buộc")
    if document.version < 1:
        raise ValueError("version phải >= 1")
    if document.text_sha256 != _hash(document.text):
        raise ValueError("text_sha256 không khớp nội dung snapshot")


def _provenance(document: VersionedDocument) -> dict[str, object]:
    return {
        "version": document.version,
        "sha256": document.text_sha256,
        "source_url": document.source_url,
        "published_date": document.published_date,
        "effective_time": document.effective_time,
        "retrieved_at": document.retrieved_at,
    }


def diff_versions(old: VersionedDocument, new: VersionedDocument) -> ChangeSet:
    """Trả diff theo đoạn; một hash không đổi được coi là không có công việc mới."""

    _validate(old)
    _validate(new)
    if (old.source, old.source_id) != (new.source, new.source_id):
        raise ValueError("Chỉ so sánh hai phiên bản của cùng một nguồn")
    if new.version <= old.version:
        raise ValueError("new.version phải lớn hơn old.version")
    provenance = {
        "old": _provenance(old),
        "new": _provenance(new),
        "compared_at": datetime.now(UTC).isoformat(),
    }
    if old.text_sha256 == new.text_sha256:
        return ChangeSet(
            source=old.source,
            source_id=old.source_id,
            old_version=old.version,
            new_version=new.version,
            old_hash=old.text_sha256,
            new_hash=new.text_sha256,
            changed=False,
            requires_review=False,
            review_key=None,
            reason="content_unchanged",
            provenance=provenance,
        )

    before, after = _paragraphs(old.text), _paragraphs(new.text)
    changes: list[ParagraphChange] = []
    matcher = SequenceMatcher(a=before, b=after, autojunk=False)
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            paired_count = min(old_end - old_start, new_end - new_start)
            for offset in range(paired_count):
                old_index = old_start + offset
                new_index = new_start + offset
                changes.append(ParagraphChange(
                    kind="changed",
                    old_paragraph=before[old_index],
                    new_paragraph=after[new_index],
                    old_index=old_index,
                    new_index=new_index,
                ))
            changes.extend(
                ParagraphChange("removed", before[index], None, index, None)
                for index in range(old_start + paired_count, old_end)
            )
            changes.extend(
                ParagraphChange("added", None, after[index], None, index)
                for index in range(new_start + paired_count, new_end)
            )
        elif tag == "delete":
            changes.extend(ParagraphChange("removed", before[index], None, index, None)
                           for index in range(old_start, old_end))
        elif tag == "insert":
            changes.extend(ParagraphChange("added", None, after[index], None, index)
                           for index in range(new_start, new_end))
    review_key = f"{old.source}:{old.source_id}:{old.text_sha256[:12]}:{new.text_sha256[:12]}"
    return ChangeSet(
        source=old.source,
        source_id=old.source_id,
        old_version=old.version,
        new_version=new.version,
        old_hash=old.text_sha256,
        new_hash=new.text_sha256,
        changed=True,
        requires_review=True,
        review_key=review_key,
        reason="content_changed",
        changes=tuple(changes),
        provenance=provenance,
    )
