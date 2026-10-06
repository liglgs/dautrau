# R2-4-07 — Protocol baseline và trước–sau (mẫu đề xuất)

> **Trạng thái:** protocol/template để chuẩn bị offline; chưa có pilot, người tham gia, dữ liệu bệnh viện, clinical review hay clinical pass.
> **Không dùng để tuyên bố:** hiệu quả lâm sàng, giảm thời gian, accuracy, superiority, năng suất, hoặc độ sẵn sàng triển khai.
> **Mẫu log:** [`templates/evaluation-log.template.json`](templates/evaluation-log.template.json).

## 1. Mục tiêu và nguyên tắc

Mục tiêu giả thuyết là đo một tác vụ chuyên môn tương đương ở điều kiện **trước** (quy trình/biểu mẫu hiện có được đơn vị xác nhận) và **sau** (lát cắt VigiLens được chốt), đồng thời tách phần người tham gia thực sự thao tác khỏi thời gian chờ bên ngoài. Mọi workflow, task, outcome và ngưỡng chấp nhận dưới đây là **giả thuyết cần đơn vị/reviewer xác nhận**.

Protocol này không thay SOP, không hướng dẫn xử trí bệnh nhân, không gán nhân quả, và không biến test kỹ thuật thành thử nghiệm chuyên môn. Chỉ bắt đầu thu dữ liệu hồ sơ bệnh viện sau khi có quyền sử dụng, quy tắc khử định danh/retention, SOP và người có thẩm quyền chấp thuận.

## 2. Đơn vị đo, sample và denominator

| Hạng mục | Định nghĩa đề xuất | Cách báo cáo bắt buộc |
|---|---|---|
| Đơn vị phân tích | một lần thử một tác vụ đã định danh của một người tham gia trong một điều kiện (`before` hoặc `after`) | `task_attempt_id`; không suy ra số ca bệnh nhân từ số attempt |
| Cặp trước–sau | cùng người, cùng loại tác vụ và dữ kiện tương đương hoặc bộ case đã cân bằng, khi đơn vị xác nhận thiết kế paired | báo `n_paired`; không ghép cặp thì báo hai mẫu độc lập và không gọi là paired |
| Sample đã mời | số người/tác vụ được mời theo nguồn dữ liệu | `n_invited` theo từng `data_source` |
| Sample bắt đầu | attempt có `started_at` | `n_started / n_invited`; lý do không bắt đầu nếu biết |
| Mẫu đủ điều kiện phân tích | attempt đạt điều kiện định trước, có timestamp hợp lệ và nguồn dữ liệu phù hợp | `n_eligible / n_started`; ghi từng lý do loại trừ |
| Hoàn thành | người tham gia đạt tiêu chí completion đã được chuyên gia/SOP xác nhận cho loại tác vụ | `n_completed / n_eligible`; chưa có tiêu chí thì `N/A`, không tự đánh dấu complete |
| Chất lượng/rubric | điểm hoặc nhãn rubric do reviewer độc lập cung cấp | `n_rubric_scored / n_eligible`; rubric thiếu thì `N/A` |
| Thời gian | median/IQR và phân bố khi có sample; với mẫu nhỏ chỉ báo từng attempt kèm `n` | luôn nêu numerator, denominator, missing và exclusion; không suy rộng từ fixture |

Không có cỡ mẫu hoặc ngưỡng pass cố định trong template. Cỡ mẫu, đơn vị randomization/cân bằng thứ tự, tiêu chí eligibility và định nghĩa completion phải được chốt trước khi thu dữ liệu cùng đầu mối bệnh viện/reviewer. Không dùng % nếu denominator bằng 0; ghi `N/A (0/0)`.

## 3. Đo thời gian: active time khác waiting time

Mỗi attempt ghi các mốc có timezone và các khoảng dừng. Chỉ cộng thời gian khi có bằng chứng timestamp; không bù bằng ước lượng hồi tưởng.

| Loại thời gian | Định nghĩa đề xuất | Được cộng vào | Không được cộng vào |
|---|---|---|---|
| `active_time_seconds` | tổng thời gian người tham gia đang đọc, nhập, quyết định, sửa hoặc duyệt tác vụ | so sánh nỗ lực thao tác trước–sau | chờ nguồn/model/hệ thống, chờ người khác phản hồi, họp không liên quan, nghỉ |
| `waiting_time_seconds` | tổng thời gian attempt bị chờ phản hồi, quyền, nguồn, queue/hệ thống, reviewer hoặc dữ liệu bổ sung | mô tả độ trễ quy trình riêng | active time; không quy waiting time thành năng suất của giao diện |
| `elapsed_time_seconds` | từ `started_at` đến `ended_at` trừ khoảng không thuộc attempt đã ghi | bối cảnh tổng thời gian nếu cách đo nhất quán | không thay thế hai số trên |
| `unclassified_time_seconds` | phần elapsed không phân loại đủ bằng log | báo riêng cùng lý do | không tự cộng vào active/waiting |

Quy tắc kiểm tra: `active + waiting + unclassified <= elapsed`. Nếu không có `ended_at`, các thời gian và completion là `N/A`; attempt vẫn có thể xuất hiện trong denominator started. Nếu một người chuyển sang việc khác nhưng không có bằng chứng dừng/tiếp tục, ghi `unclassified`, không gán active.

## 4. Ba loại nguồn dữ liệu phải tách tuyệt đối

| `data_source` | Được dùng để chứng minh điều gì | Không được dùng để tuyên bố | Yêu cầu tối thiểu trong log |
|---|---|---|---|
| `real_source_snapshot` | khả năng tái lập retrieval/evaluation trên snapshot nguồn công khai/nguồn thật đã có provenance | hành vi người dùng, hiệu quả lâm sàng, pilot bệnh viện | URI/path/ID snapshot, version/hash, cutoff, quyền sử dụng nếu áp dụng |
| `synthetic_technical_fixture` | kiểm tra kỹ thuật, deterministic replay, validation format hoặc demo kỹ thuật | kết quả chuyên môn, clinical pass, hiệu quả thời gian hay trải nghiệm người dùng thật | cờ `synthetic: true`, fixture/model/replay version, tác giả/nguồn sinh, mục đích kỹ thuật |
| `hospital_profile` | quan sát workflow/baseline/pilot với hồ sơ hoặc task đã được đơn vị cho phép | kết quả đại diện bệnh viện khác, clinical pass nếu chưa có clinical review | mã profile/attempt đã khử định danh, quyền/SOP/version, reviewer, mức khử định danh; không ghi PHI vào file repo |

Không gộp ba nguồn trong một numerator/denominator. Báo cáo phải có bảng riêng theo `data_source`; nếu tổng hợp kỹ thuật cần thiết, nêu công thức và giữ cột nguồn để truy nguyên. Repository hiện có fixture synthetic/evaluation replay; điều đó chỉ tạo kết quả kỹ thuật. Mục `hospital_profile` trong template được để trống cho tới khi quyền hợp lệ tồn tại.

## 5. Thiết kế trước–sau giả thuyết

1. **Khóa tác vụ:** chọn loại việc (ví dụ làm rõ yêu cầu DI), tiêu chí completion, dữ kiện được phép, rubric, vai người báo/dược sĩ/người duyệt và cách xử lý tình huống khẩn theo SOP trước khi đo.
2. **Ghi baseline:** người tham gia làm theo công cụ/quy trình hiện hành được đơn vị chỉ định. Ghi active, waiting, missing data, số lần sửa và outcome; không ép dùng workflow giả thuyết.
3. **Ghi điều kiện sau:** cùng scope tác vụ với form/contract/phiên bản VigiLens định danh rõ. Ghi cùng taxonomy lỗi, cùng rubric và mọi lỗi nguồn/API.
4. **Đánh giá độc lập:** reviewer chuyên môn chấm rubric và critical error khi có reviewer đủ điều kiện. AI, fixture author hoặc valid JSON không tự thành gold/reviewer.
5. **Phân tích:** báo cáo theo source, condition và task type; paired chỉ khi có cặp hợp lệ. Nêu missing, loại trừ, learning/order effect, thay đổi SOP/corpus và lỗi hệ thống.

Các bước trên là protocol đề xuất. Không có bước nào hàm ý đã triển khai VigiLens vào bệnh viện hoặc đã thực hiện thử nghiệm.

## 6. Outcome, error và sửa đổi

| Nhóm đo | Dữ liệu tối thiểu | Denominator đề xuất | Trạng thái khi thiếu đầu vào |
|---|---|---|---|
| Hoàn thành task | `completion_status`, lý do không hoàn thành | eligible attempts | `N/A` nếu completion chưa được đơn vị/reviewer định nghĩa |
| Chất lượng | rubric version, reviewer, điểm/nhãn, rationale | attempts được reviewer chấm | `N/A` nếu chưa có rubric/clinical reviewer |
| Critical error | taxonomy, severity do chuyên gia định nghĩa, phát hiện/cách xử lý | attempts đã được kiểm error | `N/A` nếu taxonomy/reviewer chưa chốt |
| Sửa/nhập lại | `revision_count`, loại sửa, ai sửa, timestamp | started hoặc eligible, phải nêu rõ mẫu số | `N/A` nếu không có audit/log đáng tin |
| Nguồn/bằng chứng | coverage, source gaps/errors, phần abstract-only | attempts có lần điều tra | không thay metric này bằng “không có lỗi” |
| Usability/hiểu bước tiếp theo | câu trả lời task-based và ghi chú quan sát | attempts hoàn tất hoạt động quan sát | không dùng điểm thích/không thích thay outcome tác vụ |

Taxonomy lỗi cần tách ít nhất: dữ liệu thiếu/unknown bị suy diễn; scope/route sai; nguồn lỗi so với nguồn rỗng; citation/coverage không đủ; version/conflict; draft bị hiểu là approved; và lỗi hiển thị/không biết bước tiếp theo. Danh sách là giả thuyết để reviewer xác nhận, không phải danh mục clinical error đã chấp thuận.

## 7. Bằng chứng tối thiểu cho báo cáo

Mỗi báo cáo phải nêu:

- mục tiêu, phiên bản protocol/template, ngày chốt và mọi deviation;
- nguồn dữ liệu tách thành ba nhóm ở mục 4, quyền sử dụng và giới hạn;
- sample flow `invited → started → eligible → completed/rubric_scored` với numerator/denominator theo nhóm;
- thời gian active, waiting, elapsed, unclassified tách riêng; quy tắc timestamp và exclusion;
- task, điều kiện before/after, phiên bản UI/API/contract/corpus/runner, và tình trạng nguồn/model;
- rubric/reviewer/clinical-review status; số lỗi/sửa và raw audit reference đã khử định danh;
- missing data, failure, deviation, conflict of interest và điều không thể kết luận.

Mẫu câu giới hạn nên dùng: “Đây là kết quả kỹ thuật trên fixture synthetic”, “chưa có clinical review”, hoặc “chưa thu hospital profile nên chỉ số này là N/A”. Không dùng “pilot pass”, “clinical pass”, “đã giảm thời gian”, “chính xác hơn”, hoặc “sẵn sàng triển khai” nếu không có bằng chứng và thẩm định tương ứng.

## 8. Điều kiện mở thu hospital profile (chưa đạt)

Trước khi ghi một record `hospital_profile`, cần có tối thiểu: đầu mối đơn vị và vai trò được xác nhận; SOP/quy tắc sử dụng dữ liệu; khử định danh và retention; consent/approval theo quy định đơn vị; rubric và người chấm; định nghĩa task/completion/error; cách xử lý sự cố; và nơi lưu dữ liệu được phép. Những điều kiện này hiện **chưa được chứng minh là có** trong repository.

Không commit hồ sơ bệnh viện, định danh cá nhân, nội dung bệnh án, hoặc file phê duyệt vào repository. Chỉ commit template rỗng, tài liệu tổng hợp đã được phép và số liệu đã khử định danh theo chính sách được xác nhận.
