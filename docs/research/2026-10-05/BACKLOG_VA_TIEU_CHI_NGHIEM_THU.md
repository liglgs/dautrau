# Backlog sau MVP — toàn nhóm

Ngày 05/10/2026. Các mục dưới đây là đề xuất, chưa được triển khai. Thứ tự dựa vào nghiên cứu tài liệu và nền MVP; phải hiệu chỉnh bằng pilot.

## Lát cắt 1: một yêu cầu thông tin thuốc được giải quyết E2E

| ID | Feature / câu chuyện người dùng | Dữ liệu / phụ thuộc | Điều kiện nghiệm thu có ý nghĩa |
|---|---|---|---|
| DI-01 | Người hỏi tạo yêu cầu và biết ai nhận việc | Requester, mục đích, khoa, hạn nội bộ, loại việc | Có thể lưu câu hỏi thiếu thông tin; không bị buộc tạo claim nhân quả; lưu được đầu mối và owner |
| DI-02 | Dược sĩ làm rõ câu hỏi và gửi yêu cầu bổ sung | Phạm vi, chỉ định, setting, comparator, nguồn dữ kiện | Người dùng thấy thông tin chưa biết và lý do cần; thông tin bổ sung không ghi đè im lặng câu hỏi ban đầu |
| DAT-01 | Xác nhận thuốc và chọn đúng nhãn | Mã thuốc BV, tên gốc, hoạt chất, dạng/hàm lượng/đường, hãng | Ciprofloxacin otic không tự khớp câu hỏi về uống; nhãn PPI tiêm không làm nhãn mặc định cho viên; mapping chưa xác nhận hiển thị rõ |
| EVI-01 | Đọc bằng chứng theo câu hỏi cụ thể | Engine hiện có; coverage, nguồn/version, study design, indication, comparator | Khi chỉ có abstract, hiển thị abstract-only; failure khác no-results; nguồn lỗi không bị đổi thành bằng chứng phủ định |
| EVI-02 | So sánh kết quả khác nhau một cách có căn cứ | Cửa sổ, quần thể, đối chứng, outcome, estimate/CI và đơn vị | Với PMID 39975698 và 40285433, giữ UTI/ngoại trú và comparator; không tự gọi là direct contradiction của cùng scope; không cộng/đếm bài để kết luận |
| EVI-03 | Kiểm tra từng nhận định của bản trả lời | Statement-to-source, đoạn gốc, loại nội dung fact/inference/gap | Claim có source thật; suy luận chuyên môn được phân biệt; quote lệch/nguồn đã loại không thể dùng như hợp lệ |
| OUT-01 | Tạo phiếu trả lời dễ đọc và duyệt | Mẫu BV đã chốt, câu hỏi, applicability, gap, reviewer | Trang đầu trả lời nhu cầu; chứa phần chưa xác định; không xuất khuyến nghị cá thể khi chưa có bối cảnh cần thiết |
| OUT-02 | Sửa và duyệt có truy vết | Version, người phụ trách, lý do và bản đã duyệt | Sửa scope hoặc nhận định sau duyệt tạo phiên bản cần xem lại; người nhận biết bản nào hiện hành |
| FUP-01 | Phân biệt xuất tệp, chuyển giao và hoàn thành việc | Kênh/đầu mối, hành động thực tế, phản hồi và lý do đóng | Export không tự thành sent; ghi nhận gửi không tự thành received; đóng có lý do, có thể mở lại |
| LIB-01 | Tái sử dụng câu trả lời đúng bối cảnh | Phạm vi, nhãn/version, ngày rà soát, người chịu trách nhiệm | Người dùng biết hồ sơ quá hạn/chờ rà soát; không tái sử dụng kết luận cá thể cho nhóm khác âm thầm |

DI-01 → DI-02 + DAT-01 → EVI-01/02/03 → OUT-01/02 → FUP-01. LIB-01 mở ở mức lưu/tìm hồ sơ trước, workflow cập nhật đầy đủ sau.

## Lát cắt 2: ca nghi ngờ ADR, sau khi có SOP và dữ liệu nội bộ

| ID | Feature | Dữ liệu / phụ thuộc | Điều kiện nghiệm thu |
|---|---|---|---|
| ADR-01 | Phiếu phát hiện ngắn cho người báo | SOP tiếp nhận, đầu mối, mô tả nghi ngờ | Không yêu cầu người báo chứng minh nhân quả; dữ liệu thiếu được giữ; lưu nháp/tiếp nhận được và hiện việc bổ sung |
| ADR-02 | Timeline nhiều thuốc và lab | Thực tế dùng, y lệnh phân biệt, ngày/giờ, đơn vị lab, xử trí | Không biến ngày không biết thành thời điểm giả; nhiều thuốc/các đợt được lưu; nhìn được nguồn dữ kiện |
| ADR-03 | Bảng đánh giá ca và nguyên nhân khác | Checklist chốt với dược sĩ; assessment riêng case | Không gán causality từ literature stance; severity/seriousness tách; chuyên viên chọn kết quả có lý do hoặc chưa đánh giá |
| ADR-04 | Báo cáo nháp theo mẫu hiện hành | Mẫu BV/Trung tâm đã xác nhận, dữ liệu đã kiểm tra | Trường trống vẫn trống; giữ người nhập/nguồn; đánh dấu draft và phiên bản; không gán mã/biên nhận gửi giả |
| ADR-05 | Theo dõi bổ sung và phản hồi | Đầu mối, file gửi, phản hồi thật | Bổ sung liên kết cùng ca; kiểm tra trùng cho người quyết định; lưu lịch sử thay vì tăng số ca vì thêm phiên bản |
| ADR-06 | Xem cụm cùng lô để kiểm tra | Lô/hãng/thời gian/đơn vị và chất lượng dữ liệu | Hiển thị danh sách liên quan và tiêu chí lọc; không tự quy kết lô gây ADR |

ADR-01 có thể làm sớm như cửa tiếp nhận; ADR-02–06 chỉ được pilot chuyên môn với hồ sơ được phép dùng và quy trình cụ thể.

## Lát cắt 3: cập nhật an toàn có tác động địa phương

| ID | Feature | Phụ thuộc | Điều kiện nghiệm thu |
|---|---|---|---|
| UPD-01 | Nguồn mới và diff nội dung | Source type/jurisdiction, retrieval/published/effective dates, hash | Phân biệt mới thu thập với nội dung thay đổi; index nhãn không là nghiên cứu mới; có lịch sử |
| UPD-02 | Đối chiếu danh mục/SOP | DAT-01 và văn bản nội bộ được duyệt | Thiếu danh mục hiện unknown; không dựng thuốc BV bị ảnh hưởng; nhãn Mỹ không mặc định là nhãn Việt Nam |
| UPD-03 | Phiếu tác động và dự thảo bản tin | Kết quả đánh giá, người nhận, người phụ trách | Chuyên viên xem/sửa/duyệt; có giới hạn; hành động sau duyệt được giao và theo dõi |

## Những phần nền để dùng dữ liệu bệnh viện

Quyền theo vai trò và đơn vị, mã ca và giới hạn dữ liệu, truy vết sửa/xem/xuất, lưu trữ và khử định danh phải theo cách đơn vị pilot cho phép. Đây là phụ thuộc thực tế của module ca. Không mở quyền cho toàn nhóm mặc định; không dùng hồ sơ bệnh nhân ngoài phạm vi được cho phép để thử prompt.

## Bộ tình huống nghiệm thu đề xuất

| Tình huống | Loại dữ liệu | Điều phải quan sát |
|---|---|---|
| FQ/động mạch chủ: nghiên cứu UTI vs nghiên cứu comparator khác | PubMed abstract/SPL thật đã lưu | Giữ phạm vi và phương pháp; phân biệt cảnh báo nhãn với kết quả nghiên cứu |
| Pantoprazole: label tiêm mới nhất nhưng câu hỏi về viên | Hai SPL thật | Người dùng chọn/kiểm tra đúng sản phẩm; published_date và effectiveTime khác nhau vẫn rõ |
| Nghi ngờ PPI/hạ magnesi chưa có lab/timeline | Phiếu trống hoặc hồ sơ nội bộ thật còn thiếu | Không dựng bệnh nhân, dữ kiện hoặc điểm nhân quả; đưa ra yêu cầu bổ sung |
| Nguồn FDA 2018 trả 404 | Lỗi HTTP đã ghi trong manifest | Gap nguồn, không coi là bằng chứng phủ định hay đã đọc thông báo |
| Nhãn có lỗi chữ | Nhãn ciprofloxacin thật | Giữ bản gốc, không làm quote “sạch” giả; cho người dùng xem/cần đối chiếu |
| Người báo và dược sĩ cùng cập nhật một ca | Hồ sơ nội bộ được phép hoặc test kỹ thuật gắn nhãn synthetic | Không mất dữ kiện gốc, không đếm bổ sung thành ca mới |
| Bản trả lời đã duyệt sau đó đổi scope | Hồ sơ pilot hoặc test versioning kỹ thuật | Bản cũ vẫn truy được; bản hiện hành cần review; người nhận không bị đưa bản cũ như mới |
| Đã xuất bản báo cáo nhưng chưa gửi | Hồ sơ pilot | Trạng thái vẫn là đã xuất/chờ chuyển; không dựng confirmation |

Test kỹ thuật có thể dùng synthetic ghi nhãn rõ. Test chuyên môn phải có nguồn/hồ sơ thật và reviewer; không tự gán gold. Các ca công khai trên chưa phải benchmark lâm sàng.

## Phân công và phụ thuộc

Phân công đúng bốn vai cũ, từng task, bàn giao và định nghĩa xong nằm tại [báo cáo chính, mục 15–19](../../phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). Không dùng bảng feature này thay cho phân công cá nhân.
