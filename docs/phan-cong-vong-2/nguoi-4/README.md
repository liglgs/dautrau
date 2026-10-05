# Phiếu giao việc vòng hai — Người 4

Đề xuất ngày 05/10/2026. Bản trích để nhận việc; cập nhật kế hoạch tại [báo cáo chính](../NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). Đọc thêm mục 16–18 trong báo cáo để biết handoff, thứ tự tích hợp và ba mức nghiệm thu. A = DI/tiếp nhận ADR ngắn; B = ca ADR đầy đủ; C = cập nhật/tái sử dụng. B/C phụ thuộc dữ liệu/SOP/reviewer; không chặn lát cắt A.

### 15.4 Người 4 — UI, evaluation, pilot và demo

#### R2-4-01 — Quan sát công việc và prototype hai bố cục [A; làm ngay]

- **Làm:** chuẩn bị walkthrough/phỏng vấn theo mục 12, mẫu đo baseline và test hai bố cục: bàn thẩm định/theo bước. Xác định người báo nhập gì và dược sĩ cần thấy gì; giữ màn hình rỗng khi chưa có dữ liệu. Prototype đã có trong packet là điểm khởi đầu, chưa phải UI chính.
- **Bàn giao:** flow, field map, lỗi hiểu/điểm tốn công cho 2 contract, 3 wording/rubric và 1 data inventory. Không dùng câu “thích AI” thay quan sát tác vụ.
- **Phụ thuộc:** không chờ backend mới; dùng packet thật + form trống. Việc quan sát người dùng thật phụ thuộc đầu mối BV, không giả đã phỏng vấn.
- **Nghiệm thu:** phân biệt người báo/dược sĩ/người duyệt; người thử biết bước tiếp theo và phần chưa biết; ghi rõ đâu là giả thuyết. **Review:** 3 nghiệp vụ, 2 khả năng API.

#### R2-4-02 — Công việc của tôi và tiếp nhận nhanh [A]

- **Làm:** mở rộng frontend hiện hành `frontend/`; hàng chờ theo owner/status/next action; form DI và cửa nhận nghi ngờ ADR ngắn; lưu nháp và unknown. Không bắt người báo đi qua màn hình agent hoặc chứng minh causality.
- **Bàn giao:** UI và contract-backed test cases cho 2 API; feedback missing fields cho 3. Có thể làm UI bằng JSON example cố định gắn nhãn development.
- **Phụ thuộc:** contract `R2-2-01`; nối thật cần `R2-2-02/07`. Fixture development giúp bắt đầu, không được nghiệm thu pilot từ mock.
- **Nghiệm thu:** lưu khi chưa đủ thông tin; không dựng count/KPI; không mất nội dung khi API lỗi; biết ai nhận và việc cần bổ sung. **Review:** 2 API/quyền, 3 field relevance.

#### R2-4-03 — Bàn bằng chứng và đối chiếu phạm vi [A]

- **Làm:** bảng study/source/coverage/comparator/estimate/CI/limitations; chọn dòng mở nguồn và đánh giá applicability bên cạnh; distinction nguồn lỗi/no-result/partial. Mapping mơ hồ có bước xác nhận.
- **Bàn giao:** views/inspector và interaction cases cho 2+3; lỗi source rendering cho 1.
- **Phụ thuộc:** contract `R2-2-01`, payload `R2-3-02/03/04`; live API từ `R2-2-03/04`. Layout/source pane làm trên snapshot trước được.
- **Nghiệm thu:** đọc được FQ hai nghiên cứu khác scope; nhãn viên/tiêm rõ; abstract-only không bị ẩn; dẫn nguồn tới đúng đoạn/version. **Review:** 3 interpretation, 2 runtime.

#### R2-4-04 — Phiếu trả lời, sửa và duyệt [A]

- **Làm:** response editor/preview, nguồn từng statement, gaps, revision history, người duyệt; thao tác review/export theo quyền; cảnh báo stale response và nguồn thay đổi. Bố cục bản xuất không làm mất ý nghĩa chuyên môn.
- **Bàn giao:** UI và output sample cho 3 xem nội dung, 2 API integration; trường hợp sửa sau duyệt cho regression.
- **Phụ thuộc:** template `R2-3-05`, API `R2-2-05/07`. Preview có thể làm trước API với examples thống nhất.
- **Nghiệm thu:** người dùng đọc trang đầu hiểu câu trả lời/giới hạn; draft nhìn rõ; đổi nội dung trọng yếu cần duyệt lại; export không hiện như đã gửi. **Review:** 3 chuyên môn, 2 review/version.

#### R2-4-05 — Theo dõi, phản hồi và đóng/mở lại [A]

- **Làm:** next-action list, người cần trả lời, hạn nội bộ, log chuyển giao/nhận/feedback, lý do đóng; thao tác reopen. Thông tin model/token để ở trang kỹ thuật, không lấn màn hình công việc.
- **Bàn giao:** screens/workflow scenarios cho 2 và 3; ghi nhận vấn đề người dùng coi “xong” khác status kỹ thuật.
- **Phụ thuộc:** API `R2-2-06`; mẫu nội dung của 3. Flow/UI skeleton làm song song ngay sau contract.
- **Nghiệm thu:** người dùng phân biệt xuất/gửi/nhận/đóng; thiếu biên nhận không có badge received; công việc chờ bên ngoài có owner/next action; reopen không mất lịch sử. **Review:** 2 state integrity, 3 workflow.

#### R2-4-06 — Generated types, error states và kiểm UI tích hợp [A]

- **Làm:** sinh client types theo OpenAPI của 2, không tự sửa generated output; kiểm quyền/loading/empty/partial/error/conflict/mode; bàn phím và màn hình hẹp; ổn định luồng E2E với real backend và nguồn thật có kiểm soát. Replay/synthetic chỉ kiểm kỹ thuật.
- **Bàn giao:** integration scenarios và lỗi tái lập cho 1/2/3; ghi commit/API/data version. Sửa UI thuộc 4, lỗi API/analysis chuyển đúng owner.
- **Phụ thuộc:** `R2-2-01/02/05/06/07`, môi trường `R2-1-06`; không đợi B/C để kiểm A.
- **Nghiệm thu:** không crash khi thiếu field cho phép; conflict có cách phục hồi; mock mode không bị nhận nhầm là live; thao tác trên màn hình hẹp không mất nội dung/nguồn. **Review:** 2 integration, 3 source presentation.

#### R2-4-07 — Evaluation, pilot, tài liệu và demo [A; baseline chuẩn bị ngay]

- **Làm:** chuẩn bị đo trước/sau, active time và waiting time riêng; đánh giá chất lượng theo rubric 3, lưu lỗi/số lần sửa và khả năng hoàn thành công việc. Tổ chức buổi thử với reviewer thật và báo cáo giới hạn; làm demo một yêu cầu E2E, không ghép clip mock thành bằng chứng pilot.
- **Bàn giao:** protocol/baseline template từ đầu; evaluation report/demo/run instructions khi tích hợp xong; issue list có owner cho cả nhóm.
- **Phụ thuộc:** `R2-3-07` rubric/labels, `R2-2-08` runner, `R2-1-06/07` môi trường; BV/reviewer cho pilot. Không chờ agent để chuẩn bị protocol hoặc thu baseline.
- **Nghiệm thu:** report tách dữ liệu nguồn thật/test synthetic/hồ sơ BV; denominator/sample và thời gian chờ rõ; chưa có clinical review không báo clinical pass; không cam kết accuracy/15 phút thiếu baseline. **Review:** 3 metrics/clinical errors, 1 reproducibility, 2 runner.

#### R2-4-08 — Timeline ADR, mẫu báo cáo và cập nhật an toàn [B/C]

- **Làm B:** nhiều thuốc/lab/timeline, nguyên nhân thay thế, checklist/unknown, mẫu báo cáo nháp, log bổ sung cùng ca. **Làm C:** hàng chờ nguồn đổi, phiếu tác động, kho phản hồi có trạng thái cần rà soát.
- **Bàn giao:** UI theo contract từng lát cắt và E2E scenarios cho 2/3.
- **Phụ thuộc:** B `R2-2-09`, `R2-3-06`, `R2-1-05`; C `R2-1-08`, `R2-3-08`, update APIs. Không tự thêm ROR dashboard hoặc thang causality để lấp màn hình.
- **Nghiệm thu:** timeline không tạo giờ giả; chuyên viên chọn/giải thích assessment; ca bổ sung không tăng ca mới; thiếu danh mục/scope hiện unknown. **Review:** 3 nghiệp vụ, 2 API, 1 data.
