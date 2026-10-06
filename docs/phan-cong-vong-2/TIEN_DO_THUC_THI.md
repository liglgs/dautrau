# Nhật ký tiến độ thực thi — vòng hai

Cập nhật lần cuối **06/10/2026**. Mẫu ghi theo mục 18.3 của [báo cáo chính](NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md).

`Task ID | Owner | Trạng thái | Artifact/SHA | Đã kiểm gì, bằng data nào | Thiếu đầu vào gì | Ai giao/ai nhận | Việc có thể làm tiếp | Người review/kết quả`

Trạng thái dùng đúng sáu mức của kế hoạch: `TODO` / `DOING` / `WAITING` / `DEV_DONE` / `INTEGRATED` / `PILOT_ACCEPTED`.

> **Nguyên tắc ghi:** chỉ đánh `DEV_DONE` khi có artifact và lệnh kiểm chứng chạy được trên máy này.
> Việc còn thiếu đầu vào bên ngoài (dữ liệu bệnh viện, dược sĩ duyệt, chuẩn vàng) ghi `WAITING`, không ghi "xong".

---

## 1. Nhánh công việc đã hoàn thành trong đợt này (nền tảng dữ liệu)

Đợt này ưu tiên **dữ liệu và cơ sở dữ liệu trước** (đúng chỉ đạo: "làm việc với dữ liệu và database trước"),
nên phần lớn kết quả nằm ở nhánh Người 1, cộng thêm hạ tầng API/RAG cho Người 2 và giao diện cho Người 4.

| Hạng mục | Bằng chứng trên máy |
| --- | --- |
| Gói 50 mẫu đã tải và kiểm băm | `data/mvp-candidates-50-2026-10-02.zip`, sha256 `6fbcfd…66f7`, 44/44 mục khớp `files.sha256.json` |
| ELT đầy đủ (PubMed + DailyMed + FAERS + tham chiếu) | `data/elt/manifests/20261005T192255Z-all.json`, `data/elt/reports/20261005T192255Z-all-quality.{json,md}` |
| Kho PostgreSQL | `docker compose -f docker-compose.elt.yml up -d --wait` → 66 tài liệu, 668 mục, 32 bản ghi PubMed, 13 nhãn DailyMed, 15 báo cáo FAERS, 182 dòng thuốc, 125 phản ứng |
| Chỉ mục vector | `vigilens_docs__gemini__gemini-embedding-001`, 1.865 đoạn, khớp 1.865 dòng `document_chunks` (lệch 0) |
| API kho | `GET /api/v1/drugs/lookup`, `/warehouse/overview`, `/warehouse/documents`, `/warehouse/documents/{id}`, `POST /rag/search`, `GET /ingestion/events`, `POST /ingestion/documents` |
| Kiểm thử | `tests/test_services/test_elt_quality.py` (12), `test_elt_parse.py` (7), `test_elt_warehouse.py` (8), `tests/test_api/test_warehouse_api.py` (7) — 34 bài mới, tất cả ngoại tuyến; toàn bộ `tests/`: 604 đạt, 1 bỏ qua, 2 lỗi có sẵn từ trước |
| Một lệnh cài đặt | `scripts/setup_elt.sh` (+ `--offline`, `--live`, `--reset`, `--no-rag`, `--skip-install`) |
| Tài liệu dữ liệu | `docs/data/{README,nguon-du-lieu,tien-xu-ly,cong-chat-luong,bao-cao-chat-luong,cau-truc-kho}.md` |

### 1.1 Sự cố đã gặp và cách xử lý (ghi lại để tái lập)

| # | Lỗi | Nguyên nhân gốc | Cách xử lý |
| --- | --- | --- | --- |
| 1 | `StringDataRightTruncation` khi nạp FAERS | cột `varchar(10)` quá hẹp cho giá trị thật (`COUNTRY NOT SPECIFIED`) | mở rộng cột trong `src/services/warehouse/models.py` + `_truncate()` phòng ngừa |
| 2 | `DomainError` nhúng vector 429 | hạn mức khoá Gemini, lô 50 quá lớn | lô 16, xoay 8 khoá, nhịp 1 giây/khoá, tôn trọng `Retry-After` |
| 3 | `AttributeError: 'str' object has no attribute 'text_sha256'` | `engine.connect()` + `select(Model)` trả về cột, không trả về đối tượng ORM | chọn đúng cột cần kiểm tra trong `scripts/elt/load_pg.py`; dùng `read_session` cho ORM |
| 4 | Hoạt chất DailyMed rỗng | XPath sai (`activeIngredientSubstance`), chỉ phủ một lớp | lặp `ACTIB`/`ACTIM`/`ACTIR` trong cả adapter và bộ phân tích |
| 5 | Chạy lại ELT vi phạm khoá ngoại `documents_pair_id_fkey` | `load_pairs` xoá rồi chèn lại cặp thuốc–biến cố đang được `documents` tham chiếu | chuyển sang cập nhật tại chỗ (upsert) + `ON DELETE SET NULL` cho `documents.pair_id` |
| 6 | Xoá tài liệu mồ côi trong Chroma | hàm xoá nhận sai tham số, không đếm được số đoạn | `purge_document()` đếm trước khi xoá, trả về số đoạn đã xoá |

### 1.2 Đợt rà soát mã (review/simplify) và các lỗi đã sửa

Nhánh `vorflux/elt-warehouse-rag` được rà soát độc lập; các phát hiện dưới đây đã sửa và có kiểm thử hồi quy.
Commit: `6c5d56c` (gộp mã trùng lặp, tái lập máy mới) và `16956fd` (cổng chất lượng, chỉ mục, khoá nhúng).

| # | Phát hiện | Mức | Cách xử lý | Kiểm chứng |
| --- | --- | --- | --- | --- |
| 1 | Bản ghi `reject` vẫn được ghi vào kho, trái hợp đồng cổng chất lượng | blocking | `run_elt` chỉ nạp `keep + quarantine`; `load_documents` chặn lần nữa và trả `skipped_rejected` | `test_rejected_document_never_reaches_the_warehouse` |
| 2 | `data/elt/dataset-spec.json` không được commit → máy mới không cài được | blocking | thêm ngoại lệ `!data/elt/dataset-spec.json` vào `.gitignore`, commit đặc tả | `git cat-file -e HEAD:data/elt/dataset-spec.json`; chạy thử bản clone sạch |
| 3 | Đoạn cũ trong Chroma không bị xoá khi văn bản ngắn lại hoặc tài liệu bị cách ly | blocking | xoá theo `doc_id` trước khi ghi lại + bước dọn (`prune`) cả hai kho | `test_reindex_drops_chunks_of_documents_that_left_the_index` |
| 4 | `setup_elt.sh` nạp kho và sinh vector hai lần | should-fix | bước 4 dùng `--skip-db`; bước 5 mới nạp | chạy lại script trên clone sạch |
| 5 | `python3 -m venv` hỏng khi máy chỉ có `python3.11-venv` | should-fix | tự chọn trình thông dịch có `ensurepip`, xoá `.venv` hỏng trước khi tạo lại | chạy trên clone sạch (chọn python3.11) |
| 6 | Khoá Gemini nằm trong query string; 401/403 làm hỏng cả lô | should-fix | gửi qua header `x-goog-api-key`; 401/403 xoay khoá kế tiếp | 604 bài kiểm thử đạt |
| 7 | Lộ chi tiết lỗi nội bộ ra HTTP | should-fix | trả mã chung (`RAG_INDEX_UNAVAILABLE`), ghi log phía máy chủ | kiểm thử API |
| 8 | Xoá tài liệu để lại sự kiện nạp; lỗi Chroma bị nuốt | should-fix | xoá sự kiện cùng mã tài liệu; ghi log thay vì im lặng | `test_purge_removes_rows_and_chunks` |
| 9 | `char_start/char_end` lệch văn bản lưu; điểm tương đồng có thể âm | optional | dịch con trỏ thay vì sửa văn bản; kẹp điểm về `[-1, 1]` | 604 bài kiểm thử đạt |
| 10 | Mã trùng lặp ở giao diện (chi tiết tài liệu, cảnh báo 503) | simplify | gộp vào `frontend/components/pv/warehouse.tsx` | `tsc`, `eslint`, 42 bài kiểm thử giao diện |
| 11 | Tài liệu từng `keep` rồi bị `reject` ở lần chạy sau vẫn nằm trong kho và trả về qua RAG | should-fix | `load_documents` xoá tài liệu bị loại (bản ghi con + đoạn vector + phát hiện của lần chạy hiện tại); `run_elt` truyền cả ba nhóm để bộ nạp tự chặn và tự dọn; `build_index` dọn Chroma | `test_document_that_becomes_rejected_is_removed_from_warehouse_and_index` (đỏ khi lùi mã cũ) |
| 12 | Cờ `manual_entry_not_verified_with_source` không hiện trên thẻ kết quả tìm kiếm RAG | should-fix | `WarehouseQualityFlagChips` + nhãn tiếng Việt trong `components/pv/warehouse.tsx`, dùng ở `/app/drugs` và panel chi tiết | `tsc`, `eslint`, 42 bài kiểm thử giao diện |
| 13 | Dọn sự kiện nạp dùng LIKE không thoát `_`/`%` → xoá nhầm sự kiện tài liệu khác | optional | `_ingest_event_pattern()` thoát ký tự đại diện trước khi so khớp | `test_delete_document_does_not_touch_other_documents_events` (đỏ khi lùi mã cũ) |
| 14 | `database "..." does not exist` khi chạy trên máy mới mà container kho đã tồn tại (đổi `ELT_DB_NAME`) | should-fix | `setup_elt.sh` kiểm tra và tạo cơ sở dữ liệu đích trong container trước khi nạp | chạy lại trên clone sạch: tự tạo `vigilens_elt_fresh`, kết thúc `EXIT=0` |
| 15 | 3 tệp HTML bản tin quốc gia lệch băm so với `manifest.json` của gói nghiên cứu (do lưu lại ở dạng LF khi nhập repo) | should-fix | ghi thêm `sha256_committed`/`bytes_committed` + `normalization` vào manifest; bước kiểm chứng chấp nhận đúng một trong hai băm và báo `normalized_files`; `verify_packet.py` chạy được trên máy mới (bỏ đường dẫn Windows) | `verify_research_packet` → 18/19 tệp đạt, 0 lỗi, 3 tệp chuẩn hoá; 2 bài kiểm thử mới |

### 1.4 Sửa lỗi tài liệu cũ (drift) phát hiện khi kiểm máy mới

| # | Chỗ sai | Cách sửa |
| --- | --- | --- |
| 1 | `docs/runbook.md` và `docs/PERSON4_TIENDAT_INTEGRATION.md` hướng dẫn `cd vigilens` — thư mục này không tồn tại (tên đúng là `frontend`) | đổi thành `cd frontend` |
| 2 | `docs/mvp-deployment.md` mô tả CI như đang chạy, nhưng `.github/workflows` đã bị xoá ở commit `db5c20f` | cập nhật ghi chú trạng thái: CI đã được dựng lại ở commit `1f654cf` (`.github/workflows/ci.yml`, 3 job trên `ubuntu-latest`) nhưng **chưa chạy trên GitHub**; phần self-hosted bên dưới chỉ còn là bản mẫu, không phải bằng chứng CI xanh |
| 3 | `docs/research/2026-10-05/verify_packet.py` đọc cứng đường dẫn Windows `C:/Users/Admin/.codex/...` nên chết ngay trên máy mới | nhận `--fragment` tuỳ chọn, bỏ qua phần fragment/health khi thiếu, chạy được trên Linux/macOS |
| 4 | Bảng biến môi trường trong README lệch với mã: ghi `VIGILENS_BACKEND_URL` (tên thật `VIGILENS_API_BASE`), thiếu `NEXT_PUBLIC_VIGILENS_DATA_MODE`, thiếu toàn bộ biến ELT/RAG | cập nhật bảng theo đúng tên biến trong mã, thêm mục cấu hình kho ELT/RAG |

### 1.3 Kiểm chứng tái lập trên máy mới (bản clone sạch)

Lệnh duy nhất `bash scripts/setup_elt.sh --skip-install` chạy trong `/var/tmp/fresh-clone`
(git clone nhánh này, `.env` chỉ có 1 khoá Gemini) và kết thúc `EXIT=0`:

- Nạp 66 tài liệu (keep 63, quarantine 3, reject 0), 668 mục nội dung, 32 bản ghi PubMed,
  13 nhãn DailyMed, 15 báo cáo FAERS, 182 dòng thuốc, 125 phản ứng.
- Chỉ mục RAG dựng bằng chế độ `hash` (không cần mạng): 1.867 đoạn, **khớp 1.867 dòng
  `document_chunks`**; `check_warehouse` kết luận "kho và chỉ mục đạt yêu cầu kiểm tra".
- Bước nhúng bằng Gemini trên máy mới từng dừng ở HTTP 429 (hết hạn mức của cả 8 khoá sau
  nhiều lần dựng chỉ mục trong ngày) — đây là giới hạn hạn mức, không phải lỗi mã; README
  nay ghi rõ cách chuyển sang `RAG_EMBEDDING_PROVIDER=hash` để kiểm tra đường ống.

Còn lại có chủ đích (chưa sửa, ghi để không hiểu nhầm là đã xong): nạp tay vẫn cho phép gắn nhãn
nguồn ELT (nay có thêm cờ `manual_entry_not_verified_with_source`); kho ELT chưa có migration
(chỉ `create_all`/`--reset-db`); Dockerfile backend chưa cài `chromadb` nên RAG trong container
chưa chạy.

### 1.5 Vòng kiểm thử đầu-cuối trên giao diện thật và năm lỗi đã sửa

Một tác nhân kiểm thử độc lập chạy 38 phép kiểm trên giao diện đang chạy (máy chủ API thật +
PostgreSQL + ChromaDB): **36 đạt, 1 hỏng, 1 bị chặn**, độ phủ 37/38. Phép bị chặn là bước dựng
chỉ mục Gemini trong `setup_elt.sh` (hết hạn mức miễn phí của cả 8 khoá), không phải lỗi mã.
Phép hỏng là soát chất lượng giao diện, và nó tìm ra 5 lỗi mã — đã sửa ở commit `4186171`:

| # | Lỗi quan sát được | Nguyên nhân | Cách sửa |
| --- | --- | --- | --- |
| 1 | Nhấp **một lần** nút "Tạo phiên bản mới" trong cảnh báo 409 lại gửi thêm một yêu cầu nạp thật, sinh phiên bản mới ngoài ý muốn | `Button` không có `type` mặc định nên nút nằm trong `<form>` trở thành nút gửi biểu mẫu | `Button` mặc định `type="button"`; nút trong cảnh báo ghi rõ `type="button"` |
| 2 | Cờ chất lượng hiển thị mã tiếng Anh thô, và một số chỗ lặp `mã (mã)` | Bảng nhãn dùng khoá không tồn tại (`no_abstract`, `multi_drug_report`, `multiple_actives`, `non_oral_route`), thiếu 6 mã thật | Bảng nhãn phủ đủ 30 mã thật, tách sang `frontend/lib/warehouse-flags.ts`, có bài vitest chặn thiếu/thừa nhãn |
| 3 | `python -m scripts.elt.load_chroma --provider hash --reset` chết trên thư mục Chroma trống | `reset_collection` luôn gọi `delete_collection` dù bộ sưu tập chưa tồn tại | bỏ qua đúng `NotFoundError`; bài kiểm thử mới chứng minh đỏ trên mã cũ |
| 4 | Trang `/app/drugs` tràn ngang (rộng 2.361 px so với khung 1.280 px) sau khi kết quả RAG hiện ra | đoạn trích chứa JSON FAERS không có chỗ ngắt dòng | thêm `min-w-0`, `break-words`, `overflow-wrap:anywhere`, `break-all` cho mã đoạn |
| 5 | Truy vấn RAG đang chạy làm `/health` mất 24,8 giây, một yêu cầu 422 bị đẩy sau 218 giây | `POST /rag/search` là `async def` nhưng gọi thư viện đồng bộ (ChromaDB, SQLAlchemy) nên chặn vòng lặp sự kiện | cả 7 hàm xử lý trong `src/api/warehouse_routes.py` chuyển thành `def` để FastAPI chạy trong threadpool; bài kiểm thử mới đo bằng đồng hồ thực và chứng minh đỏ trên mã cũ |

Sau vòng kiểm thử, kho được dọn về đúng trạng thái của lần chạy ELT `20261005T194943Z-all`:
5 tài liệu thử do tác nhân kiểm thử để lại đã bị xoá khỏi cả PostgreSQL lẫn Chroma. Hai tài liệu
(`dailymed:c47250c2-bece-46b5-8b3b-b7c97d9005d8:3`, `faers:10006639:1`) từng thiếu 1 đoạn mỗi tài
liệu trong Chroma do lần dựng chỉ mục bằng Gemini bị ngắt giữa lúc kiểm thử; hai đoạn đó đã được
ghi bù, và `check_warehouse` trở lại mã thoát 0 ("kho và chỉ mục đạt yêu cầu kiểm tra", 1.867 = 1.867).

Vòng kiểm lại (2) xác nhận cả năm lỗi đều đã được sửa và bước cài đặt một lệnh chạy tới mã thoát 0
trên bản clone sạch; vòng (3) phát hiện thêm hai chỗ còn in mã cờ thô (cột chất lượng ở bảng kho và
dòng "cờ:" trong thẻ kết quả nạp) — đã sửa ở commit `edefab3` và kiểm lại đạt. Tổng kết: **40/40
phép kiểm đạt**. Ảnh và bản ghi của ba vòng nằm trong `/code/.generated_artifacts/` (29 ảnh,
10 bản ghi, 1 tệp JSONL nhật ký kiểm toán) — xem mục Testing của pull request.

---

## 2. Người 1 — dữ liệu, nguồn, lưu trữ và deploy

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-1-01 gói dữ liệu + provenance | **DEV_DONE** | `scripts/elt/{manifest,fetch,parse}.py`; `data/elt/manifests/*.json`; `docs/data/nguon-du-lieu.md`; `docs/phan-cong-vong-2/nguoi-1/DATA_OFFLINE_HANDOFF.md`; **chuẩn vàng giai đoạn 1:** `data/gold/*`, `scripts/gold/build_gold_dataset.py`, `docs/data/chuan-vang-giai-doan-1.md` | 18 URL ghi đủ tham số/mã HTTP/số byte/sha256/thời điểm; checklist/inventory tách rõ dữ liệu đã có, dữ liệu BV chưa có và điều kiện quyền/khử định danh/đầu mối; **300 cặp vẫn là `candidate_not_gold`** | dữ liệu nội bộ bệnh viện (SOP, mẫu DI/ADR, danh mục); quyền sử dụng; đầu mối; dược sĩ duyệt nhãn | gửi checklist cho đầu mối bệnh viện; giữ phần bệnh viện **WAITING** cho tới khi có quyền và dữ liệu |
| R2-1-02 danh mục thuốc + chọn đúng nhãn | **DEV_DONE** (phần kỹ thuật offline) | `scripts/elt/hospital_catalog.py`; `data/dictionaries/hospital-drug-catalog.synthetic.csv`; `tests/test_scripts/test_hospital_catalog.py`; lookup/warehouse công khai hiện có | importer kiểm đủ mã BV/tên gốc/hoạt chất/hàm lượng/dạng/đường/hãng; file và từng dòng đều synthetic; mapping kiểm cả bốn thuộc tính sản phẩm; pantoprazole tiêm và ciprofloxacin nhỏ tai không khớp nhãn uống; mapping không tự `approved` | danh mục thuốc thật của bệnh viện; dược sĩ xác nhận mapping; đối chiếu sản phẩm lưu hành Việt Nam | khi được cấp quyền, nạp CSV thật và chạy cùng validator; không đổi `candidate` thành `approved` tự động |
| R2-1-03 lưu trữ WorkItem/Response/FollowUp | **DEV_DONE** (API `/api/v2` còn ở R2-2-02) | `src/services/casework/{models,store}.py` (7 bảng); `scripts/elt/migrate_casework.py`; `tests/test_services/test_casework_store.py` (33 bài); `docs/data/cau-truc-kho.md` §1.1–1.2 | nâng cấp thật trên PostgreSQL 5433: 14 → 21 bảng, số dòng 14 bảng cũ không đổi (66 tài liệu, 1.867 đoạn); ghi/đọc lại sau khi mở tiến trình mới vẫn còn; **đua hai luồng trên PostgreSQL thật**: đúng 1 người thắng, người kia nhận `409 VERSION_CONFLICT`, lịch sử đủ 2 dòng (không mất dữ liệu); hai lần lưu phiếu song song để lại đúng một bản hiện hành; duyệt phiếu đã `superseded` → `409 INVALID_STATE`; duyệt phiếu hiện hành tăng `version` và đổi `etag`; `--check` bắt cả cột và chỉ mục còn thiếu; bản chiếu khớp `docs/spec/hospital-v2/schemas.json` | ràng buộc chuyên môn từ Người 3; ma trận quyền R2-2-07 | nối service/API `/api/v2` (R2-2-02) đọc/ghi trên bảy bảng này |
| R2-1-04 connector/snapshot có coverage và lỗi | **DEV_DONE** | `scripts/elt/fetch.py`; `src/services/sources/result.py`; `tests/test_sources/test_source_result.py`; `elt_artifacts` | `SourceResult` phân biệt timeout/HTTP/empty/rate-limit/partial; 404 là gap nguồn; giữ version/ngày đăng/ngày hiệu lực/ngày lấy; PubMed abstract-only không thành full text; replay offline giữ lỗi thật | — | nối payload mở rộng vào UI/runner chỉ khi contract tích hợp được chốt |
| R2-1-05 tài liệu nội bộ và dữ kiện ca | **WAITING** (fixture kỹ thuật đã chuẩn bị) | `docs/spec/hospital-v2/examples/case-record-synthetic-*.json`; `$defs.CaseRecord`; `data/person3/r2_case_scenarios.json` | fixture gắn `synthetic` ở file và từng record; có nhiều thuốc, timeline unknown, lab có đơn vị, bổ sung cùng ca và trường thiếu; không có dữ liệu bệnh nhân thật | cho phép, SOP, mẫu và dữ liệu từ bệnh viện; dược sĩ xác nhận semantics | dùng fixture để kiểm pipeline; không đổi trạng thái sang `DEV_DONE`/`INTEGRATED` cho phần dữ liệu bệnh viện |
| R2-1-06 môi trường staging/pilot | **DEV_DONE** | `scripts/setup_elt.sh`, `docker-compose.elt.yml`, `scripts/db/README.md`, `.env.example`, `docs/data/cau-truc-kho.md` | chạy lại nhiều lần không lỗi; cổng 5433 tách khỏi cụm VMEC 5432; `.env.example` không chứa khoá thật | cập nhật `docs/runbook.md`; URL staging công khai | thêm mục Makefile `elt-setup/elt-run/elt-check/dev-*` |
| R2-1-07 CI, smoke, backup/restore, phát hành | **DOING** (CI đã dựng lại, chưa chạy trên GitHub) | `scripts/elt/check_warehouse.py`; `.github/workflows/ci.yml` (3 job); `Dockerfile` (thêm chromadb); `tests/conftest.py` (bỏ qua bài cần chromadb khi máy chưa cài) | kiểm tra khớp hai kho, mã thoát 1 khi lệch; dựng lại kho từ bản thô bằng `--offline`; job backend nay cài cả `requirements-elt.txt` nên bài RAG chạy được trên runner sạch (trước đó 7 lỗi + 13 lỗi thu thập vì thiếu chromadb); nhánh thiếu chromadb được kiểm bằng plugin chặn cả `find_spec` lẫn `import` (đúng như máy chưa cài gói): 22 bài bỏ qua, phần còn lại chạy; trước khi gắn nhãn cho 12 bài còn sót thì nhánh đó đổ 4 lỗi + 10 lỗi thu thập | chạy thử CI trên GitHub; backup/restore định kỳ | thêm job smoke ELT có dịch vụ PostgreSQL khi nhóm cho phép |
| R2-1-08 nguồn cập nhật và diff version | **DEV_DONE** | `documents.version`; `load_pg.load_documents`; `src/services/warehouse/version_diff.py`; `tests/test_services/test_version_diff.py` | diff theo đoạn giữ provenance hai phiên bản; hash nội dung không đổi không tạo review key/việc trùng; nội dung đổi tạo `ChangeSet` ổn định | — | chỉ nối `ChangeSet` sang FollowUp sau khi contract cập nhật an toàn được chốt |

## 3. Người 2 — agent, workflow, API

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-2-01 chốt contract nhỏ lát cắt DI | **DEV_DONE** | `docs/contracts-hospital-v2.md`; `docs/spec/hospital-v2/{schemas.json,openapi.json,examples/}` (11 ví dụ); `docs/openapi.json` (đã sinh lại, khớp `--check`) | 7 thực thể + 11 ví dụ hợp lệ theo JSON Schema; 9 điểm cuối OpenAPI có `operationId` và ví dụ; enum dùng chung khớp `src/models/schemas.py`; 11 bài kiểm thử hợp đồng đạt, gồm kiểm `$ref` nội bộ của `schemas.json` và kiểm hằng số của kho nằm trong enum hợp đồng | Người 3 xác nhận mục bắt buộc của phiếu trả lời; Người 4 xác nhận hành trình/form; Người 1 xác nhận ràng buộc lưu trữ | triển khai `/api/v2` (R2-2-02) theo hợp đồng |
| R2-2-02 WorkItem service và API | **TODO** | API điều tra MVP hiện có (`/api/v1/investigations`) | luồng MVP cũ vẫn chạy sau khi thêm router mới; khi gọi kho phải truyền `expected_version=None` chứ đừng bỏ hẳn tham số (bỏ hẳn là `TypeError`, không phải 422) | `R2-2-01` | nối form của Người 4 ngay khi endpoint chạy |
| R2-2-03 planner/agent tìm theo quyết định | **DOING** (RAG đã nối vào graph) | `src/services/sources/warehouse.py`; `src/services/runner.py`; `src/config.py`; `tests/test_services/test_warehouse_adapters.py` | chế độ `MVP_SOURCE_MODE=warehouse`: graph lấy bằng chứng từ kho + chỉ mục RAG thay vì gọi mạng; giữ provenance (chunk, điểm, cờ chất lượng, đoạn khớp); thiếu chỉ mục thì trả `SourceStatus.ERROR` thành gap, không bịa tài liệu; 7 bài kiểm thử đạt, gồm một bài chạy graph đầu-cuối | rubric `R2-3-01`; planner theo mục đích/chỉ định (ngoài cặp thuốc–biến cố) | mở planner sang mục đích, chỉ định, comparator, thời gian |
| R2-2-04 checkpoint, resume, thiếu dữ liệu | **TODO** | luồng MVP hiện có | — | `R2-2-02` | giữ nguyên hành vi cũ, bổ sung gaps theo contract mới |
| R2-2-05 phiếu phản hồi: draft/sửa/duyệt/xuất | **TODO** | — | — | template/validator từ Người 3 | — |
| R2-2-06 theo dõi, chuyển giao, khép việc | **TODO** | — | — | `R2-2-05`, `R2-1-03` | — |
| R2-2-07 quyền, phiên bản, audit | **DOING** | `src/api/auth.py` (token vai trò), `ingestion_events` | 403 khi điều tra viên gọi nạp tài liệu; nhật ký nạp ghi đủ | ma trận quyền cho WorkItem | áp quyền theo từng điểm cuối mới |
| R2-2-08 budget, trace, tích hợp lát cắt đầu | **TODO** | — | — | `R2-2-02` | — |
| R2-2-09 mở rộng CaseRecord an toàn | **WAITING** (contract nháp kỹ thuật đã chuẩn bị) | `$defs.CaseRecord` additive trong `docs/spec/hospital-v2/schemas.json`; 2 example synthetic; `docs/contracts-hospital-v2.md` §9 | schema/examples ngoại tuyến kiểm nhiều thuốc, administrations/timeline, lab có đơn vị, observations, revision và supplement cùng ca; không thêm endpoint/OpenAPI; không tự sinh Naranjo/WHO-UMC khi thiếu dữ kiện | SOP, dữ liệu và reviewer bệnh viện; dược sĩ xác nhận contract lâm sàng | review contract nháp; chỉ mở API sau khi đầu vào bên ngoài được xác nhận |

## 4. Người 3 — bằng chứng, hồ sơ chuyên môn

Mọi artifact mới dưới đây là **đề xuất, chờ dược sĩ xác nhận**. Phần clinical gold và nghiệm thu lâm sàng giữ **WAITING**.

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-3-01 rubric câu hỏi | **WAITING** (bản đề xuất kỹ thuật đã sẵn sàng) | `docs/person3/round2/field-glossary.md` | đủ purpose/indication/population/setting/route/comparator/outcome/time; tách required-for-intake và required-for-conclusion; unknown không thành false | dược sĩ xác nhận rubric và wording | review chuyên môn; chỉ đổi trạng thái sau khi được xác nhận |
| R2-3-02 extraction và chất lượng nghiên cứu | **WAITING** (fixture nguồn thật đã sẵn sàng, chưa duyệt chuyên môn) | `data/person3/r2_evidence_bundles.json`; snapshot PMID 39975698 và 40285433 | exact quote khớp XML đã commit; mọi estimate có quote; giữ hash/provenance, thiết kế, quần thể/setting, comparator, estimate/CI/đơn vị, limitation và `abstract_only` | dược sĩ/chuyên gia đánh giá chất lượng và applicability | thẩm định hai bundle; không gộp estimate hoặc gọi khác scope là contradiction |
| R2-3-06 đặc tả trường ca | **WAITING** (bản nháp kỹ thuật đã chuẩn bị) | `docs/person3/round2/case-field-specification.md`; `data/person3/r2_case_scenarios.json` | synthetic scenarios giữ trường thiếu, duplicate candidate và follow-up cùng `case_id` có version; không tự tính causality | SOP, mẫu ca, dữ liệu được phép và dược sĩ xác nhận | đối chiếu bản nháp với SOP khi được cấp |
| R2-3-07 tập đánh giá và annotation | **WAITING** (split/ledger kỹ thuật đã chuẩn bị; clinical gold = 0) | `scripts/build_person3_round2_index.py`; `data/person3/r2_pair_evaluation_index.json`; `docs/person3/round2/annotation-guide.md`; ledger template | 300 cặp tách 200 development/100 evaluation; gói 50 tài liệu tách 30/20 theo hoạt chất và khớp partition 300; không overlap `doc_id`; test chống đưa ID evaluation vào prompt; mọi nhãn vẫn `candidate_not_gold`, `gold_label: null`; vẫn có giới hạn overlap ở cấp nhóm dược lý | hai người gán độc lập, dược sĩ phân xử, gói vật lý và clinical gold đã duyệt | chạy annotation độc lập; không dùng AI/máy làm gold; đánh giá lại split theo nhóm dược lý trước benchmark chính thức |
| R2-3-03, R2-3-04, R2-3-05, R2-3-08 | **TODO/WAITING** | hỗ trợ kỹ thuật hiện có trong `docs/data/`, warehouse chunks và DailyMed metadata | chưa thay đổi trong nhánh này | dược sĩ, dữ liệu bệnh viện và contract tích hợp tương ứng | tiếp tục theo phiếu giao việc khi có đầu vào |

## 5. Người 4 — UI, evaluation, pilot, demo

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-4-06 generated types, error states, kiểm UI tích hợp | **DOING** | `frontend/lib/api/*`, trang `/app/drugs`, `/admin/ingestion`, `/admin/corpus` | kiểm tra kiểu + lint + test đơn vị; smoke HTTP 200 trên 4 tuyến | ảnh chụp E2E trình duyệt | chạy kiểm thử trình duyệt trên cổng 3100 |
| R2-4-01 field map/quan sát | **WAITING** (field map giả thuyết đã chuẩn bị) | `nguoi-4/R2-4-01_FIELD_MAP_GIA_THUYET.md` | đối chiếu người báo nhập gì/dược sĩ cần thấy gì với hospital-v2; ghi rõ chưa quan sát người dùng thật | người dùng thật, đầu mối bệnh viện, SOP và quyền quan sát | walkthrough khi có người dùng; không đổi UI từ giả thuyết chưa kiểm chứng |
| R2-4-07 protocol/baseline | **WAITING** (protocol kỹ thuật đã chuẩn bị) | `nguoi-4/R2-4-07_PROTOCOL_BASELINE.md`; `nguoi-4/templates/evaluation-log.template.json` | tách active/waiting time; có sample/denominator; tách real-source snapshot, synthetic fixture và hồ sơ bệnh viện; không cho báo clinical pass khi chưa review | baseline thật, người tham gia, hồ sơ được phép và clinical reviewer | thu baseline/pilot khi đủ quyền; giữ các chỉ số chưa đo là `N/A` |
| R2-4-02…05, R2-4-08 | **TODO/WAITING** | UI fixture hiện có | không đổi trong nhánh dữ liệu này | checkpoint/WorkItem API của Người 2; rubric và dữ liệu được phép | giữ nguyên giao diện, không đổi bố cục ngoài phạm vi |

---

## 6. Việc còn thiếu và rủi ro (ghi rõ để không hiểu nhầm là đã xong)

1. **Chưa có chuẩn vàng đã duyệt.** Gói 50 mẫu vẫn `pending`, `gold_label: null`. Bộ 300 cặp giai đoạn 1 (`data/gold/`) có nhãn máy đề xuất nhưng mọi dòng vẫn `candidate_not_gold`;
   chưa có dược sĩ duyệt nên không có nghĩa "hệ thống đã chính xác".
2. **FAERS không chứng minh nhân quả.** 14/15 báo cáo có nhiều thuốc, 157/182 dòng thiếu ngày bắt đầu,
   và mọi báo cáo gắn cờ `suspicion_not_causality`. Không dùng số báo cáo làm tỷ lệ mắc.
3. **PubMed chỉ có tóm tắt**, chưa đánh giá chất lượng từng nghiên cứu.
4. **DailyMed chưa đối chiếu danh mục lưu hành Việt Nam**; ngày đăng khác ngày hiệu lực.
5. **RAG đã nối vào agent** ở chế độ `MVP_SOURCE_MODE=warehouse` (`src/services/sources/warehouse.py`), nhưng planner vẫn xoay quanh cặp thuốc–biến cố; chưa mở sang mục đích/chỉ định/comparator.
6. **Chưa có dữ liệu bệnh viện / dược sĩ duyệt** → không thể `PILOT_ACCEPTED` cho bất kỳ task nào thuộc nhóm B/C.
7. **Chỉ mục vector phụ thuộc mô hình nhúng.** Đổi `gemini-embedding-001` phải dựng lại chỉ mục.
8. **Cổng 8000 dùng chung** với cụm VMEC cũ — không chạy đồng thời hai backend.
