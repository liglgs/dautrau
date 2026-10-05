# Phiếu giao việc vòng hai — Người 2

Đề xuất ngày 05/10/2026. Bản trích để nhận việc; cập nhật kế hoạch tại [báo cáo chính](../NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). Đọc thêm mục 16–18 trong báo cáo để biết handoff, thứ tự tích hợp và ba mức nghiệm thu. A = DI/tiếp nhận ADR ngắn; B = ca ADR đầy đủ; C = cập nhật/tái sử dụng. B/C phụ thuộc dữ liệu/SOP/reviewer; không chặn lát cắt A.

### 15.2 Người 2 — bạn: agent, contract, backend và tích hợp

#### R2-2-01 — Chốt contract nhỏ cho lát cắt DI [A; ưu tiên đầu tiên]

- **Làm:** cùng 1/3/4 chốt RequestContext, WorkItem, InvestigationLink, EvidenceBundle, ProfessionalResponse, FollowUp và Version/ReviewRef; quy định unknown, draft, lỗi, coverage. Tách status công việc khỏi status chạy agent và status duyệt. Không mở schema ADR/C đầy đủ trong lần chốt đầu.
- **Bàn giao:** `docs/contracts-hospital-v2.md` đề xuất mới, OpenAPI và JSON examples hợp lệ cho tất cả; cập nhật `docs/mvp-contracts.md`/`src/models/schemas.py` khi triển khai thật. Schema mới là additive hoặc có kế hoạch tương thích.
- **Phụ thuộc:** 3 gửi trường/rubric tối thiểu; 4 gửi hành trình và form; 1 gửi provenance/storage constraints. Đây là điểm phối hợp ngắn đầu đợt, không phải yêu cầu 2 viết xong agent.
- **Nghiệm thu:** 1 lưu, 3 xử lý và 4 render cùng examples; ví dụ có unknown/error/abstract-only; generated types đồng bộ; MVP không vỡ. **Review:** 1/3/4 cùng xác nhận contract.

#### R2-2-02 — WorkItem service và API tiếp nhận/làm rõ [A]

- **Làm:** tạo/lưu nháp yêu cầu, gán owner, cập nhật câu hỏi/phạm vi, yêu cầu bổ sung và liên kết investigation. Dùng repository của 1; chưa đủ thông tin vẫn tiếp nhận được. Luồng chuyển trạng thái đề xuất cần chốt với 3/4, không tự ép mọi yêu cầu phải tra cứu mới.
- **Bàn giao:** API hoạt động, examples và error/version semantics cho 4; context object cho runner của 2 và analysis của 3.
- **Phụ thuộc:** `R2-2-01`, storage `R2-1-03` cho persistence thật. Có thể làm service/contract tests với repository tạm cùng interface trước khi migration xong.
- **Nghiệm thu:** sửa scope tạo revision; nhiều investigation vẫn gắn đúng yêu cầu; draft không tự thành câu trả lời; quyền cập nhật/owner đúng. **Review:** 1 lưu trữ, 4 luồng người dùng.

#### R2-2-03 — Planner/agent tìm theo quyết định cần hỗ trợ [A]

- **Làm:** mở planner từ drug/event sang mục đích, chỉ định, setting, comparator và thời gian; ghi kế hoạch tra cứu và coverage. Node của 3 vẫn sở hữu extraction/scope/contradiction; 2 sở hữu graph/state/điều phối. Có điểm người dùng xác nhận mapping/phạm vi khi mơ hồ.
- **Bàn giao:** run context và evidence results cho 3; tiến độ/gaps và cách tiếp tục cho 4. Không tự gán ca nhân quả từ stance của literature.
- **Phụ thuộc:** `R2-2-01/02`; connector `R2-1-04`; interfaces/rubric `R2-3-01/02`. Có thể dựng graph với adapters test ghi nhãn, nhưng live acceptance phải dùng nguồn thật.
- **Nghiệm thu:** giữ comparator/chỉ định của bài; thiếu mapping hỏi xác nhận; source failure ghi gap; kết thúc bằng thiếu dữ liệu có lý do/việc tiếp theo, không bịa kết luận. **Review:** 3 kết quả/phạm vi, 1 source budget.

#### R2-2-04 — Checkpoint người dùng, resume và trạng thái thiếu dữ liệu [A]

- **Làm:** chuyển checkpoint hiện có thành điểm dược sĩ xem/sửa câu hỏi, mapping, bằng chứng và draft; lưu phiên bản xác nhận. Người dùng bổ sung mới phải có quyết định chạy lại phần nào; chống double-submit/retry tạo run trùng.
- **Bàn giao:** API pause/resume/cancel hoặc năng lực tương đương trong kiến trúc hiện tại, version conflict và pending action cho 4.
- **Phụ thuộc:** `R2-2-02/03`; storage/version của 1; coverage/gap của 3. Không yêu cầu thêm worker framework chỉ vì có resume.
- **Nghiệm thu:** restart/retry không mất dữ kiện, không duyệt nhầm version; người dùng thấy việc cần làm; hủy/timeout vẫn giữ bằng chứng đã lấy và phần chưa hoàn thành. **Review:** 1 recovery, 4 thao tác.

#### R2-2-05 — Phiếu phản hồi: draft, sửa, duyệt, xuất [A]

- **Làm:** điều phối generator theo template/rubric của 3; lưu statement/source links và reviewer edits; kiểm quyền, version và trạng thái duyệt trước export theo policy đã chốt. Bản nháp có thể xuất khi nghiệp vụ cho phép nhưng phải ghi nháp.
- **Bàn giao:** Response/Review/Export API cho 4; bản đầu ra có nguồn, phần chưa biết, người chịu trách nhiệm và revision.
- **Phụ thuộc:** nội dung/validator `R2-3-04/05`, storage `R2-1-03`, form/view của 4. Template có thể chuẩn bị trước; không chờ UI mới test được render server.
- **Nghiệm thu:** quote/nguồn đã loại không còn được dùng hợp lệ; đổi scope/nhận định trọng yếu sau duyệt khiến revision mới cần duyệt; bản cũ vẫn truy được; export không tự ghi sent. **Review:** 3 nội dung, 4 bản xem/xuất.

#### R2-2-06 — Theo dõi, chuyển giao và khép công việc [A]

- **Làm:** thêm request bổ sung, hạn nội bộ, người nhận, ghi nhận hành động gửi/nhận/feedback, lý do đóng/mở lại. Hành động gửi thật ngoài hệ thống có thể được người dùng ghi nhận với bằng chứng; chưa tích hợp email thì không giả auto-send.
- **Bàn giao:** FollowUp/Submission APIs và business rules cho 4; storage records cho 1. Không trộn submission status và response approval.
- **Phụ thuộc:** `R2-2-02/05`, storage `R2-1-03`; mẫu nghiệp vụ 3 và màn hình 4.
- **Nghiệm thu:** export≠sent≠received≠closed; chưa có biên nhận thì unknown; reopen giữ lịch sử và lý do; không hardcode hạn pháp lý chưa xác nhận. **Review:** 3 workflow, 4 E2E.

#### R2-2-07 — Quyền, phiên bản và audit phục vụ pilot [A trước dữ liệu nội bộ; B mở rộng]

- **Làm:** dựa auth hiện có, chốt vai người báo/dược sĩ/người duyệt và phạm vi đơn vị; kiểm read/update/review/export server-side; audit sự kiện quan trọng; đồng bộ version conflict. Cấu hình retention/nhận dạng theo lựa chọn đơn vị; không tự tuyên bố tuân thủ hay chữ ký số.
- **Bàn giao:** permission matrix, API denial examples và event schema cho 1 storage/ops, 4 UI, 3 review policy.
- **Phụ thuộc:** BV xác nhận vai/quyền; 1 data policy; 3 approval rules. Có thể kiểm quyền bằng tài khoản synthetic trước khi có dữ liệu thật.
- **Nghiệm thu:** người ngoài phạm vi không đọc được hồ sơ bằng gọi API trực tiếp; UI ẩn nút không thay kiểm quyền; stale revision bị từ chối có cách tải lại. **Review:** 1 deploy/data isolation, 4 permission scenarios.

#### R2-2-08 — Budget, trace và tích hợp lát cắt đầu [A]

- **Làm:** cấu hình provider/model qua gateway, token/request/timeout budget và retry có trần; ghi mode/coverage/error không lộ nội dung ca không cần thiết. Điều phối integration harness cho toàn luồng; mỗi người cung cấp test phần mình. Chỉ chạy rộng hơn khi có thay đổi/failure cần giải quyết.
- **Bàn giao:** run trace đã giảm dữ liệu nhạy cảm, API smoke và checklist tích hợp cho 1/3/4; contract version đang dùng.
- **Phụ thuộc:** 1 nguồn/môi trường; 3 pipeline analysis; 4 client. Trace/harness khung làm song song từ `R2-2-01`.
- **Nghiệm thu:** nguồn/model lỗi không fallback thành kết luận mock trong pilot; quota/timeout giữ kết quả từng phần và gap; cùng SHA/API/data tạo được kết quả để reviewer kiểm. **Review:** 1 vận hành, 3 fidelity, 4 E2E.

#### R2-2-09 — Mở rộng CaseRecord và cập nhật an toàn [B/C; không chặn A]

- **Làm B:** nhiều thuốc, administrations/timeline, lab có đơn vị, observations, case assessments và report revisions. Gọi rubric/validator 3; giữ case causality riêng literature stance. **Làm C:** ChangeSet→ImpactReview→FollowUp, kho phiếu trả lời và revision cần rà soát.
- **Bàn giao:** contract nhỏ riêng B rồi C; case/update APIs cho 1/3/4. Không làm cả hai module trước khi lát cắt A được review.
- **Phụ thuộc:** B cần `R2-1-05`, `R2-3-06`, BV SOP/ca; C cần `R2-1-08`, `R2-3-08`, danh mục. Chuẩn bị contract với synthetic được, nghiệm thu lâm sàng thì chưa.
- **Nghiệm thu:** không tự sinh Naranjo/WHO category khi thiếu dữ kiện; bổ sung cùng ca không thành ca mới; thiếu danh mục không dựng impact; update không tự ghi hành động đã triển khai. **Review:** 3 nghiệp vụ, 1 persistence, 4 giao diện.
