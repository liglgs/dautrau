# Thử Người 3 qua graph, backend và VigiLens

> **AUTH-01 (2026-10-06):** cầu nối giao diện không còn nhận vai do trình duyệt khai
> (`X-Vigilens-Role`) và không còn token vai trò phía máy chủ. Đăng nhập bằng email + mật khẩu;
> tạo tài khoản bằng `scripts/auth_cli.py create-user`.

Nhánh `tiendat` đã merge main và áp dụng phần Người 3. Runner API đã có chế độ `person3_demo`: normalizer, extraction, scope, contradiction và dossier của Người 3 chạy qua LangGraph, SQLite và endpoint review/export của Người 2. Nguồn tài liệu và model vẫn được giả lập, không cần API key. Chế độ này không phải demo y khoa với nguồn thật.

## 1. Kiểm thử tự động trước

Tại thư mục gốc repository:

```powershell
python scripts/test_person3_backend.py
```

Kết quả đã kiểm tra: **295 passed, 25 subtests passed** trên Python 3.12. Báo cáo: `eval/person3/backend-runtime-report.json`.

Lệnh chạy code checkout hiện tại, không dựng snapshot main. Nó kiểm tra đủ tám tình huống qua graph và luồng HTTP tạo cuộc điều tra → duyệt assessment → continue → dossier → duyệt dossier → export. Sửa quote sau khi duyệt làm mất hiệu lực approval; export bị chặn và phải đánh giá/duyệt lại. Quyết định reviewer trong test là giả lập trên SQLite tạm.

## 2. Mở backend thử

Trong terminal thứ nhất:

```powershell
$env:INVESTIGATOR_TOKEN = "person3-investigator-demo"
$env:REVIEWER_TOKEN = "person3-reviewer-demo"
python scripts/run_person3_demo.py
# Script tự bật VIGILENS_ALLOW_LEGACY_TOKENS=1: đây là đường chạy ngoại tuyến dùng khoá tĩnh cũ.
```

Giữ terminal chạy. Backend: `http://127.0.0.1:8000`. Swagger: `http://127.0.0.1:8000/docs`.

Script dùng SQLite riêng `data/person3-demo.sqlite3`, chạy trên `127.0.0.1`; không sửa `.env`. Dependencies đã chuẩn bị trong `.local-preview/python-runtime` trên máy hiện tại, được Git bỏ qua. Khi chạy ở máy khác, cài trong môi trường Python của bạn:

```powershell
python -m pip install -r requirements-person3-demo.txt
```

## 3. Mở giao diện nối backend

Trong terminal thứ hai, cũng tại thư mục gốc repository:

```powershell
cd frontend
npm.cmd ci --no-audit --no-fund
$env:NEXT_PUBLIC_VIGILENS_DATA_MODE = "api"
$env:VIGILENS_API_BASE = "http://127.0.0.1:8000"
npm.cmd run dev -- --hostname 127.0.0.1
```

Đợi `Ready`, mở `http://localhost:3100/app/investigations/new`. Không dùng `.local-preview/vigilens` nữa; `frontend/` là code đã merge.

Lần thử npm trong chat bị lỗi quyền `EACCES` khi tải gói từ npm registry. UI chưa được xác nhận trong trình duyệt; các lệnh trên cần chạy trong terminal người dùng để tải dependencies.

## 4. Nhập ca thử

| Ô nhập | Giá trị |
|---|---|
| Claim | Fictional demo: Drug Alpha and Event Alpha in the stated scope. |
| Thuốc | Drug Alpha |
| Biến cố | Event Alpha |
| Quần thể | adults |
| Liều | 10 mg/day |
| Đường dùng | oral |
| Thời gian | 30 days |

Đây là tên thuốc và biến cố hư cấu. Đừng nhập aspirin vào chế độ này để mong nhận bằng chứng thật.

1. Tạo cuộc điều tra; kiểm tra timeline có thông báo `Person 3 demo: synthetic sources and model` và bước đánh giá `Person 3`.
2. Xem evidence và mở nguồn để đối chiếu nguyên văn quote/locator. Ca mặc định có hai tài liệu hư cấu; agent vẫn tìm bằng chứng phản bác trước khi dừng.
3. Chọn vai trò reviewer trong giao diện, gửi quyết định duyệt đánh giá kèm lý do.
4. Bấm chạy tiếp để tạo dossier. Duyệt đánh giá chưa cho phép export.
5. Kiểm tra dossier, duyệt riêng dossier rồi tải Markdown.

Giao diện hiện chưa bật sửa evidence ở chế độ API: cần bộ chọn evidence và form nhập nội dung sửa do Người 4 nối thêm. Việc sửa sau duyệt và chặn export đã được kiểm tra qua HTTP API; không coi đó là đã kiểm tra qua UI.

## 5. Đổi tình huống

Dừng backend bằng Ctrl+C, chạy lại với một ca khác:

```powershell
python scripts/run_person3_demo.py --scenario fake_quote
```

Các tên ca: `match`, `route_mismatch`, `missing_scope`, `imprecise_null`, `fake_quote`, `contradiction`, `ambiguous_brand`, `faers_only`.

Tạo cuộc điều tra mới sau khi đổi ca. Riêng `ambiguous_brand`, nhập thuốc `Brand Ambiguous`: graph dừng tại normalization trước khi tìm nguồn. Các ca khác dùng input trong bảng trên.

## 6. Cấu hình trong backend nhóm

Backend `src.main:app` cũng nhận `MVP_EVIDENCE_MODE=person3_demo` và `MVP_PERSON3_DEMO_SCENARIO=match`. Mặc định `fixture` giữ các ca demo của Người 2. Chế độ Người 3 sẽ được cắm khi `configure_mvp()` khởi tạo runner; thay đổi cấu hình cần restart.

Người 2 cần review các file chung, nhất là cấu hình runner, checkpoint khi sửa cuộc điều tra đã hoàn tất và quy tắc chỉ đếm bằng chứng hợp lệ trong đánh giá hiện tại. Người 1 vẫn cần bàn giao connector/tài liệu thật để có luồng live. Bộ 20 claim và nhãn chuyên môn của M09 vẫn chưa hoàn thành.
