# Hướng dẫn thao tác qua ảnh và video fixture

[Video UI fixture](../../presentation/person4_ui_fixture_demo.webm) ghi các thao tác browser thật với API contract responses tổng hợp. TestDrug/TestEvent là hư cấu. Có nhãn fixture xuyên các đoạn chính; không có audio, nguồn/model live, tài khoản thật hoặc phê duyệt chuyên môn. Tên người trên sidebar là dữ liệu UI minh họa, không phải tên thành viên nhóm.

File dài 58,32 giây, 1440×900. Đã kiểm decode/seek/phát đến cuối bằng Chromium. [Media metadata và SHA-256](../../presentation/person4_ui_fixture_demo.media.json) giúp xác nhận file đã kiểm tra; [chapters](../../presentation/person4_ui_fixture_demo.chapters.json) là mốc thao tác xấp xỉ.

| Ảnh | Thao tác | Điều có thể kiểm tra |
|---|---|---|
| [01-claim](01-claim.png) | Nhập claim/drug/event, bắt đầu điều tra | Nguồn/budget bị khóa theo API hiện có |
| [02-timeline](02-timeline.png) | Mở tiến trình | Events từ contract fixture |
| [03-scope](03-scope.png) | Chọn hai evidence, so sánh | Khác quần thể/liều; UI không tự xác nhận contradiction |
| [04-quote](04-quote.png) | Mở citation | Quote khớp span Unicode, version và abstract-only; hash chưa kiểm tra được ghi rõ |
| [05-version-conflict](05-version-conflict.png) | Submit review khi version cũ | Lỗi 409 giữ reason; cần tải và đọc version mới |
| [06-approved](06-approved.png) | Duyệt checkpoint fixture, mở dossier | Review status và export theo response fixture |

File [approved-fixture-dossier.md](approved-fixture-dossier.md) là nội dung response tải xuống để minh họa, không phải dossier chuẩn nghiệp vụ hoặc kết quả agent. Bốn dossier scenario trong `data/demo/person4/dossiers/` do seed tạo riêng.

## Tái tạo

Trong `vigilens/`, sau `npm ci` và `npm.cmd exec playwright install chromium`:

```powershell
npm.cmd run test:e2e -- --config playwright.demo.config.ts
```

Cổng 3102 phải rảnh; không chạy đồng thời Next build hoặc E2E khác dùng cùng `.next`. Script chỉ dùng API fixtures phía browser, ghi lại sáu ảnh/video/chapters và file download trong các đường dẫn trên. Chạy lại sẽ cập nhật những artifacts do script này tạo. Trên Windows cần quyền dừng đúng server con do lượt kiểm tra tạo; không dừng server của công việc khác.

Review riêng việc tạo/lọc/duyệt bằng API và quyền server sau khi Người 2 bàn giao. Caption của video không phải chức năng sản phẩm; script thêm nó để công bố nguồn fixture trong bản ghi.
