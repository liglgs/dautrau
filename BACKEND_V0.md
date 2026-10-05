# MedReview VMEC-03 backend

Backend này dùng hồ sơ **mô phỏng** để đối chiếu thuốc. Không nhập hồ sơ người bệnh thật hoặc dùng kết quả để ra quyết định điều trị. Hệ thống chưa đánh giá tương tác thuốc.

## Chạy local

1. Tạo `.env` từ `.env.example`. Đặt `DEMO_PASSWORD` và khóa model. Với proxy OpenAI Chat Completions, đặt `GEMINI_API_KEY`, `GEMINI_BASE_URL=http://localhost:8317`, `MODEL_PROVIDER=openai_compatible`, `MODEL_NAME=gemini-3.6-flash-high`. `MODEL_PROVIDER=auto` cũng chọn proxy khi có cả URL và key. Có thể chọn `openai` hoặc `gemini` cho API chính thức với khóa tương ứng; xem [.env.example](.env.example).
2. Bật Docker Desktop, chạy `docker compose up -d --build`. Compose chạy PostgreSQL 16, migration, seed, FastAPI cổng 8000 và worker. Trong container, URL proxy trên host cần là `http://host.docker.internal:8317`; `docker-compose.yml` dùng URL đó mặc định khi `GEMINI_BASE_URL` trên host là `http://localhost:8317`.
3. Kiểm tra `http://127.0.0.1:8000/health` và OpenAPI tại `/docs`. Trong `frontend`, chạy `npm ci`, `$env:VITE_API_MODE='live'`, `npm run dev` rồi mở `http://127.0.0.1:5173`.

Các tài khoản seed và mật khẩu demo được mô tả trong [README](README.md). Không mở demo ra Internet khi dùng mật khẩu mặc định. Docker build loại `.env`, dữ liệu local và thư mục GitHub runner khỏi build context.

## Hợp đồng và ranh giới

- `/api/v1` dùng cookie phiên HttpOnly, quyền reviewer/clinician/responder, `Idempotency-Key` cho mutation và `expected_revision` cho cập nhật. Lỗi nghiệp vụ trả `code`, `message`, `request_id`, `retryable`.
- Nguồn TXT có `source_id`, `version`, `available_at`. Worker chỉ đọc nguồn đã đến mốc `visible_at`, kiểm quote nguyên văn trước khi lưu evidence, giữ liều/trạng thái chưa rõ ở dạng null/uncertain. Catalog và phép so sánh nằm trong `src/vmec.py`.
- Worker có lease, checkpoint và ngân sách bước/tool. Model chỉ đề xuất trích xuất và hành động; API kiểm quyền và điều kiện xác nhận/đóng/duyệt. Chỉ clinician xác nhận ý định kê đơn và duyệt bản tổng hợp.
- Phản hồi của người được giao là evidence mới, không tự đóng issue. Bàn giao chỉ thành `handed_off` sau khi người nhận xác nhận; trạng thái này vẫn inconclusive.
- Snapshot duyệt bất biến. Nguồn đến muộn qua research endpoint có `X-Research-Token` riêng, chuyển ca sang `changes_pending` và tạo một successor run cho event. Không đặt `RESEARCH_TOKEN` thì endpoint này khóa.

## Kiểm tra

Chạy `.venv/Scripts/python.exe -m pytest tests -q` và `.venv/Scripts/python.exe -m ruff check src research tests`. Test backend dùng SQLite/model stub để kiểm bất biến, còn bài Playwright `npm run test:live` dùng PostgreSQL/worker/model thật. Kết quả theo ngày và môi trường nằm trong [AC ledger](docs/acceptance/AC01-18.md). Benchmark riêng ở [research README](research/README.md).
