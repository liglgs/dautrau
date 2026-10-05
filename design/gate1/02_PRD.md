# PRD — AI Agent điều tra bằng chứng an toàn thuốc

Phiên bản: 0.1 · Ngày: 2026-10-02 · Trạng thái: nháp để review, chưa phê duyệt triển khai.

Nguồn phạm vi: [planMVPfinal.md](../../docs/planMVPfinal.md). Bối cảnh sản phẩm: [Brief](01_ONE_PAGE_BRIEF.md). Thiết kế màn hình: [Wireframe](03_WIREFRAME_UI_FLOW.md).

## 1. Mục tiêu và giới hạn

Tạo prototype cho investigator/reviewer kiểm tra một claim thuốc–biến cố, theo dõi điều tra thích ứng và xuất dossier có nguồn sau review. Chứng minh scope checking, contradiction analysis, abstention, provenance và reviewer gate.

MVP chạy cục bộ, xử lý một investigation tại một thời điểm. Không thêm tài khoản tổ chức, PostgreSQL, worker riêng, vector DB, PDF, historical benchmark hoặc tư vấn điều trị. Evidence tiếng Anh; UI tiếng Việt là giả định thiết kế cần xác nhận.

## 2. Vai trò

| Hành động | Investigator | Reviewer |
|---|---|---|
| Tạo và đọc investigation cục bộ | Có | Có với quyền đọc/tạo tương ứng |
| Xem timeline, evidence, nguồn và dossier nháp | Có | Có |
| Xác nhận normalization, sửa/loại evidence, duyệt assessment/dossier | Không | Có |
| Yêu cầu tìm thêm và quyết định review | Không | Có |
| Tiếp tục từ checkpoint hợp lệ | Có quyền điều tra, sau decision hợp lệ | Có quyền điều tra, sau decision hợp lệ |
| Tải dossier hiện hành đã duyệt | Có quyền đọc | Có quyền đọc |

Quyền phụ thuộc token được server xác nhận. Hai token MVP ánh xạ identity cục bộ theo vai trò; UI không tự quyết định role hoặc gửi reviewer_id làm danh tính tin cậy. Việc tài khoản tổ chức chia sẻ investigation nằm ngoài phạm vi.

## 3. Luồng sử dụng

### F1 — Nhập → điều tra → duyệt → xuất

Chọn phiên vai trò → nhập claim/thuốc/biến cố → chọn nguồn/ngân sách → tạo run → xem timeline/evidence → assessment review nếu cần → dossier review → xuất Markdown đúng version.

### F2 — Claim mơ hồ

Normalization có nhiều ứng viên → lưu checkpoint → hiển thị cách hiểu và unknowns → reviewer xác nhận hoặc sửa có lý do → tiếp tục từ next_stage hợp lệ, giữ counters. Investigator chỉ xem và chờ.

### F3 — Evidence thiếu hoặc nguồn lỗi

Ghi gap → planner đổi query/nguồn trong ngân sách → nếu vẫn chưa đủ, tạo kết quả insufficient/mismatch/review phù hợp → dossier nêu limitations. Không tìm thấy và lỗi nguồn phải khác nhau trên timeline.

### F4 — Sửa hoặc tìm thêm sau review

Reviewer gửi action có reason/expected_version → server tạo version mới và vô hiệu approval liên quan → request_more tạo decision → gọi continue hợp lệ trong budget cũ → tính lại assessment/dossier và duyệt lại.

### F5 — Restart

Refresh trình duyệt đọc state đã lưu, không tạo run mới. Restart backend giữa queued/running đánh dấu interrupted; người dùng có thể tạo run mới liên kết bản cũ. Checkpoint waiting_for_review đã lưu có thể tiếp tục sau restart khi decision hợp lệ. Không tự khôi phục external call dang dở trong MVP.

## 4. Mô hình trạng thái và nhãn UI

| Loại | Giá trị → nhãn hiển thị |
|---|---|
| Run | queued → Chờ chạy; running → Đang điều tra; waiting_for_review → Chờ chuyên viên; completed → Hoàn tất xử lý; interrupted → Bị gián đoạn; failed → Lỗi hệ thống |
| Assessment | supported_for_scope → Được bằng chứng ủng hộ trong phạm vi; contradicted_for_scope → Bị bằng chứng phản bác trong phạm vi; insufficient_evidence → Chưa đủ bằng chứng; scope_mismatch → Khác phạm vi; out_of_scope → Ngoài phạm vi; requires_human_review → Cần chuyên viên đánh giá; null → Chưa đánh giá |
| Review | pending → Chưa duyệt; approved → Đã duyệt; rejected → Từ chối; changes_requested → Cần sửa |
| Checkpoint | normalization → Xác nhận nhận định; assessment → Duyệt đánh giá; dossier → Duyệt hồ sơ |
| Evidence stance | support → Ủng hộ; contradict → Phản bác; uncertain → Chưa rõ; background → Thông tin nền |
| Scope field | matched → Phù hợp; mismatched → Khác phạm vi; unknown → Chưa xác định |

Run completed không phải dossier approved. Đề xuất supported/contradicted chưa được assessment review phải có nhãn “Đề xuất — chưa duyệt”, không hiển thị như quyết định đã xác nhận.

## 5. Yêu cầu chức năng và nghiệm thu

| ID | Yêu cầu MUST | Tiêu chí nghiệm thu | Screen / kế hoạch |
|---|---|---|---|
| FR01 | Input claim_text 1–5.000 ký tự; drug/event 1–200 | Thiếu/rỗng/quá giới hạn báo lỗi đúng field trước khi gọi nguồn | W01 / M01, M07, M08 |
| FR02 | Scope population/dose/route/time_window tùy chọn | Không có giá trị giữ unknown; không tự bịa thông tin | W01–W02 / M01, M04 |
| FR03 | Chọn ít nhất một trong PubMed/DailyMed/FAERS | Nguồn không hỗ trợ hoặc tập rỗng bị từ chối; thiếu nguồn ghi coverage gap | W01–W02 / M01, M03, M05 |
| FR04 | Default 8 steps/50 docs; trần 20/100 | Input vượt trần bị từ chối; UI hiển thị counters thực từ server | W01–W02 / M01, M05 |
| FR05 | Tạo investigation idempotent và một runner | Double create không tạo hai run; runner bận trả 409 runner_busy, không xếp hàng chạy ngầm | W01 / M02, M07 |
| FR06 | Lưu state, event và snapshot có hash | Refresh đọc lại dữ liệu; URL/version/locator truy được đúng nguồn | W02 / M02, M03 |
| FR07 | Ba connectors chuẩn hóa và lỗi có kiểu | Fixture đủ success/empty/error/partial; live smoke riêng từng nguồn | W02 / M03 |
| FR08 | Normalization giữ ambiguity | Brand nhiều ứng viên chuyển checkpoint; reviewer xác nhận trước tìm tiếp | W02 / M04, M05, M06 |
| FR09 | Extraction giữ quote, scope, result và limitations | Quote giả, ref ngoài investigation hoặc hash sai không thành evidence trực tiếp hợp lệ | W02 / M04 |
| FR10 | Kiểm tra scope theo sáu trường ưu tiên | Khác route/population/liều quan trọng chặn direct evidence; unknown không thành matched | W02 / M04 |
| FR11 | Phân tích contradiction theo phạm vi | Hai study khác population không tự thành phản bác trực tiếp; mâu thuẫn quan trọng chuyển review | W02 / M04, M05 |
| FR12 | Replanning theo gap và tìm contrary evidence | Có trace query/source thay đổi kèm gap/reason; không lặp fingerprint vô ích | W02 / M05 |
| FR13 | Dừng/abstain có reason | Hết budget/thiếu evidence/nguồn chính lỗi giữ gaps và next actions; FAERS-only không auto-support | W02–W03 / M05, M06 |
| FR14 | Review normalization/assessment/dossier tách riêng | Approve assessment không approve dossier; wrong role bị server từ chối | W02–W03 / M06, M07 |
| FR15 | Sửa có reason và expected_version | Stale version trả 409, không ghi đè; sửa claim/evidence tạo version và invalidation phù hợp | W02–W03 / M06, M07 |
| FR16 | Request_more/continue giữ budget | Double continue không chạy hai lần; counters không reset; hết budget không tiếp tục gọi nguồn | W02 / M05–M07 |
| FR17 | Dossier có citations, gaps, limitations và audit | Mỗi factual statement cần evidence hỗ trợ; nguồn lỗi/abstract-only và stop reason có trong hồ sơ | W03 / M06 |
| FR18 | Export kiểm tra current approval phía server | Unapproved hoặc approval cũ không tải chính thức được dù gọi API trực tiếp | W03 / M06, M07 |
| FR19 | Phân biệt refresh, review resume và crash | Refresh không tạo run; restart giữa run → interrupted; review checkpoint tiếp tục giữ state | W01–W03 / M02, M05, M10 |
| FR20 | Phân biệt synthetic/fixture/live/replay | Mode rõ trên UI, dossier và audit; synthetic không được trình bày như evidence thật | Tất cả / M02, M08–M10 |

## 6. Quy tắc evidence và phê duyệt

- Chỉ FAERS không đủ để agent đề xuất supported/contradicted; không suy incidence hoặc quan hệ nhân quả từ số reports.
- Null result với độ bất định cao không tự thành bằng chứng phủ nhận nguy cơ.
- Mismatch quan trọng và citation lỗi khiến evidence không đủ điều kiện tổng hợp trực tiếp; vẫn giữ để audit.
- Trùng kỹ thuật cùng source/ID/version/hash không tính lại documents. Report nghi cùng case chỉ được gắn candidate, không tự xóa.
- Sửa claim ảnh hưởng normalization, scope, assessment và dossier; phê duyệt nội dung bị ảnh hưởng mất hiệu lực.
- Sửa/loại/thêm evidence cần cập nhật gaps, contradiction, assessment/dossier; approval liên quan mất hiệu lực.
- Mọi export chính thức phải đúng dossier version hiện hành đã duyệt; không chỉ kiểm tra trạng thái nút trên UI.

## 7. Budget và xử lý lỗi

| Giới hạn/run | Mức đề xuất từ MVP |
|---|---|
| Search steps / documents | Default 8 / 50; trần 20 / 100 |
| HTTP requests nguồn | 80 |
| LLM calls | 80 |
| Input / output tokens | 150.000 / 25.000 |
| Retry nguồn lỗi tạm thời | Tối đa một lần sau lần đầu |
| Repair LLM output sai schema | Tối đa một lần |

Reserve bền vững trước external call; retries/repairs tính vào budget. Cache hit vẫn tính search step nhưng không tính request mạng mới. Budget cho dossier phải được dành trước hoặc dùng template fallback có gaps. Không reset counters khi reviewer yêu cầu tìm thêm.

Lỗi API có code/message/details: 401 chưa có token hợp lệ; 403 sai quyền; 409 version/checkpoint/runner conflict; 422 input sai. Nguồn lỗi được ghi trong investigation thay vì luôn biến thành API 500. Dùng thông báo có hành động tiếp theo, không lộ stack trace/secret.

## 8. API ở mức hợp đồng sản phẩm

Prefix `/api/v1`, trừ `/health`. Chi tiết payload được chốt trong M01; bảng này không chứng minh endpoint đã tồn tại.

| Endpoint | Mục đích |
|---|---|
| POST /investigations | Tạo, trả 202 + ID; idempotency key |
| GET /investigations và GET /investigations/{id} | Danh sách, summary/status/checkpoint/version/counters |
| GET /investigations/{id}/events?after_id=... | Timeline theo cursor |
| GET /investigations/{id}/evidence | Evidence, scope, citation và contradiction refs |
| GET /investigations/{id}/documents/{doc_id} | Nội dung/locator của document thuộc investigation |
| GET /investigations/{id}/dossier | Dossier và version/approval |
| POST /investigations/{id}/reviews | Action theo checkpoint; expected_version/reason |
| POST /investigations/{id}/continue | Tiếp tục hợp lệ, idempotent, giữ counters |
| GET /investigations/{id}/export | Markdown hiện hành đã duyệt |
| GET /health | Liveness backend |

MVP dùng `/continue`, không đưa `/resume`, `/cancel` hoặc auth tài khoản từ bản P01–P29 vào contract này.

## 9. Yêu cầu phi chức năng

| ID | Yêu cầu | Cách nghiệm thu |
|---|---|---|
| NFR01 | Backend/frontend bind loopback; một Uvicorn worker | Kiểm tra cấu hình demo và runner_busy |
| NFR02 | Token nhập theo phiên, giữ trong bộ nhớ; không bundle/URL/log secret | Kiểm tra direct API, bundle và log; reload cần nhập lại token trước khi đọc state |
| NFR03 | Nguồn là dữ liệu untrusted; URL do adapters tạo theo allowlist | Fixture injection/redirect không thay policy hoặc tool |
| NFR04 | Markdown/nguồn không thực thi HTML/script | Kiểm tra renderer với XSS fixtures |
| NFR05 | State/version/audit bền vững trong SQLite | Test restart, stale updates và backup citation |
| NFR06 | Có label form, thao tác bàn phím, status bằng chữ | Review W01–W03; không chỉ dùng màu |
| NFR07 | UI không mất kết quả khi polling lỗi | Banner mất kết nối và retry; reload không khởi chạy mới |
| NFR08 | Tests offline, live smoke opt-in | Chạy suite không key/Internet; live workflow riêng |
| NFR09 | Nguồn/version/hash/model/prompt/parser/dictionary/mode trong audit | Mở lại chuỗi dossier → evidence → source snapshot |

Chưa đặt SLA latency hoặc uptime khi chưa có phép đo trên máy demo. Loading/queued/running được hiển thị trung thực, không dùng phần trăm hoàn thành giả.

## 10. Evaluation và release gate

20 claim: 5 development, 15 held-out, tách theo họ drug–event/tài liệu. Hai reviewer chuyên môn gán nhãn độc lập và xử lý bất đồng; nếu chưa có thì ghi bộ kiểm thử kỹ thuật. Keyword BM25 chỉ đo retrieval; RAG một lượt và agent có cùng corpus đóng băng/cấu hình phù hợp.

Mục tiêu nghiên cứu: Recall@20 ≥ 0,85; citation precision ≥ 0,95; unsupported-claim rate ≤ 0,02; scope-mismatch recall ≥ 0,80; reviewer time giảm ≥ 25% nếu thử nghiệm phù hợp. Ghi kết quả từng claim, mẫu số, raw results, limitations; không có mẫu số trả N/A.

Điều kiện release/demo: luồng UI đầu-cuối, ba live smokes có bằng chứng, bốn scenario có fixture, budgets/review/citation checks đạt và dựng lại từ clone sạch. Citation giả, bypass approval, export sai version hoặc vượt budget là lỗi chặn nghiệm thu dù metric trung bình tốt.

## 11. Kịch bản review wireframe và kiểm thử

| Scenario | Điều cần quan sát |
|---|---|
| D1 Claim quá rộng | Scope mismatch, phạm vi evidence thực có, thu hẹp hoặc abstain |
| D2 Mâu thuẫn biểu kiến | So sánh scope hai studies; không gọi phản bác trực tiếp khi khác population |
| D3 FAERS dễ diễn giải sai | Report-level data, limitations, tìm thêm literature/label; không incidence/causality |
| D4 Replanning | Query/source đổi vì gap, reason và evidence mới |
| E1 Lỗi nguồn/hết budget | Gap riêng, stop reason, evidence cũ còn đọc được |
| E2 Evidence sửa sau approval | Version mới, mất duyệt, export bị chặn |
| E3 Investigator gọi review API | Server từ chối, không chỉ ẩn nút |
| E4 Stale review/double continue | Conflict hoặc một lượt chạy hữu hiệu, giữ counters |
| E5 Restart giữa run | Interrupted và liên kết tạo run mới; không báo completed |

## 12. Những gì cần xác nhận trước chốt PRD

Người dùng thử và người gán nhãn; UI tiếng Việt; tên sản phẩm; bố cục desktop. [Workflow Archify](05_WORKFLOW.html) mô tả luồng điều tra, các checkpoint và điều kiện xuất hồ sơ. Mọi thay đổi phạm vi cần cập nhật Brief/PRD/wireframe và contract cùng nhau; không mặc định coi bản nháp là đã được nhóm duyệt.
