# Báo cáo kiểm thử giao diện VMEC-03

Kiểm tra ngày 2026-09-23 trên bản checkout Windows này, với Node 24.15.0 và Playwright Chromium. Mọi ca đều dùng hồ sơ tổng hợp.

| Lệnh | Kết quả quan sát | Phạm vi |
|---|---:|---|
| `npm run build` | Đạt | Build TypeScript/Vite |
| `npm test` | 19 ca đạt | Hành vi thành phần/API qua Vitest + MSW |
| `npm run test:e2e -- --workers 1 --timeout 60000` | 11 ca đạt | Diễn tập trình duyệt với MSW và IndexedDB; chạy tuần tự để tránh tranh chấp tài nguyên cục bộ |
| `npm run test:live` | 2 ca đạt, 2 ca tùy chọn được bỏ qua | PostgreSQL 16 + FastAPI + worker + proxy mô hình tùy chỉnh: nhập ca mới → AI xử lý → bảng bằng chứng → bác sĩ phê duyệt; mật khẩu sai và hộp thư người tiếp nhận |

Kiểm thử live dùng phiên cookie và gọi mô hình thật. Kiểm thử MSW là diễn tập độc lập, không chứng minh luồng backend. Chất lượng mô hình và phép so sánh A/B1/B2 trên 30 ca được ghi riêng trong [benchmark](../research/README.md) và [bảng AC](../docs/acceptance/AC01-18.md). Giao diện không đưa ra quyết định lâm sàng; máy chủ kiểm tra việc xác nhận và phê duyệt.

Ở lượt chạy lại đầu tiên, `npm run test:e2e` kết nối nhầm tới Vite **live** còn chạy ở cổng 5173 nên toàn bộ ca MSW thất bại. Sau khi dừng server đó, 9/11 ca đạt với ba worker và timeout 30 giây; hai ca còn lại đạt khi chạy tuần tự. Lượt chạy đầy đủ 11 ca theo lệnh ở bảng trên sau đó đạt trong 35,7 giây. Nguyên nhân là tranh chấp server kiểm thử, không phải thay đổi mã sản phẩm.
