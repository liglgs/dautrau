# Benchmark tổng hợp VMEC-03

Trạng thái: **completed**. Bộ dữ liệu: `vmec03-synthetic-1`. Nhà cung cấp: `openai_compatible`. Mô hình yêu cầu: `gemini-3.6-flash-high`. ID trả về: `gemini-3.6-flash`.

Đây là kiểm tra hành vi phần mềm trên ca tổng hợp do nhóm tự soạn. Nhãn chưa được bác sĩ duyệt; kết quả không chứng minh an toàn lâm sàng hay tiết kiệm thời gian.

| Chiến lược | Hoàn tất / tổng số | Precision vấn đề micro | Recall vấn đề micro | Đóng sai | Chuyển giao | Lượt gọi | Token | Chi phí USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 30 / 30 | 0.6296 | 0.85 | 0 | 0 | 186 | 141995 | chưa rõ |
| B1 | 30 / 30 | 0.4286 | 0.45 | 0 | 1 | 40 | 154184 | chưa rõ |
| B2 | 30 / 30 | 0.6429 | 0.9 | 0 | 0 | 75 | 73488 | chưa rõ |

| Chiến lược | Độ chính xác trường | Có trích dẫn | Trích dẫn hỗ trợ trường | Tỷ lệ xử lý xong | Câu hỏi lặp | Nguồn đến muộn hiển thị | Thời gian (giây) |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0.9167 (220/240) | 1.0 | 1.0 | 0.0 | 0 | 1.0 | 3632.471 |
| B1 | 0.9667 (232/240) | 1.0 | 1.0 | 0.0 | 0 | 1.0 | 696.013 |
| B2 | 0.9083 (218/240) | 1.0 | 1.0 | 0.0 | 5 | 1.0 | 1054.368 |

Số đếm và mẫu số chi tiết: `vmec03-aggregate.json`. Mọi dòng chưa hoàn tất được giữ trong `vmec03-per-case.jsonl`. Mẫu số bằng 0 được ghi N/A. Chi phí USD chưa rõ nếu chưa cấu hình đơn giá token đã kiểm chứng. Giới hạn chi phí được kiểm tra trước mỗi lượt gọi mới; một lượt vẫn có thể vượt giới hạn vì chưa biết trước số token đầu ra.
