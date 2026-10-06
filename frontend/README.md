# VigiLens — giao diện điều tra an toàn thuốc

Frontend Next.js trong `frontend/`, kết nối backend MVP qua proxy cùng origin. Dùng Node 24 và lockfile với `npm ci`.

## Chạy trang web

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --hostname 127.0.0.1
```

Mở http://127.0.0.1:3100. Mặc định dùng dữ liệu mock, không cần backend. Cấu hình theo `.env.example` trong `.env.local`, rồi khởi động lại dev server khi đổi mode.

## Kết nối backend và đăng nhập

Đặt `NEXT_PUBLIC_VIGILENS_DATA_MODE=api` và `VIGILENS_API_BASE` theo backend đang chạy. Mở `/login`, đăng nhập bằng email và mật khẩu của tài khoản do `scripts/auth_cli.py create-user` tạo. Proxy chỉ chuyển tiếp danh tính đã xác thực: chuyển cookie phiên HttpOnly và không trả session ID trong JSON cho trình duyệt. Trình duyệt không gửi vai; role lấy từ `/auth/me`; hết phiên quay lại login và giữ đường dẫn cần mở. Nút Đăng xuất hủy phiên máy chủ.

Các POST/PATCH/PUT/DELETE trong session mode cần Origin cùng host với trang web. Reverse proxy HTTPS cần giữ đúng Host/protocol; kiểm lại cấu hình trên môi trường triển khai. Backend xác thực bằng tài khoản có mật khẩu và kiểm quyền sở hữu trên các tuyến đọc ca (AUTH-01/AUTH-02). Gói frontend này không tự thay đổi backend của Người 2.

Không còn chế độ để trình duyệt tự khai vai hay gắn token vai trò (AUTH-01); cầu nối chỉ chuyển tiếp danh tính đã xác thực. Ở chế độ dữ liệu mẫu, màn login và công tắc role minh họa vẫn hoạt động nhưng chỉ là tiện ích demo.

## Kiểm thử

```powershell
npm.cmd run lint
npm.cmd run check:api
npm.cmd run typecheck
npm.cmd test
npm.cmd exec playwright install chromium
npm.cmd run test:e2e
$env:PERSON4_TEST_PYTHON=(Resolve-Path ../.tools/venv/Scripts/python.exe).Path
$env:MVP_SOURCE_MODE='fixture'
npm.cmd run test:integration
$env:NEXT_PUBLIC_VIGILENS_DATA_MODE='api'
npm.cmd run build
```

Mỗi browser suite dùng cache riêng trong `.next` để không lẫn cấu hình auth/data đã biên dịch. E2E dùng contract fixtures (không cần backend), Next cổng 3102. Integration dùng cookie session thật, FastAPI 8203/Next 3103/SQLite tạm và graph Người 3 với nguồn/model synthetic. Interpreter `.tools/venv` chỉ có trên máy hiện tại; clone khác phải đặt `PERSON4_TEST_PYTHON` tới Python đã cài `requirements.lock.txt`.

Types sinh từ `../docs/openapi.json` bằng `npm.cmd run generate:api`, không sửa tay file generated. Frontend gửi `config.sources`, `config.max_steps`, `config.max_documents` theo contract và gọi `/cancel`; server kiểm quyền hủy. Review luôn gắn version/checkpoint đang xem, giữ form khi 409 hoặc refresh lỗi. Evidence/dossier giữ dữ liệu đã tải kèm cảnh báo khi refetch lỗi; export phải được server cho phép. Summary list không được xem là số đo usage/config hoặc verified coverage.

## Phần còn phụ thuộc

Backend chưa trả typed contradiction pairs/duplicate candidates/coverage riêng đầy đủ. UI giữ mô tả gaps/limitations và quote/version, không tự suy ra pair hoặc kết luận chuyên môn. Gold độc lập, statement–citation review, nghiên cứu reviewer và nghiệm thu nguồn/model live nằm ngoài kiểm thử fixture. Video/deck/báo cáo đánh giá được hoãn theo yêu cầu.
