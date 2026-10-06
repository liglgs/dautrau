# Cấu trúc kho dữ liệu

Hai kho, hai mục đích:

| Kho | Vai trò | Dữ liệu |
| --- | --- | --- |
| PostgreSQL (`vigilens_elt`, cổng 5433) | nguồn sự thật, dữ liệu hay đổi | tài liệu, mục, bảng nguồn, đoạn văn, phát hiện chất lượng, nhật ký nạp, lần chạy ELT |
| ChromaDB (`data/chroma`) | truy vấn ngữ nghĩa trên dữ liệu tĩnh | vector của từng đoạn văn, kèm `doc_id` để đối chiếu ngược |

Mã nguồn: `src/services/warehouse/` (mô hình, truy vấn, nạp tay), `src/services/rag/` (nhúng, cắt đoạn, chỉ mục, tìm kiếm),
`src/api/warehouse_routes.py` (điểm cuối HTTP).

## 1. Bảng PostgreSQL

| Bảng | Khoá chính | Nội dung |
| --- | --- | --- |
| `elt_runs` | `run_id` | một lần chạy ELT: hồ sơ, git sha, trạng thái, thống kê |
| `elt_artifacts` | `artifact_id` | dấu vết tải: URL, tham số, mã HTTP, số byte, `sha256` |
| `drugs` | `drug_id` | hoạt chất (`drug:ibuprofen`) |
| `drug_event_pairs` | `pair_id` | cặp thuốc–biến cố ứng viên, trạng thái `candidate_not_gold` |
| `documents` | `doc_id` | tài liệu chuẩn hoá: nguồn, phiên bản, tiêu đề, văn bản, `text_sha256`, trạng thái chất lượng, cờ |
| `document_sections` | `(doc_id, ordinal)` | mục nội dung và khoảng ký tự trong văn bản |
| `pubmed_records` | `doc_id` | tạp chí, ngày, loại công bố, DOI, tác giả, có tóm tắt |
| `dailymed_labels` | `doc_id` | SETID, phiên bản, ngày hiệu lực, đường dùng, hoạt chất, số mục |
| `faers_reports` | `doc_id` | mã báo cáo, ngày nhận, quốc gia, tuổi/giới, số thuốc, số phản ứng |
| `faers_report_drugs` | `(doc_id, ordinal)` | từng dòng thuốc trong báo cáo |
| `faers_report_reactions` | `(doc_id, ordinal)` | từng phản ứng trong báo cáo |
| `quality_findings` | `id` | phát hiện của cổng chất lượng theo lần chạy |
| `document_chunks` | `chunk_id` | đoạn văn: `doc_id`, thứ tự, khoảng ký tự, `text_sha256` |
| `ingestion_events` | `event_id` | nhật ký: lần chạy ELT và các lần nạp tài liệu thủ công |

Khoá ngoại: bản ghi con của `documents` xoá theo (`ON DELETE CASCADE`); `documents.pair_id` đặt `NULL` khi cặp bị xoá.
`documents` có ràng buộc duy nhất trên `(source, source_id, version)`.

### 1.1. Bảng lát cắt DI (yêu cầu → trả lời → theo dõi)

Bảy bảng dưới đây nằm cùng cơ sở dữ liệu, dựng theo hợp đồng `docs/spec/hospital-v2/schemas.json`.
Chúng **chỉ được thêm**, không sửa bảng kho ở trên.

| Bảng | Khoá chính | Nội dung |
| --- | --- | --- |
| `work_items` | `work_item_id` | yêu cầu tra cứu: câu hỏi, phạm vi, ẩn số, ba trạng thái (`work_status`, `run_status`, `review_status`), `version` + `etag` |
| `investigation_links` | `link_id` | nối yêu cầu với một lần điều tra: mục đích (`initial/additional/recheck/reproduce`), trạng thái, lỗi |
| `evidence_bundles` | `bundle_id` | gói bằng chứng bất biến của một lần chạy: mục bằng chứng, gap, coverage, lỗi nguồn, giới hạn |
| `professional_responses` | `response_id` | phiếu trả lời theo phiên bản: `version`, `status`, các mục, `supersedes` |
| `follow_ups` | `follow_up_id` | việc theo dõi: loại, trạng thái, hạn, người nhận, kết quả |
| `version_refs` | `id` | nhật ký append-only: mỗi lần ghi một dòng, kèm ảnh chụp và danh sách trường đã đổi |
| `review_refs` | `review_id` | quyết định duyệt append-only: hành động, người duyệt, trạng thái trước/sau |

Quy ước chống mất dữ liệu:

* Mọi lần sửa `work_items` phải gửi kèm `expected_version`; lệch phiên bản trả `409 VERSION_CONFLICT`
  và không ghi gì.
* Mọi lần tạo/sửa đều ghi thêm một dòng `version_refs` (kèm ảnh chụp), nên đọc lại được lịch sử.
* Phiếu trả lời là append-only theo phiên bản: bản cũ chuyển sang `superseded` nhưng vẫn còn trong bảng.
* Chỉ nhận các trường trong danh sách trắng; khoá lạ trả `422 INVALID_REQUEST`.

### 1.2. Nâng cấp lược đồ (chỉ thêm bảng)

```bash
python -m scripts.elt.migrate_casework --check   # mã thoát 1 nếu còn thiếu bảng
python -m scripts.elt.migrate_casework           # tạo bảy bảng còn thiếu, in số dòng trước/sau
```

Script đếm số dòng của 14 bảng cũ trước và sau khi chạy; lệch thì báo lỗi và trả mã thoát 1.
Muốn bỏ bảy bảng mới (chấp nhận mất dữ liệu DI): `python -m scripts.elt.migrate_casework --rollback --yes`.

## 2. Chỉ mục vector

- Tên bộ sưu tập: `<RAG_COLLECTION>__<provider>__<model>` → `vigilens_docs__gemini__gemini-embedding-001`.
- Mỗi vector có metadata: `doc_id`, `source`, `pair_id`, `quality_status`, `ordinal`, `char_start`, `char_end`.
- Đoạn văn 1.200 ký tự, chồng lấn 200 ký tự (xem `tien-xu-ly.md`).
- **Bất biến cần giữ:** số đoạn trong ChromaDB = số dòng `document_chunks` trong PostgreSQL.
  `check_warehouse` kiểm tra và trả mã thoát 1 nếu lệch.

## 3. Cách truy vấn

```bash
# Tổng quan kho + chỉ mục (kiểm tra khớp hai kho)
.venv/bin/python -m scripts.elt.check_warehouse

# Tra cứu thuốc qua API
curl -s -H "X-API-Token: $INVESTIGATOR_TOKEN" \
  "http://127.0.0.1:8000/api/v1/drugs/lookup?name=ibuprofen"

# Tìm kiếm ngữ nghĩa qua API
curl -s -H "X-API-Token: $INVESTIGATOR_TOKEN" -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/v1/rag/search \
  -d '{"query":"hạ magnesi do thuốc ức chế bơm proton","k":3}'
```

```python
# Truy vấn trực tiếp trong Python
from src.services.rag.search import search
from src.services.warehouse.db import get_warehouse_engine
from src.services.warehouse.queries import lookup_drug, warehouse_overview

engine = get_warehouse_engine()
print(warehouse_overview(engine)["documents_by_quality_status"])
print(lookup_drug(engine, "ibuprofen")["pairs"])
print([(hit["score"], hit["document"]["doc_id"]) for hit in search(engine, "metformin diarrhoea")["hits"]])
```

## 4. Điểm cuối HTTP (đều cần vai trò)

| Phương thức | Đường dẫn | Vai trò | Trả về |
| --- | --- | --- | --- |
| GET | `/api/v1/drugs/lookup?name=` | investigator trở lên | thuốc, cặp ứng viên, số tài liệu theo nguồn |
| GET | `/api/v1/warehouse/overview` | investigator trở lên | số liệu kho, phát hiện chất lượng, trạng thái chỉ mục |
| GET | `/api/v1/warehouse/documents` | investigator trở lên | danh sách tài liệu (lọc `source`, `pair_id`, `quality_status`) |
| GET | `/api/v1/warehouse/documents/{doc_id}` | investigator trở lên | chi tiết + trích đoạn đầu + mục nội dung |
| POST | `/api/v1/rag/search` | investigator trở lên | các đoạn gần nghĩa kèm điểm và tài liệu gốc |
| GET | `/api/v1/ingestion/events` | investigator trở lên | nhật ký nạp tài liệu |
| POST | `/api/v1/ingestion/documents` | **reviewer** | nạp tài liệu thủ công, trả về `doc_id`, `sha256`, trạng thái RAG |

Lỗi có mã rõ ràng: `401` thiếu token, `403` sai vai trò, `404` không có tài liệu,
`409 INGEST_CONFLICT` trùng định danh nhưng khác nội dung, `422` đầu vào sai,
`503 WAREHOUSE_UNAVAILABLE` PostgreSQL chưa chạy.

## 5. Giao diện dùng kho

- `/app/drugs` — tra cứu thuốc và hỏi kho bằng chứng (tìm kiếm ngữ nghĩa).
- `/admin/ingestion` — nạp tài liệu thủ công (chỉ vai trò dược sĩ duyệt) và xem nhật ký.
- `/admin/corpus` — số liệu kho, danh sách tài liệu và chi tiết tài liệu.

## 6. Sao lưu và dựng lại

- Dữ liệu thô nằm trong `data/elt/raw/` (đã băm) — có thể dựng lại kho mà không cần tải lại.
- Dựng lại từ đầu: `./scripts/setup_elt.sh --reset`.
- Chỉ dựng lại chỉ mục vector: `python -m scripts.elt.run_elt --profile bundle --reset-index`.
- Volume PostgreSQL: `elt_postgres_data` (xoá bằng `docker compose -f docker-compose.elt.yml down -v`).
