# Hợp đồng hospital-v2 — lát cắt DI (đề xuất, additive)

> **Task:** R2-2-01 — chốt contract nhỏ cho lát cắt DI. **Người soạn:** Người 2.
> **Trạng thái:** `proposed_not_implemented` — hợp đồng đã viết và kiểm bằng máy, **chưa** nối vào ứng dụng.
> **Nguồn sự thật của lược đồ:** `docs/spec/hospital-v2/schemas.json` (JSON Schema 2020-12).
> **Đoạn OpenAPI:** `docs/spec/hospital-v2/openapi.json` · **Ví dụ:** `docs/spec/hospital-v2/examples/` · **Kiểm thử:** `tests/test_scripts/test_hospital_contract.py`.
> **Căn cứ:** `docs/phan-cong-vong-2/NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md` §15.2 (R2-2-01), `docs/mvp-contracts.md`.

## 1. Phạm vi và nguyên tắc

Lần chốt này **chỉ** mở lát cắt DI (drug–event investigation) và bảy thực thể đi kèm.
**Không** mở lược đồ ADR/C đầy đủ, không đổi lược đồ MVP hiện có.

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

Quy ước: sửa `work_items` mà thiếu `expected_version` hoặc lệch phiên bản thì trả `409 VERSION_CONFLICT`
và không ghi gì; mọi lần ghi đều thêm một dòng `version_refs`.
