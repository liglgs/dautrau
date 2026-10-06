# Triển khai demo local MVP và kiểm tra CI

Gói này bổ sung môi trường và kiểm tra tự động cho runtime MVP: SQLite, runner trong tiến trình, fixture synthetic, FastAPI và VigiLens. Demo mặc định không cần model key hoặc nguồn ngoài. Có connectors PubMed/DailyMed/FAERS và PubMed local; xem [runbook](runbook.md). Cấu hình `MVP_EVIDENCE_MODE=person3` + `MVP_SOURCE_MODE=live` ghép bộ phân tích/hồ sơ Người 3; [hướng dẫn](person3/merged_runtime.md) mô tả model và dictionary container. Giữ network guard; chỉ bật source live vẫn dùng extractor fixture.

## Chạy Docker trên Windows

Bật Docker Desktop. Từ thư mục gốc, tạo token riêng cho hai vai trò trong phiên PowerShell:

```powershell
$env:INVESTIGATOR_EMAIL = "dieutra@benhvien.vn"
$env:INVESTIGATOR_PASSWORD = [guid]::NewGuid().ToString('N')
$env:REVIEWER_EMAIL = "duyet@benhvien.vn"
$env:REVIEWER_PASSWORD = [guid]::NewGuid().ToString('N')
docker compose -f docker-compose.mvp.yml config --quiet
docker compose -f docker-compose.mvp.yml up -d --build --wait --wait-timeout 120
```

Mở `http://127.0.0.1:3100`; backend ở `http://127.0.0.1:8000`, `/ready` và `/docs`. Cả hai cổng host chỉ bind loopback. Một worker Uvicorn, database và snapshots giữ trong volume `mvp_data`. Không chạy đồng thời stack cũ dùng cùng cổng.

Frontend build chế độ API và mặc định xác thực bằng session. Đăng nhập bằng token tương ứng của backend; Next server proxy chuyển cookie `session_id` HttpOnly và backend kiểm tra vai trò từ session. Các request thay đổi dữ liệu phải có `Origin` trùng origin frontend. Gói này phục vụ demo local.

## Smoke luồng triển khai

Python 3.11+, cài dependencies bằng lockfile:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m scripts.mvp_deployment_smoke --output data/deployment-smoke.json
```

Giữ `INVESTIGATOR_PASSWORD` và `REVIEWER_PASSWORD` trong cùng phiên PowerShell, đúng với mật khẩu đã dùng khi khởi động stack. Smoke đăng nhập hai vai trò qua proxy, giữ cookie riêng và gửi `Origin`, rồi tạo một cuộc điều tra synthetic, chờ assessment, kiểm tra investigator không được duyệt, export bị chặn trước cả hai lần duyệt, approve assessment, continue, approve dossier rồi export Markdown. Mỗi quote được so với `document.text[start:end]`; output ghi ID, số evidence, byte và SHA-256 của export, không ghi token/cookie. Không gọi nguồn hoặc LLM thật; không dùng kết quả này làm benchmark y khoa.

## Backup/restore

Dừng backend trước khi backup để DB và snapshots cùng mốc. Dùng thư mục output mới; công cụ không ghi đè backup/restore cũ:

```powershell
docker compose -f docker-compose.mvp.yml stop backend
docker compose -f docker-compose.mvp.yml run --rm --no-deps backend python -m scripts.mvp_backup backup --stopped --output /app/data/backup-001
docker compose -f docker-compose.mvp.yml run --rm --no-deps backend python -m scripts.mvp_backup restore --source /app/data/backup-001 --output /app/data/restored-001
$env:MVP_DB_PATH = '/app/data/restored-001/mvp.sqlite3'
docker compose -f docker-compose.mvp.yml up -d --wait --wait-timeout 120 backend
.\.venv\Scripts\python.exe -m scripts.mvp_deployment_smoke --verify-result data/deployment-smoke.json
```

Lần verify đọc lại đúng cuộc điều tra đã duyệt và kiểm tra export/hash/quote sau restore. `MVP_DB_PATH` trong Compose là đường dẫn **trong container**; nếu chạy Uvicorn trực tiếp trên host thì dùng đường dẫn Windows phù hợp. Muốn lấy backup ra host, dùng `docker compose -f docker-compose.mvp.yml cp backend:/app/data/backup-001 data/backup-001`.

Backup mặc định lấy database trong `MVP_DB_PATH` và snapshots trong `MVP_SNAPSHOT_ROOT`, nên sau restore sẽ lấy đúng dữ liệu đang dùng. `--db`/`--snapshots` được ưu tiên hơn biến môi trường khi cần chọn đường dẫn khác.

Dừng gói demo bằng `docker compose -f docker-compose.mvp.yml down`. Không thêm `-v` nếu cần giữ database. CI dùng `down -v` chỉ cho volume thử nghiệm được tạo trong job.

## CI và giới hạn CD

> **Trạng thái hiện tại (06/10/2026):** CI đã được dựng lại ở commit `1f654cf` —
> `.github/workflows/ci.yml` gồm 3 job trên runner `ubuntu-latest` (backend: lint + kiểm OpenAPI +
> pytest offline; data-and-contract; frontend: tsc/lint/vitest), nhưng **chưa chạy trên GitHub**
> (việc R2-1-07 trong `docs/phan-cong-vong-2/TIEN_DO_THUC_THI.md`). Phần dưới đây mô tả bộ CI
> self-hosted trước đây và chỉ còn là bản mẫu; **đừng coi là bằng chứng CI đang xanh**.

`.github/workflows/ci.yml` chạy khi push `main`/`develop`/`feat/project-foundation`, PR vào `main` hoặc nhánh `codex/pr-mvp-*`, hoặc chạy thủ công:

1. Backend dùng lockfile, Ruff, test offline và kiểm tra OpenAPI.
2. VigiLens dùng `npm ci`, TypeScript, Vitest và build chế độ API.
3. Docker build/start toàn bộ gói, smoke qua proxy, backup/restore rồi kiểm tra lại hồ sơ đã duyệt; giữ summary artifact và log container nếu lỗi.

Các workflow dùng runner của đội hoặc pool chung theo label:

| Workflow | `runs-on` | Yêu cầu máy |
| --- | --- | --- |
| CI | `self-hosted` | Windows hoặc Linux; Docker job cần Docker chạy Linux containers, Compose v2 và cổng 8000/3100 trống |
| Frontend / Person 4 frontend | `self-hosted` | Windows hoặc Linux; Chromium và dependencies Playwright; cổng 3102/3103/8203 trống theo suite |
| Person 4 evaluation | `self-hosted` | Windows hoặc Linux; replay dùng Python, không phụ thuộc Bash |
| Backend (VMEC/PostgreSQL) | `[self-hosted, Linux]` | Linux có Docker cho PostgreSQL service container; GitHub cấp host port trống rồi workflow lấy port đó cho DATABASE_URL |

Không gắn label `Windows` hay `team-66` cho các job portable: GitHub có thể giao cho máy đội hoặc pool chung còn rảnh. Backend phải có runner Linux online; runner Windows không nhận được job này. Máy cần Git, internet và quyền cài dependencies; workflow cài Python 3.11/Node 24 bằng setup actions. Xem [yêu cầu self-hosted runner](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).

Docker CI đặt tên Compose project riêng theo run/attempt, cố định fixture source/evidence và bỏ model keys. Các job dùng cùng cổng Docker hoặc cùng browser suite được nối hàng bằng concurrency group; PostgreSQL dùng host port động để tránh xung đột với repo khác trong pool chung. Cleanup `down -v --rmi local` chỉ xóa stack, volume và image local của project thử nghiệm. Giữ các cổng Docker/browser trên trống khi máy nhận job.

Các nhóm dùng chung cổng bật `queue: max` để giữ các job đang chờ, tránh hai workflow E2E tự hủy job pending của nhau. Xem [quy tắc concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

Python jobs dùng `python -m pip/ruff/pytest` để luôn chạy đúng interpreter được setup action chọn. Pytest dùng thư mục con riêng trong `runner.temp`, tránh quyền hoặc file tồn đọng ở temp cá nhân của máy chạy runner.

Playwright workflow chỉ tải Chromium bằng quyền user, không chạy `sudo` cài OS packages trên pool chung. Runner Linux cần chuẩn bị dependencies hệ thống theo [hướng dẫn Playwright](https://playwright.dev/docs/ci#linux) trước khi nhận job.

Runner đội hiện được khởi động thủ công; sau khi đóng tiến trình hoặc khởi động lại Windows cần chạy lại `actions-runner/run.cmd`. Chưa cấu hình dịch vụ tự khởi động. Giữ repo private theo điều kiện cấp token của Phoenix; workflow chạy dưới quyền tài khoản runner nên chỉ dùng máy đội tin cậy.

Backend VMEC vẫn chạy migration/seed PostgreSQL; workflow Frontend kiểm tra VigiLens trong `frontend/`. CI và Docker smoke dùng fixture, không gọi nguồn/model thật. Hiện chưa có job tự triển khai lên VPS/cloud, registry hoặc môi trường production.

Kiểm tra GitHub Actions trên `main` ngày 2026-10-02 cho thấy runner GitHub-hosted chưa chạy do annotation: account payments failed hoặc spending limit cần tăng. Bản cấu hình này chuyển job sang self-hosted để dùng máy đội/pool chung; không sửa trạng thái billing của tài khoản. Job vẫn có thể chờ nếu không có máy online khớp label. Xem [lượt CI cũ được kiểm tra](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/actions/runs/36966676595).

Trước khi gọi CI đạt trên GitHub, cần run thành công trên đúng SHA được push. Docker local đạt chỉ chứng minh gói có thể chạy trong môi trường đã kiểm tra.
