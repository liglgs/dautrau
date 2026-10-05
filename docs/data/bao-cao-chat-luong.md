# Báo cáo chất lượng dữ liệu ELT (tự sinh)

Tài liệu này do `python -m scripts.elt.docs_data` sinh ra từ báo cáo ELT thật. Không sửa tay; chạy lại lệnh trên sau mỗi lần nạp dữ liệu.

- Lần chạy: `20261005T194943Z-all` (profile `all`)
- Thời điểm sinh báo cáo ELT: 2026-10-05T19:49:43.744668+00:00
- Thời điểm sinh tài liệu này: 2026-10-05T19:54:42+00:00

## 1. Khối lượng theo nguồn

| Nguồn | Số tài liệu | Mức nội dung |
| --- | --- | --- |
| DailyMed (nhãn thuốc FDA) | 13 | các mục nhãn thuốc (13) |
| openFDA FAERS (báo cáo ADR tự nguyện) | 15 | báo cáo tự nguyện (15) |
| PubMed (trích y văn) | 32 | chỉ có tóm tắt + siêu dữ liệu (không có toàn văn) (32) |
| Tài liệu tham chiếu (không phải bằng chứng chính) | 6 | hướng dẫn đánh giá ca (1), tài liệu mô tả nguồn dữ liệu (1), bản tin cảnh giác dược quốc gia (2), mục lục bản tin cảnh giác dược (1), tài liệu tham chiếu (1) |
| **Tổng** | **66** | |

## 2. Quyết định của cổng chất lượng

| Quyết định | Số tài liệu | Ý nghĩa |
| --- | --- | --- |
| keep | 63 | đủ điều kiện vào kho và chỉ mục RAG |
| quarantine | 3 | vào kho nhưng bị gắn cờ, không dùng làm bằng chứng chính |
| reject | 0 | bị loại, không nạp |

## 3. Cấu trúc từng nguồn

- PubMed: 32 bản ghi, 32 có tóm tắt, 0 chỉ có siêu dữ liệu.
- DailyMed: 13 nhãn, 13 đơn hoạt chất, 12 dùng đường uống.
- FAERS: 15 báo cáo, 14 báo cáo có nhiều thuốc, 182 dòng thuốc, 157 dòng thiếu ngày bắt đầu, 2 báo cáo thiếu tuổi, 1 thiếu giới tính, văn bản dài nhất 172,081 ký tự.

## 4. Phát hiện theo mã kiểm tra

| Mã kiểm tra | Số lần |
| --- | --- |
| `has_abstract` | 32 |
| `has_journal` | 32 |
| `missing_age` | 2 |
| `missing_doi` | 1 |
| `missing_drug_route` | 3 |
| `missing_drug_start_date` | 4 |
| `missing_sex` | 1 |
| `multiple_drugs` | 14 |
| `route_not_oral` | 1 |
| `suspicion_not_causality` | 15 |

## 5. Số bản ghi thật trong PostgreSQL

| Bảng | Số bản ghi |
| --- | --- |
| `dailymed_labels` | 13 |
| `document_chunks` | 1,865 |
| `document_sections` | 668 |
| `documents` | 66 |
| `drug_event_pairs` | 5 |
| `drugs` | 5 |
| `faers_report_drugs` | 182 |
| `faers_report_reactions` | 125 |
| `faers_reports` | 15 |
| `ingestion_events` | 3 |
| `pubmed_records` | 32 |
| `quality_findings` | 315 |

## 6. Chỉ mục vector (ChromaDB)

- Bộ sưu tập: `vigilens_docs__gemini__gemini-embedding-001`
- Mô hình nhúng: `gemini-embedding-001` (provider `gemini`)
- Số đoạn trong ChromaDB: 1,865
- Số đoạn trong PostgreSQL: 1,865
- Lệch: 0 (0 nghĩa là hai kho khớp nhau)
- Thư mục lưu: `./data/chroma`

## 7. Cách chạy lại

```bash
# 1. Tải dữ liệu thô và ghi manifest (không cần mạng nếu đã có sẵn)
python -m scripts.elt.run_elt --profile bundle
# 2. Nạp kho PostgreSQL + dựng chỉ mục ChromaDB
python -m scripts.elt.run_elt --profile all --reset-db
# 3. Kiểm tra kho và sinh lại tài liệu này
python -m scripts.elt.check_warehouse
python -m scripts.elt.docs_data
```
