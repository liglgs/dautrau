# MedReview VMEC-03 — Phân việc nhóm 4 người trong 3 tuần

**Mốc rà soát:** 23/09/2026 · **Repo:** P-066 · **Commit nền:** `1f2dd92`.

Đây là bảng công việc dựa trên **sản phẩm hiện có**, dùng để nhận việc, kiểm thử và bàn giao. Giữ nguyên tài liệu cũ; yêu cầu chi tiết vẫn tra trong [spec](docs/spec/specvm03.md), [PRD](design/gate1/02_PRD.md) và [tổng quan](docs/TONG_QUAN_DU_AN_VA_MVP.md). Không triển khai lại các mục đã có chỉ vì checklist kế hoạch cũ chưa đánh dấu.

“State” trong tài liệu này nghĩa là **giai đoạn triển khai** S0–S3, khác trạng thái ca/agent/issue trong phần mềm. Lịch chính là **3 tuần**, D1–D15 là 15 ngày làm việc tính từ lúc nhóm nhận kế hoạch; chưa ấn định ngày Demo Day. Tuần 4 chỉ là phương án mở rộng nếu thực sự được thêm thời gian, không chứa điều kiện bắt buộc để bàn giao tuần 3.

## 1. Hiện tại đã đến đâu?

**Đã có MVP kỹ thuật chạy cục bộ và benchmark mô hình thật. Chưa đủ bằng chứng để gọi là bản triển khai Internet đã nghiệm thu hoặc sản phẩm lâm sàng.** Thông tin cũ “Docker chưa chạy/chưa có khóa model” đã được các commit và báo cáo mới thay thế.

### S0 — Nền đã hoàn thành, kế thừa và kiểm tra lại khi tích hợp

- [x] React/TypeScript/Vite: danh sách ca, workspace, nguồn, nhiệm vụ, tổng hợp và phiên bản; giao diện navy/xanh ngọc, có MSW và chế độ live.
- [x] FastAPI `/api/v1`, đăng nhập cookie HttpOnly, mật khẩu hash, quyền theo ca; vai trò reviewer/clinician/responder.
- [x] PostgreSQL, Alembic, Docker Compose, seed 5 tài khoản và 3 ca; worker lưu lease/checkpoint.
- [x] Nhập JSON/TXT, evidence có nguồn/phiên bản/quote, đối chiếu bằng code; trường thiếu giữ null/chưa rõ.
- [x] Tạo/trả lời nhiệm vụ, chờ/tiếp tục, xác nhận, bàn giao cần ack, duyệt đúng revision, snapshot và nguồn đến muộn.
- [x] Adapter model, lỗi thật không thay bằng dữ kiện giả; A/B1/B2 và bộ dữ liệu tổng hợp 10 dev + 30 test.
- [x] Báo cáo benchmark giữ riêng: **90/90 dòng, 301 yêu cầu model**, có manifest/checksum và báo cáo từng ca.
- [x] Bảng AC01–18 đã ghi `pass` với các giới hạn môi trường; CI backend/frontend đã có cấu hình.
- [x] Rà soát lần này chạy lại `.venv/Scripts/python.exe -m pytest tests -q`: **44 passed**, một cảnh báo deprecation của Starlette. Test này dùng fixture/model stub, không gọi model thật.

**Bằng chứng đã lưu, chưa chạy lại trong lượt lập kế hoạch này:** 19 Vitest, 11 Playwright MSW, 2 Playwright live đạt và 2 bài live tùy chọn bị skip; Docker/PostgreSQL/model thật theo [AC ledger](docs/acceptance/AC01-18.md) và [báo cáo frontend](frontend/TEST_REPORT.md). Không biến kết quả lịch sử thành kết quả mới. Checklist `[x]` ở trên xác nhận nền đã có, không xác nhận mọi trường hợp production đã được thử.

### Khoảng trống cần ưu tiên từ mã và tài liệu hiện tại

| Khoảng trống | Bằng chứng cụ thể | Hệ quả / việc giao |
|---|---|---|
| Độ phủ PostgreSQL còn hẹp | `tests/test_vmec_api.py` tự tạo SQLite; service PostgreSQL trong CI chủ yếu phục vụ migration/seed, không tự biến fixture thành PostgreSQL | TV3 bổ sung test DB thật, giao dịch đồng thời, lease/restart; TV4 hỗ trợ worker |
| Luồng live chưa bao trọn hành trình khó | `frontend/tests/live/live.spec.ts` chủ yếu nhập ca khớp → AI → duyệt và đăng nhập/inbox | TV2/TV3 bổ sung phản hồi → resume, bàn giao ack, nguồn muộn, 409 và giữ form |
| Chất lượng AI còn hạn chế | Test đã công bố: A precision/recall **0,6296/0,85**, B2 **0,6429/0,90**; lượt gọi A/B2 **186/75** | TV4 phân tích lỗi và tối ưu trên dev; không tuyên bố A tốt hơn B2 |
| Bộ ca và nhãn chưa được thẩm định độc lập | Dữ liệu tổng hợp; báo cáo chưa có chuyên gia rà nhãn/B0 | TV1 quản lý rubric/nhãn, tuyển người đánh giá; TV4 tạo dữ liệu mới có kiểm soát |
| Schema MVP giản lược hơn PRD | `Assertion` hiện có name/product/dose/frequency/type và evidence chung; chưa biểu diễn đầy đủ đường dùng, khoảng thời gian, field evidence theo PRD | TV1/TV3/TV4 lập bảng sai khác và chốt trường cần bổ sung; không suy AC pass là đủ mọi trường PRD |
| Trace vận hành chưa tương đương benchmark | `src/ai/model.py::ask_json` lấy `.data`, bỏ metadata token/model của transport; audit ca chủ yếu là chuỗi | TV4 giữ usage/model/latency, TV3 lưu và liên kết request/run; thu 5–10 trace bàn giao |
| Health chưa đo khả năng phục vụ | `/health` hiện trả `ok`, worker healthcheck bị tắt | TV3 thêm readiness DB, tín hiệu sống worker và giám sát hàng đợi |
| Chưa có bằng chứng triển khai Internet trong repo | Compose chỉ bind API localhost, Vite chạy riêng; chưa thấy cấu hình frontend production/HTTPS, backup/rollback | TV2 đóng gói frontend, TV3 dựng staging có giới hạn truy cập |
| CI có file nhưng chưa đủ bằng chứng pipeline release | Workflow chỉ PR vào main/push main–develop; Ruff chưa phủ thống nhất research/transport; chưa có coverage artifact | TV3 sửa phạm vi CI, TV2 giữ test MSW/live độc lập, TV1 thu link run đúng commit |
| Bàn giao BTC còn thiếu bằng chứng | JOURNAL/WORKLOG còn mẫu; presentation chỉ có README; README chưa đủ tên nhóm, screenshot và live URL | TV1 quản lý bộ nộp; từng người bổ sung bằng chứng của mình |

Không gọi các mục “chưa có bằng chứng trong repo” là chắc chắn chưa tồn tại ở nơi khác. Ngày D1 nhóm kiểm tra thêm tài liệu/URL đang giữ ngoài repo rồi mới nhận việc trùng.

## 2. Mục tiêu và phạm vi chốt cho 3 tuần

**Đầu ra cuối tuần 3:** một bản demo triển khai có HTTPS, giới hạn truy cập, dùng **hồ sơ mô phỏng + API/DB/model thật**, chạy được ba hành trình chuẩn; test và trace kiểm tra lại được; có phản hồi người dùng và đủ bộ bàn giao BTC. Người khác có thể clone/cấu hình/chạy theo README.

Ba hành trình phải trình diễn:

1. **Ca khớp:** nhập → trích xuất có nguồn → không hỏi thừa → tạo nháp → clinician duyệt.
2. **Ca thiếu thông tin:** tạo câu hỏi → responder trả lời → lưu nguồn → worker tiếp tục → reviewer/clinician xác nhận đúng loại; hoặc bàn giao có ack và vẫn ghi chưa giải quyết.
3. **Nguồn mới sau duyệt:** giữ snapshot cũ → `changes_pending` → một lượt xử lý tiếp theo → nháp mới → duyệt bản mới; revision cũ bị chặn.

Giữ phạm vi TXT/JSON, một lần nhập viện/ca, danh mục nhỏ, timeline dạng danh sách. Không đưa OCR/HIS, email/SMS, kê/ngừng/đổi thuốc, tương tác thuốc hay dữ liệu bệnh nhân thật vào đường găng. Việc hoãn tương tác thuốc so với đề gốc cần **TV1 có xác nhận của mentor**, không mặc định đã được duyệt.

Kiến trúc kế thừa: **React → FastAPI → PostgreSQL; worker Python ↔ PostgreSQL → model adapter**. `research/` là bộ đánh giá riêng, không phải worker production. Không bổ sung LangGraph, vector DB, Redis hay nhiều agent chỉ để giống ví dụ trong guide; spec §7.2 cho phép state machine DB hiện tại.

## 3. Phân công 4 thành viên

Tên người chưa được cung cấp, nên dùng TV1–TV4 để nhóm điền. Vai trò phát triển dưới đây khác tài khoản reviewer/clinician trong app.

| Thành viên | Vai trò và mục tiêu phải chịu trách nhiệm | Feature / phạm vi sở hữu | Kiểm thử và đầu ra chịu trách nhiệm |
|---|---|---|---|
| **TV1 — [Tên]** | **Product, UX, QA/nghiệm thu**: chứng minh người dùng hiểu và hoàn tất đúng luồng | Chốt scope, quy tắc nghiệp vụ, rubric data, kịch bản UAT; nội dung trạng thái/lỗi; ưu tiên backlog; phản hồi 3–5 người | Ma trận yêu cầu→test, nhãn có người rà, biên bản UAT, AC ledger, task.md, README/team, journal/worklog, deck/video |
| **TV2 — [Tên]** | **Frontend/UI**: ba màn chính và inbox dùng được trong live, kể cả khi lỗi | `frontend/`: nguồn theo trường, form đúng vai trò, chờ/khôi phục, stale revision, snapshot, responsive/a11y, build production | Vitest/Playwright, ảnh 390/1280 px, test live xuyên suốt; artifact frontend chạy trên staging |
| **TV3 — [Tên]** | **Backend, tích hợp và DevOps**: quyền/trạng thái/dữ liệu đúng khi dùng thật và khi lỗi | API/schema, DB/migration, transaction/idempotency, runtime persistence, CI, HTTPS, secrets, health, backup/restore/rollback | PostgreSQL test, kiểm đồng thời/restart, CI đúng commit, staging/live URL, runbook, đo tải và phục hồi |
| **TV4 — [Tên]** | **AI, Data engineering và Evaluation**: đầu ra có nguồn, đo được lỗi/chi phí, không rò tập test | `src/ai/`, extraction/catalog/compare trong `src/vmec.py`, quyết định worker; `research/`, prompt/version/model usage, error analysis | Regression AI, dataset card/manifest, A/B1/B2 trên dev và holdout mới nếu đổi model/prompt, trace/cost/latency, quyết định fine-tune |

**Quyền sửa file chung:** TV3 sở hữu `src/db.py`, migration, API và phần lease/event/transaction của `src/worker.py`; TV4 sở hữu nội dung prompt, action schema, compare và phần lựa chọn hành động. Mọi PR đụng interface chung cần người còn lại review. TV2 sở hữu types/client UI nhưng chỉ đổi contract sau khi thống nhất với TV3. TV1 giữ nhãn/test độc lập và không để TV4 tự chấm công trình của mình một mình.

**Năng lực giả định:** 15 giờ/người/tuần × 4 × 3 = **180 giờ**. Mỗi tuần giao 12 giờ/người, giữ 3 giờ/người cho review, tích hợp và sửa lỗi: **144 giờ công việc + 36 giờ dự phòng**. Các ước lượng là timebox; D1 phải điều chỉnh theo lịch thật. Không nhận thêm feature nếu phải dùng hết quỹ sửa lỗi.

## 4. Các state triển khai và điều kiện qua mốc

| State | Thời gian | Kết quả phải có | Điều kiện chuyển tiếp |
|---|---|---|---|
| **S0 — MVP/API v0 đã có** | Hoàn thành trước kế hoạch này | Các checkbox mục 1, báo cáo benchmark v1 | Kế thừa; không làm lại framework, seed, runner hoặc ba màn từ đầu |
| **S1 — Chốt MVP và dựng staging** | Tuần 1, D1–D5 | Contract rõ, regression nền, staging HTTPS hạn chế truy cập, ít nhất ca khớp gọi model thật | G1: clone mới chạy được; ca live từ nhập→duyệt; lỗi model hiện đúng; CI có bằng chứng; test quyền/nguồn/phiên bản không lỗi |
| **S2 — Kiểm nghiệm luồng khó và AI** | Tuần 2, D6–D10 | Live phản hồi/resume/bàn giao/nguồn muộn; dữ liệu/rubric v2; trace và phản hồi người dùng | G2: cả ba hành trình đạt; test PG đồng thời/restart đạt; có quyết định cấu hình AI dựa vào dev; bản release candidate đóng băng |
| **S3 — Nghiệm thu và bàn giao** | Tuần 3, D11–D15 | Test bản đóng băng, tải/khôi phục, kiểm độc lập trên staging, báo cáo và 10 deliverables | G3: không còn lỗi chặn; link truy cập và bằng chứng khớp commit; có người vận hành đến Demo Day + 7 ngày |

Không đánh dấu state “xong” chỉ vì đã hết tuần. Nếu G1/G2 trễ: sửa nguyên nhân và giảm hạng mục P1; không bỏ quyền server, evidence, revision, chờ/resume, ack hoặc người duyệt.

### S1 — Tuần 1: MVP hiện có → bản nhóm có thể tích hợp và deploy thử

**TV1 — Product/UX/QA, 12 giờ**

- [ ] **S1-P1 (3h, D1): Chốt scope và người nhận việc.** Điền tên TV1–4, lịch 15 ngày, tài nguyên deploy/ngân sách, danh sách liên hệ mentor và người rà nhãn. Ghi quyết định về tương tác thuốc, schema giản lược, điều kiện bàn giao. Đầu ra: decision log trong task/biên bản; các yêu cầu chưa chốt ghi rõ người xử lý và hạn D3.
- [ ] **S1-P2 (5h, D2–D3): Kiểm sản phẩm hiện tại.** Đi đủ ba màn/inbox bằng từng vai trò; lập lỗi có bước tái hiện, ảnh, mức ảnh hưởng. Đặc biệt phân biệt “agent xong”, “đã duyệt”, “đã bàn giao”, “đã giải quyết”. Đầu ra: ma trận FR01–12/AC01–18→test; ưu tiên tối đa 5 lỗi UX chặn luồng cho TV2.
- [ ] **S1-P3 (4h, D4–D5): Bộ thử và chuẩn bị UAT.** Soạn ba script demo + bài đọc nguồn, câu hỏi quan sát và form ghi thời gian thao tác/chờ riêng. Tuyển mục tiêu 3–5 người có đồng ý tham gia; ghi rõ ai là thành viên nhóm, người ngoài nhóm, chuyên gia. Đầu ra: lịch thử tuần 2; không có chuyên gia thì báo giới hạn, không tự xác nhận nhãn lâm sàng.

**TV2 — Frontend/UI, 12 giờ**

- [ ] **S1-F1 (3h, D1–D2): Khóa baseline frontend.** Chạy build, Vitest, MSW E2E; cấu hình test tránh dùng nhầm Vite live/MSW chung cổng. Đầu ra: lệnh tái lập, ảnh ba màn 390/1280 px và lỗi thực tế; không cập nhật ảnh chuẩn để che lỗi.
- [ ] **S1-F2 (5h, D2–D4): Sửa các điểm UX chặn công việc.** Theo S1-P2: ưu tiên ca cần rà lại, issue/evidence dễ đối chiếu, thiếu dữ liệu hiển thị rõ, nút duyệt nêu điều kiện, giữ form khi poll/lỗi. Phần evidence theo trường chỉ làm theo contract đã chốt S1-B1. Test: TC01–03, TC09–10, TC13.
- [ ] **S1-F3 (4h, D4–D5): Frontend production trên staging.** Tạo build live, phục vụ tài nguyên tĩnh và deep-link route qua cấu hình TV3; kiểm cookie, đăng nhập lại, cache và refresh URL. Đầu ra: ca khớp chạy live qua trình duyệt trên URL staging, không còn cần Vite dev server để demo. Test: TC01, TC05, TC15.

**TV3 — Backend/DevOps, 12 giờ**

- [ ] **S1-B1 (3h, D1–D2): Contract và môi trường tích hợp.** Đối chiếu schema API với PRD; lập quyết định cho route/strength/form/time/field evidence còn thiếu. Khóa schema v0 được chấp nhận hoặc chia phần bắt buộc vào S2-B1/S2-A2. Kiểm migration/seed trên DB test riêng, pin dependency bằng lock/constraints tái lập. Đầu ra: contract/sample payload để TV2/TV4 dùng.
- [ ] **S1-B2 (4h, D2–D3): CI thực sự dùng PostgreSQL.** Cho bộ test tích hợp trọng yếu nhận DB test PG qua cấu hình; giữ test SQLite nhanh riêng. Kiểm import rollback, scope/role, revision và snapshot trên PG. Sửa triggers để PR vào nhánh tích hợp nhóm chọn được kiểm; Ruff phủ `src research tests`, lưu test/coverage artifact. Test: TC02, TC05, TC09, TC14.
- [ ] **S1-B3 (5h, D3–D5): Staging HTTPS có giới hạn truy cập.** Cùng TV2 dựng frontend tĩnh + `/api` cùng origin + API/worker/PG, giữ DB nội bộ. Đặt tài khoản riêng, secret ngoài image, `SESSION_COOKIE_SECURE=true`, allowlist origin, chặn research endpoint từ Internet thông thường. Chốt model endpoint cloud truy cập được; không phụ thuộc proxy localhost máy cá nhân. Đầu ra: URL, cấu hình triển khai và kiểm sạch G1/TC15.

**TV4 — AI/Data, 12 giờ**

- [ ] **S1-A1 (4h, D1–D2): Rà dữ liệu và điểm xuất phát AI.** Kiểm manifest 10/30 ca, phân loại kết quả v1 thành extraction/catalog/compare/action/evidence. Tách FP ca khớp, FN, hỏi trùng; ghi rõ A chưa hơn B2. Đầu ra: bảng lỗi và tối đa 3 giả thuyết sửa trên dev. Tập test v1 đã công bố chỉ còn là regression, không tiếp tục gọi là holdout cho các lần tune mới.
- [ ] **S1-A2 (4h, D2–D4): Regression sát dữ liệu thiếu.** Thêm ca dev cho đơn cũ, PRN, alias mơ hồ, khác hàm lượng/dạng, g/mg/mcg, câu phủ định, hai thuốc trong cùng quote, Unicode và nguồn chứa chỉ dẫn. Test phải kiểm null/nguồn/chọn bước, không chỉ JSON parse được. Sửa một nhóm lỗi có tác động lớn nhất trong timebox. Test: TC03–04, TC11–12.
- [ ] **S1-A3 (4h, D4–D5): Trace model cho app live.** Giữ provider, requested/returned model, prompt version/hash, token, latency, retry/error và case/run ID khi qua adapter; cùng TV3 chọn nơi lưu. Không lưu secret hoặc chuỗi suy nghĩ nội bộ. Đầu ra: ít nhất 3 trace đầu tiên của staging; plan ngân sách lượt gọi cho S2/S3. Test: TC11, TC18.

**G1 — TV1 nghiệm thu với TV2/3/4:** ca khớp từ nhập file mới đến snapshot trên staging; bằng chứng đúng nguồn; 401/403/409/lỗi model quan sát được; CI/build đạt. Phản hồi/resume, bàn giao và nguồn muộn đã có mã nhưng phải chứng minh đầy đủ trên live trong S2.

### S2 — Tuần 2: kiểm nghiệm thực tế, củng cố dữ liệu và độ tin cậy

**TV1 — Product/UX/QA, 12 giờ**

- [ ] **S2-P1 (4h, D6–D7): Rà nhãn và tập đánh giá mới.** Cùng người rà thứ hai kiểm rubric/forbidden conclusions; ghi nguồn gốc, người gán, bất đồng và cách giải quyết. Nếu sửa prompt/model/catalog sau v1, giữ riêng **12 ca holdout v2 mới (2 ca/nhóm)** do TV1 giữ, khác họ ca dev; người phát triển không xem nhãn trước khóa cấu hình. Đây là pilot bổ sung, không thay hay xóa 30 ca v1.
- [ ] **S2-P2 (5h, D7–D9): UAT với mục tiêu 3–5 người.** Dùng hồ sơ mô phỏng, giao nhiệm vụ không hướng dẫn bấm từng nút; đo hoàn thành đúng, số lần cần trợ giúp, hiểu nhãn bàn giao/duyệt, thời gian thao tác và chờ. Đầu ra: số người thực tế, lỗi quan sát, giới hạn. Thành viên nhóm đóng vai không được gọi là B0 chuyên môn.
- [ ] **S2-P3 (3h, D10): Đánh giá G2 và đóng phạm vi release.** Chốt lỗi P0/P1, cấu hình AI, các field hỗ trợ/không hỗ trợ, quyết định có/không cần fine-tune. Chốt bản RC, rubric và ngưỡng trước lượt holdout mới; chuyển mọi feature mới không bắt buộc sang backlog tuần 4.

**TV2 — Frontend/UI, 12 giờ**

- [ ] **S2-F1 (5h, D6–D8): Luồng live nhiều vai trò.** Bổ sung Playwright phản hồi → nguồn → resume → xác nhận; bàn giao chưa ack/đã ack; giữ nội dung khi mạng lỗi sau gửi, hết phiên và retry cùng thao tác. Sửa các lỗi lộ ra. Test: TC06–08, TC10; gọi API thật, không dùng MSW để ghi đạt live.
- [ ] **S2-F2 (4h, D8–D9): Phiên bản và nguồn mới.** UI rõ bản đang xem, việc bàn giao còn mở, lý do chặn duyệt; nguồn mới không trộn vào snapshot cũ; cảnh báo 409 có cách tải lại mà giữ nội dung cần phục hồi. Test live: TC09, TC16; đối chiếu payload với TV3.
- [ ] **S2-F3 (3h, D9–D10): Sửa UAT và kiểm khả năng tiếp cận.** Sửa tối đa 3 lỗi UX có mức ảnh hưởng cao nhất; kiểm 390/1280 px, text Việt dài, Tab/Esc/focus, zoom 200%, bảng cuộn và nút không bị che. Đầu ra: ảnh trước/sau và kết quả TC13; dark mode chỉ P1 nếu còn giờ.

**TV3 — Backend/DevOps, 12 giờ**

- [ ] **S2-B1 (5h, D6–D8): Giao dịch và phục hồi PostgreSQL.** Hai request cùng revision, response/event trùng đồng thời, hai worker giành job; kill/restart worker quanh checkpoint. Chứng minh một hiệu ứng ghi, 409 khi stale, không reset counter, snapshot giữ nguyên. Sửa nguyên nhân nếu fail; đồng bộ contract bắt buộc đã chốt ở S1-B1. Test: TC06–09, TC16–17.
- [ ] **S2-B2 (4h, D8–D9): Theo dõi và giới hạn vận hành.** Tách liveness với readiness DB; heartbeat/lease/tuổi job cho worker; log có request/run ID; cảnh báo worker dừng hoặc model lỗi; giới hạn login/upload/start-run và ngân sách gọi model. Kiểm 403/origin, session hết hạn, nghiên cứu bị cô lập. Test: TC05, TC11, TC18–19.
- [ ] **S2-B3 (3h, D9–D10): Backup và bản triển khai có thể quay lại.** Backup DB, thử restore vào DB riêng và mở snapshot cũ; ghi quy trình migration một lần và rollback image tương thích schema. Đầu ra: runbook + mốc backup/restore đo được; không thử xóa volume demo đang dùng. Test: TC20.

**TV4 — AI/Data, 12 giờ**

- [ ] **S2-A1 (4h, D6–D7): Nguồn dữ liệu và dataset card.** Kế thừa synthetic hiện có; bổ sung tối đa 6 ca dev khó khác cách diễn đạt. Lập bảng candidate Synthea/MIMIC/RxNorm từ tài liệu định hướng: mục đích, license/điều kiện phải kiểm lại, schema, mốc thời gian, thiếu nhãn, chi phí tiếp cận. Không chờ dữ liệu hạn chế để làm MVP; không tải hay đưa vào model khi chưa xác minh quyền.
- [ ] **S2-A2 (5h, D7–D9): Một vòng cải thiện AI có đối chứng.** Sửa tối đa 2 nhóm lỗi lớn trên dev, ưu tiên compare/alias/prompt/action validation trước đổi model. Chạy A/B1/B2 cùng đầu vào và ngân sách đã chốt; ghi lỗi lẫn ca thành công. Rà assertion type/field evidence theo contract, không suy nguồn hỗ trợ chỉ vì có tên thuốc trong quote. Test: TC03–04, TC11–12, TC21.
- [ ] **S2-A3 (3h, D10): Khóa cấu hình và bằng chứng vận hành.** Chọn giữ A hoặc giới hạn phần chọn bước bằng ADR; B2 hiện là runner nghiên cứu, không tự chuyển thành worker live nếu chưa tích hợp/test. Đóng băng prompt/catalog/model/schema; đủ 5–10 trace cho khớp/hỏi/chờ/resume/lỗi. Ước lượng token/lượt/ca, USD chỉ khi có giá đã xác minh. Giao cấu hình/hash cho TV1 giữ holdout.

**G2 — TV1 và TV3 cùng chốt:** ba hành trình live đạt; test sai quyền/nguồn/phiên bản, chống trùng và restart PG đạt; UAT có bằng chứng; mọi sai khác PRD được sửa hoặc có quyết định thu hẹp minh bạch. Nếu chưa có người ngoài nhóm/chuyên gia, ghi thiếu bằng chứng và hạ mức kết luận; không tạo feedback hay chữ ký thay họ.

### S3 — Tuần 3: release, kiểm độc lập và bộ nộp BTC

**TV1 — Product/UX/QA, 12 giờ**

- [ ] **S3-P1 (4h, D11–D12): Nghiệm thu độc lập bản RC.** Chạy checklist TC01–21 cần thiết với một người không viết feature đó; cập nhật AC bằng lệnh, môi trường, commit, pass/fail/skip. Tổng hợp phản hồi S2; phân biệt lỗi sản phẩm với giới hạn benchmark. Nếu lỗi làm đổi prompt/logic sau khi mở holdout, đánh dấu holdout đó đã dùng và cần lượt đánh giá mới.
- [ ] **S3-P2 (5h, D12–D14): Deck và video.** Viết 10 slide, xuất PDF cùng bản PPTX; quay 3–5 phút từ staging, gồm hành trình chính và edge case, ghi rõ synthetic/live/replay. Nêu trung thực A/B2, giới hạn nhãn, giá trị UX chưa đo được. Thu tên/vai trò, nguồn số liệu và link kiểm được từ TV2/3/4.
- [ ] **S3-P3 (3h, D14–D15): Chốt 10 deliverables.** Cập nhật README, journal/worklog có tên/ngày/PR thật; kiểm quyền truy cập repo/video/deck/trace/URL trong trình duyệt riêng. Tập trình bày tối thiểu 3 lượt; chỉ tick hoàn thành khi artifact tồn tại và mở được.

**TV2 — Frontend/UI, 12 giờ**

- [ ] **S3-F1 (4h, D11–D12): Regression RC.** Build/Vitest/MSW/live trên server test tách biệt; lưu screenshot/trace khi lỗi. Thử máy/trình duyệt khác, reload deep-link, hết phiên và mất mạng; không sửa test bằng cách bỏ assertion nghiệp vụ. Test: TC01, TC06–10, TC13, TC15–16.
- [ ] **S3-F2 (4h, D12–D13): Sửa lỗi release và hỗ trợ demo.** Chỉ nhận lỗi P0/P1 từ nghiệm thu; sau sửa chạy lại nhóm bị tác động và full gate trước release. Chuẩn bị bộ ca nhập mô phỏng riêng cho demo, ảnh ba màn, hướng dẫn thao tác 1 trang; nhãn replay luôn rõ nếu có bản dự phòng.
- [ ] **S3-F3 (4h, D14–D15): Bàn giao frontend.** Kiểm bản build trên URL cuối, tài nguyên tĩnh/deep-link/cache; cùng TV1 quay video và cập nhật ảnh README; ghi cách build/config và kiểm phiên bản bundle khớp RC. Reviewer: TV3 kiểm contract, TV1 kiểm UX.

**TV3 — Backend/DevOps, 12 giờ**

- [ ] **S3-B1 (5h, D11–D12): Đo tải và phục hồi.** Đo xem/sửa API với **5 người đồng thời**, tách read/write, mục tiêu p95 ≤2s theo spec; báo model/queue latency riêng. Test API/DB/worker/model downtime và restore/rollback trên môi trường thử. Đầu ra: số mẫu, cấu hình, kết quả, RPO/RTO thực đo. Test: TC17–20.
- [ ] **S3-B2 (4h, D12–D14): Phát hành bản demo.** Lint/test/build/PG gate xanh đúng commit; pin image/config, migration theo runbook, smoke sau deploy. Kiểm HTTPS/cookie/origin, không lộ DB/secret/research token; chuẩn bị tài khoản BTC riêng. Có người và kế hoạch giữ dịch vụ đến Demo Day +7 ngày; không dựa vào proxy trên laptop đang mở.
- [ ] **S3-B3 (3h, D14–D15): Bàn giao vận hành.** Ghi URL, phiên bản, người trực, giới hạn tải/chi phí, backup/restore, rollback, xử lý hết quota/mất model. Thu link CI thật, kết quả khởi tạo sạch từ máy khác và log vận hành đã che secret. TV2 cùng kiểm rollout; TV1 xác nhận artifact nộp được.

**TV4 — AI/Data, 12 giờ**

- [ ] **S3-A1 (5h, D11–D12): Đánh giá bản đã khóa.** Nếu không đổi cấu hình AI, giữ benchmark v1 và bổ sung kiểm live/regression cần thiết; không chạy lại 90 dòng chỉ để tìm kết quả đẹp. Nếu đổi sau v1, chạy holdout v2 do TV1 giữ: **12 ca × A/B1/B2 =36 dòng**, công bố đây là pilot bổ sung nhỏ. Giữ mọi lỗi/timeout, mẫu số và manifest, không ghi đè `test-final` v1. Test: TC21.
- [ ] **S3-A2 (4h, D12–D13): Báo cáo và model card.** Ghi FP/FN theo nhóm, câu hỏi trùng/thừa, trường còn thiếu, quote tồn tại và mức hỗ trợ; token/calls/latency/cost, requested/returned model, giới hạn proxy. Chỉ báo resolved/false closure/handoff từ những ca thực sự có người xác nhận/ack; mẫu số 0 là N/A. So sánh A/B2 và ghi quyết định giữ/cắt agent dựa trên bằng chứng.
- [ ] **S3-A3 (3h, D14–D15): Bàn giao AI.** Giao prompt/catalog/model version, 5–10 trace đã chọn đại diện, hướng dẫn tái chạy dev/benchmark và giới hạn chi tiêu. Cùng TV1 chuẩn bị trả lời “agent hơn workflow ở đâu?”, “lỗi gì?”, “chi phí/ca?”; thiếu số liệu trả lời chưa đo. Không fine-tune sát ngày demo.

**G3 — nhóm cùng ký checklist:** không còn lỗi gây vượt quyền, evidence sai, mất dữ liệu/trạng thái, duyệt nháp cũ hay giả thành công model; đủ ba demo live, báo cáo đánh giá, backup/rollback và link bàn giao. Nếu chưa đạt, phát hành chỉ ở mức demo nội bộ có ghi giới hạn, không đánh dấu triển khai Internet đã nghiệm thu.

## 5. Bộ test chung để giao việc và nghiệm thu

Các TC dưới đây là phần kiểm chứng bổ sung/recheck của bản phát hành; không khẳng định hiện tất cả đã đạt. Mỗi test cần: dữ liệu synthetic riêng, role, bước thao tác, trạng thái trước/sau, expected result, actual result, commit/môi trường/ngày/người chạy và link bằng chứng. Không dùng DB benchmark/DB demo chung để test phá lỗi.

| ID | Thao tác / lỗi cần thử → kết quả mong đợi | Môi trường; owner | Mốc / AC |
|---|---|---|---|
| TC01 | Tìm/lọc, mở ca, quay lại, reload URL → đúng ca và bộ lọc; ngoài phạm vi không hiện | UI live + MSW; TV2 | S1 / AC16 |
| TC02 | JSON sai, thiếu TXT, trùng ID, chéo ca, 8 nguồn/12.000 ký tự/file và biên vượt giới hạn → lỗi rõ, không dữ liệu dở | API PostgreSQL; TV3 | S1 / AC01 |
| TC03 | Mở quote có emoji/chữ Việt tổ hợp, sai version/nguồn tương lai, quote chứa nhiều thuốc → đúng span và hỗ trợ trường; sai bị chặn | API + UI + AI fixture; TV4/TV2 | S1–2 / AC02,14 |
| TC04 | Đơn cũ, PRN, alias mơ hồ, khác hàm lượng/dạng, 0,5g/500mg → không tự suy đang dùng/liều; loại issue đúng | Domain + dev model; TV4 | S1–2 / AC03–05 |
| TC05 | Sửa role/header client, responder đọc ca khác, reviewer/agent duyệt, hết phiên → server từ chối đúng; không lộ dữ liệu | API PG + UI live; TV3 | S1–2 / AC09,14 |
| TC06 | Phản hồi trắng, gửi hai lần/cùng key và lỗi mạng sau commit → bị chặn hoặc chỉ một response/source; chưa tự đóng issue | API PG đồng thời + UI; TV3/TV2 | S2 / AC07–08 |
| TC07 | Chờ phản hồi rồi restart worker; trả lời sau đó → không gọi model lúc chờ, resume đúng, counter không reset | PG + tiến trình worker + trace; TV3/TV4 | S2 / AC07–08 |
| TC08 | Đề nghị bàn giao → vẫn mở; sai người ack bị chặn; đúng người ack → handed_off/inconclusive, resolved không tăng | PG + UI live; TV2/TV3 | S2 / AC10 |
| TC09 | Thiếu lý do/nguồn/trường xác minh, sai loại xác nhận, còn nguồn lỗi/việc mở; sửa ca khi modal duyệt mở → chặn hoặc 409, không có approval sai | API PG + UI; TV3/TV2 | S1–2 / AC05,09,11 |
| TC10 | Polling, offline, 401/503 khi đang gõ; gửi lại sau timeout → không mất form/nhân bản/hiển thị thành công giả | UI live + lỗi được tiêm có kiểm soát; TV2 | S2 / AC13,16 |
| TC11 | Model 403/429/timeout/JSON sai/trả rỗng, hết ngân sách → phân loại đúng, retry giới hạn, còn việc mở, token/calls ghi được | Mock transport + dev live mẫu; TV4 | S1–2 / AC13 |
| TC12 | TXT yêu cầu bỏ quyền/đổi y lệnh/đọc ca khác → chỉ là dữ liệu, action ngoài allowlist bị chặn, có audit | Worker/API; TV4/TV3 | S1–2 / AC14 |
| TC13 | Ba màn và inbox ở 390/1280 px, text dài, Tab/Esc/focus, zoom 200% → đọc được nguồn/nút, modal giữ/trả focus, badge có chữ | Browser + UAT; TV2/TV1 | S2–3 / AC16 |
| TC14 | Clone/cài mới, migration/seed trên DB rỗng; chạy lại seed → sẵn tài khoản/ca, không phá dữ liệu | PG test + CI; TV3 | S1 / AC17 |
| TC15 | URL HTTPS từ máy khác/incognito, refresh deep-link, logout/login, API origin/cookie và build live → luồng thật hoạt động | Staging; TV2/TV3 | S1–3 / AC16–17 |
| TC16 | Phát nguồn liên quan/không liên quan sau duyệt; gửi event lại → một successor, changes_pending, snapshot cũ nguyên vẹn sau reload/restart | PG + UI live; TV3/TV2 | S2 / AC11–12 |
| TC17 | Hai request cập nhật cùng revision, hai worker nhận job, crash sau ghi task trước trả kết quả → không mất update/nhân bản, hồi phục có giới hạn | PG + 2 worker thử nghiệm; TV3 | S2–3 / AC07–08,11 |
| TC18 | Model lỗi, worker chết, DB mất kết nối, job quá hạn → dashboard/log/cảnh báo chỉ đúng thành phần, có request/run ID, không lộ key | Staging test; TV3/TV4 | S2–3 / AC13,17 |
| TC19 | 5 người dùng đồng thời xem/sửa ca → p95 read/write báo riêng, mục tiêu ≤2s; login/run/upload vượt hạn bị chặn theo cấu hình | Load test staging; TV3 | S3 / yêu cầu vận hành §13 |
| TC20 | Backup→restore DB riêng; rollback app tương thích schema → xem snapshot/task/checkpoint; ghi mất dữ liệu/thời gian khôi phục thực đo | Môi trường phục hồi riêng; TV3 | S2–3 / AC17 mở rộng |
| TC21 | A/B1/B2 cùng visible_at/config/catalog; nhãn/nguồn tương lai ẩn; giữ ca lỗi, N/A khi mẫu số 0 → báo cáo đầy đủ, không tune test | Research offline + model thật khi đánh giá; TV4, TV1 review | S2–3 / AC15,18 |

**Tiêu chí dừng phát hành:** TC về quyền, nguồn, đóng/duyệt, snapshot, chống trùng hoặc phục hồi thất bại. Thiếu chuyên gia/B0 thì không được tuyên bố hiệu quả chuyên môn, nhưng có thể bàn giao demo kỹ thuật nếu ghi rõ. Lỗi trang trí nhỏ có thể ghi backlog; số test xanh không thay thế UAT.

**Lệnh nền hiện có:**

```powershell
# Tại repo gốc — môi trường ảo đã cài requirements.txt
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m ruff check src research tests
docker compose config --quiet

# Tại frontend/
npm run build
npm test
npm run test:e2e -- --workers 1 --timeout 60000
# Cần API/PG/worker/model cấu hình hợp lệ, dùng server test live riêng:
npm run test:live
```

PG concurrency/restore/load và coverage là **đầu ra phải bổ sung**, không giả định các lệnh hiện có đã kiểm hết. Live test có thể phát sinh chi phí; dùng tập dev và giới hạn đã chốt. Mục tiêu coverage theo guide: tổng ≥60%, tập trung API/logic trọng yếu; bổ sung `pytest-cov`/cấu hình ở S1-B2 rồi đo, không tự ghi con số chưa có.

## 6. Những việc AI/Data và triển khai cần nhớ

### 6.1. Dữ liệu: tìm có mục đích, quản lý cả nhãn và thời gian

- Kế thừa 10/30 ca và 26 mã thuốc tổng hợp; không xây bộ mới hoàn toàn để tick “tìm data”. Dùng dữ liệu mới để kiểm lỗi biểu đạt, phủ định, đơn vị, tên mơ hồ, phản hồi thiếu và nguồn đến muộn.
- Dataset card phải ghi nguồn/license hoặc cách sinh, mục đích, version/checksum, nhóm ca, họ ca, nguồn hiển thị từng mốc, người gán/rà nhãn, bất đồng và hạn chế. Hai biến thể cùng họ ca không chia sang dev/holdout.
- Tập v1 đã công bố giữ nguyên làm baseline/regression. Nếu tối ưu sau khi thấy kết quả test, tạo holdout v2 mới do TV1 giữ; không chỉnh v1 rồi tuyên bố kết quả độc lập. Tập mới 12 ca là giới hạn nguồn lực, phải báo cỡ mẫu nhỏ.
- Synthea/MIMIC/RxNorm là **candidate trong tài liệu cũ cần xác minh lại**, không phải nguồn đã được nhóm cấp quyền. Ưu tiên synthetic đủ dùng. Không lấy API danh mục làm nhãn ý định kê đơn; không mặc định dữ liệu nước ngoài phù hợp tiếng Việt.
- Có chuyên gia: rà rubric và các kết luận quan trọng, lưu xác nhận. Chưa có: người thứ hai kiểm tính nhất quán kỹ thuật và gọi đúng tên “nhãn tổng hợp chưa thẩm định”.

### 6.2. Fine-tune: chưa làm trong đường găng

Hiện chỉ có bộ ca nhỏ và nhãn tự soạn, lỗi còn ở cả compare/action/UX. Thứ tự xử lý: **phân tích lỗi → sửa rule/schema/evidence → prompt/tool → thử cấu hình model trên dev → mới xem fine-tune**. Không coi fine-tune là yêu cầu bắt buộc của AI production.

TV4 nộp quyết định ngày D10. Chỉ mở thử nghiệm sau tuần 3 nếu: lỗi lặp đã được chứng minh là khả năng model; có dữ liệu huấn luyện hợp lệ/được rà, train/validation/test độc lập theo họ ca, nhà cung cấp hỗ trợ, ngân sách và baseline rõ. Nghiệm thu cần so trước/sau về FP/FN/citations/latency/cost và bất biến không suy diễn/không tự duyệt; có version và khả năng quay về model cũ. Không dùng 30 ca test v1 hoặc 12 holdout v2 làm dữ liệu train rồi chấm lại trên chính chúng.

### 6.3. Mức triển khai cần đạt trong 3 tuần

Phương án triển khai tối giản để nhóm lập cấu hình: một môi trường Linux chạy reverse proxy HTTPS, frontend build tĩnh, API, worker và PostgreSQL có lưu bền; cùng origin để đơn giản phiên cookie. Có thể dùng dịch vụ tương đương nếu nhóm đã có tài khoản. TV3 xác minh hạn mức/chi phí và khả năng worker chạy lâu ở D1; không lấy bảng giá/free tier trong guide cũ làm giá hiện hành.

- **Cấu hình:** tách dev/test/staging, image/version cố định, secret server-side, tài khoản demo riêng, origin allowlist, cookie Secure/HttpOnly, giới hạn truy cập. Không build key vào frontend, không dùng Vite dev làm máy chủ bàn giao.
- **Model:** endpoint truy cập được từ môi trường deploy, timeout/retry hữu hạn, giới hạn run/token/calls, ghi model trả về và prompt version. Hết quota/lỗi provider giữ run lỗi và cho người xử lý; không âm thầm đổi model hay chuyển replay.
- **Quan sát:** request/run/issue ID, tool/action/error/timing/usage, hàng đợi và heartbeat worker. 5–10 trace chứa dữ liệu tổng hợp, đầu vào/đầu ra cần thiết và bước công cụ; không cần lưu chain-of-thought.
- **Dữ liệu/vận hành:** migration có thứ tự, persistent volume, lịch backup và diễn tập restore, retention cho demo/log; rollback bằng image tương thích DB hoặc phương án restore đã kiểm. Không coi container “running” hay `/health=ok` hiện tại là mọi thành phần hoạt động.
- **Đo lường:** số 130,615 ms p95 hiện tại chỉ là đọc danh sách local; đo read/write 5 người đồng thời trên staging và thời gian chờ/model riêng. Ghi USD unknown nếu chưa có giá tin cậy; budget phải gồm model, hạ tầng và thời gian rà nhãn.
- **Giới hạn bàn giao:** triển khai được trên Internet bằng dữ liệu mô phỏng không đồng nghĩa sẵn sàng xử lý hồ sơ bệnh nhân thật. Giai đoạn có dữ liệu thật cần đối tác, quyền dữ liệu, quy trình chuyên môn và thẩm định riêng; không nằm trong 15 ngày này.

## 7. Hướng dẫn BTC cần đưa vào công việc bàn giao

Nguồn là **bản guide đang lưu trong repo**, trọng tâm [chương 2](docs/guide/chapter-02.md), [7](docs/guide/chapter-07.md), [8](docs/guide/chapter-08.md), [9](docs/guide/chapter-09.md) và [deliverables checklist](docs/guide/deliverables/checklist.md). Chưa đối chiếu thông báo BTC mới ngoài repo; TV1 xác nhận deadline/cách nộp với mentor ở D1.

| Deliverable BTC | Hiện trạng | Việc còn lại / người chịu trách nhiệm |
|---|---|---|
| 1. Source code GitHub | Có mã và lịch sử; local refs cho thấy nền ở nhánh feature, chưa dùng đó làm bằng chứng main/CI đã phát hành | TV3 kiểm remote đúng repo BTC, PR/nhánh nộp, clone sạch và link CI; tất cả review phần mình |
| 2. README | Có hướng dẫn và mô tả; còn thiếu nội dung nhóm/ảnh/URL bàn giao | TV1 tổng hợp, TV2 ảnh, TV3 lệnh setup/env/API/live URL |
| 3. Architecture diagram | Có Mermaid và mô tả runtime | TV3 cập nhật deployment thật; TV2/TV1 đưa hình SVG/PNG dễ xem và link; không vẽ vector DB/LangGraph không chạy |
| 4. AI logs | Có hook coding và audit/benchmark; chưa thấy gói 5–10 trace app được chọn làm bằng chứng | TV4 trace model/tool, TV3 lưu/che secret; mọi người kiểm hook coding. Hai loại log có mục đích khác nhau |
| 5. Live URL/deploy | Có bằng chứng local, chưa có bằng chứng URL Internet trong repo | TV3 chính, TV2 tích hợp; kiểm browser khác/incognito, `/health`/readiness/API và duy trì đến Demo Day +7 ngày |
| 6. Video demo | Chưa thấy video/link thực tế trong presentation | TV1 chính, TV2 quay thao tác; 3–5 phút, có use case/edge case, HD, link người chấm mở được |
| 7. Pitch deck | Chưa thấy deck thực tế | TV1 chính; 10 slide; lưu bản chỉnh sửa PPTX và PDF nộp để đáp ứng cả hai hướng dẫn, tập nói 3 lượt |
| 8. Journal | `JOURNAL.md` còn mẫu | Mỗi TV ghi hằng tuần; TV1 tổng hợp, ít nhất 5–7 entry có quyết định/khó khăn/bài học theo guide |
| 9. Worklog | `WORKLOG.md` còn mẫu | Mỗi TV ghi ngày, task ID, PR/test, giờ thực tế; TV1 kiểm. Lịch sử cũ chỉ ghi theo commit/bằng chứng thật, không bịa giờ/tác giả |
| 10. Evaluation evidence | Có benchmark v1, AC và báo cáo frontend | TV4 AI metrics, TV3 coverage/load/PG, TV2 UI/live, TV1 feedback và traceability; ghi các mục chưa đo |

Lưu ý áp dụng:

1. Dùng **repo do BTC cấp**; không tạo repo ngoài tổ chức rồi mặc định được tính nộp. Giữ lịch sử Git; guide chương 2 có câu hỏi cuối cũ nói xóa `.git`, mâu thuẫn hướng dẫn đầu chương — không làm theo câu hỏi cũ đó.
2. Mỗi người cài/kiểm hook AI trên máy mình theo script dự án, giữ `.ai-log/` nguyên vẹn; không bypass pre-push hook. Kiểm việc log thực sự hoạt động, kể cả công cụ web dùng log thủ công theo hướng dẫn. Không chép key vào prompt/log. Không tự thay chính sách CODEOWNERS của BTC để vượt review.
3. Rubric trong chương 9 có 5 nhóm: Product, System Design, UI/UX, DevOps, Code Quality, mỗi nhóm 10 điểm. Mục tiêu nhóm đề xuất ≥35/50; đây không phải điểm tự bảo đảm. Ưu tiên đủ bằng chứng hơn thêm feature trang trí.
4. Guide checklist gợi ý dark mode, LangGraph/RAGAS và một số nhà cung cấp; đó không tự trở thành feature bắt buộc của VMEC-03. Dùng evaluation đúng tác vụ đối chiếu và kiến trúc thật; TV1 xác nhận nếu mentor có yêu cầu riêng.
5. Guide có lịch học 6 tuần, spec/định hướng cũ có giả định 8 tuần; lịch vận hành nhóm tại đây là **3 tuần**. Tên chiến lược dùng chuẩn hiện tại: **A=agent, B1=LLM trực tiếp, B2=workflow cố định, B0=người đọc**, không dùng nhãn A/B/C/D cũ để trộn số liệu.
6. Giá model/free tier trong guide có ngày tham khảo cũ; TV3/4 kiểm lại khi chọn dịch vụ. Không hứa USD/ca, giảm thời gian hay tăng độ chính xác khi chưa đo đúng.

## 8. Phối hợp hằng ngày và xử lý khi trễ

- Mỗi task có **một owner**, ít nhất một người review và link bằng chứng. Trạng thái: `todo → doing → review → done`; bị chặn ghi `blocked + nguyên nhân + người gỡ + hạn`, không tick `[x]`.
- Mỗi ngày báo 3 dòng: hôm qua xong task nào, hôm nay làm gì, đang vướng gì; cập nhật WORKLOG. Giới hạn mỗi người một task code chính đang làm; PR nhỏ theo task ID.
- TV3/TV4 chốt contract trước khi TV2 tích hợp; thay schema kèm migration/test/payload mẫu. TV1 review điều kiện nghiệp vụ; backend phải kiểm quyền độc lập với UI.
- Review chéo: TV1↔TV2 về trải nghiệm/acceptance, TV3↔TV4 về API/runtime/AI; không tự duyệt thay đổi trọng yếu. CI kiểm PR vào nhánh tích hợp thật, không chỉ tạo file workflow rồi bỏ đó.
- Definition of Done: hành vi đáp ứng expected result; test đúng môi trường đạt; reviewer xác nhận; docs/traceability cập nhật; không lộ secret; không regress ba hành trình. Mock pass không đổi thành live pass.
- D5/D10/D15 có buổi demo gate, dùng quỹ 3h/người/tuần cho review/tích hợp. Không mở feature mới sau D10.

| Rủi ro | Người theo dõi / hạn | Cách tiếp tục thực tế |
|---|---|---|
| Chưa có mentor chấp thuận scope | TV1, D3 | Ghi rõ phạm vi đề xuất và điểm cần quyết định; không tự thêm tương tác thuốc sát hạn |
| Chưa tuyển chuyên gia/người dùng | TV1, D5 | Làm usability nội bộ có nhãn đúng, tiếp tục mời; B0/chuyên môn ghi chưa thực hiện |
| Proxy chỉ chạy trên laptop | TV3+TV4, D3 | Dùng endpoint triển khai truy cập được và cấu hình được; smoke lại. Nếu đổi model, đánh giá lại trên dev/holdout mới |
| Không có host/ngân sách deploy | TV3, D1 | Chuẩn bị artifact/runbook đầy đủ, ghi live URL bị chặn; đây là deliverable chưa hoàn thành, local không thay thế |
| AI không tốt hơn B2 hoặc vượt chi phí | TV4, D10 | Giữ kết quả trung thực; giới hạn agent hoặc giữ baseline hiện tại. Chuyển B2 sang live cần task tích hợp/test riêng, không đổi tên cho xong |
| Test PG concurrent/restore phát hiện lỗi lớn | TV3, ngay khi có | Dùng giờ dự phòng, cắt P1; không mở demo Internet cho người dùng khi lỗi ảnh hưởng dữ liệu/quyền/duyệt |
| Không đủ 15h/người/tuần | TV1, D1 | Giảm scope từng timebox; giữ ba luồng, test quan trọng, deploy và bộ nộp |

**Cắt trước nếu trễ:** dark mode, animation, PDF export sản phẩm, semantic search, đa model, fine-tune, MIMIC và dashboard nâng cao. **Không cắt:** evidence, phân quyền, revision/snapshot, ack, chờ/resume, lỗi thật, test trọng yếu và báo cáo trung thực.

## 9. Tuần 4 chỉ khi được thêm thời gian

Không có task tuần 4 nào được dùng để hợp thức hóa gate tuần 3 chưa đạt.

- [ ] **TV1:** mở rộng phỏng vấn/người có chuyên môn, protocol B0 và rà nhãn sâu; giữ báo cáo kỹ thuật riêng với kết quả chuyên môn.
- [ ] **TV2:** xử lý UX P1/dark mode nếu có nhu cầu, hỗ trợ hiển thị field/schema mở rộng; nghiệm thu với người dùng mới.
- [ ] **TV3:** tăng độ phủ tải/soak test, tự động backup/restore và cảnh báo, dọn module sau khi regression đủ; mở rộng triển khai theo tải đã đo.
- [ ] **TV4:** thêm dữ liệu hợp lệ và thí nghiệm model/fine-tune có đối chứng nếu qua điều kiện mục 6.2; tạo holdout độc lập mới. Không mở thí nghiệm chỉ vì còn GPU/thời gian.

## 10. Đọc gì và bắt đầu từ đâu?

| Tài liệu | Dùng cho |
|---|---|
| [Tổng quan dự án/MVP](docs/TONG_QUAN_DU_AN_VA_MVP.md) | Cả nhóm đọc để hiểu sản phẩm hiện tại |
| [Spec VMEC-03](docs/spec/specvm03.md) | Quyền, trạng thái, contract, dữ liệu, AC và bất biến |
| [PRD](design/gate1/02_PRD.md), [wireframe/flow](design/gate1/03_WIREFRAME_UI_FLOW.md), [HTML tham chiếu](design/gate1/04_WIREFRAME.html) | TV1/TV2 đối chiếu hành trình; HTML là minh họa |
| [Định hướng/nghiên cứu](docs/spec/VMEC-03_DINH_HUONG_AGENT_DOI_CHIEU_THUOC.md) | TV1/TV4: dữ liệu, nhãn, câu hỏi nghiên cứu, giới hạn và nguồn cần xác minh |
| [Kế hoạch MVP cũ](docs/superpowers/plans/2026-09-23-vmec03-mvp.md), [thiết kế hoàn thiện](docs/superpowers/specs/2026-09-23-vmec03-mvp-completion-design.md) | Lịch sử triển khai; đọc bảng tiến độ thay vì suy từ checkbox cũ |
| [Kiến trúc](ARCHITECTURE.md), [backend](BACKEND_V0.md), [frontend](frontend/README.md) | TV2/TV3/TV4 tích hợp và chạy |
| [AC01–18](docs/acceptance/AC01-18.md), [frontend tests](frontend/TEST_REPORT.md) | Môi trường/kết quả/giới hạn đã ghi |
| [Research README](research/README.md), [kết quả v1](eval/results/report.md) | TV1/TV4 giữ baseline, rubric, manifest, test không rò dữ liệu |
| [BTC chương 2](docs/guide/chapter-02.md), [7](docs/guide/chapter-07.md), [8](docs/guide/chapter-08.md), [9](docs/guide/chapter-09.md), [checklist](docs/guide/deliverables/checklist.md) | Repo/logging, deploy, test, bộ nộp và rubric |
| [JOURNAL](JOURNAL.md), [WORKLOG](WORKLOG.md), [presentation](presentation/README.md) | Những mẫu phải điền bằng công việc thực tế |

Một số liên kết cũ trong brief/PRD/spec trỏ tới file đã đổi chỗ hoặc bản phân công chưa tồn tại; dùng bản đồ trên khi đọc. TV1 ghi lỗi liên kết vào backlog tài liệu; file này không xóa hay thay thế các bản cũ.

**Việc nhận ngay D1:** TV1 nhận S1-P1/P2; TV2 nhận S1-F1; TV3 nhận S1-B1; TV4 nhận S1-A1. Bốn người có thể bắt đầu song song trên nền đã có. Cuối D1 điền tên, giờ thực tế, deadline và link nơi lưu bằng chứng vào file này.
