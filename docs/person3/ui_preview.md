# Thử UI VigiLens bằng dữ liệu mẫu

**Cập nhật:** nhánh đã merge main, runner Người 3 có chế độ thử qua graph/API. Dùng [hướng dẫn backend/UI](backend_demo.md) để chạy `vigilens/` ở mode `api`. Phần bên dưới lưu cách thử UI mock trước khi merge.

UI lấy nguyên bản `vigilens/` từ main `7c559e4`, đặt trong `.local-preview/vigilens/` để chưa cần merge Git. Thư mục preview được Git bỏ qua. Đây là giao diện đúng đề tài điều tra an toàn thuốc, gồm claim, investigation timeline, evidence, dossier và reviewer.

Từ terminal PowerShell tại thư mục gốc repository:

```powershell
npm.cmd --prefix .local-preview/vigilens ci --no-audit --no-fund
$env:NEXT_PUBLIC_VIGILENS_DATA_MODE = "mock"
npm.cmd --prefix .local-preview/vigilens run dev -- --hostname 127.0.0.1
```

Đợi terminal báo `Ready`, mở [danh sách cuộc điều tra](http://localhost:3100/app/investigations). Giữ terminal này chạy; Ctrl+C để dừng.

## Luồng nên thử

1. Mở một cuộc điều tra mẫu có sẵn để xem timeline và ngân sách.
2. Vào evidence, mở quote và scope.
3. Xem dossier và phần còn thiếu/giới hạn.
4. Chuyển vai trò reviewer trong giao diện và thử các thao tác review trên dữ liệu mẫu.
5. Thử form Điều tra mới để xem input và validation. Luồng này ở mock mode không thực hiện truy xuất nguồn hoặc phân tích thật.

Có thể vào thẳng khu vực làm việc, không cần tài khoản thật. Màn hình đăng nhập và vai trò là mô phỏng. Chế độ `mock` không cần API key/backend, không gọi model thật và chưa chạy code Người 3 mới viết. Các ca có sẵn phù hợp để xem toàn bộ màn hình; tạo ca mới ở mock mode chỉ là mô phỏng và có thể không tạo đủ evidence/dossier.

Muốn kiểm thử Người 3 qua UI: merge main, áp dụng integration patch, cấu hình runner bằng `make_person3_executor`, chạy backend và chuyển VigiLens sang mode `api`. Việc backend chạy fixture mặc định của Người 2 chưa chứng minh nó đã gọi phần Người 3.

Trạng thái chuẩn bị: code UI đã có; thử `npm ci --offline` trong bản sao tạm thất bại vì cache thiếu gói `zwitch`. Chưa chạy build hoặc xác nhận UI trong trình duyệt ở phiên này. Lệnh `npm ci` trên dùng mạng trong terminal người dùng để tải đủ dependencies. Chỉ mở dev server tại 127.0.0.1 cho bản demo cục bộ.
