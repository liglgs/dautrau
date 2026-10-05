# Wireframe — Ba màn hình MVP

Phiên bản 0.1 · Ngày 2026-10-02 · **Low-fidelity, nháp để review**.

Phạm vi: [PRD](02_PRD.md). Bản vẽ là tài liệu tĩnh; nút chưa hoạt động. Dữ liệu thuốc, biến cố, study và quotes đều synthetic. Không có kết quả nghiên cứu thật trong hình.

[Mở wireframe W01–W03](04_WIREFRAME.html) · [Mở workflow Archify](05_WORKFLOW.html)

Workflow được render bằng Archify từ PRD, đã qua validate/deliver/check/browser-check. Nội dung sơ đồ bằng tiếng Việt; các điều khiển có sẵn của viewer dùng tiếng Anh. Đây là thiết kế nháp.

## 1. Hướng thiết kế và lựa chọn

| Phương án | Ưu/nhược | Quyết định đề xuất |
|---|---|---|
| Ba màn hình, tabs trong chi tiết | Bảng evidence và hồ sơ đủ không gian; đi sát MVP | Chọn cho bản nháp |
| Wizard tuần tự mỗi bước một trang | Dễ hướng dẫn lần đầu; khó quay lại so sánh nguồn khi đang review | Chưa chọn |
| Chat làm màn hình chính | Dễ bắt đầu; khó nhìn coverage, version và đối chiếu evidence | Chưa chọn |

Desktop ưu tiên, bố cục grayscale, labels rõ, không dùng điểm “độ tin cậy” hay risk score chưa hiệu chỉnh. Evidence tiếng Anh giữ nguyên; trạng thái và hướng dẫn tiếng Việt. Nội dung kỹ thuật như database/model tokens không đi vào tác vụ chính của người dùng.

## 2. Bản vẽ

### W01 — Tạo và mở cuộc điều tra

[Xem bản vẽ W01](04_WIREFRAME.html#W01)

- Header: tên mô tả sản phẩm, mode có nhãn, vai trò phiên và nút đổi token.
- Cột chính: claim text, drug, event; scope tùy chọn trong vùng riêng; nguồn và giới hạn bước/tài liệu.
- Cột phụ: investigation đã lưu, status/version và mở lại.
- CTA chính “Bắt đầu điều tra”; thông báo điều kiện bị chặn ngay tại form.
- Không có dashboard admin, SSO, trường cutoff lịch sử hoặc nút cancel trong MVP.

Tương tác: create hợp lệ → W02. Mở investigation → W02 hoặc tab Hồ sơ. Double click dùng cùng idempotency key. Runner bận → giữ nguyên form, báo “Một cuộc điều tra đang chạy”, có link mở run đó.

### W02 — Tiến trình, bằng chứng và review

[Xem bản vẽ W02](04_WIREFRAME.html#W02)

- Summary có claim, scope, version và ba nhóm status riêng: run, assessment, review.
- Timeline cho thấy source/query/reason và ngân sách; chỉ có sự kiện đã lưu, không hiển thị hidden reasoning.
- Evidence matrix có stance, source, scope, quote và hạn chế nội dung.
- Inspector mở quote/version/locator/hash và scope fields; có nhãn abstract-only/partial/link-only.
- Contradiction mở hai evidence cạnh nhau, các khác biệt scope và classification.
- Gaps và lỗi nguồn có khu vực riêng; nguồn lỗi không được tô như evidence phản bác.
- Reviewer panel đổi theo checkpoint: normalization, assessment hoặc dossier. Investigator xem trạng thái chờ, không thấy các action ghi dành cho reviewer.

Tương tác: chọn evidence → inspector; chọn contradiction → comparison; review edit → yêu cầu reason/expected_version và invalidation; request_more → decision rồi continue khi hợp lệ. Hết budget → không tìm thêm trong run cũ; có hướng dẫn tạo investigation mới liên kết bản cũ. Tab Hồ sơ → W03.

### W03 — Hồ sơ và phê duyệt

[Xem bản vẽ W03](04_WIREFRAME.html#W03)

- Bản preview có claim/scope, assessment, search strategy, evidence, gaps, limitations, stop/abstention reason và audit ref.
- Header chỉ rõ dossier version và approval hiện hành.
- Review panel dành cho dossier, không coi assessment approved là dossier approved.
- CTA xuất chính thức bị chặn cho tới khi version hiện hành đã duyệt; hiện lý do bằng chữ.
- Sau sửa evidence, banner yêu cầu kiểm tra bản mới và duyệt lại; badge approved cũ không còn áp dụng.
- Citation mở inspector/nguồn tương ứng W02; bản preview không chạy HTML/script.

## 3. Luồng điều hướng

[Xem sơ đồ workflow tương tác bằng Archify](05_WORKFLOW.html).

Workflow mô tả nhánh sử dụng, không cho phép bỏ qua checkpoint. Với insufficient evidence, reviewer vẫn có thể duyệt một dossier mô tả thiếu dữ liệu, nếu citations/policy hợp lệ; không biến approval thành kết luận thuốc an toàn.

## 4. Trạng thái cần vẽ trong công cụ thiết kế

| Screen | Variant | Nội dung và hành động |
|---|---|---|
| W01 | Empty | Form trống, chưa có investigation, hướng dẫn bắt đầu |
| W01 | Input error | Lỗi đúng field; không gọi nguồn |
| W01 | Runner busy | Form còn nguyên; link run đang chạy |
| Tất cả | Token invalid/missing | Yêu cầu nhập token phiên; không có UI đăng ký tài khoản |
| W02 | Running | Timeline cập nhật, counters, evidence hiện có |
| W02 | Ambiguity review | Các ứng viên drug/event; reviewer xác nhận; investigator chờ |
| W02 | Scope mismatch | Sáu trường scope và lý do không dùng trực tiếp |
| W02 | Apparent contradiction | Hai evidence khác population/route, lời giải thích |
| W02 | Source error | Error riêng + gap + phương án tiếp theo trong budget |
| W02 | Budget exhausted | Lý do dừng; giữ evidence; không reset limits |
| W02 | Interrupted | Dữ liệu đã lưu; tạo run mới liên kết bản cũ |
| W02 | Polling lost | Banner retry, giữ nội dung đang xem |
| W02–W03 | Stale review | Không ghi đè; tải version mới và review lại |
| W03 | Draft | Preview, reason chưa export được |
| W03 | Approved current version | Approval/version/reviewer-local rõ; tải Markdown |
| W03 | Approval invalidated | Bản mới chưa duyệt, export khóa và hướng dẫn duyệt lại |
| W03 | Rejected/changes requested | Lý do quyết định; quay lại evidence hoặc sửa dossier |

## 5. Component inventory

StatusBadge có label; ModeBadge; ClaimForm; SourceSelector; BudgetFields; InvestigationList; SummaryCard; Timeline; EvidenceTable; QuoteInspector; ScopeFields; ContradictionCompare; GapList; ReviewPanel; VersionConflictBanner; DossierPreview; ExportGate.

Mỗi component hiển thị trạng thái từ contract chung. Quyền action và eligibility export vẫn do server kiểm tra.

## 6. Review bằng nhiệm vụ thực tế

Cho reviewer thực hiện D1–D4 trong PRD: tìm vì sao evidence không áp dụng, mở đúng quote, phân biệt mâu thuẫn biểu kiến, xem trace replanning, sửa evidence và hiểu vì sao cần duyệt lại. Ghi điểm khó hiểu và sửa wireframe trước khi chốt UI. Chưa có kết quả usability test ở bản nháp này.
