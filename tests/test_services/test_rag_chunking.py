"""Kiểm thử thuần cho bộ chia đoạn RAG (``src/services/rag/chunking.py``).

Không cần cơ sở dữ liệu, không cần mạng: chỉ kiểm tra các bất biến của đoạn —
mã đoạn tất định, khoảng ký tự trỏ đúng vào văn bản gốc, độ chồng lấn và việc
giữ nguyên dấu tiếng Việt.
"""

from __future__ import annotations

from src.services.rag.chunking import CHUNK_SIZE, OVERLAP, chunk_text

PARAGRAPH = (
    "Bệnh nhân nam 71 tuổi dùng ibuprofen liều cao trong hai tuần, sau đó xuất hiện "
    "xuất huyết tiêu hoá và được nhập viện cấp cứu.\n\n"
)
LONG_TEXT = PARAGRAPH * 40


def test_empty_and_whitespace_text_produce_no_chunks() -> None:
    assert chunk_text("", "tai-lieu:1:1") == []
    assert chunk_text("   \n\t  ", "tai-lieu:1:1") == []


def test_short_text_is_one_chunk_with_exact_offsets() -> None:
    text = "  Tài liệu ngắn về tương tác thuốc.  "
    body = text.strip()

    chunks = chunk_text(text, "tai-lieu:1:1")

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_id == "tai-lieu:1:1#0000"
    assert chunk.ordinal == 0
    assert chunk.text == body
    assert body[chunk.char_start : chunk.char_end] == chunk.text


def test_long_text_keeps_offset_integrity_and_overlap() -> None:
    chunks = chunk_text(LONG_TEXT, "pubmed:1:1")

    assert len(chunks) > 3, "văn bản dài phải bị chia thành nhiều đoạn"
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert [c.chunk_id for c in chunks] == [f"pubmed:1:1#{i:04d}" for i in range(len(chunks))]

    for chunk in chunks:
        # Khoảng ký tự phải trỏ đúng vào văn bản đã lưu, kể cả khi đoạn bị cắt khoảng trắng.
        assert LONG_TEXT[chunk.char_start : chunk.char_end] == chunk.text
        assert chunk.text == chunk.text.strip()

    assert chunks[0].char_start == 0
    # Đoạn cuối kết thúc ở ký tự cuối cùng có nội dung; phần còn lại chỉ là khoảng trắng.
    assert LONG_TEXT[chunks[-1].char_end :].strip() == ""
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.char_start < previous.char_end, "đoạn sau phải chồng lấn đoạn trước"
        assert current.char_start >= previous.char_start + 1, "con trỏ phải luôn tiến"


def test_chunk_size_and_overlap_parameters_are_honoured() -> None:
    chunks = chunk_text(LONG_TEXT, "pubmed:2:1", chunk_size=120, overlap=30)

    assert all(len(c.text) <= 120 for c in chunks)
    assert all(c.char_end - c.char_start <= 120 for c in chunks)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        overlap = previous.char_end - current.char_start
        assert 0 < overlap <= 30 + 1, f"độ chồng lấn {overlap} nằm ngoài khoảng cho phép"


def test_defaults_are_1200_characters_with_200_overlap() -> None:
    assert CHUNK_SIZE == 1200
    assert OVERLAP == 200


def test_vietnamese_diacritics_are_preserved() -> None:
    chunks = chunk_text(LONG_TEXT, "dailymed:1:1", chunk_size=100, overlap=20)
    joined = "".join(c.text for c in chunks)

    assert "xuất huyết tiêu hoá" in joined
    assert "được nhập viện cấp cứu" in joined
    for chunk in chunks:
        assert chunk.text.encode("utf-8").decode("utf-8") == chunk.text


def test_text_hash_is_stable_and_content_dependent() -> None:
    first, second = chunk_text(LONG_TEXT, "pubmed:3:1")[:2]

    assert first.text_sha256 == chunk_text(LONG_TEXT, "pubmed:3:1")[0].text_sha256
    assert first.text_sha256 != second.text_sha256
    assert len(first.text_sha256) == 64
