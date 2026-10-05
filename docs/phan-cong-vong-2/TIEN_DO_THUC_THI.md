# Nhật ký tiến độ thực thi — vòng hai

Cập nhật ngày **05/10/2026**. Mẫu ghi theo mục 18.3 của [báo cáo chính](NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md).

`Task ID | Owner | Trạng thái | Artifact/SHA | Đã kiểm gì, bằng data nào | Thiếu đầu vào gì | Ai giao/ai nhận | Việc có thể làm tiếp | Người review/kết quả`

Trạng thái dùng đúng bốn mức của kế hoạch: `TODO` / `DOING` / `WAITING` / `DEV_DONE` / `INTEGRATED` / `PILOT_ACCEPTED`.

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

---

## 2. Người 1 — dữ liệu, nguồn, lưu trữ và deploy

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-1-01 gói dữ liệu + provenance | **DEV_DONE** | `scripts/elt/{manifest,fetch,parse}.py`; `data/elt/manifests/*.json`; `docs/data/nguon-du-lieu.md` | 18 URL ghi đủ tham số/mã HTTP/số byte/sha256/thời điểm; 30/30 băm văn bản khớp JSON đã phát hành; 44/44 mục gói khớp | dữ liệu nội bộ bệnh viện (SOP, mẫu DI/ADR) | bổ sung checklist xin dữ liệu BV; thêm nguồn danh mục lưu hành VN khi có |
| R2-1-02 danh mục thuốc + chọn đúng nhãn | **DEV_DONE** (nhánh công khai) | `drugs`, `drug_event_pairs`; `GET /api/v1/drugs/lookup`; `dailymed_labels`; `docs/data/tien-xu-ly.md` §2 | nhãn đơn hoạt chất 13/13, đường uống 12/13; cổng cách ly nhãn nhiều hoạt chất; giữ cả `published_date` và `effectiveTime` | danh mục thuốc của bệnh viện | nạp CSV danh mục BV khi được cấp; thêm kiểm tra hàm lượng/dạng bào chế |
| R2-1-03 lưu trữ WorkItem/Response/FollowUp | **TODO** (phần kho tài liệu đã có) | `src/services/warehouse/models.py` (14 bảng) | dựng lược đồ, nạp 66 tài liệu, chạy lại không nhân bản | contract `R2-2-01`; ràng buộc chuyên môn từ Người 3 | dựng bảng yêu cầu/phiếu trả lời/theo dõi trên nền storage hiện có |
| R2-1-04 connector/snapshot có coverage và lỗi | **DEV_DONE** | `scripts/elt/fetch.py`; `elt_artifacts` | ghi cả trường hợp lỗi; `--offline` phát lại bản thô; chờ 0,35–0,6 giây/theo host; thử lại 429/5xx | — | bổ sung `SourceResult` theo contract của Người 2 |
| R2-1-05 tài liệu nội bộ và dữ kiện ca | **WAITING** | — | — | cho phép và dữ liệu từ bệnh viện | chuẩn bị mẫu synthetic có nhãn để kiểm kỹ thuật |
| R2-1-06 môi trường staging/pilot | **DEV_DONE** | `scripts/setup_elt.sh`, `docker-compose.elt.yml`, `scripts/db/README.md`, `.env.example`, `docs/data/cau-truc-kho.md` | chạy lại nhiều lần không lỗi; cổng 5433 tách khỏi cụm VMEC 5432; `.env.example` không chứa khoá thật | cập nhật `docs/runbook.md`; URL staging công khai | thêm mục Makefile `elt-setup/elt-run/elt-check/dev-*` |
| R2-1-07 CI, smoke, backup/restore, phát hành | **DOING** | `scripts/elt/check_warehouse.py` | kiểm tra khớp hai kho, mã thoát 1 khi lệch; dựng lại kho từ bản thô bằng `--offline` | workflow CI (đã bị xoá ở HEAD `db5c20f`) | dựng lại CI tối thiểu: lint + test + smoke ELT |
| R2-1-08 nguồn cập nhật và diff version | **DEV_DONE** | `documents.version`; `load_pg.load_documents` | cùng `doc_id` khác nội dung → 409; phát hiện `content_changed`; `--reset-db`/`--reset-index` | — | thêm báo cáo diff giữa hai phiên bản tài liệu |

## 3. Người 2 — agent, workflow, API

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-2-01 chốt contract nhỏ lát cắt DI | **DOING** | `src/api/warehouse_routes.py` (7 điểm cuối, mô hình Pydantic, OpenAPI) | `/openapi.json` có đủ 7 đường dẫn; 401/403/404/409/422/503 đều có mã lỗi rõ | contract WorkItem/Response/FollowUp với Người 1 và 3 | phát hành schema + ví dụ cho 1/3/4 |
| R2-2-02 WorkItem service và API | **TODO** | API điều tra MVP hiện có (`/api/v1/investigations`) | luồng MVP cũ vẫn chạy sau khi thêm router mới | `R2-2-01` | nối form của Người 4 ngay khi endpoint chạy |
| R2-2-03 planner/agent tìm theo quyết định | **TODO** | `src/services/rag/search.py` (dịch vụ tìm kiếm đã có) | truy vấn tiếng Việt khớp nhãn tiếng Anh (0,782) | rubric `R2-3-01`; planner mới | nối RAG vào `src/agents/graph.py` thay vì chỉ dùng từ điển |
| R2-2-04 checkpoint, resume, thiếu dữ liệu | **TODO** | luồng MVP hiện có | — | `R2-2-02` | giữ nguyên hành vi cũ, bổ sung gaps theo contract mới |
| R2-2-05 phiếu phản hồi: draft/sửa/duyệt/xuất | **TODO** | — | — | template/validator từ Người 3 | — |
| R2-2-06 theo dõi, chuyển giao, khép việc | **TODO** | — | — | `R2-2-05`, `R2-1-03` | — |
| R2-2-07 quyền, phiên bản, audit | **DOING** | `src/api/auth.py` (token vai trò), `ingestion_events` | 403 khi điều tra viên gọi nạp tài liệu; nhật ký nạp ghi đủ | ma trận quyền cho WorkItem | áp quyền theo từng điểm cuối mới |
| R2-2-08 budget, trace, tích hợp lát cắt đầu | **TODO** | — | — | `R2-2-02` | — |
| R2-2-09 mở rộng CaseRecord an toàn | **WAITING** | — | — | SOP/dữ liệu/reviewer bệnh viện | — |

## 4. Người 3 — bằng chứng, hồ sơ chuyên môn

Toàn bộ 8 task `R2-3-01…08` giữ **TODO/WAITING**: cần dược sĩ và dữ liệu bệnh viện.
Đóng góp kỹ thuật đã sẵn sàng cho Người 3 dùng:

| Hỗ trợ kỹ thuật đã có | Dùng cho task |
| --- | --- |
| `docs/data/nguon-du-lieu.md` — mỗi nguồn trả lời được gì, **không** trả lời được gì | R2-3-02, R2-3-03 |
| `docs/data/cong-chat-luong.md` — 3 mức và mã kiểm tra | R2-3-02, R2-3-04 |
| Trích đoạn kèm `char_start/char_end` + `doc_id` trong `document_chunks` | R2-3-04 (citation) |
| `GET /api/v1/warehouse/documents/{doc_id}` trả mục nội dung và trích đoạn | R2-3-05, R2-3-06 |
| Nhãn DailyMed giữ cả ngày đăng và ngày hiệu lực | R2-3-08 |

## 5. Người 4 — UI, evaluation, pilot, demo

| Task | Trạng thái | Artifact | Đã kiểm gì | Thiếu đầu vào | Việc có thể làm tiếp |
| --- | --- | --- | --- | --- | --- |
| R2-4-06 generated types, error states, kiểm UI tích hợp | **DOING** | `frontend/lib/api/*`, trang `/app/drugs`, `/admin/ingestion`, `/admin/corpus` | kiểm tra kiểu + lint + test đơn vị; smoke HTTP 200 trên 4 tuyến | ảnh chụp E2E trình duyệt | chạy kiểm thử trình duyệt trên cổng 3100 |
| R2-4-01…05, 07, 08 | **TODO** | — | — | checkpoint/WorkItem API của Người 2; rubric của Người 3 | giữ nguyên giao diện hiện có, không đổi bố cục ngoài luồng dữ liệu |

---

## 6. Việc còn thiếu và rủi ro (ghi rõ để không hiểu nhầm là đã xong)

1. **Chưa có chuẩn vàng.** `review.jsonl` của gói 50 mẫu vẫn `pending`, `gold_label: null`; mọi cặp là `candidate_not_gold`.
   Không có nghĩa "hệ thống đã chính xác".
2. **FAERS không chứng minh nhân quả.** 14/15 báo cáo có nhiều thuốc, 157/182 dòng thiếu ngày bắt đầu,
   và mọi báo cáo gắn cờ `suspicion_not_causality`. Không dùng số báo cáo làm tỷ lệ mắc.
3. **PubMed chỉ có tóm tắt**, chưa đánh giá chất lượng từng nghiên cứu.
4. **DailyMed chưa đối chiếu danh mục lưu hành Việt Nam**; ngày đăng khác ngày hiệu lực.
5. **Chưa nối RAG vào agent.** Dịch vụ tìm kiếm đã chạy nhưng `src/agents/graph.py` vẫn dùng từ điển tĩnh.
6. **Chưa có dữ liệu bệnh viện / dược sĩ duyệt** → không thể `PILOT_ACCEPTED` cho bất kỳ task nào thuộc nhóm B/C.
7. **Chỉ mục vector phụ thuộc mô hình nhúng.** Đổi `gemini-embedding-001` phải dựng lại chỉ mục.
8. **Cổng 8000 dùng chung** với cụm VMEC cũ — không chạy đồng thời hai backend.
