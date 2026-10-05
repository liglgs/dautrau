# Kiểm thử UI và xuất Markdown trên nguồn thật

Ngày 2026-10-02, người dùng tự thao tác UI với runtime `metformin / transport`, nguồn là snapshot của bộ `mvp-candidates-50-2026-10-02.zip`.

- Cuộc điều tra: `INV-d136fcc39e15`; hồ sơ bản 2; trạng thái quy trình cuối: `completed`.
- Có 10 tài liệu từ PubMed, DailyMed và FAERS; 16 bản ghi bằng chứng, 14 hoạt động và 2 bị loại.
- Lượt đầu dừng vì `llm_format_error`; thử riêng tài liệu và mở lại bằng `request_more` đã thành công. Đây là một ca đã phục hồi lỗi, không phải bằng chứng mọi phản hồi model đều đúng định dạng.
- Người dùng xem trích dẫn PubMed/DailyMed, duyệt assessment để tạo hồ sơ, duyệt dossier để thử export và gửi file tải xuống.
- File `INV-d136fcc39e15-dossier.md` là bản xuất nguyên gốc. `export-check.json` xác nhận file khớp renderer của hồ sơ đã lưu, content hash khớp, kiểm tra dossier không có lỗi. Các lý do duyệt được giữ trong báo cáo.
- Kết luận vẫn là `insufficient_evidence`, có 12 khoảng trống. `approved` chỉ là trạng thái của thử nghiệm quy trình; không xác nhận nhãn gold, độ chính xác lâm sàng, entailment hoặc nghiệm thu bởi hai reviewer chuyên môn.
- Kiểm tra dựa trên ảnh người dùng, file tải xuống và SQLite đọc chỉ; không dùng tự động hóa trình duyệt, không gọi model thêm khi kiểm tra export.

Đây là bằng chứng kỹ thuật cho một ca development. Chưa thay thế bộ đánh giá heldout, baseline hoặc nghiệm thu chuyên môn.
