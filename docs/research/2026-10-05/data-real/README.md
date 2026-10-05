# Gói nguồn công khai thật

Thu thập ngày 05/10/2026. Xem `manifest.json` để có URL đầy đủ, params, loại nguồn, thời điểm UTC, trạng thái và SHA-256.

- 18 snapshot được kiểm tra payload/hash; 1 lượt lấy nguồn FDA lỗi 404, không có snapshot PDF. Lượt hợp nhất bổ sung PMID 35799184 để lưu cả nguồn khảo sát dược lâm sàng đã được dẫn trong báo cáo.
- PubMed XML là metadata/abstract thật; không phải full text, dữ liệu bệnh nhân gốc hay nhãn chuyên gia.
- SPL là văn bản nhãn Hoa Kỳ thật; phải kiểm tra đúng sản phẩm, dạng/đường, SETID/version và ngày nội dung. Không phải danh mục hoặc nhãn thuốc bệnh viện Việt Nam.
- Bản tin quốc gia là báo cáo/tài liệu công khai; không phải dữ liệu từng ca của Trung tâm hoặc bệnh viện.
- PDF workflow là bản tác giả tại kho đại học; dùng như nguồn nghiên cứu, không dùng quyền tái sử dụng cho sản phẩm thương mại mà chưa kiểm tra giấy phép.
- Không có hồ sơ bệnh nhân, danh mục thuốc BV, SOP nội bộ, clinical gold hoặc kết quả model live trong gói này.

Hai script ở thư mục cha: `collect_public_sources.py` lấy nhóm nguồn đầu; `prepare_research_packet.py` bổ sung khảo sát và tạo metadata nhãn. Chạy theo thứ tự bằng Python có httpx. Ngày/phiên bản có thể thay đổi khi thu lại; giữ riêng snapshot đánh giá đã chốt.

`label-metadata-and-sections.json` là dữ liệu dẫn xuất từ SPL để kiểm tra phiên bản/section, không phải bản nhãn chính thức thay thế. `*-label-selection.json` chứa các kết quả thật của trang đầu tìm kiếm; phần tử đầu không mặc nhiên phù hợp câu hỏi. Ví dụ index pantoprazole trả bản tiêm trước; nghiên cứu lấy thêm bản viên để thể hiện yêu cầu lựa chọn.

Nhãn ciprofloxacin v3 có lỗi chữ trong mục 5.9. Giữ nguyên snapshot; cần đối chiếu trước sử dụng chuyên môn, không sửa nguyên văn để làm quote hợp lệ.

Manifest không có snapshot toàn văn QĐ 29/QĐ-BYT. Cần bản hướng dẫn/mẫu hiện hành được đầu mối bệnh viện xác nhận trước xây xuất báo cáo.
