# Quyết định tiền xử lý

Pipeline: **tải thô → ghi manifest → phân tích → văn bản chuẩn hoá + băm → cổng chất lượng → PostgreSQL → ChromaDB**.
Mã nguồn: `scripts/elt/` (tải/phân tích/cổng chất lượng) và `src/services/warehouse/`, `src/services/rag/` (kho và chỉ mục).

## 1. Giữ nguyên bản thô, không sửa

- Mọi phản hồi HTTP được lưu nguyên byte vào `data/elt/raw/<host>/<tệp>.<ext>` **trước khi** phân tích.
- `data/elt/manifests/<run_id>.json` ghi cho từng tệp: URL, tham số truy vấn, mã trạng thái HTTP,
  số byte, `sha256`, thời điểm, và cả **lỗi** nếu có.
- Vì sao: có thể chạy lại phần phân tích mà không cần mạng, và có thể chứng minh dữ liệu đến từ đâu.
- Lần chạy lại không tải lại tệp đã có (`--offline` chỉ dùng bản thô; `--force` mới tải lại).

## 2. Văn bản chuẩn hoá (canonical text)

Mỗi tài liệu có **một** chuỗi văn bản chuẩn hoá, và `sha256` của chuỗi đó là định danh nội dung
(`documents.text_sha256`). Quy tắc theo nguồn:

| Nguồn | Cách dựng văn bản chuẩn hoá |
| --- | --- |
| PubMed | tái tạo văn bản gắn thẻ (`PMID- …`, `TI  - …`, `AB  - …`) từ XML |
| DailyMed | ghép tiêu đề nhãn + từng mục SPL theo thứ tự, giữ nhãn mục |
| FAERS | JSON rút gọn, sắp xếp khoá, phân tách dòng rõ ràng |
| Tham chiếu | HTML → văn bản thuần (bỏ `script`/`style`), PDF → văn bản (`pypdf`) |

**Kiểm chứng hai chiều:** phân tích lại 30 tệp thô của gói 50 mẫu bằng chính bộ phân tích của ứng dụng
cho ra đúng `sha256` mà gói JSON đã phát hành (30/30 khớp). Nếu bộ phân tích đổi hành vi, phép kiểm này sẽ báo lệch.

## 3. Định danh tài liệu

```
doc_id = "<nguồn>:<mã nguồn>:<phiên bản>"
```

Ví dụ `pubmed:39466269:1`, `dailymed:c47250c2-bece-46b5-8b3b-b7c97d9005d8:3`, `faers:10006463:4`.
Khoá duy nhất trong kho là `(source, source_id, version)`. Cùng `doc_id` mà nội dung khác
→ **409 `INGEST_CONFLICT`**, buộc tạo phiên bản mới thay vì ghi đè (giữ được lịch sử).

## 4. Cổng chất lượng trước khi nạp

Ba mức: `keep` (đủ điều kiện), `quarantine` (vào kho nhưng gắn cờ, không dùng làm bằng chứng chính),
`reject` (loại, không nạp). Chi tiết và bằng chứng ở [`cong-chat-luong.md`](cong-chat-luong.md).

Quyết định đáng chú ý: **hai lỗi phổ biến của FAERS bị hạ xuống mức ghi chú, không cách ly** —
`missing_drug_start_date` và `missing_drug_route`. Lý do: chúng là đặc điểm cố hữu của dữ liệu tự nguyện
(157/182 dòng thiếu ngày bắt đầu), nếu cách ly theo tiêu chí này thì gần như toàn bộ FAERS bị loại,
trong khi văn bản vẫn dùng được để *phát hiện* vấn đề. Cờ vẫn được ghi để UI cảnh báo người đọc.

## 5. Cắt đoạn (chunking) cho RAG

- Kích thước đoạn 1.200 ký tự, chồng lấn 200 ký tự.
- Ưu tiên cắt tại ranh giới tự nhiên theo thứ tự: đoạn trống đôi → xuống dòng → cuối câu → khoảng trắng.
- Mỗi đoạn giữ `doc_id`, `ordinal`, `char_start`, `char_end` để ánh xạ ngược về văn bản gốc.
- Mỗi đoạn có bản ghi trong PostgreSQL (`document_chunks`) **và** một vector trong ChromaDB;
  số lượng hai bên phải bằng nhau (lệch 0) — `check_warehouse` kiểm tra điều này.
- Ghi lại chỉ mục luôn xoá đoạn cũ của chính tài liệu đó trước khi ghi (văn bản ngắn lại không để lại
  đoạn mồ côi), và lần dựng toàn bộ sẽ dọn khỏi **cả hai kho** những tài liệu không còn đủ điều kiện
  (chuyển sang `quarantine`/`reject`). Thống kê `pruned_documents` cho biết số tài liệu đã dọn.

**Vì sao cần cả hai kho:** ChromaDB phục vụ truy vấn ngữ nghĩa trên dữ liệu tĩnh, ít đổi (nhãn, tóm tắt, báo cáo);
PostgreSQL là nguồn sự thật cho dữ liệu hay đổi (trạng thái điều tra, hàng đợi duyệt, nhật ký nạp tài liệu).
Đoạn văn trong ChromaDB luôn kèm `doc_id` để đối chiếu ngược lại PostgreSQL.

## 6. Nhúng (embedding)

- Nhà cung cấp: Google Gemini, mô hình `gemini-embedding-001`, 3.072 chiều.
- Tên bộ sưu tập gắn cả nhà cung cấp và mô hình: `vigilens_docs__gemini__gemini-embedding-001`.
  Đổi nhà cung cấp/mô hình → bộ sưu tập **khác**, không so sánh điểm số giữa hai bộ sưu tập.
- Xoay vòng 8 khoá API; mỗi khoá cách nhau tối thiểu 1 giây; gặp HTTP 429 thì đổi khoá và chờ theo `Retry-After`.
- Lô 16 đoạn/lần gọi (lô 50 bị hạn mức chặn).
- Chế độ `hash` (384 chiều, cục bộ, không cần mạng) dùng cho kiểm thử — chất lượng ngữ nghĩa thấp hơn,
  chỉ để chạy test ngoại tuyến.

## 7. Chống trùng và chống lệch

- Trùng nội dung: hai tài liệu cùng `text_sha256` bị phát hiện và ghi vào `quality_findings`.
- Lệch hai kho: `python -m scripts.elt.check_warehouse` so số đoạn ChromaDB với `document_chunks`
  trong PostgreSQL và báo lệch (mã thoát 1 nếu lệch).
- Nạp lại cùng tài liệu: ghi đè bản ghi cũ và thay toàn bộ bản ghi con (mục, bảng nguồn, đoạn) —
  không để lại bản ghi mồ côi.

## 8. Giới hạn đã biết của tiền xử lý

1. **Không có toàn văn PubMed** — chỉ tóm tắt; trích dẫn luôn ghi rõ mức nội dung.
2. **Không chuẩn hoá được sang mã MedDRA** — biến cố giữ nguyên văn bản nguồn (`reactionmeddrapt`),
   chưa ánh xạ mã; đây là việc của giai đoạn sau và cần giấy phép MedDRA.
3. **FAERS không ánh xạ chắc cặp thuốc–biến cố** — một báo cáo có nhiều thuốc và nhiều phản ứng.
4. **Chưa có chuẩn vàng** cho 5 cặp ứng viên → chưa chấm được độ chính xác của agent.
5. **Bộ sưu tập vector gắn với mô hình nhúng** — đổi mô hình phải dựng lại chỉ mục (`--reset-index`).
