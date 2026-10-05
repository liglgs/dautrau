# MedReview frontend

React/TypeScript/Vite hiển thị ba màn: danh sách ca, workspace đối chiếu, và bản tổng hợp để duyệt. Ứng dụng chỉ dùng hồ sơ **mô phỏng**. Chế độ `live` nói chuyện với FastAPI/PostgreSQL; chế độ mặc định dùng MSW/IndexedDB để diễn tập giao diện.

## Chạy

Từ `frontend`:

```powershell
npm ci
npm run dev
```

Để dùng backend/worker đã chạy bằng Docker Compose, đặt `$env:VITE_API_MODE='live'` trước `npm run dev`, rồi mở `http://127.0.0.1:5173`. Vite chuyển `/api` tới backend cổng 8000. Đăng nhập bằng tài khoản seed và `DEMO_PASSWORD` trong `.env`. Live mode dùng cookie phiên HttpOnly; browser không tự khai vai trò qua header.

Trong chế độ mặc định, MSW chạy ba ca `SIM-001` (khớp), `SIM-002` (câu hỏi/phản hồi), `SIM-003` (nguồn đến sau duyệt). Các nút chạy/phát nguồn mẫu của chế độ này là replay. Dữ liệu IndexedDB chỉ thuộc origin và browser hiện tại. Chế độ live gọi worker và model thật, có thể mất thời gian và phát sinh chi phí API.

Nhập gói theo [spec VMEC-03](../docs/spec/specvm03.md) §4.1: manifest JSON và tất cả file TXT được tham chiếu; tối đa 8 nguồn/gói, 12.000 Unicode code point/nguồn. Chỉ nhập dữ liệu tổng hợp. Evidence panel mở quote gốc qua ID nguồn/phiên bản; reviewer xác nhận có nguồn, clinician duyệt cuối. Responder chỉ thấy nhiệm vụ được giao.

## Kiểm thử

```powershell
npm run build
npm test
npx playwright install chromium
npm run test:e2e
```

Các lệnh trên kiểm TypeScript, unit/MSW và 11 bài Playwright diễn tập. Với Compose đang chạy và cấu hình model hợp lệ, dùng `npm run test:live` để kiểm một ca nhập mới, AI, evidence, duyệt và lỗi phiên/inbox trên backend thật. Test live tạo ca mô phỏng mới trong DB. Kết quả đã quan sát nằm trong [TEST_REPORT](TEST_REPORT.md) và [AC ledger](../docs/acceptance/AC01-18.md).
