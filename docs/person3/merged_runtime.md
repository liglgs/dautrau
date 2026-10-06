# Chạy Người 3 trên code tổng hợp

> **AUTH-01 (2026-10-06):** cầu nối giao diện không còn nhận vai do trình duyệt khai
> (`X-Vigilens-Role`) và không còn token vai trò phía máy chủ. Đăng nhập bằng email + mật khẩu;
> tạo tài khoản bằng `scripts/auth_cli.py create-user`.

## Phụ thuộc và trạng thái

Người 1 cung cấp adapters/parser/snapshot/dictionary từ nguồn; Người 2 cung cấp schema, graph, gateway, budget và review/API; Người 4 dùng các endpoint để hiển thị kết quả. Người 3 có thể kiểm tra dịch vụ bằng fixture, nhưng cần Người 1/2 để nghiệm thu luồng nguồn thật. UI Người 4 dùng để kiểm tra hành trình người dùng; nhãn chuyên môn cần reviewer.

Runtime API hỗ trợ `person3` từ ngày 2026-10-03. Mỗi run/resume gắn normalizer/extractor/analyzer/dossier Người 3; `source_factory` Người 1 nhận claim đã chuẩn hóa. Model qua TransportProvider/LLMGateway; source HTTP và model calls tính riêng trong ngân sách.

## Terminal backend Windows

Tại thư mục gốc, cài dependencies theo runbook và cấu hình model/key, token trong `.env`, sau đó:

```powershell
$env:MVP_EVIDENCE_MODE = "person3"
$env:MVP_SOURCE_MODE = "live"
$env:MVP_DICTIONARY_PATH = "data/dictionaries/mvp_candidates_2026_10_02.json"
$env:MVP_PUBMED_MODE = "api"
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Chế độ này gọi dịch vụ nguồn/model đã cấu hình. Dừng backend cũ bằng Ctrl+C nếu cổng 8000 đang dùng. Tạo investigation mới để thử; investigation cũ giữ nguồn và quyết định đã lưu.

Dictionary hỗ trợ `metformin / diarrhoea`, `ibuprofen / gastrointestinal haemorrhage`, `lisinopril / cough`, `atorvastatin / myalgia`, `amoxicillin / rash`; có `diarrhea` và một số tên muối được attested. Từ tiếng Việt/brand ngoài dictionary cần mapping/review. Dictionary thiếu/sai/synthetic khiến cấu hình dừng trước khi mở store; `person3` với nguồn fixture bị từ chối.

Nếu dùng export PubMed đã import theo [runbook](../runbook.md#21-pubmed-local-từ-bản-export-thật), chủ động thay:

```powershell
$env:MVP_PUBMED_MODE = "local"
$env:MVP_PUBMED_CORPUS_ROOT = "data/pubmed-local"
```

DailyMed/FAERS vẫn qua HTTP. PubMed API lỗi không tự chuyển sang local. Các launcher corpus/demo vẫn là chế độ thử riêng.

## Terminal UI

Các token bên dưới phải khớp token backend của nhóm:

```powershell
$env:NEXT_PUBLIC_VIGILENS_DATA_MODE = "api"
$env:VIGILENS_API_BASE = "http://127.0.0.1:8000"
cd frontend
npm.cmd run dev -- --hostname 127.0.0.1
```

Mở `http://127.0.0.1:3100/app/investigations`. Ca development đầu tiên dùng `metformin`, `diarrhoea`; scope chỉ nhập khi nhận định xác định các trường đó. Kiểm tra quote/scope trong ma trận → duyệt assessment → continue → kiểm tra dossier → duyệt dossier → export. Thiếu evidence/lỗi extraction phải có gap/reason.

## Docker

Đặt `MVP_EVIDENCE_MODE=person3`, `MVP_SOURCE_MODE=live`, model/key trong môi trường hoặc `.env` của Compose, rồi dựng lại `docker-compose.mvp.yml`. Compose chuyển cấu hình model chính vào container; `.env` không được COPY. Dictionary verified đóng gói ở `/app/resources/dictionaries/`, tránh volume `/app/data` che mất.

Dùng `MVP_DOCKER_DICTIONARY_PATH` để thay dictionary bằng đường dẫn **trong container**; không truyền đường dẫn Windows. Proxy trên Windows dùng `GEMINI_DOCKER_BASE_URL=http://host.docker.internal:8317` nếu model của nhóm dùng proxy đó. Chưa dựng/chạy Docker live trong lần kiểm tra này.

## Kiểm thử và bàn giao

```powershell
python scripts/test_person3_backend.py --all
```

Script kiểm tra checkout từ thư mục tạm, không đọc `.env` thật, pytest chặn mạng ngoài loopback; ghi `eval/person3/merged-runtime-report.json`. Test mới `tests/test_evidence/test_person3_live_runtime.py` dùng parsers/graph/API thật với HTTP/model responses tự soạn: ba nguồn, aliases, counters, dedup, quote/hash/version, FAERS background, quote giả, schema repair, normalization checkpoint và hai lần review/export. Đây là kiểm thử kỹ thuật, không phải live smoke hoặc clinical gold.

M09 còn cần hai chuyên gia và đánh giá Người 4 chủ trì. Corpus/split draft và annotation checklist ở [real_sources.md](real_sources.md).

### Kết quả ngày 2026-10-03

- Checkout tổng hợp cộng thay đổi hiện tại: **442 passed, 1 skipped, 28 subtests passed**, Python 3.12.4, 31,48 giây. Skip không được tính là pass; subtests không phải test độc lập bổ sung.
- `scripts.export_openapi --check`: khớp contract; `git diff --check`: không lỗi whitespace; Compose YAML parse được.
- Không dùng key/dotenv thật hay gọi model/nguồn live. Ruff chưa có trong runtime cục bộ; Docker engine bị từ chối quyền truy cập, nên chưa kiểm tra build/container mới hoặc smoke live. Không thay các gate CI bằng kết quả này.
