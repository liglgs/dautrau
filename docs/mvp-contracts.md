# HỢP ĐỒNG DỮ LIỆU MVP — AI AGENT ĐIỀU TRA AN TOÀN THUỐC (P-066)

> **Người thực hiện:** Người 2 (Core Backend & Agent Orchestration) — mốc **M01**.
> **Nguồn sự thật:** `src/models/schemas.py` (Pydantic). Tài liệu này mô tả hợp đồng cho Người 1 (connectors),
> Người 3 (extraction/scope/contradiction) và Người 4 (frontend).
> **Căn cứ:** `docs/planMVPfinal.md` §4, §10, §11 và `docs/QUY_TAC_PHOI_HOP_4_NGUOI.md` §6, §7, §11.

---

## 1. Nguyên tắc bất biến

1. Agent **không bao giờ** kết luận nhân quả. Enum `AssessmentStatus` không có giá trị `causal`; mọi giá trị
   `causal` gửi lên đều bị từ chối ở tầng schema (422).
2. Mọi trích dẫn phải **kiểm chứng được**: `EvidenceUnit.quote` phải nằm trong `SourceDocument.text` tại đúng
   `locator.start`/`locator.end`.
3. Trường `unknown` **không bao giờ** được gộp thành `match` (xem `ScopeComparison`).
4. Reviewer ID do **server** xác định từ token; body request không bao giờ được đặt `reviewer_id`.
5. Mọi giới hạn ngân sách là **trần cứng**: 20 bước, 100 tài liệu, 80 request nguồn, 80 lượt gọi LLM,
   150.000 token vào, 25.000 token ra.
6. Tài liệu nguồn là bất biến (immutable) theo `(source, source_id, version)`; nội dung trùng được nhận diện
   bằng `hash` SHA-256.

---

## 2. Giới hạn ngân sách (`src/models/schemas.py`)

| Hằng số | Giá trị | Ý nghĩa |
|---|---|---|
| `DEFAULT_MAX_STEPS` | 8 | Số bước nghiệp vụ mặc định cho một cuộc điều tra |
| `DEFAULT_MAX_DOCUMENTS` | 50 | Số tài liệu mặc định |
| `HARD_MAX_STEPS` | 20 | Trần cứng số bước |
| `HARD_MAX_DOCUMENTS` | 100 | Trần cứng số tài liệu |
| `MAX_SOURCE_REQUESTS` | 80 | Trần request ra nguồn ngoài |
| `MAX_LLM_CALLS` | 80 | Trần lượt gọi LLM |
| `MAX_INPUT_TOKENS` | 150 000 | Trần token vào |
| `MAX_OUTPUT_TOKENS` | 25 000 | Trần token ra |
| `RESERVED_STEPS_FOR_DOSSIER` | 1 | Bước dự phòng cho hồ sơ/abstain |
| `RESERVED_LLM_CALLS_FOR_DOSSIER` | 2 | Lượt gọi LLM dự phòng cho hồ sơ |

Một **bước nghiệp vụ** = một quyết định truy xuất (kể cả cache hit). Tài liệu chỉ được đếm **một lần** theo
`(source, source_id, version)` hoặc theo `hash`.

---

## 3. Enum trạng thái

### 3.1 `RunStatus`
`queued` → `running` → (`waiting_for_review` → `running`)* → `completed` | `interrupted` | `failed`

### 3.2 `AssessmentStatus`
`supported_for_scope`, `contradicted_for_scope`, `insufficient_evidence`, `scope_mismatch`, `out_of_scope`,
`requires_human_review`.

### 3.3 `ReviewStatus`
`pending`, `approved`, `rejected`, `changes_requested`.

### 3.4 `CheckpointKind`
`normalization` (chốt claim/hoạt chất), `assessment` (chốt kết luận), `dossier` (chốt hồ sơ xuất bản).

### 3.5 Enum khác
`ReviewAction` (`approve`, `reject`, `edit_claim`, `edit_evidence`, `exclude_evidence`, `request_more`),
`Stance` (`supports`, `contradicts`, `uncertain`), `ScopeOutcome` (`match`, `mismatch`, `unknown`),
`StopReason` (`success`, `saturation`, `needs_review`, `insufficient_evidence`, `budget_exhausted`, `source_error`),
`PlannerActionKind` (`search_source`, `change_query`, `change_source`, `stop`),
`GapKind` (`no_results`, `missing_evidence`, `missing_source`, `scope_mismatch`, `contradiction`, `ambiguity`),
`EvidenceType` (`rct`, `observational`, `case_report`, `label`, `faers_report`, `review`, `other`),
`SourceStatus` (`ok`, `empty`, `error`, `skipped`).

---

## 4. Models

### 4.1 `ClaimInput` (input người dùng)
| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `claim_text` | str 1–5000 | ✔ | Câu claim nguyên văn |
| `drug` | str 1–200 | ✔ | Tên thuốc/hoạt chất/thương mại |
| `event` | str 1–200 | ✔ | **Thiếu `event` ⇒ 422 trước khi gọi nguồn** |
| `population` | str ≤200 | ✘ | Quần thể |
| `dose` | str ≤120 | ✘ | Liều |
| `route` | str ≤120 | ✘ | Đường dùng |
| `time_window` | str ≤120 | ✘ | Cửa sổ thời gian |

`extra="forbid"`: trường lạ ⇒ 422 (không được âm thầm bỏ qua).

### 4.2 `NormalizedClaim`
`claim_text`, `drug_ingredient`, `drug_synonyms[]`, `event_term`, `population`, `dose`, `route`, `time_window`,
`unknowns[]` (tên các trường chưa xác định), `ambiguities[]` (ví dụ thương mại khớp nhiều hoạt chất),
`requires_review: bool`, `version: int`.

### 4.3 `SourceDocument` (Người 1 trả về)
`doc_id`, `source` ∈ {`pubmed`, `dailymed`, `faers`}, `source_id`, `version`, `title`, `source_url`, `text`,
`hash` (SHA-256 hex), `retrieved_at`, `metadata{}`.

### 4.4 `EvidenceUnit` (Người 3 trích xuất)
`evidence_id`, `doc_id`, `source`, `stance` (`Stance`), `quote` (1–2000), `locator{start,end,section}`,
`scope{population,dose,route,time_window,study_type}`, `confidence` 0–1, `evidence_type`, `version`,
`excluded: bool`, `notes`.

### 4.5 `AssessmentResult`
`assessment_status`, `rationale`, `evidence_ids[]`, `scope_notes[]`, `confidence`.

### 4.6 `InvestigationState`
`investigation_id`, `claim`, `normalized_claim`, `run_status`, `assessment_status`, `assessment`, `budget`
(`BudgetState`), `step_index`, `gaps[]`, `evidence[]`, `documents[]`, `queries[]` (fingerprint chống lặp),
`next_stage`, `checkpoint`, `stop_reason`, `version`, `created_at`, `updated_at`.

### 4.7 `ReviewDecision`
`decision_id`, `investigation_id`, `checkpoint`, `action`, `reviewer_id` (**server**), `expected_version`
(khóa lạc quan — sai ⇒ 409), `reason` (bắt buộc với `reject`/`request_more`), `target_evidence_id`
(bắt buộc với `edit_evidence`/`exclude_evidence`), `payload{}`, `created_at`.

### 4.8 `Dossier`
`dossier_id`, `investigation_id`, `version`, `status` (`ReviewStatus`, mặc định `pending`), `assessment_status`,
`summary`, `sections[{title, body, evidence_ids[]}]`, `limitations[]`, `gaps[]`, `citations[]` (doc_id),
`created_at`, `approved_at`, `approved_by`, `content_hash`.

### 4.9 Model điều phối
`EvidenceGap{gap_id, kind, field, description, priority, created_step}`,
`PlannerDecision{action, source, query, fingerprint, gap_id, reason}`,
`StopDecision{should_stop, reason, run_status, assessment_status, message}`,
`BudgetReservation{operation_key, granted, amounts, remaining, reason}`,
`ReviewResult{investigation_id, version, run_status, review_status, invalidated[], message}`,

Trong `ReviewResult`, `review_status` là **kết quả của chính quyết định vừa gửi** (ví dụ duyệt ở checkpoint
`assessment` trả `approved` dù chưa có hồ sơ nào); trường cùng tên trong payload danh sách/chi tiết mới là
**trạng thái phiên bản hồ sơ**.

Trong đó `review_status` (payload) là trạng thái phiên bản hồ sơ mới nhất (`null` khi chưa có hồ sơ) và
`last_review{action, checkpoint, created_at}` là quyết định người duyệt mới nhất ở **bất kỳ** checkpoint nào
(`null` khi chưa ai duyệt). Một ca bị từ chối ở checkpoint `assessment` không có hồ sơ nên
`review_status=null` nhưng `last_review.action=reject`.
`ValidationReport{ok, errors[], warnings[]}`.

---

## 5. So khớp phạm vi (scope)

`ScopeComparison.compare(field, claim_value, evidence_value)`:

| claim | evidence | outcome |
|---|---|---|
| known | known, giống nhau | `match` |
| known | known, khác nhau | `mismatch` |
| unknown/None/rỗng | bất kỳ | `unknown` |
| bất kỳ | unknown/None/rỗng | `unknown` |

`unknown` **không** phải `match` và **không** phải `mismatch`: agent phải ghi nhận thành `EvidenceGap`
và không được suy rộng.

---

## 6. Mã lỗi chuẩn (`ErrorCode`)

Envelope lỗi của MVP: `{"error": {"code", "message", "details", "request_id"}}`.

| Code | HTTP | Khi nào |
|---|---|---|
| `invalid_request` | 422 | Schema/trường không hợp lệ |
| `unauthorized` | 401 | Thiếu/sai token |
| `forbidden` | 403 | Sai role (ví dụ investigator gọi approve) |
| `not_found` | 404 | Không thấy investigation/tài liệu |
| `version_conflict` | 409 | `expected_version` cũ (stale) |
| `idempotency_conflict` | 409 | Cùng `Idempotency-Key` nhưng payload khác |
| `runner_busy` | 429 | Đang có cuộc điều tra khác chạy |
| `invalid_state` | 409 | Hành động không hợp lệ với trạng thái hiện tại |
| `budget_exhausted` | 409 | Hết ngân sách |
| `dossier_not_approved` | 409 | Export khi hồ sơ chưa được duyệt |
| `dossier_invalid` | 409 | Duyệt/export hồ sơ nhưng kiểm tra an toàn thất bại (trích dẫn không còn khớp nguồn, thiếu trích dẫn, bằng chứng đã bị loại) |
| `source_error` | 502 | Nguồn ngoài lỗi |
| `llm_format_error` | 502 | LLM trả sai định dạng sau 1 lần sửa |

---

## 7. Luồng trạng thái & phiên bản

```
POST /investigations → queued → running
  normalize → (ambiguity?) → waiting_for_review@normalization
  checklist → plan → retrieve → extract/assess → update_gaps → stop_or_continue
  → waiting_for_review@assessment        (luôn qua reviewer)
  → [reviewer approve] → dossier → waiting_for_review@dossier
  → [reviewer approve dossier] → completed → export Markdown
```

Quy tắc vô hiệu hóa (invalidation):

| Hành động | Vô hiệu hóa |
|---|---|
| Sửa claim/scope | normalization + assessment + dossier |
| Thêm/sửa/xóa bằng chứng | assessment + dossier |
| `request_more` | assessment + dossier của nội dung mới |
| Sửa nội dung hồ sơ | dossier |
| Đổi policy/model | run mới, không sửa hồi tố |

`approve assessment` **không** tự động `approve dossier`. `request_more` giữ nguyên toàn bộ bộ đếm ngân sách
của cuộc điều tra.

Hiện thực: `src/services/review.py::apply_review` (lưu quyết định trước khi áp dụng, chặn replay theo
`decision_id`, chặn `expected_version` cũ bằng khóa lạc quan). Export Markdown
(`src/services/dossier.py::export_markdown`) chỉ đọc phiên bản đã duyệt; mọi thay đổi claim/bằng chứng
đặt lại các phiên bản hồ sơ cũ thành `rejected`.

---

## 8. Mock fixtures (`tests/fixtures/mvp/`)

| Fixture | Kịch bản | Kỳ vọng |
|---|---|---|
| `supported_fixture.json` | Nhãn DailyMed + nghiên cứu PubMed cùng phạm vi | `supported_for_scope`, dừng `success` |
| `insufficient_fixture.json` | Chỉ có FAERS | `insufficient_evidence` (không bao giờ `supported`) |
| `scope_mismatch_fixture.json` | Claim trẻ em, bằng chứng người lớn | `scope_mismatch` (demo D1) |
| `contradiction_fixture.json` | Hai nghiên cứu trái chiều khác quần thể | `requires_human_review` (demo D2) |
| `source_error_fixture.json` | Nguồn chính lỗi timeout | `insufficient_evidence`, lý do `source_error` |
| `ambiguous_brand_fixture.json` | Thương mại khớp 2 hoạt chất | Dừng ở checkpoint `normalization` |
| `replanning_fixture.json` | Query đầu bằng biệt dược không có kết quả, sau đó đổi sang hoạt chất | Đổi query rồi đổi nguồn (demo D4), kết luận `supported_for_scope` |

Mỗi fixture chứa: `claim`, `source_results[]` (trạng thái từng nguồn cho mock connector), `documents[]`,
`evidence[]`, `expected{}` và (với case 6) `normalization{}`.

---

## 9. Nghiệm thu M01

```bash
python -m pytest tests/test_models/test_mvp_contracts.py -q
```

---

## 10. Hợp đồng API (`src/api/`, mốc M07)

Tiền tố `/api/v1` (trừ `/health`, `/ready`). Mọi request đọc/ghi đều cần token vai trò:

| Header | Ý nghĩa |
|---|---|
| `Cookie: session_id=<opaque>` | Phiên đăng nhập email + mật khẩu (chế độ nội bộ). Cầu nối giao diện chuyển tiếp cookie này. |
| `Authorization: Bearer <access_token>` | Access token Supabase (chế độ Supabase). |
| `X-API-Token: <vln_...>` | Khoá máy do `scripts/auth_cli.py issue-token` cấp, dành cho công cụ dòng lệnh. |
| `Authorization: Bearer <token>` | Cách gửi thay thế tương đương |
| `Idempotency-Key: <key>` | Bắt buộc trên thực tế cho `POST /investigations` và `POST /{id}/continue` để chặn double click |

| Endpoint | Quyền | Mã thành công | Ghi chú |
|---|---|---|---|
| `POST /investigations` | investigator | `202` | Trả `investigation_id`, `created`, `started`, `version`, `events_url`; cùng key + cùng payload ⇒ `created=false`; nếu lượt trước bị `429` (job còn `queued`) thì lần gọi lại **chạy nốt** và trả `started=true` |
| `GET /investigations` | investigator | `200` | `limit` 1–200, mới nhất trước; mỗi dòng có `review_status` của phiên bản hồ sơ mới nhất và `last_review` của quyết định người duyệt mới nhất (`null` khi chưa có) |
| `GET /investigations/{id}` | investigator | `200` | State summary cho polling: `run_status`, `assessment_status`, `checkpoint`, `next_stage`, `review_status`, `last_review`, `version`, `budget`, `counters`, `gaps` |
| `GET /investigations/{id}/events?after_id=` | investigator | `200` | `items` + `last_id`; `after_id` không trả lại event cũ |
| `GET /investigations/{id}/evidence` | investigator | `200` | Bằng chứng kèm `document` (nguồn, URL, hash) để UI dựng bảng đối chiếu |
| `GET /investigations/{id}/documents/{doc_id}` | investigator | `200` | `document.text` + `locators[]`; `text[start:end] == quote` |
| `GET /investigations/{id}/dossier` | investigator | `200` | `dossier` (nháp/đã duyệt gần nhất), `approved`, `validation` |
| `POST /investigations/{id}/reviews` | **reviewer** | `200` | Body `ReviewRequest`; `reviewer_id` do server gán, body gửi `reviewer_id` ⇒ `422` |
| `POST /investigations/{id}/continue` | investigator | `202` | Cần checkpoint đã xử lý; giữ nguyên budget; đã `completed` ⇒ `409`; **cùng `Idempotency-Key` ⇒ `202 resumed=false`** (double-click); yêu cầu MỚI khi cuộc điều tra đang `running` ⇒ `409`, khi runner bận việc khác ⇒ `429` (key chưa bị tiêu thụ nên gọi lại được) |
| `GET /investigations/{id}/export` | investigator hoặc reviewer | `200` (`text/markdown`) | Chỉ khi có hồ sơ đã duyệt **và còn hợp lệ**, ngược lại `409 dossier_not_approved` / `409 dossier_invalid` |
| `GET /health` | không cần token | `200` | Liveness |
| `GET /ready` | không cần token | `200`/`503` | Readiness: store đọc được + trạng thái runner |

**Envelope lỗi** (mọi lỗi nghiệp vụ, dựng bởi `MvpError.envelope`):

```json
{"error": {"code": "dossier_not_approved", "message": "…", "details": {"investigation_id": "INV-…"}, "request_id": "…", "retryable": false}}
```

Lỗi `422` của FastAPI (schema sai) và `404` route không tồn tại dùng **cùng hình dạng** `{"error": {…}}`
kèm `details.errors[]` (`loc`, `msg`, `type`). Các handler dùng chung còn giữ thêm khoá phẳng
`code`/`message`/`request_id`/`retryable` để không phá vỡ client VMEC cũ đang đọc trực tiếp các khoá này.

Mã HTTP dùng trong MVP: `401` thiếu/sai token, `403` sai vai trò, `404` không tìm thấy hoặc tài liệu
không thuộc cuộc điều tra, `409` version/checkpoint/idempotency/dossier chưa duyệt, `422` input sai,
`429` runner đang bận (`runner_busy`, có `retryable=true`), `502` lỗi nguồn/mô hình, `503` mô hình không khả dụng.

**Trạng thái MVP:** hai token vai trò chỉ phục vụ demo cục bộ — chưa có tài khoản người dùng, session cookie,
CSRF hay chặn theo chủ sở hữu (để lại cho P18 của kế hoạch đầy đủ). OpenAPI sinh bằng
`python scripts/export_openapi.py` → `docs/openapi.json` để Người 4 tạo types cho UI.
Spec khai báo security scheme `MvpApiToken` (apiKey, header `X-API-Token`) và gắn cho mọi route tag `mvp`,
nên client sinh tự động không bị `401` oan; route `export` được khai báo trả `text/markdown`.
Hạn chế còn lại: body của các route MVP chưa có response model nên schema vẫn là `additionalProperties`
(Người 4 viết type tay theo bảng trên).

**Bất biến dữ liệu (đợt rà soát M05–M07):** `doc_id` phải ổn định theo `(source, source_id, version)`;
nội dung tài liệu dùng chung giữa các cuộc điều tra qua bảng liên kết `investigation_documents`,
còn `evidence_versions` khoá theo `(investigation_id, evidence_id, version)` — nhờ vậy chạy lại cùng
một kịch bản trong cùng file SQLite không còn lỗi `UNIQUE` và mỗi cuộc điều tra vẫn đọc được tài liệu
mà bằng chứng của nó trích dẫn.


---

## 11. Nghiệm thu M07

```bash
python -m pytest tests/test_api/test_mvp_api.py -q
```


---

## 12. Vòng rà soát an toàn (sau M05–M07)

Các quy tắc dưới đây được bổ sung sau đợt rà soát độc lập (agent core + HTTP surface) và đều có
kiểm thử hồi quy trong `tests/test_agents/test_mvp_graph.py`, `tests/test_services/test_mvp_runtime.py`,
`tests/test_services/test_mvp_review.py`, `tests/test_api/test_mvp_api.py`.

| # | Quy tắc | Vì sao |
|---|---|---|
| 1 | Chỉ giữ `assessment_status` đã tính khi lượt chạy dừng vì `success`; mọi lý do dừng khác (bão hoà, hết ngân sách, lỗi nguồn, hết chiến lược) hạ kết luận xuống mức của quyết định dừng | Không được trình bày kết luận dương tính khi chưa chạy bước phản bác / chưa có nguồn thứ hai |
| 2 | `supported_for_scope` chỉ được dừng khi có bước phản bác **và** bằng chứng đến từ ≥2 nguồn; nếu chỉ một nguồn thì phải có ≥2 đơn vị bằng chứng từ ≥2 tài liệu khác nhau. Nguồn đã gọi nhưng rỗng, hoặc hai trích đoạn của cùng một tài liệu, không tính | Chống "hai nguồn" giả |
| 3 | Trần tài liệu là trần cứng: `retrieve` chỉ nhận phần còn ngân sách, phần dư ghi thành gap; `BudgetController.commit` chặn trước khi lưu | Vượt trần làm `BudgetState` không đọc được nữa (mất toàn bộ hồ sơ) |
| 4 | `edit_evidence` phải validate lại qua pydantic; sửa `quote` thì phải tìm thấy nguyên văn trong tài liệu nguồn và locator được tính lại | Tránh payload sai làm hỏng vĩnh viễn bản ghi và tránh trích dẫn bịa |
| 5 | `validate_dossier` kiểm lại `text[start:end] == quote` cho mọi bằng chứng đang hoạt động (lệch vị trí ⇒ cảnh báo, không khớp ⇒ lỗi) | Bất biến #2 của hợp đồng phải được kiểm ở cửa export |
| 6 | Duyệt ở checkpoint `normalization` đưa về `checklist` (không nhảy thẳng `build_dossier`) | Chưa đánh giá bằng chứng thì không được tạo hồ sơ |
| 7 | Policy "không nhân quả" chỉ soi phần agent tự viết; nguyên văn claim và nguyên văn trích dẫn nguồn được giữ nguyên | Bài báo thật luôn có "due to"/"caused by" — soi cả phần này sẽ chặn oan mọi hồ sơ |
| 8 | Chỉ kết luận `scope_mismatch` khi có ít nhất một trường thực sự `mismatch`; toàn `unknown` ⇒ `insufficient_evidence` | `unknown` không phải là bằng chứng lệch phạm vi |
| 9 | Claim còn `ambiguities` sinh gap `GAP-AMBIGUITY-*` trong checklist | Hồ sơ phải ghi lại rằng hoạt chất chưa được chốt |
| 10 | `/continue`: kiểm tra runner bận trước khi tiêu thụ `Idempotency-Key`; replay cùng key ⇒ `202 resumed=false`; yêu cầu mới khi đang chạy ⇒ `409`; không chiếm được khoá ⇒ ghi event `queued` | 429 là lỗi tạm thời — không được "khoá" key và không được trả 202 sai sự thật |
| 11 | `content_hash` của hồ sơ được tính lại sau khi tăng phiên bản | Hash phải khớp bản ghi được lưu |
| 12 | `_state`/`_load_state` không còn bọc `except Exception → 404` | Lỗi DB/ValidationError phải nổi lên, không bị báo nhầm là "không tìm thấy" |
| 13 | `/ready` chỉ trả `runner_busy`/`runner_active`, không trả ID cuộc điều tra hay chi tiết lỗi nội bộ | Endpoint không cần token |
| 14 | Khởi tạo lười store/runner có khoá | Hai request đầu tiên cùng lúc không tạo hai store trên cùng file SQLite |

**Ghi chú còn để lại (chấp nhận trong MVP):** `apply_review` vẫn lưu quyết định trước khi áp dụng
(để không mất audit trail); nếu handler lỗi thì quyết định đã lưu và lần gửi lại cùng `decision_id`
trả `409 idempotency_conflict` — cần một `decision_id` mới. Body của route MVP chưa có response model.

---

## 13. Cổng LLM có kiểm soát (P11)

`src/services/prompts.py` + `src/prompts/manifest.json` + `src/prompts/*.md` là nguồn duy nhất của
prompt; `src/services/llm.py` là cửa duy nhất để gọi mô hình.

| Hạng mục | Quy tắc |
|---|---|
| Tách kênh | `system` = chính sách hệ thống (không bao giờ trộn nội dung nguồn); `payload` = khóa do manifest khai báo, thiếu/thừa khóa ⇒ lỗi; `untrusted` = văn bản tài liệu, chỉ nằm trong khối `<<<DỮ LIỆU KHÔNG TIN CẬY…>>>` đã vô hiệu hóa `<<<`/`>>>`, token `<\|…\|>` và dòng giả `SYSTEM:` |
| Quyền hạn | Danh sách hành động hợp lệ (`allowed_values`) và schema đầu ra lấy từ manifest, không lấy từ mô hình hay từ tài liệu nguồn |
| Sửa lỗi | Sai schema / sai danh sách hành động / ID bằng chứng không tồn tại ⇒ sửa **đúng một lần**; vẫn sai ⇒ `llm_format_error` (502) và lượt chạy dừng, output lỗi không điều hướng graph |
| Đối chiếu bằng chứng | Manifest khai báo `evidence_refs` (hỗ trợ đường dẫn qua danh sách, ví dụ `sections.evidence_ids`); mọi ID phải tồn tại trong cuộc điều tra |
| Ngân sách | Đặt trước 1 lượt gọi + token ước lượng **trước** khi gọi provider; sau khi trả lời ghi số thật và luôn giữ bộ đếm trong trần. Lỗi provider hoặc provider không trả usage ⇒ **giữ nguyên** phần đặt trước (`ledger.unknown_usage_calls`), đối chiếu sau bằng `LLMGateway.reconcile` |
| Giới hạn | `max_output_chars` theo tác vụ, trần prompt 40 000 ký tự, mỗi khối nguồn cắt theo `untrusted_char_limit`, tối đa 50 khối; provider thật đã có 3 lần thử với backoff |
| Metadata nội bộ | `UsageLedger.records` ghi `task`, `prompt_version`, `prompt_hash` (32 ký tự), `model`, `repair`, token — không trả ra API công khai |
| Cấu hình mô hình | Provider và tên mô hình lấy từ `get_settings()` (`MODEL_PROVIDER`, `MODEL_NAME`), không hard-code trong node |

**Bổ sung (vòng P16/P17):** checklist mặc định gồm đủ 5 nhóm — kiểm tra nhãn thuốc (DailyMed), đối chiếu
y văn (PubMed), mẫu báo cáo tự nguyện (FAERS), bằng chứng phản bác (`GAP-CONTRARY`) và khoảng trống phạm vi
(`GAP-UNKNOWN-*`). Nguồn chưa chạy được ghi rõ "chưa kiểm tra được"; `GAP-CONTRARY` chỉ được đóng khi truy vấn
phản bác thực sự chạy. Kết luận dương tính cần bước phản bác **và** ≥2 nguồn, hoặc ≥2 tài liệu khác nhau khi
chỉ có một nguồn.
