# Đánh giá kỹ thuật VMEC-03

Mọi hồ sơ trong đánh giá này đều là dữ liệu tổng hợp. Nhãn do nhóm tự soạn để kiểm tra hành vi phần mềm, chưa được bác sĩ thẩm định. Báo cáo không chứng minh an toàn lâm sàng, kết quả đánh giá tương tác thuốc hay thời gian nhân viên tiết kiệm được.

## Phương pháp đã cố định

Tập phát triển 10 ca và tập kiểm thử giữ riêng 30 ca thuộc sáu nhóm loại trừ nhau. Mỗi chiến lược nhận cùng mốc hiển thị nguồn và danh mục. A trích xuất bằng chứng, đối chiếu có quy tắc rồi dùng mô hình chọn hành động tiếp theo. B1 yêu cầu mô hình tạo trực tiếp cấu trúc đầu ra tại mỗi trạng thái nguồn đang hiển thị. B2 dùng cùng bước trích xuất/đối chiếu như A, sau đó tìm ghi chú/chọn hành động theo thứ tự cố định. Alias mô hình yêu cầu là `gemini-3.6-flash-high` qua proxy cấu hình tương thích OpenAI; nhà cung cấp trả `gemini-3.6-flash` trong lượt phát triển hoàn tất. Xem [quy trình](../../research/README.md).

Mã, prompt, danh mục, nhãn và tiêu chí kỹ thuật được cố định tại commit `79d57d4` trước khi chạy tập giữ riêng. Manifest của hai tập có cùng hash ca/danh mục/prompt và ID mô hình yêu cầu.

## Tập phát triển

Lượt dev dùng mô hình thật hoàn tất 30/30 dòng A/B1/B2 với 111 yêu cầu mô hình. Số đếm và mẫu số đầy đủ có trong [tổng hợp dev](dev-final/vmec03-aggregate.json), [dòng từng ca](dev-final/vmec03-per-case.jsonl) và [manifest](dev-final/vmec03-manifest.json).

| Chiến lược | Dòng hoàn tất | Precision vấn đề micro | Recall vấn đề micro | Độ chính xác trường | Trích dẫn hỗ trợ | Lượt gọi mô hình |
|---|---:|---:|---:|---:|---:|---:|
| A | 10/10 | 0.5000 | 0.8571 | 0.8500 | 1.0000 | 73 |
| B1 | 10/10 | 0.2857 | 0.2857 | 0.9875 | 1.0000 | 13 |
| B2 | 10/10 | 0.5000 | 0.8571 | 0.8750 | 1.0000 | 25 |

Trên tập dev, A không cải thiện precision hoặc recall vấn đề so với B2 nhưng gọi mô hình nhiều hơn. B1 có độ chính xác trường cao hơn song điểm nhận diện vấn đề thấp hơn. Đây là quan sát từ tập phát triển tổng hợp nhỏ, không phải tuyên bố hiệu năng trong lâm sàng.

## Tập kiểm thử giữ riêng

Lượt chạy cố định trên 30 ca hoàn tất **90/90** dòng chiến lược/ca với **301 yêu cầu mô hình thật**, không có dòng chưa hoàn tất. [Manifest](test-final/vmec03-manifest.json), [JSONL từng ca](test-final/vmec03-per-case.jsonl), [tổng hợp có mẫu số](test-final/vmec03-aggregate.json) và [báo cáo tạo ra](test-final/vmec03-report.md) lưu đầy đủ kết quả. Proxy trả ID `gemini-3.6-flash` cho alias yêu cầu `gemini-3.6-flash-high`.

| Chiến lược | TP/FP/FN vấn đề | Precision micro | Recall micro | Precision macro | Độ chính xác trường | Trích dẫn hỗ trợ | Lượt gọi | Tổng token nhà cung cấp |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 17/10/3 | 0.6296 | 0.8500 | 0.6905 | 220/240 (0.9167) | 1.0000 | 186 | 141,995 |
| B1 | 9/12/11 | 0.4286 | 0.4500 | 0.4250 | 232/240 (0.9667) | 1.0000 | 40 | 154,184 |
| B2 | 18/10/2 | 0.6429 | 0.9000 | 0.7045 | 218/240 (0.9083) | 1.0000 | 75 | 73,488 |

B2 nhỉnh hơn A về precision và recall vấn đề, đồng thời dùng ít lượt gọi và token hơn. A tránh được năm câu hỏi lặp xuất hiện ở B2; B1 trích xuất trường chính xác nhất nhưng recall vấn đề thấp hơn đáng kể. Mọi trích dẫn được tạo đều qua kiểm tra nguồn đã hiển thị và mức hỗ trợ cho trường trong bộ dữ liệu tổng hợp này. A và B2 đều báo sai một số vấn đề ở nhóm ca khớp, nên người duyệt vẫn phải kiểm tra kết quả.

Không chiến lược nào thực sự đóng vấn đề qua xác nhận của người dùng trong benchmark chạy trong bộ nhớ. Vì vậy, số đóng sai bằng 0 **không** chứng minh tỷ lệ đóng an toàn; tỷ lệ xử lý xong bằng 0 do cách thiết kế phép thử. B1 xuất một trạng thái `handed_off` nhưng không có xác nhận của người nhận, nên không tính là chuyển giao được chấp nhận. Kiểm thử API PostgreSQL kiểm tra xác nhận, tiếp nhận, tiếp tục và bản chụp duyệt bất biến; bộ chạy này không thay thế các kiểm thử đó. Kết quả xử lý tác vụ, trường còn thiếu sau phản hồi thật, phút thao tác của người dùng và phút chờ chưa được đo tự động. Nguồn đến muộn xuất hiện đúng mốc hiển thị ở mọi lượt liên quan, nhưng điều đó chưa kiểm chứng việc giữ bản chụp sau phê duyệt.

## Độ trễ đọc API cục bộ

[Phép đo cục bộ](api-latency.json) gửi 20 yêu cầu `GET /api/v1/cases` đã xác thực từ mỗi tài khoản trong năm tài khoản tổng hợp tới demo PostgreSQL. Trên 100 lượt đọc, p50 là 48.680 ms, p95 là 130.615 ms, tối đa 214.422 ms. Tài khoản người tiếp nhận và quản trị có danh sách ca rỗng. Phép đo không gồm thao tác ghi, xử lý mô hình, mạng từ xa hay người dùng lâm sàng; nó chỉ kiểm tra luồng đọc cục bộ theo mục tiêu demo hai giây.

## Giới hạn

Bộ chạy tự động không mô phỏng người đọc B0 và không đếm phút thao tác của bác sĩ. Chi phí USD chưa rõ vì không có đơn giá đã kiểm chứng cho proxy tùy chỉnh; số lượt gọi và token vẫn được lưu. Nghiệm thu của người dùng và thẩm định nhãn cần người tham gia phù hợp; các điểm số này không đại diện cho hai việc đó.
