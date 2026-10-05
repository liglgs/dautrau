# Cổng chất lượng dữ liệu

Mục tiêu: **không nạp dữ liệu không đủ điều kiện, không cắt quá tay.** Mọi quyết định đều có mã kiểm tra,
mức độ và lý do, lưu trong bảng `quality_findings` và trong `data/elt/reports/<run_id>-quality.{json,md}`.

Mã nguồn: `scripts/elt/quality.py`. Số liệu thật của lần chạy gần nhất: [`bao-cao-chat-luong.md`](bao-cao-chat-luong.md).

## Ba mức quyết định

| Quyết định | Nghĩa | Vào kho? | Vào chỉ mục RAG? | Dùng làm bằng chứng? |
| --- | --- | --- | --- | --- |
| `keep` | đạt | có | có | có |
| `quarantine` | chưa đạt nhưng còn giá trị nền | có | có (mặc định loại khỏi chỉ mục khi dựng `--only-keep`) | **không** — UI hiển thị cờ |
| `reject` | không dùng được | không | không | không |

## Kiểm tra chung (mọi nguồn)

| Mã | Mức | Quyết định | Điều kiện |
| --- | --- | --- | --- |
| `no_title` | error | reject | thiếu tiêu đề |
| `text_too_short` | error | reject | văn bản < 40 ký tự |
| `raw_hash_missing` | error | reject | không xác định được băm bản thô |
| `duplicate_in_run` | error | reject | trùng `(nguồn, mã nguồn, phiên bản)` trong cùng lần chạy |
| `possible_markup` | warn | note | văn bản còn ký tự giống thẻ HTML |

## PubMed

| Mã | Quyết định | Điều kiện |
| --- | --- | --- |
| `missing_abstract` | quarantine | chỉ có siêu dữ liệu, không có tóm tắt |
| `retracted_publication` | **reject** | bài đã bị rút |
| `not_primary_evidence` | quarantine | thư/ý kiến/biên tập, không phải nghiên cứu gốc |
| `missing_doi` | note | không có DOI (cảnh báo nhẹ) |
| `has_abstract`, `has_journal` | keep | có tóm tắt / có tên tạp chí |

## DailyMed

| Mã | Quyết định | Điều kiện |
| --- | --- | --- |
| `missing_sections` | **reject** | nhãn không có mục nội dung nào |
| `multi_ingredient` | quarantine | nhãn nhiều hoạt chất → phải xác minh sản phẩm trước khi dùng |
| `missing_route` | quarantine | thiếu đường dùng |
| `route_not_oral` | quarantine | đường dùng không phải uống |
| `missing_effective_time` | quarantine | thiếu ngày hiệu lực SPL |
| `few_sections` | note | nhãn chỉ có < 3 mục |

## FAERS

| Mã | Quyết định | Điều kiện |
| --- | --- | --- |
| `no_reactions` | **reject** | không có phản ứng nào |
| `no_drugs` | **reject** | không có thuốc nào |
| `report_too_large` | **reject** | văn bản > 200.000 ký tự |
| `missing_age` | quarantine | thiếu tuổi bệnh nhân |
| `missing_sex` | quarantine | thiếu giới tính bệnh nhân |
| `missing_receivedate` | quarantine | thiếu ngày FDA nhận báo cáo |
| `multiple_drugs` | note | báo cáo có > 1 thuốc → quan hệ thuốc–biến cố chưa chắc chắn |
| `missing_drug_start_date` | note | không dòng thuốc nào có ngày bắt đầu |
| `missing_drug_route` | note | thiếu đường dùng |
| `suspicion_not_causality` | note | luôn gắn: báo cáo nghi ngờ, không kết luận nhân quả |

### Vì sao hai lỗi phổ biến của FAERS chỉ ở mức ghi chú

`missing_drug_start_date` và `missing_drug_route` xuất hiện ở gần như mọi báo cáo
(157/182 dòng thuốc thiếu ngày bắt đầu trong mẫu 15 báo cáo). Nếu cách ly theo hai tiêu chí này
thì toàn bộ nguồn FAERS bị loại, trong khi văn bản vẫn dùng được để **phát hiện** vấn đề.
Vì vậy: ghi cờ để UI cảnh báo, vẫn đưa vào kho, nhưng **không bao giờ** dùng để suy nhân quả hay tỷ lệ mắc.

## Điều kiện cấu hình trong `data/elt/dataset-spec.json`

Mỗi nguồn khai báo ba danh sách `require` / `quarantine_if` / `reject_if` để người đọc đặc tả
thấy ngay chuẩn dữ liệu, không phải đọc mã:

```json
"pubmed":  { "require": ["pmid", "title", "text"], "quarantine_if": ["missing_abstract"], "reject_if": ["no_title", "no_text", "hash_mismatch"] },
"dailymed":{ "require": ["setid", "version", "title", "effective_time"], "quarantine_if": ["missing_sections", "multi_ingredient"], "reject_if": ["no_title", "no_sections", "setid_mismatch"] },
"faers":   { "require": ["safetyreportid", "reactions", "drugs"], "quarantine_if": ["missing_age", "missing_sex", "missing_route", "missing_dose_start_date", "large_report", "event_not_exact"], "reject_if": ["no_reactions", "no_drugs", "report_too_large"] }
```

## Kết quả lần chạy gần nhất (66 tài liệu)

- `keep` 63, `quarantine` 3, `reject` 0.
- 3 tài liệu bị cách ly: 1 nhãn DailyMed nhiều hoạt chất/không đường uống, 2 báo cáo FAERS thiếu tuổi hoặc giới tính.
- Không có tài liệu nào bị loại trong lần chạy này.

## Việc còn thiếu (đã ghi nhận, chưa làm)

1. **Chưa có chuẩn vàng** để đo độ chính xác — `review.jsonl` của gói 50 mẫu vẫn `pending`.
2. **Chưa đối chiếu danh mục lưu hành Việt Nam** — không xác nhận được nhãn DailyMed có phù hợp thị trường VN.
3. **Chưa xếp hạng chất lượng nghiên cứu** (cỡ mẫu, nguy cơ sai lệch) — chỉ kiểm tra có/không tóm tắt.
4. **Chưa ánh xạ MedDRA** — biến cố giữ nguyên văn bản nguồn.
5. **Chưa có bộ kiểm thử hồi quy cho cổng chất lượng trên dữ liệu mới** — hiện chỉ có bộ kiểm thử đơn vị
   trên dữ liệu mẫu trong `tests/` (xem `tests/test_elt_quality.py`).
