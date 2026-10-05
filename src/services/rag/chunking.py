"""Chia văn bản tài liệu thành đoạn (chunk) tất định cho RAG.

Quy tắc:
  * cắt theo ranh giới đoạn văn/xuống dòng, không cắt giữa từ;
  * cửa sổ ``chunk_size`` ký tự, chồng lấn ``overlap`` ký tự;
  * mã đoạn = ``{doc_id}#{ordinal:04d}`` và băm nội dung để phát hiện thay đổi.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

CHUNK_SIZE = 1200
OVERLAP = 200


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    ordinal: int
    char_start: int
    char_end: int
    text: str

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def _boundary(text: str, start: int, limit: int) -> int:
    """Chọn điểm cắt gần ``start + limit`` nhất nhưng không vượt quá, ưu tiên ranh giới đoạn."""
    end = min(len(text), start + limit)
    if end >= len(text):
        return len(text)
    window = text[start:end]
    for marker in ("\n\n", "\n", ". "):
        index = window.rfind(marker)
        if index > limit // 3:
            return start + index + len(marker)
    space = window.rfind(" ")
    if space > limit // 3:
        return start + space + 1
    return end


def chunk_text(text: str, doc_id: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[Chunk]:
    body = (text or "").strip()
    if not body:
        return []
    chunks: list[Chunk] = []
    start = 0
    ordinal = 0
    while start < len(body):
        end = _boundary(body, start, chunk_size)
        piece = body[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}#{ordinal:04d}",
                    doc_id=doc_id,
                    ordinal=ordinal,
                    char_start=start,
                    char_end=end,
                    text=piece,
                )
            )
            ordinal += 1
        if end >= len(body):
            break
        start = max(end - overlap, start + 1)
    return chunks
