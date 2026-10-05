# Báo cáo triển khai Người 3 — 02/10/2026

## Bản đã kiểm tra

- Kế hoạch: `docs/planMVPfinal.md`.
- Main Người 2: `7c559e4f51c238dd393aac0d6f0bae66f0f2fd24`.
- Code Người 3 đã ghép trên nhánh `tiendat`; `docs/person3/integration.patch` hiện có 12 tệp chung.
- Python 3.12 trên Windows. Offline, không có source/provider network call.

## Kết quả đã chạy

### Bản chạy qua graph và API — cập nhật sau khi merge

```powershell
python scripts/test_person3_backend.py
```

**295 passed, 25 subtests passed**, trên checkout hiện tại. Dependencies đã cài riêng vào `.local-preview/python-runtime`, không thay Python hệ thống. Gồm bộ test dịch vụ/schema/prompt/gateway cũ, graph/runtime/review/dossier/API của Người 2 và các test runtime Người 3 mới.

- Tám tình huống chạy qua `InProcessRunner → LangGraph → Person 3`, nguồn/model giả lập. Match dùng hai tài liệu hư cấu để thử điều kiện dừng; ambiguity dừng trước retrieval.
- Runner singleton API bật Người 3 qua `MVP_EVIDENCE_MODE=person3_demo`. Lazy initialization dùng khóa cho phép gọi lồng, tránh deadlock.
- Luồng HTTP thực tế trong ASGI test: tạo → polling → evidence/document → duyệt đánh giá → continue → dossier → duyệt dossier → export. Kiểm tra token/role, stale version và budget khi resume.
- Sửa quote sau khi dossier đã duyệt: điều tra mở lại, assessment/dossier cũ bị vô hiệu, export bị chặn. Bằng chứng có context chưa xác minh sau sửa không được đếm vào điều kiện hai tài liệu hợp lệ.
- Dữ liệu các tình huống có ID riêng, có thể lưu nhiều ca trong một SQLite demo.
- Script mở backend: `python scripts/run_person3_demo.py`; hướng dẫn UI: `docs/person3/backend_demo.md`.
- Báo cáo máy đọc được: `eval/person3/backend-runtime-report.json`.

### Bộ snapshot và preview dịch vụ trước đó

```powershell
python scripts/test_person3_on_main.py --preview
```

**168 passed, 25 subtests passed.** Các test bao gồm ambiguity, six-field scope, thiếu target/dose, khác route, population chưa rõ, FAERS, uncertain null, contradiction, quote/offset/hash, cache, token/call budget và repair một lần. Phần M06 dùng SQLite store/review/export Người 2 để kiểm tra statement phiên bản, chặn hồ sơ chưa duyệt, approve assessment riêng, edit invalidation, request_more giữ budget, stale reference và fabricated statement. Chạy thêm tests schema/gateway/prompt do patch thay các giao tiếp này.

Preview đi qua normalizer → shared gateway với MockProvider → node extract/assess → dossier builder → shared validator/renderer. Không chạy retrieval, full graph hoặc approval; fixtures được nạp trực tiếp, nguồn/model giả lập. `supported_for_scope` trong preview chỉ là expected technical outcome của dữ liệu hư cấu.

- `python scripts/preview_person3.py`: 20/20 tình huống kỹ thuật cũ đạt.
- Compile Python code Người 3 và scripts mới: đạt.
- `git diff --check`: đạt cho diff tracked trong workspace.

## Chưa xác nhận

- Người dùng đã chạy UI và gửi ảnh danh sách, chi tiết, ma trận và trình xem quote từ backend Người 3. Đã sửa mapping population/dose từ evidence và ẩn JSON nội bộ; API trả scope_match cho các evidence có context Người 3. `npm run typecheck` đạt; 10 tests Vitest đạt. Chưa có xác nhận sau sửa hoặc hoàn tất duyệt/export qua UI.
- Các gate còn lại của toàn repository chưa chạy; kết quả 295 tests chỉ áp dụng các nhóm test nêu trên.
- Ruff, Python 3.11, model thật và documents từ ba connector thật chưa kiểm tra.
- Chưa có 20 claim/gold chuyên môn, 5 dev/15 held-out hoặc clinical metrics.
- Typed statements hiện chỉ tự sinh nguyên văn quote. Semantic fact/inference/hypothesis bị chặn cho tới entailment review riêng; quote/hash đúng không tự thành diễn giải verified.

Không suy precision, recall hoặc độ chính xác lâm sàng từ số test trên.
