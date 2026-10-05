# Benchmark tổng hợp VMEC-03

Trạng thái: **completed**. Bộ dữ liệu: `vmec03-synthetic-1`. Nhà cung cấp: `openai_compatible`. Mô hình yêu cầu: `gemini-3.6-flash-high`. ID trả về: `gemini-3.6-flash`.

Đây là kiểm tra hành vi phần mềm trên ca tổng hợp do nhóm tự soạn. Nhãn chưa được bác sĩ duyệt; kết quả không chứng minh an toàn lâm sàng hay tiết kiệm thời gian.

| Chiến lược | Hoàn tất / tổng số | Precision vấn đề micro | Recall vấn đề micro | Đóng sai | Chuyển giao | Lượt gọi | Token | Chi phí USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 10 / 10 | 0.5 | 0.8571 | 0 | 0 | 73 | 50044 | chưa rõ |
| B1 | 10 / 10 | 0.2857 | 0.2857 | 0 | 0 | 13 | 54990 | chưa rõ |
| B2 | 10 / 10 | 0.5 | 0.8571 | 0 | 0 | 25 | 26967 | chưa rõ |

| Chiến lược | Độ chính xác trường | Có trích dẫn | Trích dẫn hỗ trợ trường | Tỷ lệ xử lý xong | Câu hỏi lặp | Nguồn đến muộn hiển thị | Thời gian (giây) |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0.85 (68/80) | 1.0 | 1.0 | 0.0 | 0 | 1.0 | 1522.214 |
| B1 | 0.9875 (79/80) | 1.0 | 1.0 | 0.0 | 0 | 1.0 | 275.287 |
| B2 | 0.875 (70/80) | 1.0 | 1.0 | 0.0 | 3 | 1.0 | 462.181 |

Số đếm và mẫu số chi tiết: `vmec03-aggregate.json`. Mọi dòng chưa hoàn tất được giữ trong `vmec03-per-case.jsonl`. Mẫu số bằng 0 được ghi N/A. Chi phí USD chưa rõ nếu chưa cấu hình đơn giá token đã kiểm chứng. Giới hạn chi phí được kiểm tra trước mỗi lượt gọi mới; một lượt vẫn có thể vượt giới hạn vì chưa biết trước số token đầu ra.
