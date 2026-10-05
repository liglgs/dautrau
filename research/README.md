# Benchmark tổng hợp VMEC-03

Thư mục này tách khỏi luồng vận hành FastAPI. Bộ dữ liệu gồm 10 ca phát triển và 30 ca kiểm thử giữ riêng. Tập kiểm thử có sáu nhóm loại trừ nhau, mỗi nhóm năm ca: khớp, đã có lời giải thích, cần phản hồi, mơ hồ, chuyển giao và nguồn đến muộn. Toàn bộ văn bản là dữ liệu tổng hợp; nhãn chưa được bác sĩ thẩm định.

`fixtures.py` lưu nguồn ban đầu, nguồn đến muộn và nhãn chỉ dành cho bộ đánh giá. `public_view` chỉ công bố nguồn có `available_at <= visible_at` và loại mọi nhãn. Bộ chạy dùng hàm này cho cả A, B1 và B2. A dùng mô hình trích xuất, đối chiếu có quy tắc rồi để mô hình chọn hành động kế tiếp. B1 yêu cầu cùng mô hình trả trực tiếp cấu trúc đầu ra từ mỗi trạng thái nguồn đang hiển thị. B2 dùng cùng bước trích xuất và đối chiếu, sau đó tìm ghi chú và đặt câu hỏi/đề xuất theo thứ tự cố định. Benchmark trong bộ nhớ không thay thế quy trình PostgreSQL hay phê duyệt của con người.

## Cách chạy

Từ thư mục gốc của repo, sau khi cài `requirements.txt` và cấu hình `.env` được Git bỏ qua:

```powershell
.venv/Scripts/python.exe -m research.run_benchmark --split dev --strategies A B1 B2 --workers 4 --output eval/results/dev
.venv/Scripts/python.exe -m research.run_benchmark --split test --strategies A B1 B2 --workers 4 --output eval/results/test
```

Tùy chọn `--max-calls N` dừng trước yêu cầu mô hình tiếp theo và đánh dấu các dòng còn lại là chưa hoàn tất. `--max-cost-usd` cần `MODEL_INPUT_USD_PER_MILLION` và `MODEL_OUTPUT_USD_PER_MILLION` đã kiểm chứng trong môi trường; giới hạn được kiểm tra trước mỗi lượt gọi mới, nên một lượt có thể vượt ngưỡng. Khi không có đơn giá, chi phí USD của proxy tùy chỉnh là chưa rõ, nhưng số token và lượt gọi vẫn được báo cáo. Worker và bộ chạy nghiên cứu đều giữ giới hạn công cụ/quyết định riêng cho mỗi lượt.

`--workers` chạy các ca độc lập đồng thời (1–8) và giữ thứ tự dòng đầu ra ổn định. Khi đặt giới hạn lượt gọi hoặc USD, cần `--workers 1` để điểm dừng xác định. Số worker được ghi vào manifest.

Đầu ra gồm `vmec03-manifest.json` (hash bộ dữ liệu/danh mục/prompt, mô hình yêu cầu và ID trả về), `vmec03-per-case.jsonl` (mọi dòng, kể cả thất bại), `vmec03-aggregate.json` (số đếm và mẫu số) và `vmec03-report.md`. Lượt chạy chỉ có trạng thái `completed` khi mọi ca và chiến lược được yêu cầu đều hoàn tất. Lỗi gọi mô hình không bao giờ được thay bằng phản hồi mẫu.

Đây là phép kiểm tra hành vi phần mềm. Kết quả không chứng minh hiệu quả, độ an toàn lâm sàng hay thời gian tiết kiệm của nhân viên. B0 và việc bác sĩ rà nhãn cần người tham gia phù hợp, nằm ngoài lượt chạy tự động.

## Tiêu chí được cố định sau tập phát triển

Lượt chạy phát triển ngày 2026-09-23 hoàn tất 30 dòng chiến lược/ca (111 yêu cầu mô hình). Với **MVP kỹ thuật** này, lượt chạy kiểm thử giữ riêng phải có đủ 90 dòng, gắn nhãn mọi dòng chưa hoàn tất hoặc lỗi mô hình, không lộ nguồn tương lai hay nhãn đánh giá, và không có trường hợp đóng vấn đề khi chưa xác nhận. Mỗi trích dẫn được tạo phải trỏ đến nguồn/phiên bản đã hiển thị và hỗ trợ các trường được nêu. Benchmark công bố precision/recall của vấn đề và độ chính xác trường kể cả khi thấp; không đặt ngưỡng phát hành lâm sàng vì nhãn do nhóm tự soạn chưa được bác sĩ duyệt. Sau khi xem kết quả kiểm thử giữ riêng, không chỉnh prompt, danh mục, dữ liệu hoặc các tiêu chí này.
