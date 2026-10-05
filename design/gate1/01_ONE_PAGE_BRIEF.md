# Product Brief — Điều tra bằng chứng an toàn thuốc

Phiên bản: 0.1 · Ngày: 2026-10-02 · Trạng thái: nháp, cần nhóm review.

Nguồn: [MVP](../../docs/planMVPfinal.md), [đề tài gốc](../../docs/spec/SPEC_AI_AGENT_DIEU_TRA_AN_TOAN_THUOC.md). Các mô tả nhu cầu người dùng dưới đây là giả thuyết từ đề tài, chưa có kết quả phỏng vấn xác thực.

## 1. Tóm tắt sản phẩm

Ứng dụng hỗ trợ chuyên viên điều tra một nhận định về một thuốc và một biến cố bất lợi. Agent chủ động xác định bằng chứng còn thiếu, chọn truy vấn và nguồn tiếp theo, kiểm tra phạm vi áp dụng và mâu thuẫn, rồi tạo hồ sơ có đoạn trích và nguồn để con người duyệt.

Giá trị cần chứng minh là vòng điều tra thay đổi theo bằng chứng mới, cùng khả năng giải thích khi chưa đủ dữ liệu. Một lần tìm kiếm và tóm tắt top-k tài liệu chưa chứng minh được giá trị này.

## 2. Vấn đề và hoàn cảnh sử dụng

Reviewer cần ghép thông tin từ literature, nhãn thuốc và báo cáo tự phát. Khó khăn được đề tài đặt ra gồm tìm thiếu bằng chứng phản bác, áp dụng nghiên cứu khác quần thể/liều/đường dùng, coi khác biệt phạm vi là mâu thuẫn, và khó đối chiếu nhận định với đúng đoạn nguồn.

MVP phục vụ nghiên cứu và demo cục bộ bằng tài liệu công khai phù hợp quyền sử dụng hoặc dữ liệu synthetic có nhãn. Đây là giả thuyết sản phẩm cần kiểm chứng bằng việc cho reviewer thực hiện cùng nhiệm vụ thủ công và với prototype.

## 3. Người dùng và nhu cầu

| Người dùng | Công việc cần hoàn thành | Đầu ra mong muốn |
|---|---|---|
| Investigator | Xác định thuốc, biến cố và phạm vi; tạo và theo dõi điều tra | Biết đã tìm gì, còn thiếu gì, vì sao dừng hoặc cần review |
| Reviewer dược/y khoa | Kiểm tra nguồn và khả năng áp dụng; sửa evidence, xử lý ambiguity/mâu thuẫn | Quyết định có lý do, đúng phiên bản, có thể đối chiếu |

Trong demo, hai token theo vai trò là phương tiện kiểm soát truy cập cục bộ, chưa chứng minh danh tính cá nhân. Người có role investigator không được duyệt chỉ vì nhìn thấy hồ sơ.

## 4. Giá trị đề xuất

- Truy xuất thích ứng theo gaps, có lý do cho từng bước tìm tiếp.
- Evidence matrix phân biệt ủng hộ, phản bác, chưa rõ và thông tin nền.
- So khớp phạm vi trước tổng hợp; hiển thị các trường chưa biết.
- Citation tới đoạn trích của đúng phiên bản nguồn đã phân tích.
- Khi thiếu dữ liệu, trả evidence hiện có, gaps, limitations và bước tiếp theo.
- Reviewer giữ quyền xác nhận đánh giá và duyệt hồ sơ chính thức.

## 5. Phạm vi MVP

| Có trong phiên bản đầu | Để sau MVP |
|---|---|
| Một thuốc/hoạt chất và một adverse event mỗi investigation | Điều tra nhiều cặp đồng thời |
| PubMed, DailyMed, openFDA FAERS | ClinicalTrials.gov và regulatory connectors bổ sung |
| Evidence tiếng Anh, UI tiếng Việt là giả định thiết kế | Dịch evidence và literature đa ngôn ngữ |
| SQLite, runner trong backend, một investigation chạy mỗi lần | PostgreSQL, worker riêng, hàng đợi và nhiều người dùng |
| Reviewer checkpoints, dossier Markdown và audit | SSO, phân quyền tổ chức, PDF export |
| Current-data investigation và corpus replay đóng băng | Bảo đảm tái dựng dữ liệu lịch sử |
| Dictionary nhỏ có nguồn; loại trùng kỹ thuật và gắn nghi trùng cơ bản | MedDRA đầy đủ và duplicate detection chuyên sâu |

MVP không cung cấp tư vấn điều trị, kết luận nhân quả tự động hoặc nộp hồ sơ regulatory. Không suy incidence từ số báo cáo FAERS.

## 6. Trải nghiệm cốt lõi

1. Investigator nhập claim, drug, event và scope tùy chọn.
2. Hệ thống kiểm tra input và yêu cầu reviewer xác nhận khi normalization mơ hồ.
3. Agent tìm bằng chứng, kiểm tra scope/contradiction và cập nhật gaps.
4. Timeline cho thấy truy vấn/nguồn thay đổi theo kết quả và ngân sách còn lại.
5. Agent dừng với đề xuất đánh giá hoặc lý do chưa đủ dữ liệu.
6. Reviewer xem nguồn, sửa có lý do, yêu cầu tìm thêm hoặc duyệt đánh giá.
7. Reviewer duyệt dossier hiện hành; người có quyền tải Markdown.

Sửa nội dung liên quan làm mất hiệu lực duyệt cũ. Tiếp tục sau review giữ counters; restart giữa run giữ dữ liệu và đánh dấu interrupted, không tự hứa tiếp tục external call dang dở.

## 7. Thành công được đo như thế nào?

### Điều kiện chứng minh sản phẩm

- Một claim đi hết luồng qua UI; không cần sửa DB hoặc gọi API thủ công.
- Cả ba adapters có live smoke riêng; demo fixture luôn được gắn nhãn.
- Có trace đổi query/nguồn vì gap và có chủ đích tìm evidence phản bác.
- Citation, budget, reviewer gate và invalidation được kiểm tra bằng failure cases.
- Một người khác có thể dựng demo từ clone sạch theo hướng dẫn.

### Mục tiêu nghiên cứu từ kế hoạch

| Metric | Mục tiêu, chưa phải kết quả |
|---|---|
| Evidence Recall@20 | ≥ 0,85 |
| Citation precision | ≥ 0,95 |
| Unsupported-claim rate | ≤ 0,02 |
| Scope-mismatch recall | ≥ 0,80 |
| Dossier có audit và phê duyệt đúng version | 100% |
| Giảm thời gian reviewer | ≥ 25%, chỉ báo khi đã có thử nghiệm phù hợp |

Benchmark dự kiến 20 claim, 5 development và 15 held-out; keyword, RAG một lượt và agent dùng corpus đóng băng có thể đối chiếu. Chưa có gold phù hợp hoặc thử nghiệm reviewer thì ghi chưa đo.

## 8. Giả định và rủi ro cần kiểm chứng

| Giả định/rủi ro | Cách kiểm chứng hoặc xử lý |
|---|---|
| Reviewer cần bố cục evidence matrix hơn giao diện chat | Cho reviewer thực hiện bốn scenario trên wireframe |
| Ba nguồn đủ để chứng minh luồng MVP | Tạo corpus cho các claim; ghi coverage gaps thay vì mở rộng ngầm |
| Có reviewer chuyên môn để gán gold | Xác nhận người tham gia; synthetic chỉ chứng minh kỹ thuật |
| Citation đúng URL nhưng sai ý nghĩa | Kiểm tra quote/locator/hash và statement support |
| Reviewer quá tin đề xuất agent | Tách đề xuất/chưa duyệt; hiển thị contrary evidence và unknowns |
| Nguồn lỗi hoặc hết ngân sách | Giữ evidence đã có, ghi gaps và dừng có lý do |

## 9. Quyết định cần nhóm xác nhận

Xác nhận người dùng thử, tên sản phẩm, ngôn ngữ UI và bố cục desktop. Công cụ đã được xác định là [tt-a1i/archify](https://github.com/tt-a1i/archify); dùng cho sơ đồ luồng/kiến trúc/trạng thái bổ sung trong [workflow](05_WORKFLOW.html). Những điều này chưa thay đổi phạm vi kỹ thuật của kế hoạch MVP.
