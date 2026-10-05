# Kết quả kiểm tra phần chuẩn bị Người 3

**Ngày:** 02/10/2026. **Môi trường kiểm tra:** Python 3.12 trên Windows. Kế hoạch mục tiêu Python 3.11; cần chạy lại gate môi trường đó khi M02 khóa dependencies.

## Các lệnh đã chạy

```powershell
python -m pytest --confcutdir=tests/test_evidence tests/test_evidence/test_mvp_evidence.py -q
python scripts/preview_person3.py
```

- Unit suite: **25 tests passed**; pytest cũng báo **25 subtests passed**. Đây không phải 50 test case độc lập.
- Preview: **20/20 tình huống kỹ thuật synthetic** khớp expected behavior.
- [Raw output](technical-results.json): expected/actual theo ID, fixture hash, dictionary version và mode.
- [Dossier nháp](dossier-synthetic-draft.md): synthetic, pending review, citation entailment pending.
- `git diff --check -- .gitignore`: không có lỗi whitespace. Ngoại lệ Git cho hai tài nguyên authored đã được kiểm tra; snapshots và dữ liệu benchmark khác vẫn ignored.

## Phạm vi được kiểm tra

Normalization exact/ambiguous/unlisted; phạm vi khớp/khác/thiếu/partial/subgroup; contradiction candidate; FAERS và imprecise-null không thành comparative support/contradiction; quote/locator/version/hash; Unicode offsets; preview nháp.

Citation checker chỉ xác minh tính toàn vẹn. Chưa đo entailment, retrieval, precision/recall chuyên môn, thời gian reviewer hoặc lợi ích Agent. Fixture không phải M09 held-out; expected labels do nhóm viết cho test kỹ thuật.

## Gate chưa thực hiện

- Ruff chưa có trong môi trường hiện tại; chưa chạy Ruff lint/format gate.
- Full repository suite chưa chạy: bộ chuẩn bị dùng test độc lập; LangGraph/langchain-openai chưa có trên Python đang dùng. M02 cần hoàn thiện dependency injection và môi trường chung.
- Chưa tích hợp M01 schema, nguồn thật M03, gateway/budget M02/M05, review/version/DB/API M06/M07 hoặc UI M08.
- Chưa được chuyên viên review policy/dictionary/gold labels, chưa nghiệm thu M04/M06/M09.

Xem [hướng dẫn bàn giao](../../docs/person3/README.md) để chốt contract và ghép các bước tiếp theo.
