# Nội dung pitch dự thảo — VigiLens

Đây là nội dung để dựng deck/video sau khi nhóm chốt sản phẩm và kết quả thật; chưa phải `pitch_deck.pptx` hoặc video.

1. **Bài toán:** chuyên viên cần kiểm tra nhận định thuốc–biến cố và phạm vi bằng chứng từ nhiều nguồn.
2. **Người dùng:** investigator và reviewer; hệ thống hỗ trợ nghiên cứu, không quyết định điều trị.
3. **Giải pháp:** claim → evidence gaps → truy xuất/thay đổi query → kiểm tra scope → human review → dossier có nguồn.
4. **Demo:** bảng lọc, hai cột evidence, nguyên văn/version, form review và 409. Gắn nhãn rõ fixture.
5. **Kiến trúc hiện tại:** VigiLens Next.js → proxy → FastAPI → LangGraph + SQLite runner; các adapter nghiệp vụ đang có fixture fallback. Worker/PostgreSQL của MedReview là luồng kế thừa riêng.
6. **Điều đã kiểm tra:** dùng số thực ở `vigilens/TEST_REPORT.md`; so sánh metric chỉ sau gold/replay handoff.
7. **Phương pháp đánh giá:** keyword BM25, single-shot RAG, agent; corpus/cutoff chung, gold tách biệt, N/A khi chưa đủ dữ liệu.
8. **Giới hạn:** source/model thật, expert labels, session/ownership, agent replay integration và reviewer study chưa nghiệm thu.
9. **Phân công:** Người 1 sources/storage/ops; Người 2 contracts/agent/API; Người 3 evidence/gold; Người 4 UI/eval/docs/demo. Tên thật cần nhóm bổ sung.
10. **Bước tiếp:** bàn giao phụ thuộc, chạy held-out khóa cấu hình, sửa lỗi blocking, nghiệm thu clone sạch rồi quay demo/deploy.

Không dùng kết quả synthetic do chính tác giả tạo để tuyên bố đạt ngưỡng chất lượng, lợi ích lâm sàng hoặc agent hơn baseline.
