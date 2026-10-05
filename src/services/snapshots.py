"""Snapshot store dạng file (M02): bất biến, địa chỉ theo hash, không cache lỗi thành kết quả rỗng.

Đường dẫn sinh từ ``source`` + ``hash`` (không bao giờ từ tên file người dùng gửi).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.models.schemas import SourceDocument, SourceSearchResult, SourceStatus
from src.services.errors import invalid_state


class FileSnapshotStore:
    """Lưu snapshot thô của tài liệu nguồn xuống đĩa, khoá theo hash."""

    def __init__(self, root: str | Path = "data/snapshots"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, document: SourceDocument) -> Path:
        return self.root / document.source / f"{document.hash}.json"

    def save(self, document: SourceDocument) -> str:
        """Lưu snapshot; trả về đường dẫn. Cùng hash ⇒ cùng file (idempotent)."""
        if len(document.hash) < 8:
            raise invalid_state("Tài liệu thiếu hash hợp lệ.", {"doc_id": document.doc_id})
        path = self.path_for(document)
        if path.exists():
            return str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(document.model_dump_json(indent=2), encoding="utf-8")
        return str(path)

    def load(self, path: str | Path) -> SourceDocument:
        return SourceDocument.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))

    def save_search_result(self, result: SourceSearchResult) -> list[str]:
        """Chỉ lưu tài liệu của lượt tìm kiếm THÀNH CÔNG.

        Lỗi/timeout và kết quả rỗng không bao giờ được cache như thể là bằng chứng.
        """
        if result.status is not SourceStatus.OK:
            return []
        return [self.save(document) for document in result.documents]
