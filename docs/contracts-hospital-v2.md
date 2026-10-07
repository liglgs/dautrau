# Hợp đồng hospital-v2 — lát cắt DI (đề xuất, additive)

> **Task:** R2-2-01 — chốt contract nhỏ cho lát cắt DI. **Người soạn:** Người 2.
> **Trạng thái:** `proposed_not_implemented` — hợp đồng đã viết và kiểm bằng máy, **chưa** nối vào ứng dụng.
> **Nguồn sự thật của lược đồ:** `docs/spec/hospital-v2/schemas.json` (JSON Schema 2020-12).
> **Đoạn OpenAPI:** `docs/spec/hospital-v2/openapi.json` · **Ví dụ:** `docs/spec/hospital-v2/examples/` · **Kiểm thử:** `tests/test_scripts/test_hospital_contract.py`.
> **Căn cứ:** `docs/phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md` §15.2 (R2-2-01), `docs/mvp-contracts.md`.

## 1. Phạm vi và nguyên tắc

Lát A của lần chốt này mở DI (drug–event investigation) và bảy thực thể đi kèm.
Lát B `CaseRecord` ở §9 chỉ là đề xuất kỹ thuật có fixture synthetic, chưa là lược đồ ADR/C
được xác nhận. **Không** đổi lược đồ MVP hiện có.

1. **Additive.** Mọi đường dẫn mới nằm trong `/api/v2`. Lược đồ cũ (`src/models/schemas.py`) giữ nguyên.
   Các enum dùng chung phải **giữ đủ giá trị MVP**; chỉ được thêm giá trị mới (kiểm bằng test đồng bộ).
2. **Ba trạng thái tách biệt.** `work_status` (nghiệp vụ), `run_status` (agent), `review_status` (duyệt)
   là ba trường riêng trên `WorkItem`. Không có trường `status` gộp.
3. **Unknown không tự thành giá trị.** Trường chưa biết ghi `resolution: "unknown"` và vào `unknowns`;
   không suy diễn, không lấy mặc định.
4. **Draft không tự thành câu trả lời.** `ProfessionalResponse.status` chỉ đổi qua endpoint duyệt.
5. **Lỗi nguồn không thành "không có kết quả".** `sources_error` khác `sources_empty`; lỗi ghi vào
   `source_errors` kèm `retryable`, và `assessment_status` không được suy ra từ lỗi.
6. **Không kết luận nhân quả.** `assessment_status` dùng đúng enum của MVP (không có `causal`).
7. **Mọi ghi đều có phiên bản.** `version` + `etag`; sửa bằng `If-Match`; lệch phiên bản trả 409.

## 2. Bảy thực thể

| Thực thể | Vai trò | Trường bắt buộc chính |
|---|---|---|
| `RequestContext` | Ai hỏi, hỏi gì, từ hệ thống nào; không có dữ liệu định danh bệnh nhân | `request_id`, `requester`, `channel`, `received_at`, `raw_text`, `language` |
| `WorkItem` | Yêu cầu điều tra: câu hỏi, phạm vi, người phụ trách, ba trạng thái, liên kết | `work_item_id`, `version`, `context`, `question`, `scope`, `unknowns`, `priority`, ba trạng thái |
| `InvestigationLink` | Nối yêu cầu với một lần chạy điều tra (nhiều liên kết là bình thường) | `link_id`, `work_item_id`, `investigation_id`, `purpose`, `state`, `created_at`, `created_by` |
| `EvidenceBundle` | Bằng chứng của một lần chạy: mục bằng chứng, khoảng trống, bao phủ, lỗi nguồn | `bundle_id`, `work_item_id`, `investigation_id`, `items`, `gaps`, `coverage`, `assessment_status`, `source_errors` |
| `ProfessionalResponse` | Phiếu trả lời chuyên môn (nháp → duyệt) | `response_id`, `work_item_id`, `version`, `status`, `sections`, `assessment_status`, `coverage` |
| `FollowUp` | Việc bổ sung: xin thông tin, chạy lại, theo dõi, chuyển giao, khép việc | `follow_up_id`, `work_item_id`, `kind`, `status`, `note`, `created_at` |
| `VersionRef` / `ReviewRef` | Kiểm soát đồng thời và vết duyệt | `entity`, `id`, `version`, `etag` / `action`, `reviewer`, `decided_at`, trạng thái trước–sau |

Quan hệ: `WorkItem 1—n InvestigationLink`, `WorkItem 1—n ProfessionalResponse`, `WorkItem 1—n FollowUp`,
`InvestigationLink 1—1 EvidenceBundle`. Sửa phạm vi tạo `WorkItem` mới với `revision_of` trỏ bản cũ.

## 3. Ba trạng thái và ma trận chuyển

| `work_status` | Nghĩa | Được chuyển sang |
|---|---|---|
| `draft` | Đã tiếp nhận, còn thiếu thông tin | `accepted`, `cancelled` |
| `accepted` | Đã đủ để chạy | `in_progress`, `awaiting_information`, `cancelled` |
| `in_progress` | Đang chạy hoặc đang soạn trả lời | `awaiting_information`, `awaiting_review`, `completed`, `cancelled` |
| `awaiting_information` | Chờ người hỏi bổ sung | `in_progress`, `cancelled` |
| `awaiting_review` | Chờ duyệt chuyên môn | `in_progress`, `completed`, `cancelled` |
| `completed` | Đã trả lời và khép | — (chỉ mở lại bằng bản mới) |
| `cancelled` | Hủy | — |

`run_status` phản chiếu `RunStatus` của MVP và thêm `not_started`. `review_status` là
`not_required | pending | approved | rejected | changes_requested`. Ba trường **không** ràng buộc cứng nhau:
một yêu cầu có thể `awaiting_information` trong khi lần chạy trước đã `completed`.

## 4. Ngữ nghĩa unknown / draft / lỗi / bao phủ

- **Unknown.** `ScopeField.resolution = "unknown"` với `value = null`; kèm mục trong `unknowns`
  (`field`, `reason`, `needs_confirmation`). Chỉ người dùng hoặc người duyệt được đổi thành `confirmed`.

  Quy ước "chưa rõ" phân biệt **ba** trạng thái, không phải hai (chốt IN-06):

  | Dạng trên dây | Nghĩa |
  | --- | --- |
  | `{"value": null, "resolution": "unknown"}` | Đã hỏi nhưng chưa xác định được |
  | Trường **vắng hẳn** | Chưa hỏi — chưa ai đặt câu hỏi này |
  | `{"value": "metformin", "resolution": "confirmed"}` | Đã xác định |

  Chuỗi rỗng `""` và chuỗi `"chưa rõ"` **không** phải giá trị sentinel: `""` lẫn với câu trả lời
  rỗng hợp lệ và không phân biệt được "chưa hỏi" với "đã hỏi, chưa ra"; `"chưa rõ"` dính vào mọi
  so khớp, tìm kiếm và dịch, và không tách được khỏi trường hợp người dùng thật sự gõ "chưa rõ".

  Hai mức bắt buộc khác nhau, và điều đó quyết định dạng nào dùng được ở đâu. `scope.required` là
  `["drug", "event"]`, và mỗi `ScopeField` bắt buộc `["value", "resolution"]` — nên **gửi `scope`
  thì phải gửi cả hai trường, kể cả trường chưa biết**: "chưa biết thuốc" vẫn phải nói ra bằng
  `null` + `unknown`, không được bỏ qua. Ngược lại `source` và `evidence_ref` là tuỳ chọn, nên chưa
  biết thì **vắng hẳn** chứ không ghi `null` — lược đồ từ chối `null` ở đó. Bỏ hẳn `scope` khỏi thân
  yêu cầu cũng hợp lệ, và khi đó tầng API tự điền hai trường ở dạng "chưa rõ".
- **Draft.** `ProfessionalResponse.status = "draft"` không được xuất chính thức; chỉ `approved` mới xuất.
- **Lỗi.** Envelope lỗi giữ nguyên của MVP: `{"error": {code, message, details, request_id}}`;
  danh mục `code` **bằng đúng** `ErrorCode` của MVP (test đồng bộ).
- **Bao phủ.** `CoverageReport` tách `sources_ok`, `sources_empty`, `sources_error`; `abstract_only` ghi rõ
  khi bằng chứng chỉ là tóm tắt. Mục bằng chứng ghi `retrieval` (`abstract_only`, `full_text`,
  `label_section`, `warehouse_chunk`) và `quality_flags`.

## 5. Ví dụ hợp lệ (kiểm tự động)

| Tệp | Thực thể | Thể hiện điều gì |
|---|---|---|
| `work-item-draft-unknown.json` | `WorkItem` | nháp, còn `dose`/`time_window` unknown, chưa có chủ sở hữu |
| `work-item-accepted.json` | `WorkItem` | đã nhận, đang chạy, đã gán dược sĩ phụ trách |
| `investigation-link.json` | `InvestigationLink` | liên kết lần chạy đầu đã xong |
| `evidence-bundle-abstract-only.json` | `EvidenceBundle` | có bằng chứng nhưng chỉ tóm tắt + 2 khoảng trống |
| `evidence-bundle-source-error.json` | `EvidenceBundle` | lỗi nguồn, không có bằng chứng, `insufficient_evidence` |
| `professional-response-draft.json` | `ProfessionalResponse` | phiếu nháp, chưa duyệt |
| `professional-response-approved.json` | `ProfessionalResponse` | phiếu đã duyệt kèm `ReviewRef` |
| `review-decision.json` | `ReviewRef` | quyết định duyệt |
| `follow-up.json` | `FollowUp` | việc theo dõi sau trả lời |
| `version-conflict-error.json` | `ApiError` | hai người cùng sửa → 409 `version_conflict` |

Chạy kiểm: `python -m pytest tests/test_scripts/test_hospital_contract.py -q` (9 bài, ngoại tuyến).
Test kiểm: lược đồ hợp lệ; mọi ví dụ hợp lệ theo lược đồ; có đủ ví dụ unknown/draft/lỗi nguồn/tóm tắt;
mọi `$ref` phân giải được; enum dùng chung khớp MVP; OpenAPI đủ `operationId` và ví dụ.

## 6. Kế hoạch tương thích và triển khai

| Bước | Task | Việc |
|---|---|---|
| 1 | R2-1-03 | Dựng bảng `work_items`, `investigation_links`, `evidence_bundles`, `professional_responses`, `follow_ups`, `version_refs`, `review_refs` theo lược đồ này; migration cộng thêm, không sửa bảng cũ. |
| 2 | R2-2-02 | Triển khai service/API `/api/v2/...` đúng đoạn OpenAPI; repository trỏ về bảng mới. |
| 3 | R2-4-06 | Sinh kiểu TypeScript từ `openapi.json` để frontend render đúng các ví dụ. |
| 4 | R2-2-04/05/06 | Checkpoint, phiếu trả lời, theo dõi dùng `ProfessionalResponse`/`FollowUp`. |

**Tương thích:** không đổi đường dẫn `/api/v1`; MVP đang chạy không bị ảnh hưởng. Khi triển khai thật,
cập nhật `docs/mvp-contracts.md` và bổ sung mô hình Pydantic tương ứng trong `src/models/`.

## 7. Điểm chưa chốt (cần 1/3/4 xác nhận)

1. **Người 3:** danh sách mục bắt buộc của phiếu trả lời và rubric `supported/contradicted/insufficient`
   — hiện hợp đồng chỉ ràng buộc `key` của mục, chưa ràng buộc nội dung chuyên môn.
2. **Người 4:** hành trình người dùng và trường nào hiển thị trên form; hợp đồng đã có `unknowns` nhưng
   chưa chốt cách hỏi lại.
3. **Người 1:** ràng buộc lưu trữ (khoá chính, chỉ mục, xoá mềm) và cách sao lưu/phục hồi theo bảng mới.
4. **Ai được duyệt:** hợp đồng ghi `ReviewRef.reviewer.role` nhưng chưa chốt ma trận quyền theo vai trò
   (thuộc R2-2-07).

## 8. Ánh xạ lưu trữ (bước 1 đã dựng)

Bảy thực thể của hợp đồng đã có bảng tương ứng trong cùng cơ sở dữ liệu kho ELT
(`src/services/casework/models.py`), tạo bằng `python -m scripts.elt.migrate_casework`:

| Thực thể hợp đồng | Bảng | Ghi chú |
|---|---|---|
| `WorkItem` | `work_items` | `version` + `etag` là khoá lạc quan; ba trạng thái là ba cột riêng |
| `InvestigationLink` | `investigation_links` | một dòng cho mỗi lần chạy nối vào yêu cầu |
| `EvidenceBundle` | `evidence_bundles` | bất biến: mỗi lần chạy một dòng, không sửa |
| `ProfessionalResponse` | `professional_responses` | append-only theo `version`; bản cũ giữ lại với `status=superseded` |
| `FollowUp` | `follow_ups` | trạng thái `open/in_progress/done/cancelled`, có `closed_at` |
| `ReviewRef` | `review_refs` | append-only; cập nhật luôn trạng thái của thực thể được duyệt |
| `VersionRef` | `version_refs` | nhật ký phiên bản kèm ảnh chụp, phục vụ đọc lại lịch sử |

Quy ước chống mất dữ liệu:

* Sửa `work_items` mà thiếu `expected_version` thì trả `422 INVALID_REQUEST`; lệch phiên bản thì trả
  `409 VERSION_CONFLICT` và không ghi gì. Phép kiểm và phép ghi nằm trong **cùng một câu**
  `UPDATE ... WHERE version = :expected` có kiểm `rowcount`, nên hai người sửa cùng một phiên bản
  thì đúng một người thắng — không còn khe thời gian để cả hai cùng thắng.
* Hai lần lưu phiếu trả lời song song không tạo hai bản "hiện hành": lần lưu khoá dòng yêu cầu
  (`SELECT ... FOR UPDATE`), và hai chỉ mục duy nhất là lưới an toàn — `(work_item_id, version)`
  chặn trùng số phiên bản, `(work_item_id) WHERE status <> 'superseded'` chặn hai bản hiện hành.
* Hai lần duyệt song song cùng một phiếu chỉ có một quyết định thắng: lần duyệt dùng câu lệnh
  `UPDATE ... WHERE version = expected_version AND status <> 'superseded'`, bên thua nhận
  `409 VERSION_CONFLICT` (kèm `expected_version` và `current_version`) chứ không ghi đè im lặng.
* Mã do người gọi đặt phải là chuỗi không rỗng và không dài quá độ rộng cột; mã rỗng **không**
  được thay bằng mã mới sinh, mà trả `422 INVALID_REQUEST`.
* Phiếu trả lời đã ở trạng thái `superseded` thì không duyệt được (`409 INVALID_STATE`); mỗi lần
  duyệt phiếu hiện hành tăng `version` và đổi `etag`.
* Mọi lần ghi đều thêm một dòng `version_refs` giữ ảnh chụp; `history()` đọc lại được toàn bộ.
* Khoá ngoài do người gọi đặt mà trùng thì trả `409 IDEMPOTENCY_CONFLICT`, không phải lỗi hệ thống.

Phạm vi kiểm tra của tầng lưu trữ: kho kiểm **kiểu** và **giá trị enum** của từng trường, và
kiểm bản chiếu của mình khớp lược đồ này (`tests/test_services/test_casework_store.py::test_store_documents_match_the_hospital_contract`).
Kho **không** kiểm cấu trúc lồng sâu do người gọi gửi vào (`context`, `scope`, `unknowns`, `items`,
`coverage`, ...); tầng `/api/v2` (R2-2-02) chịu trách nhiệm kiểm bằng chính `schemas.json`.

Hai điều tầng `/api/v2` phải nhớ khi gọi kho:

* `expected_version` là tham số bắt buộc theo từ khoá; **truyền `None`** khi thiếu, đừng bỏ hẳn tham
  số — bỏ hẳn sẽ thành `TypeError` của Python (lỗi hệ thống) thay vì `422`.
* `VersionRef.version` luôn bằng `1` cho `investigation_link` và `follow_up`: hai bảng này chưa có
  cột `version`, nên mỗi liên kết/việc theo dõi chỉ có một dòng nhật ký và `etag` không đổi theo lần sửa.
* `history()` trả **bản mở rộng** của `VersionRef`: sáu trường lõi (`entity`, `id`, `version`, `etag`,
  `updated_at`, `updated_by`) cộng thêm `revision`, `change_kind`, `changed_fields`, `snapshot`.
  Lược đồ `VersionRef` đặt `additionalProperties: false`, nên endpoint lịch sử ở `/api/v2` phải
  chiếu lại sáu trường lõi, **không** trả nguyên dòng của `history()`.

Ba chỗ hợp đồng đã nới cho khớp thực tế lưu trữ:

* `Actor.role` không còn bắt buộc — kho chỉ chắc chắn có mã người dùng; máy chủ điền vai trò từ token khi biết.
* `InvestigationLink.created_by` cho phép `null` — lần chạy tự động có thể không có người tạo.
* `VersionRef.entity` thêm `investigation_link` và `follow_up` — nhật ký phiên bản phủ cả hai, không chỉ ba thực thể API.

Ánh xạ trường khi đọc/ghi: kho chuẩn hoá đầu vào `{"actor_id": ...}` về dạng hợp đồng `{"id": ...}`,
nên mọi bản chiếu trả ra (`owner`, `updated_by`, `reviewer`, `assignee`, `drafted_by`) đều là `Actor`.
`work_items.created_by_json` vẫn được lưu để kiểm toán nhưng **không** xuất hiện trong bản chiếu
`WorkItem` vì lược đồ cấm trường này (`additionalProperties: false`); muốn biết ai tạo thì đọc
`history()[0].updated_by`.

## 9. Lát B — `CaseRecord` (đề xuất kỹ thuật, chờ dược sĩ xác nhận)

**Task:** R2-2-09 và R2-1-05. Phần này chỉ là contract nháp để kiểm kỹ thuật ngoại tuyến;
chưa có SOP/ca được đơn vị cho phép và **không phải clinical acceptance**. Không thêm endpoint,
không đổi `openapi.json`, và không làm thay đổi lát A DI đang có.

`CaseRecord` trong `schemas.json` là hồ sơ **một ca đã khử định danh**, không chứa tên, mã bệnh
nhân hoặc dữ liệu bệnh viện thật. Các phần chính là:

| Phần | Quy ước đề xuất |
|---|---|
| Phiên bản và trùng ca | `case_version`, `supersedes_version`, `record_kind` (`initial`, `follow_up`, `correction`, `duplicate_candidate`) và `duplicate_candidate_of` giữ đúng lịch sử. `duplicate_candidate` chỉ chờ dược sĩ rà soát, không tự gộp/xóa ca. |
| `medications`, `administrations` | Một ca có nhiều thuốc; mỗi lần dùng trỏ `medication_id`. Vai trò, liều và đường dùng chưa rõ giữ `null` + `unknowns`, không đoán thuốc nghi ngờ. |
| `timeline`, `PartialDateTime` | `resolution` tách `known_date_and_time`, `known_date`, `unknown`; `unknown` buộc `date`, `time`, `timezone` là `null`, còn `known_date` buộc `time` và `timezone` là `null`. Vì vậy timezone không xuất hiện khi không có giờ và không có giờ giả. |
| `labs`, `observations` | Lab có đơn vị đã biết dùng `unit_resolution: confirmed`; khi nguồn thiếu đơn vị bắt buộc dùng `unit: null` + `unit_resolution: unknown`, không bịa/qui đổi đơn vị. Quan sát luôn có nguồn và không tự trở thành kết luận nhân quả. |
| `dechallenge`, `rechallenge` | Tách `observed`, `not_observed`, `not_done`, `unknown`, cùng nguồn và thời điểm. `unknown` không phải `not_observed`; không yêu cầu rechallenge. |
| `assessments` | Là đánh giá **ca**, tách riêng literature stance của `EvidenceBundle`. Khi thiếu dữ kiện dùng `framework: none`, `status: unknown`; Naranjo/WHO-UMC hoặc assessment không-unknown phải có `assessed_by` khác `null`, không tự sinh score/category. |
| `report_revisions` | Mỗi bản có `case_id`, phiên bản và trạng thái; mọi trạng thái lâm sàng mặc định là `proposed_needs_pharmacist_confirmation` cho đến khi dược sĩ xác nhận. |
| `supplements` | Bổ sung bắt buộc mang cùng `case_id` với ca đang có; không tạo bệnh nhân hoặc ca mới. Kiểm thử ngoại tuyến kiểm quan hệ này. |

Hai fixture mới là `case-record-synthetic-multidrug.json` và
`case-record-synthetic-missing-and-supplement.json`. Chúng dùng envelope
`SyntheticCaseRecordFile`: **cả tệp lẫn từng record** đều có `synthetic: true`, cố ý gồm
nhiều thuốc, ngày/giờ unknown, lab có đơn vị, bổ sung cùng ca và trường thiếu. Chúng không phải
dữ liệu bệnh nhân thật và không được dùng làm kết luận chuyên môn.

`SyntheticCaseRecord` cấm `confirmed_by_pharmacist` ở record, assessment và report revision:
fixture chỉ kiểm kỹ thuật, không thay xác nhận chuyên môn. Ràng buộc liên trường như
`supplement.case_id == case.case_id`, mọi report revision cùng ca, và
`case_version == supersedes_version + 1` được kiểm trong test Python vì JSON Schema chuẩn không
biểu diễn phép so sánh giá trị giữa hai nhánh của instance.

R2-3-06 giữ các scenario nhỏ riêng tại `data/person3/r2_case_scenarios.json` để mô tả intake,
trùng ca và follow-up; chúng không phải payload `CaseRecord` và không tham chiếu schema này trực
tiếp. Các tên trường chung (`case_id`, `case_version`, `supersedes_version`, `record_kind`,
`duplicate_candidate_of`, `dechallenge`, `rechallenge`) dùng cùng ngữ nghĩa theo bảng trên.
`CaseRecord` fixtures trong thư mục này là bộ kiểm schema đầy đủ và chỉ synthetic.

Việc chọn rubric, xác nhận ngữ nghĩa và mở API chỉ thực hiện sau khi có SOP/dữ liệu được phép và
dược sĩ xác nhận.

## Workflow intake v2 (additive)

Các object workflow sau là hợp đồng additive, không thay đổi `WorkItem`,
`ProfessionalResponse` hoặc route v1 có `additionalProperties: false`:

- `WorkflowIntake` lưu `kind` (`di` hoặc `adr`) và `raw_text` nguyên văn trước mọi
  thao tác extraction. Mỗi thay đổi tạo `InputSource` bất biến, có SHA-256 và actor.
- `FieldAssertion` chỉ có thể là `proposed`, `confirmed` hoặc `unknown`. `SourceSpan`
  dùng chỉ số Unicode code point `[start,end)` và quote phải khớp đúng source text.
  `unknown`, `not_recorded`, `not_applicable` và `not_assessed` không có nghĩa false.
- `Clarification` dùng semantic key để không mở lại cùng câu hỏi đang `open`; câu trả
  lời `unknown` đóng câu hỏi đó. Required chỉ chặn bước liên quan, useful không chặn
  draft giới hạn.
- `Readiness` tách preliminary retrieval, scoped analysis, limited draft và submit
  review. Không namespace assessment nào được suy ra từ namespace khác.
- `AdrIntake` giữ narrative ngay cả khi thiếu dữ kiện; `AdrMinimumFour` biểu diễn
  bốn nhóm `present|missing|unknown`, với validity
  `complete|incomplete|undetermined` độc lập với `AdrReportability`. Không có SOP
  đã xác nhận thì reportability bắt đầu ở `not_assessed`.

`WorkflowAggregate` là hình dạng đọc của workflow v2. `OutputBasis` và
`ReviewBasis` luôn pin
`input_revision`, assertion/evidence/runtime/response hashes trong basis bất biến.
Người có mặt trong `author_ids` của basis không thể approve basis đó; thay đổi material
làm approval cũ stale. Các body mutation dùng Idempotency-Key theo actor + route và
CAS `expected_version`; cùng key với body khác trả `idempotency_conflict`.
