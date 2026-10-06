# MVP điều tra an toàn thuốc — chạy và khôi phục demo local

Phạm vi: `docs/planMVPfinal.md`, SQLite và runner trong tiến trình, một worker Uvicorn. Compose mặc định của repo vẫn là luồng VMEC cũ; MVP mới dùng `docker-compose.mvp.yml`.

## 1. Chạy trên Windows

Python 3.11+, Node.js 24. Từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
# Tạo token riêng cho từng vai trò, chỉ giữ trong phiên PowerShell này.
$env:INVESTIGATOR_TOKEN = [guid]::NewGuid().ToString('N')
$env:REVIEWER_TOKEN = [guid]::NewGuid().ToString('N')
$env:MVP_SOURCE_MODE = 'fixture'
.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Trong cửa sổ PowerShell thứ hai, đặt cùng hai token vào biến môi trường phía server Next.js (không đặt `NEXT_PUBLIC_*_TOKEN`), rồi:

```powershell
cd frontend
npm ci
$env:NEXT_PUBLIC_VIGILENS_DATA_MODE = 'api'
$env:VIGILENS_API_BASE = 'http://127.0.0.1:8000'
$env:VIGILENS_INVESTIGATOR_TOKEN = $env:INVESTIGATOR_TOKEN
$env:VIGILENS_REVIEWER_TOKEN = $env:REVIEWER_TOKEN
npm run dev -- --hostname 127.0.0.1
```

Mở `http://127.0.0.1:3100`; backend có `/health`, `/ready`, `/docs`. Hai shell không tự chia sẻ biến môi trường: đặt hai giá trị token của shell đầu trong shell thứ hai trước khi gán các biến `VIGILENS_*`.

VigiLens hiện cho trình duyệt chọn vai trò và chưa có phiên đăng nhập kiểm chứng ở server. Gói này chỉ dùng demo local trên loopback, chưa phải triển khai công khai.

## 2. Fixture và nguồn thật

`MVP_SOURCE_MODE=fixture` là mặc định, không gọi nguồn thật hoặc model. Claim có kịch bản trong `tests/fixtures/mvp` dùng dữ liệu synthetic; claim ngoài bộ kịch bản trả thiếu bằng chứng.

`MVP_SOURCE_MODE=live` gắn PubMed, DailyMed và FAERS sau normalization. Đặt thêm `MVP_EVIDENCE_MODE=person3` và dictionary verified để bật normalizer/extractor/analyzer/dossier Người 3 qua gateway và budget Người 2; xem [cấu hình đầy đủ](person3/merged_runtime.md). Chỉ bật source live giữ extractor fixture. Chế độ person3 không bịa quote khi nguồn/model lỗi; có gap và checkpoint review.

`MVP_SOURCE_MODE=warehouse` lấy bằng chứng từ **kho ELT đã nạp** thay vì gọi mạng: chỉ mục RAG (Chroma) xếp hạng đoạn theo ngữ nghĩa, rồi toàn văn được đọc từ PostgreSQL — nguồn chuẩn của nội dung. Mọi tài liệu đưa vào điều tra đều có provenance trong kho (`retrieval_method=warehouse_rag`, `chunk_id`, điểm tương đồng, cờ chất lượng), trích dẫn trỏ đúng vào văn bản đã lưu. Chỉ mục thiếu hoặc lỗi trả về `error` của nguồn và được ghi thành gap, không bịa tài liệu. Truy hồi cục bộ không tiêu request nguồn nhưng vẫn tính một bước nghiệp vụ. Chạy chế độ này sau khi đã nạp kho và dựng chỉ mục (`python -m scripts.elt.run_elt`, `python -m scripts.elt.load_chroma`); kết hợp được với `MVP_EVIDENCE_MODE=person3`.

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_sources --live
```

Smoke lấy tối đa một tài liệu mỗi nguồn, không gọi LLM, lưu raw snapshots dưới `data/snapshots`, in ID/hash/status. HTTP timeout 15 giây, retry tối đa một lần và mỗi request/retry đều tính ngân sách trước khi gọi mạng. Host và content type được kiểm tra; redirect bị từ chối. XML dùng defusedxml, không mở external entities. Cache trong adapter chỉ giữ kết quả thành công/empty, không biến lỗi thành kết quả rỗng; cache chỉ tồn tại trong lượt runtime hiện tại.

DailyMed giữ từng SETID/version và route riêng, không khẳng định candidate label là đúng sản phẩm người dùng muốn. Chỉ lấy nhãn hiện hành, không phục dựng lịch sử. FAERS giữ báo cáo nhiều thuốc và reaction ở report level, không kết luận quan hệ nhân quả hoặc incidence. PubMed giữ metadata khi thiếu abstract, không gọi đó là full text. Tài liệu bị cắt có cảnh báo coverage. Xem API gốc: [NCBI E-utilities](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html), [DailyMed SPL](https://dailymed.nlm.nih.gov/dailymed/webservices-help/v2/spls_setid_api.cfm), [openFDA drug events](https://open.fda.gov/apis/drug/event/how-to-use-the-endpoint/).

Live smoke quan sát ngày 2026-10-02: DailyMed và FAERS trả tài liệu hợp lệ. PubMed chuyển sang `misuse.ncbi.nlm.nih.gov/error/abuse.shtml`; transport từ chối redirect. Vì vậy chưa nghiệm thu PubMed live trên mạng này. PubMed đã được kiểm tra offline với batch, structured abstract, metadata-only và XML lỗi.

### 2.1. PubMed local từ bản export thật

Khi cần tìm trên bản export đã tải, chủ động chọn corpus local. API lỗi không tự chuyển sang local; kết quả local không phải nghiệm thu PubMed API live.

Trên PubMed, tìm theo claim rồi dùng **Save → Format: PubMed** để tải export UTF-8 có tag `PMID`, `TI`, `AB`. Giữ nguyên file, không tự thêm abstract hoặc nhãn đánh giá. Lệnh import lưu raw export, query gốc, PMID, metadata, hash và locator:

```powershell
.\.venv\Scripts\python.exe -m scripts.import_pubmed --input data/downloads/pubmed-export.txt --corpus-root data/pubmed-local --query 'metformin diarrhea'
$env:MVP_SOURCE_MODE = 'live'
$env:MVP_PUBMED_MODE = 'local'
$env:MVP_PUBMED_CORPUS_ROOT = 'data/pubmed-local'
```

Khởi động lại backend. PubMed dùng retrieval lexical local; DailyMed và FAERS vẫn gọi API. Query local chỉ hỗ trợ văn bản thường, không hỗ trợ Boolean/field tag của PubMed. Mọi từ query phải có trong tài liệu; `empty` chỉ nói không có tài liệu phù hợp trong corpus đã nhập. Thiếu corpus, corpus hỏng hoặc query không hỗ trợ trả `error`.

Mỗi lượt tìm kiểm tra hash raw và parse lại export để đối chiếu title, text, metadata và locator. PMID có nội dung hoặc metadata thư mục khác lần nhập trước bị từ chối; dùng corpus mới khi cập nhật. `version=1` là phiên bản thu thập local, không khẳng định revision PubMed. Local không tiêu ngân sách HTTP; graph vẫn tính bước nghiệp vụ và số tài liệu.

Với Docker, Compose truyền `MVP_PUBMED_MODE` vào backend; corpus ở `/app/data/pubmed-local` trong volume. Chép export vào container, rồi chạy `docker compose -f docker-compose.mvp.yml exec backend python -m scripts.import_pubmed --input /app/data/downloads/pubmed-export.txt --corpus-root /app/data/pubmed-local --query 'metformin diarrhea'`. Đặt `MVP_SOURCE_MODE=live`, `MVP_PUBMED_MODE=local` và chạy lại `up -d`.

## 3. Docker demo local

Bật Docker Desktop. Đặt hai token như mục 1 hoặc giữ trong `.env` local (không commit). Không chạy đồng thời stack VMEC và MVP trên cùng cổng.

```powershell
docker compose -f docker-compose.mvp.yml config --quiet
docker compose -f docker-compose.mvp.yml up -d --build
docker compose -f docker-compose.mvp.yml ps
```

Backend dùng một worker; dữ liệu SQLite và raw snapshots chung volume `mvp_data`. Cổng host backend/frontend chỉ bind `127.0.0.1`. `/ready` kiểm tra store/runner; health này không xác nhận nguồn hoặc LLM đã tích hợp.

Thay đổi `NEXT_PUBLIC_VIGILENS_DATA_MODE` ở image frontend phải build lại vì Next.js đóng gói biến public lúc build. Token chỉ truyền lúc chạy, không đi vào build args/bundle. `Dockerfile.mvp` có fixture JSON cho demo offline và prompt Markdown cho runtime.

## 4. Backup, restore và kiểm tra citation

Dừng backend trước khi backup để database và raw snapshots thuộc cùng mốc. Không dùng `docker compose down -v` vì lệnh đó xóa volume. Với bản chạy trực tiếp trên host, dừng Uvicorn bằng Ctrl+C rồi:

```powershell
.\.venv\Scripts\python.exe -m scripts.mvp_backup backup --stopped --output data/backups/demo-001
.\.venv\Scripts\python.exe -m scripts.mvp_backup verify --source data/backups/demo-001
.\.venv\Scripts\python.exe -m scripts.mvp_backup restore --source data/backups/demo-001 --output data/restored-demo
$env:MVP_DB_PATH = 'data/restored-demo/mvp.sqlite3'
$env:MVP_SNAPSHOT_ROOT = 'data/restored-demo/snapshots'
```

Backup dùng SQLite backup API, manifest SHA-256, integrity check, parsed text hashes và raw hashes của tài liệu có snapshot. Destination phải chưa tồn tại, không ghi đè dữ liệu cũ. Raw snapshot trong bản restore được tìm theo source/raw hash; `metadata.raw_ref` là đường dẫn lúc thu thập và có thể còn trỏ tới vị trí cũ, không phải đường dẫn có thể di chuyển giữa máy. Citation qua API dùng text/locator đã lưu trong SQLite.

Khởi động backend với DB restore, mở một investigation có evidence, mở citation và kiểm tra quote trên đúng document/version. Với Docker, cần dừng backend và sao chép toàn bộ `/app/data` ra host hoặc dùng một container riêng gắn volume để chạy công cụ backup; không sao chép riêng SQLite khi app đang ghi.

Backup trên chỉ gồm SQLite và snapshots của tài liệu đã truy xuất. Để tiếp tục tìm bằng PubMed local sau restore, giữ thêm toàn bộ `MVP_PUBMED_CORPUS_ROOT` (manifest và raw exports), rồi cấu hình lại đường dẫn. Citation đã lưu vẫn đọc được từ DB/snapshots khi chưa khôi phục corpus; tìm tài liệu mới cần corpus.

Rollback local: dừng backend, giữ bản data hiện tại, checkout bản code trước và cấu hình `MVP_DB_PATH` tới một bản restore tương thích. Chưa có cam kết migration downgrade tự động.

## 5. Kiểm thử và giới hạn nghiệm thu

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts/mvp_backup.py scripts/mvp_deployment_smoke.py scripts/smoke_sources.py scripts/import_pubmed.py
```

Test mặc định chặn socket ngoài loopback; live tests phải đánh dấu `live` và chạy chủ động bằng `-m live`. HTTP fixtures dùng `httpx.MockTransport`, không cần API key.

Lockfile được lấy từ bộ dependencies đã chạy test, kiểm tra riêng khả năng resolve cho Python 3.11. Không coi việc có Dockerfile là bằng chứng Docker stack đã chạy thành công. M10 nghiệm thu cuối còn phụ thuộc M04/M08/M09, clone sạch, luồng UI → review → export, bốn demo và báo cáo đánh giá của các thành viên liên quan.
