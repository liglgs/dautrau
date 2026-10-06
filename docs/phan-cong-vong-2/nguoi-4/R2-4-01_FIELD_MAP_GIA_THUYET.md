# R2-4-01 — Field map tiếp nhận và thẩm định (giả thuyết)

> **Trạng thái:** mẫu làm việc đề xuất, chưa triển khai UI/API và chưa quan sát người dùng thật.
> **Contract đối chiếu:** [`docs/contracts-hospital-v2.md`](../../../contracts-hospital-v2.md), nguồn lược đồ là `docs/spec/hospital-v2/schemas.json` tại thời điểm viết.
> **Phạm vi:** lát cắt DI của `hospital-v2`; không phải mẫu báo cáo ADR bệnh viện và không thay SOP.

## 1. Cách dùng và giới hạn

Mọi nhận định về người báo, dược sĩ, người duyệt, thứ tự thao tác, wording và hai bố cục trong tài liệu này là **giả thuyết thiết kế**. Chưa có phỏng vấn, walkthrough, quan sát tác vụ hay dữ liệu bệnh viện thật. Không dùng tài liệu này để tuyên bố người dùng đã hiểu, hoàn thành công việc, thích một bố cục, hay hệ thống đã qua pilot/clinical pass.

Khi có đầu mối bệnh viện, đề xuất kiểm tra giả thuyết bằng một walkthrough trên yêu cầu đã khử định danh hoặc một form trống. Ghi riêng: vai trò, loại việc, trường bị thiếu, cách người tham gia diễn giải wording, lỗi hiểu, số lần phải hỏi lại và bước tiếp theo họ mong đợi. Không ghi định danh bệnh nhân vào log quan sát.

## 2. Vai trò và luồng giả thuyết cần kiểm chứng

| Vai trò giả định | Có thể nhập hoặc xác nhận | Cần thấy để làm bước tiếp theo | Không được giả định |
|---|---|---|---|
| Người báo (bác sĩ, điều dưỡng hoặc dược sĩ khoa) | câu hỏi/mô tả, đầu mối, thời điểm cần phản hồi, thông tin thuốc/biến cố nếu biết | yêu cầu đã được nhận; phần nào thiếu; ai/cách nào có thể hỏi bổ sung | họ biết đánh giá nhân quả, có đủ dữ liệu ca, hoặc phải hoàn thành mọi trường trước khi gửi |
| Dược sĩ DI/PV | làm rõ câu hỏi và phạm vi, xác nhận/giữ unknown, ưu tiên, người phụ trách, nội dung phiếu nháp và việc bổ sung | bối cảnh gốc; phạm vi từng trường; nguồn/bằng chứng, coverage, gap, lỗi nguồn; phiên bản và trạng thái tách biệt | mọi trường candidate là đúng; nguồn tìm được đã đủ; draft là câu trả lời được duyệt |
| Người duyệt | quyết định duyệt/từ chối/yêu cầu sửa và lý do | phiên bản cụ thể, phiếu nháp, bằng chứng/citation, giới hạn, thay đổi trước-sau | đã có thẩm quyền hoặc tiêu chí duyệt cụ thể trước khi đơn vị xác nhận |

**Luồng giả thuyết A — yêu cầu DI:** người báo lưu câu hỏi ngắn → dược sĩ làm rõ phạm vi/unknown → lần điều tra tạo bằng chứng hoặc gap → dược sĩ soạn phiếu nháp → người duyệt quyết định → theo dõi việc bổ sung/khép. Đây chỉ là khung để walkthrough; `hospital-v2` hiện là `proposed_not_implemented`.

**Luồng giả thuyết B — nghi ngờ ADR ngắn:** người báo chỉ ghi quan sát và thông tin liên hệ tối thiểu → dược sĩ xin dữ kiện bổ sung và tạo timeline theo SOP đã được đơn vị xác nhận. `hospital-v2` hiện có lát B `CaseRecord` **đề xuất kỹ thuật, chờ dược sĩ xác nhận**; chưa có API và không phải SOP/case form bệnh viện đã được phê duyệt. Vì vậy không ép người báo nhập toàn bộ dữ kiện ca.

## 3. Field map: người báo nhập gì

Các cột “đối chiếu contract” nêu đúng đường dẫn hiện có. “Không có trường” nghĩa là không được tự nhét dữ liệu vào object có `additionalProperties: false`; chỉ đề xuất theo dõi ngoài contract hoặc chờ contract do owner chốt.

| Nhãn/ý nghĩa đề xuất cho người báo | Bắt buộc trong giả thuyết tiếp nhận | Đối chiếu `hospital-v2` | Cách ghi khi chưa biết / lưu ý |
|---|---|---|---|
| Câu hỏi hoặc mô tả bằng lời người báo | Có | `RequestContext.raw_text`; dược sĩ chốt thành `WorkItem.question` | Không tự viết lại làm thay đổi ý. `raw_text` và `question` đều không rỗng trong contract khi tạo đủ object. |
| Người/đầu mối đã xác thực | Có theo contract, không nhất thiết là ô tự nhập | `RequestContext.requester` (`Actor.id`, `role`, `unit`) | `Actor` phải lấy từ xác thực theo contract, không tin body tự khai; role/unit chỉ hiện khi có. |
| Kênh nhận yêu cầu | Có | `RequestContext.channel`: `web`, `api`, `import`, `email` | Chọn/gán theo kênh thực tế, không suy đoán. |
| Thời điểm tiếp nhận | Có | `RequestContext.received_at` | Máy chủ ghi thời điểm; người báo chỉ sửa khi đơn vị có quy tắc cho phép. |
| Ngôn ngữ | Có | `RequestContext.language`: `vi` hoặc `en` | Không mặc định im lặng nếu không xác định được. |
| Hệ thống/mã tham chiếu nguồn | Không | `RequestContext.source_system.name`, `.record_id`, `.deidentified` | Chỉ ghi khi được phép; `record_id` không phải định danh bệnh nhân. |
| Tệp/URL/text đính kèm | Không | `RequestContext.attachments[].kind`, `.ref`, `.sha256` | Không suy ra nội dung tệp; kiểm quyền/quy tắc lưu trữ trước khi nhận. |
| Mức khẩn/ưu tiên | Có trong giả thuyết triage | `WorkItem.priority`: `routine`, `urgent`, `stat` | Cần đơn vị xác nhận nghĩa và quyền đặt `stat`; không suy ra từ từ ngữ tự do. |
| Thuốc và biến cố/câu hỏi trọng tâm | Có cho `WorkItem.scope` nhưng được phép chưa biết | `scope.drug`, `scope.event` (`ScopeField`) | Mỗi `ScopeField` phải có `value` và `resolution`; chưa biết ghi `value: null`, `resolution: "unknown"`, không dùng chuỗi “chưa rõ”. |
| Quần thể, đường dùng, liều, cửa sổ thời gian, chỉ định, comparator | Không trong giả thuyết tiếp nhận; có thể cần để kết luận | `scope.population`, `.route`, `.dose`, `.time_window`, `.indication`, `.comparator` | Vắng khi chưa hỏi; nếu đã hỏi nhưng chưa có đáp án thì dùng `ScopeField` unknown và thêm `unknowns[]`. |
| Mục đích quyết định/cần dùng câu trả lời để làm gì | Có trong giả thuyết DI | **Không có trường contract hiện tại** | Giữ trong biểu mẫu nghiên cứu/ghi chú ngoài contract; không map nhầm vào `question`. Cần owner contract quyết định trước triển khai. |
| Hạn mong muốn/cần trước khi nào | Có trong giả thuyết DI | **Không có trường contract hiện tại** | Không suy ra SLA/hạn pháp lý; nếu phải theo dõi, cần chốt trường/contract riêng. |
| Loại việc “DI”, “ADR”, “cập nhật an toàn” | Có để định tuyến giả thuyết | **Không có trường contract hiện tại** | Không dùng `labels` như một contract thay thế cho loại việc đã được chốt. |
| Mã ca đã khử định danh; thuốc cùng dùng/nghi ngờ; lần dùng thuốc; timeline, lab, quan sát, đánh giá, bản báo cáo và bổ sung | Không trong tiếp nhận DI ngắn | Lát B đề xuất: `CaseRecord.case_id`, `.medications`, `.administrations`, `.timeline`, `.labs`, `.observations`, `.assessments`, `.report_revisions`, `.supplements`, `.unknowns` | Chỉ xin theo SOP/quyền dữ liệu được xác nhận. Giữ ngày/giờ unknown, lab phải có đơn vị; không lấy dữ kiện từ nguồn công khai để điền ca và không tự gán Naranjo/WHO-UMC. |

## 4. Field map: dược sĩ cần thấy và có thể xác nhận gì

| Thông tin/bước cho dược sĩ theo giả thuyết | Đối chiếu `hospital-v2` | Diễn giải hiển thị bắt buộc theo giả thuyết |
|---|---|---|
| Danh tính yêu cầu, nguyên văn, kênh, thời điểm, ngôn ngữ, tệp và nguồn hệ thống | Toàn bộ `WorkItem.context` / `RequestContext` | Phân biệt nguyên văn (`raw_text`) với câu hỏi đã làm rõ (`question`); không hiển thị dữ liệu không được phép. |
| Câu hỏi đã chốt và phạm vi từng chiều | `WorkItem.question`, `scope.drug/event/population/route/dose/time_window/indication/comparator` | Mỗi chiều phải hiện giá trị cùng `resolution`; candidate/unknown không được trình bày như confirmed. |
| Phần chưa biết và lý do hỏi lại | `WorkItem.unknowns[].field/reason/needs_confirmation/asked_at` | Nêu lý do và việc cần người nào xác nhận, không chỉ badge “thiếu dữ liệu”. |
| Ưu tiên, người phụ trách, ba trạng thái và liên kết chạy | `priority`, `owner`, `work_status`, `run_status`, `review_status`, `investigation_ids` | Ba trạng thái không gộp thành một nhãn; không suy ra đã duyệt từ agent completed. |
| Phiên bản, etag, tạo/cập nhật, quan hệ bản sửa | `version`, `etag`, `created_at`, `updated_at`, `revision_of`, `revision_reason` | Báo conflict/thay đổi thay vì ghi đè; không gọi revision là hồ sơ mới độc lập. |
| Nhãn kỹ thuật | `labels` | Chỉ hiển thị khi nguồn tạo/ý nghĩa đã chốt; không dùng thay mục đích, deadline hoặc clinical classification. |
| Mỗi lần điều tra và lỗi chạy | `InvestigationLink.link_id/work_item_id/investigation_id/purpose/state/run_summary/error/created_at/created_by` | `purpose` là initial/additional/recheck/reproduce; lỗi nguồn/running khác “không có bằng chứng”. |
| Nhận định, item bằng chứng, gap, coverage và lỗi nguồn | `EvidenceBundle.claim/items/gaps/coverage/assessment_status/source_errors/limitations` | Hiện quote + locator + retrieval + scope match. Tách `sources_empty` khỏi `sources_error`; `abstract_only` phải nhìn thấy. Không rút kết luận nhân quả từ bundle. |
| Phiếu phản hồi nháp/duyệt, nội dung từng phần và citation | `ProfessionalResponse.status/sections/assessment_status/coverage/drafted_by/review/approval/supersedes/...` | `draft`/`in_review` không xuất chính thức; mỗi section hiện citation theo `evidence_id` và giới hạn. |
| Việc xin thêm dữ liệu, kiểm lại nguồn, theo dõi, chuyển giao, khép | `FollowUp.kind/status/note/due_at/assignee/created_by/created_at/closed_at/resolution` | `due_at` là hạn việc theo dõi, không phải hạn pháp lý; việc đóng phải có `resolution` khi có. |
| Quyết định duyệt và lý do | `ReviewRef.review_id/entity/entity_id/entity_version/action/reviewer/reason/decided_at/previous_status/new_status` | Cho biết quyết định áp vào entity + version nào; quyền duyệt còn chờ ma trận quyền được xác nhận. |
| Hồ sơ ADR lát B: thuốc, lần dùng, diễn biến, xét nghiệm, quan sát, đánh giá, bản báo cáo và bổ sung | `CaseRecord` và các object lồng `CaseMedication`, `Administration`, `TimelineEvent`, `LabResult`, `CaseObservation`, `CaseAssessment`, `ReportRevision`, `CaseSupplement` | Chỉ hiển thị/lưu với dữ liệu được phép. `record_status` đề xuất không phải clinical pass; assessment `unknown` phải dùng `framework: none`, `value: null`. |

## 5. Kiểm tra độ phủ contract trước khi triển khai

Để tránh bỏ sót field contract trong UI, bảng này liệt kê các field cấp một thuộc các object của lát cắt DI và owner hiển thị/nhập dự kiến. Đây không phải thay đổi schema.

| Object | Field cấp một | Ai tạo/xem theo giả thuyết |
|---|---|---|
| `RequestContext` | `request_id`, `requester`, `channel`, `received_at`, `raw_text`, `language`, `source_system`, `attachments` | Máy chủ/người báo tạo bối cảnh; dược sĩ đọc. |
| `WorkItem` | `work_item_id`, `version`, `etag`, `context`, `question`, `scope`, `unknowns`, `priority`, `owner`, `work_status`, `run_status`, `review_status`, `investigation_ids`, `response_ids`, `follow_up_ids`, `revision_of`, `revision_reason`, `labels`, `created_at`, `updated_at` | Hệ thống tạo định danh/version/thời gian; dược sĩ quản lý câu hỏi/phạm vi/unknown và xem toàn bộ. |
| `InvestigationLink` | `link_id`, `work_item_id`, `investigation_id`, `purpose`, `state`, `run_summary`, `error`, `created_at`, `created_by` | Hệ thống/lần chạy tạo; dược sĩ đọc, có thể yêu cầu `additional`/`recheck` theo API được chốt. |
| `EvidenceBundle` | `bundle_id`, `work_item_id`, `investigation_id`, `created_at`, `claim`, `items`, `gaps`, `coverage`, `assessment_status`, `source_errors`, `limitations` | Pipeline tạo; dược sĩ kiểm tra/đánh dấu theo quyền API. |
| `ProfessionalResponse` | `response_id`, `work_item_id`, `version`, `etag`, `status`, `sections`, `assessment_status`, `coverage`, `drafted_by`, `review`, `approval`, `supersedes`, `created_at`, `updated_at` | Dược sĩ soạn/đọc nháp; người duyệt quyết định theo quyền đã chốt. |
| `FollowUp` | `follow_up_id`, `work_item_id`, `kind`, `status`, `note`, `due_at`, `assignee`, `created_by`, `created_at`, `closed_at`, `resolution` | Dược sĩ/nhóm theo dõi tạo và cập nhật; người báo chỉ thấy phần được phép. |
| `ReviewRef` | `review_id`, `entity`, `entity_id`, `entity_version`, `action`, `reviewer`, `reason`, `decided_at`, `previous_status`, `new_status` | Người duyệt/hệ thống tạo; dược sĩ đọc audit trail. |
| `CaseRecord` | `case_id`, `record_status`, `synthetic`, `medications`, `administrations`, `timeline`, `labs`, `observations`, `assessments`, `report_revisions`, `supplements`, `unknowns` | Lát B chỉ là đề xuất kỹ thuật; dược sĩ xem/xác nhận khi đơn vị cho phép, không có API/UI được hàm ý. |

Các object lồng trong `items`, `coverage`, `gaps`, `source_errors`, `sections` và `CaseRecord` phải được render từ schema, không tự thêm field. Đặc biệt cần giữ `EvidenceItem.quote`, `locator`, `retrieval`, `scope_match`, `quality_flags`; `CoverageReport.documents_retrieved`, `sources_ok`, `sources_empty`, `sources_error`, `abstract_only`; và `ResponseSection.key`, `title`, `text`, `citations`.

Độ phủ lát B ở mức field lồng: `CaseMedication` gồm `medication_id`, `recorded_name`, `role`, `route`, `dose_text`, `unknowns`; `Administration` gồm `administration_id`, `medication_id`, `administered_at`, `dose_text`, `route`, `source`; `TimelineEvent` gồm `event_id`, `kind`, `description`, `occurred_at`, `source`; `LabResult` gồm `lab_id`, `test_name`, `value_text`, `unit`, `reference_range`, `collected_at`, `source`; và `CaseObservation` gồm `observation_id`, `text`, `observed_at`, `source`.

`CaseAssessment` gồm `assessment_id`, `axis`, `framework`, `status`, `value`, `rationale`, `assessed_at`, `assessed_by`; `ReportRevision` gồm `report_revision_id`, `case_id`, `version`, `status`, `created_at`, `summary`, `revision_of`; `CaseSupplement` gồm `supplement_id`, `case_id`, `received_at`, `kind`, `note`, `source`. `PartialDateTime` của các mốc ca giữ rõ phần ngày/giờ unknown theo schema, thay vì bịa mốc đầy đủ.

## 6. Kịch bản walkthrough và tiêu chí ghi nhận (đều là giả thuyết)

1. **Form trống:** nhờ người tham gia mô tả thông tin họ có thể cung cấp cho một yêu cầu DI; ghi trường họ bỏ qua, wording không rõ và dữ liệu họ không được phép đưa vào.
2. **Bàn thẩm định:** cho dược sĩ giả định đọc một `WorkItem` có unknown, `sources_error` và phiếu `draft`; hỏi bước tiếp theo và nội dung nào không được dùng để kết luận.
3. **Theo từng bước:** dùng cùng dữ kiện; kiểm tra liệu người tham gia phân biệt được nhận yêu cầu, làm rõ, đánh giá nguồn, soạn nháp, duyệt và follow-up hay không.

Ghi kết quả bằng mô tả quan sát, không bằng câu hỏi “có thích AI không”. Một lỗi hiểu được coi là tín hiệu cần sửa wording/rubric/contract khi người tham gia diễn giải sai trạng thái, không biết phần thiếu, hoặc không biết bước tiếp theo. Đây là quy tắc ghi nhận đề xuất, không phải kết quả đã đo.

## 7. Câu hỏi còn mở trước khi triển khai

- Đơn vị nào xác nhận vai trò, phạm vi đơn vị và quyền xem/sửa/duyệt?
- Mục đích, deadline và loại việc sẽ nằm ở contract nào thay vì bị nhét vào `labels`?
- SOP nào cho phép nhận dữ liệu ca, và lát B `CaseRecord` đề xuất sẽ được dược sĩ/đơn vị xác nhận hay sửa thế nào?
- Nội dung bắt buộc của `ProfessionalResponse.sections` và rubric chuyên môn nào được người duyệt chấp thuận?
- Hai bố cục có phù hợp với loại việc/vai trò nào sau walkthrough thực tế?

Cho đến khi các câu hỏi này được trả lời bằng bằng chứng quan sát và quyết định của đơn vị, đây chỉ là field map giả thuyết.
