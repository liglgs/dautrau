# Sửa ảnh hưởng của dotenv lên pytest

Ngày 2026-10-03, kiểm tra phản hồi về nhánh `tiendat` / PR #7.

## Lỗi xác nhận được

`tests/test_scripts/test_submit_log.py` import `scripts/submit_log.py` ở cấp module. Script trước đó gọi `load_dotenv()` và `_load_dotenv_fallback()` ngay khi import, đưa biến từ dotenv vào `os.environ` trong giai đoạn pytest collection. `Settings(_env_file=None)` vẫn đọc biến môi trường của tiến trình, nên các Gemini key phụ có thể làm sai pool và vòng quay trong test transport.

Đã tái hiện bằng dotenv và key giả, chặn mạng ngoài loopback: chạy chung hai file test cho `1 failed, 9 passed, 3 subtests passed`, với lỗi `key-1` không có trong `['key-2']`. Không đọc dotenv riêng của người dùng trong lần tái hiện. Chưa có bằng chứng một lượt gọi API trả phí đã xảy ra trước đây.

## Thay đổi

- `scripts/submit_log.py`: chỉ nạp dotenv qua `configure_from_environment()` khi chạy script trực tiếp. Import module không nạp dotenv. Pre-push vẫn đọc cấu hình khi gọi CLI.
- `tests/test_scripts/test_submit_log.py`: kiểm tra import không thay đổi môi trường và CLI vẫn đọc dotenv, cả khi có hoặc thiếu python-dotenv. Dùng file/key giả, không upload.
- `tests/test_model_transport.py`: đặt rõ các key phụ mặc định rỗng, reset round-robin giữa các test. `_env_file=None` không còn được hiểu như tắt `os.environ`.
- `tests/conftest.py`: cài chặn DNS và TCP ngoài loopback trong `pytest_configure`, trước collection; gỡ ở `pytest_unconfigure`. Fixture HTTP client import app khi sử dụng. Máy chủ test loopback vẫn được phép. Scripts chạy demo/model thật bên ngoài pytest không bị thay đổi.
- `tests/test_network_guard.py`: xác nhận chặn DNS, connect/connect_ex ngoài loopback và vẫn kết nối được máy chủ loopback.

## Kết quả kiểm tra

- Nhóm regression sau sửa: **20 passed, 3 subtests passed**.
- Toàn bộ `tests/`: **378 passed, 28 subtests passed** trong 63,59 giây, trên Python 3.12 cục bộ. Dùng dotenv và biến môi trường Gemini giả, tracing tắt, mạng ngoài loopback bị chặn.
- Báo cáo: `eval/person3/environment-isolation-report.json`.
- Chưa chạy lại GitHub Actions/Python 3.11 do CI của tổ chức đang bị chặn bởi billing. Ruff không có trong runtime cục bộ nên chưa xác nhận lint.

Đây là bản sửa local cần commit/push lên `tiendat` để cập nhật PR #7. Không cần thay đổi hoặc chia sẻ API key của người dùng.
