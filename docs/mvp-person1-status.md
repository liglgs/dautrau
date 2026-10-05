# Bàn giao MVP — Người 1

Cập nhật ngày **2026-10-02**, theo `docs/planMVPfinal.md`. Người 1 phụ trách storage/config/dependencies, connectors/parser/snapshots và môi trường/backup của M10. Runner/schema/graph thuộc Người 2; normalizer/extractor thật thuộc Người 3; UI, benchmark và bốn demo thuộc Người 4.

## Trạng thái theo mốc

| Mốc | Đã kiểm chứng | Còn cần nghiệm thu/phối hợp |
| --- | --- | --- |
| M02 | SQLite/state/version/audit, restart → interrupted, runner đơn và ngân sách qua bộ test hiện có | Người 2 review runner/gateway khi thay cách thực thi |
| M03 | Ba adapters đúng contract qua HTTP fixture; parser/locator, hash, query escaping, XML an toàn, timeout/retry/allowlist và request budget; DailyMed/FAERS smoke live đạt | PubMed API live vẫn bị redirect chặn truy cập; Người 3 review dữ liệu và report-level mapping |
| M10 — môi trường | Backend và VigiLens build/chạy Docker trên loopback; luồng fixture qua Next proxy → API → review → export; backup/restore mở lại citation và hồ sơ đã duyệt | Chạy lại từ clone sạch bởi thành viên khác; luồng live đầy đủ, bốn demo và đánh giá còn phụ thuộc Người 3/4 |

Không đánh dấu toàn bộ M03/M10 hoàn thành chỉ từ test offline hoặc từ việc có Dockerfile. Các checkbox nghiệm thu chung trong kế hoạch vẫn cần review của thành viên phụ trách.

## Đầu ra và phần hoàn thiện trong lượt này

- `src/services/sources/`: PubMed, DailyMed, FAERS; HTTP có trần, source error khác empty, raw snapshots SHA-256 và parser giữ locator trên đúng text đã lưu.
- `RunContext.source_factory`: tạo adapters từ normalized claim khi `MVP_SOURCE_MODE=live`; graph lưu mỗi request trước HTTP qua callback `on_request`. Cache hit dùng 0 request; adapter không tự ghi state/budget.
- Hoàn thiện lựa chọn **PubMed local** đang có trong workspace: `scripts/import_pubmed.py`, `pubmed_local.py`, cấu hình `MVP_PUBMED_MODE`/`MVP_PUBMED_CORPUS_ROOT` và test tích hợp graph. Không tự fallback khi PubMed API lỗi.
- Sửa kiểm chứng corpus local: parse lại raw export để đối chiếu title, text, bibliographic metadata và sections; sửa manifest cùng hash không đủ để làm giả citation. Từ chối PMID trùng trong cùng export trước khi ghi; metadata author/journal thay đổi khi reimport được coi là conflict.
- `docker-compose.mvp.yml` truyền mode PubMed và giới hạn số tài liệu; corpus container nằm ở `/app/data/pubmed-local`.
- Sửa `vigilens/Dockerfile`: project root dùng `/workspace/vigilens` ở cả build/runtime. Build tại `/app` tái hiện lỗi prerender AppShell thiếu QueryClient trong Linux; chuyển đường dẫn, giữ nguyên dependencies và mã UI, đã build đạt ở bản probe và Dockerfile chính.
- `README.md` khôi phục tiếng Việt UTF-8 bị mất dấu và chỉ rõ kiến trúc MVP so với VMEC cũ; runbook bổ sung import/cấu hình/giới hạn/backup corpus local.
- Giữ công cụ backup/restore, lock dependencies và offline guard hiện có. Không thay normalizer/extractor fixture bằng suy luận live.

## Bằng chứng kiểm tra

| Kiểm tra | Kết quả ngày 2026-10-02 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests -q` | **314 passed, 1 skipped**; skip là kiểm tra symlink không được Windows cấp quyền; có 1 cảnh báo deprecation từ Starlette/AnyIO |
| Ruff `src tests scripts/mvp_backup.py scripts/smoke_sources.py scripts/import_pubmed.py` | Đạt |
| `python -m scripts.export_openapi --check` | Khớp; không sửa schema API |
| PubMed local tests | **24 passed**, gồm tampering, reimport conflict, unsupported query, thiếu corpus, CLI và graph/request budget |
| VigiLens Vitest | **8 passed** |
| VigiLens production build trên host, chế độ API | Đạt |
| Docker Python 3.11/Node 24, cài bằng lockfile và build | Đạt backend và frontend; container backend healthy, frontend chạy |
| Luồng fixture qua `/api/backend/*` của Next container | Tạo → checkpoint assessment → approve → continue → checkpoint dossier → approve → export Markdown đạt; investigator review bị 403; export trước duyệt bị 409; quote khớp locator |
| Backup/restore từ DB Docker khi backend đã dừng | Integrity/hash đạt; 2 documents; citation và hồ sơ đã duyệt đọc lại được |
| Live source smoke | DailyMed: `ok`, 2 HTTP, 1 document; FAERS: `ok`, 1 HTTP, 1 document; PubMed: `error`, 1 HTTP, redirect rejected |

Nghiệm thu Docker dùng project riêng `p066-person1-check`, cổng host `127.0.0.1:18066` và `127.0.0.1:31066`, volume riêng; không dùng dữ liệu của stack khác. Probe và output cục bộ nằm dưới `data/person1-verification/` (được Git ignore), gồm `approved-dossier.md`, DB/backup/restore và `stack-result.json`. Chúng là dữ liệu **synthetic**; không dùng làm kết quả benchmark hay bằng chứng y khoa.

Sau kiểm tra đã gỡ container/network của project thử bằng `down` không kèm `-v`; giữ volume riêng và các bản backup/output. Không để stack nghiệm thu tự chạy nền.

## Giới hạn bàn giao

- PubMed local chỉ tìm lexical trên corpus export đã nhập; không có cutoff lịch sử, không có full text và không chứng minh PubMed API hoạt động. `version=1` là phiên bản thu thập local; revision nguồn chưa biết được ghi rõ.
- Cache adapters hiện trong bộ nhớ, không phải persistent cache. Backup SQLite/snapshots không tự kèm corpus local chưa truy xuất; giữ thêm manifest/raw của corpus nếu cần tìm tiếp sau restore.
- DailyMed lấy nhãn hiện hành/candidate product; FAERS giữ báo cáo nhiều thuốc/reaction ở report level, không tự suy ra cặp nhân quả hoặc incidence.
- Normalizer/extractor mặc định vẫn là fixture. Người 3 phải gắn implementation thật vào `RunContext` trước nghiệm thu điều tra live.
- Vai trò VigiLens do trình duyệt khai báo, chưa có server session kiểm chứng; gói này dành cho demo local.
- Luồng đã kiểm tra qua HTTP proxy, chưa thay thế nghiệm thu thao tác trình duyệt, clone sạch, bốn demo và eval của Người 4.

Các lệnh chạy, smoke, import và backup/restore nằm trong [runbook](runbook.md); giao diện adapters/callback ở [điểm cắm tích hợp](INTEGRATION_PLUG_POINTS.md).

## Ghép vào foundation — kiểm tra ngày 2026-10-03

Gói Người 1 được ghép vào `feat/project-foundation`: ba connectors, PubMed local, config/runner/graph, tests và tài liệu. Giữ CI Docker, healthcheck frontend, backup/restore và override `MVP_DB_PATH` đã có trên foundation. README/ARCHITECTURE mô tả bản ghép này; phần Người 3 trên main chưa được đưa vào nhánh.

- Backend trên Windows/Python 3.14.5: **317 passed, 1 skipped**, một cảnh báo Starlette/AnyIO. Đây là kết quả trên bản ghép, khác bộ 314 tests local ghi ở mục lịch sử phía trên.
- Ruff cho `src`, `tests`, backup/deployment smoke/source smoke/import: đạt.
- OpenAPI `--check`: khớp; chạy với `PYTHONUTF8=1` để in tiếng Việt trên console Windows.
- Compose config mặc định và cấu hình DB restore: đạt. Các link tài liệu được kiểm tra; `git diff --check` đạt.
- Lượt ghép này chưa chạy lại live source smoke hoặc dựng/chạy Docker; kết quả Docker/live ở mục trên là bằng chứng ngày 2026-10-02. CI trên GitHub cần được xác nhận trên SHA được push.

## Tách PR trên main — kiểm tra ngày 2026-10-03

Các PR được chuẩn bị trên main `e48d5ce` theo thứ tự lint → Docker/CI → connectors/PubMed local. Giữ network guard chặn mạng từ trước test collection, cấu hình `person3_demo`, `evidence_analyzer`, các điểm gọi Người 3 trong graph, schema statements và guard dossier/review/export. Đã bỏ guard mạng cũ bị trùng khi port gói Docker.

- PR lint: **378 passed, 28 subtests passed**; Ruff đạt.
- PR Docker/CI sau lint và sửa backup: **387 passed, 1 skipped, 28 subtests passed**; Ruff/OpenAPI/Compose config đạt.
- PR connectors/PubMed local sau Docker và sửa ngân sách: **435 passed, 1 skipped, 28 subtests passed**; Ruff/OpenAPI và Compose config mặc định/restore đạt.
- Sau review độc lập, backup dùng `MVP_SNAPSHOT_ROOT` đang hoạt động, vẫn ưu tiên `--snapshots`; retrieval local/cache không bị chặn bởi quota HTTP đã hết, còn HTTP thật vẫn bị chặn trước khi gửi. Test hồi quy đã tái hiện lỗi trước sửa và đạt sau sửa.
- Các kiểm tra trên dùng Windows/Python 3.14.5. Một cảnh báo Starlette/AnyIO; skip liên quan quyền symlink trên Windows. Subtests không cộng thành test độc lập.
- Các PR chưa tự bật phân tích Người 3 cho retrieval live mặc định. Không chạy nguồn/model thật hoặc dựng lại Docker trong lượt tách PR; CI Python 3.11/Docker cần được xác nhận riêng trên đúng SHA.
