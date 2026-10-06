# Chuẩn vàng giai đoạn 1 — cặp thuốc–biến cố từ nguồn công khai quốc tế

**Trạng thái: `candidate_not_gold`.** Máy đề xuất nhãn; **chưa có dược sĩ/chuyên gia cảnh giác dược duyệt**. Không dùng làm chuẩn vàng chính thức cho tới khi có người duyệt.

## Tệp

| Tệp | Nội dung |
|---|---|
| `spec.json` | Đặc tả đầu vào: 30 hoạt chất, 10 biến cố, từ đồng nghĩa, quy tắc chọn nhãn và khớp chuỗi, nguồn và giấy phép. |
| `drug-event-pairs.jsonl` | 300 cặp thuốc–biến cố (30 × 10) với bằng chứng nhãn và số liệu FAERS. |
| `manifest.json` | Băm SHA-256 của `spec.json` và tệp dữ liệu, thống kê, danh sách nguồn, ghi chú và giới hạn. |
| `raw/` | Bản thô phản hồi openFDA (360 tệp). **Không commit** (dung lượng); dùng để chạy lại offline. |

## Nguồn và giấy phép

- **openFDA Drug Label API** (`https://api.fda.gov/drug/label.json`) — nhãn SPL của FDA Hoa Kỳ; dữ liệu công khai của chính phủ Hoa Kỳ.
- **openFDA Drug Adverse Event API** (`https://api.fda.gov/drug/event.json`) — báo cáo FAERS; dữ liệu công khai của chính phủ Hoa Kỳ.

Không dùng MedDRA có bản quyền: chuỗi trong `meddra_pt_query` là chuỗi truy vấn do nhóm soạn, chưa đối chiếu từ điển.

## Trường chính của mỗi dòng

```text
pair_id, drug, drug_vn_name, drug_class, event, event_slug,
meddra_pt_query, event_synonyms_used,
label_evidence { status, set_id, spl_version, spl_effective_time, label_title, label_url,
                 checked_sections, matched_section, matched_term, matched_quote,
                 query_http_status, retrieved_at, error },
faers_reports  { reports_drug_total, reports_drug_and_event, term_observed,
                 drug_query_http_status, pair_query_http_status, *_query_url, retrieved_at, caveat },
gold_label, gold_basis, split, review { status, proposed_by, reviewer_role_required, ... }, limitations
```

`label_evidence.status`:

| Giá trị | Nghĩa | `gold_label` |
|---|---|---|
| `listed` | Biến cố được nêu tên trong một mục đã kiểm tra của nhãn (có `matched_section`, `matched_term`, `matched_quote`). | `label_listed` |
| `not_listed` | Nhãn có mục an toàn nhưng không nêu tên biến cố trong các mục đã kiểm tra. | `label_not_listed` |
| `no_section` | Nhãn không có mục nào trong `checked_sections`. | `label_not_listed` |
| `no_label` | Không tìm thấy nhãn khớp truy vấn. | `null` |

## Cách dựng lại

```bash
python -m scripts.gold.build_gold_dataset --force     # gọi mạng, làm mới bản thô
python -m scripts.gold.build_gold_dataset --offline   # dùng bản thô, không gọi mạng
```

Kiểm thử (không gọi mạng): `python -m pytest tests/test_scripts/test_gold_dataset.py -q`.

## Quy trình duyệt (bắt buộc trước khi gọi là chuẩn vàng)

1. Dược sĩ lâm sàng/chuyên gia cảnh giác dược mở `label_url` của từng dòng, đối chiếu `matched_quote` với mục `matched_section`.
2. Sửa nhãn sai, ghi `review.reviewer_id`, `review.reviewed_at`, `review.notes`; đổi `review.status` sang `expert_reviewed`.
3. Chỉ khi mọi dòng đã duyệt mới chuyển `manifest.status` sang `gold` và đóng băng băm.

## Giới hạn (nguyên văn trong từng bản ghi)

- Nhãn dương tính là bằng chứng **nhãn có nêu tên** biến cố, không phải bằng chứng nhân quả.
- Nhãn âm tính chỉ nói biến cố **không được nêu** trong các mục đã kiểm tra của nhãn đã chọn.
- Chỉ dùng nhãn Hoa Kỳ; không đối chiếu tờ hướng dẫn của Việt Nam.
- Số FAERS là báo cáo tự nguyện, có trùng lặp, không có mẫu số; không dùng để tính tỉ lệ.
- Bộ dữ liệu là ảnh chụp tại thời điểm lấy (xem `manifest.generated_at`).
