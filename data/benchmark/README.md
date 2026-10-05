# Bộ nhận định và nhãn — bản đề xuất Người 3

**Trạng thái:** `draft_not_frozen_not_gold`. Đây là 20 đầu vào kỹ thuật được tạo từ 4 họ thuốc–biến cố của gói ứng viên ngày 02/10/2026; chưa phải benchmark clinical đã nghiệm thu.

| Tập đề xuất | Họ | Số nhận định |
|---|---|---|
| Development | metformin / diarrhoea | 5 |
| Heldout | ibuprofen / gastrointestinal haemorrhage | 5 |
| Heldout | lisinopril / cough | 5 |
| Heldout | amoxicillin / rash | 5 |
| Dự phòng | atorvastatin / myalgia | Chưa tạo claim |

Mỗi họ có broad scope, population/route, scope yêu cầu cụ thể, route challenge và brand chưa xác định. Các giá trị liều/thời gian là **giả định đầu vào kiểm thử**, không phải trích từ nguồn, khuyến nghị dùng thuốc hoặc gold. Các brand chưa xác định là input kỹ thuật, không phải tên biệt dược đã xác thực.

## Các tệp

- `mvp_claims.jsonl`: Người 3/4 và chuyên gia cần chọn/sửa/chấp nhận từng claim. Không điền expected label theo output agent.
- `mvp_manifest.json`: Hash corpus, đề xuất split/family và các giới hạn. Chưa đóng băng; chưa đạt yêu cầu đủ supported/contradicted/contradiction của plan.
- `mvp_gold.jsonl`: **Rỗng có chủ đích**, vì chưa có nhãn chuyên môn đã chốt.
- `reviewer_a.jsonl`, `reviewer_b.jsonl`: Mỗi reviewer nhận một file riêng; không xem file còn lại hoặc prediction trước khi gán nhãn.

Đọc corpus gốc trong ZIP hoặc `data/person3/corpus/documents.jsonl` sau khi chạy `prepare_person3_corpus.py`. Tra cứu từng tài liệu theo `source_doc_ids` của claim. Hướng dẫn/rubric: `docs/person3/annotation_guidelines.md`, schema mẫu `docs/person3/annotation_template.json`.

## Quy trình gán nhãn

1. Người 4 cùng reviewer chuyên môn xác nhận hoặc sửa 20 claim, coverage và split. Khóa phiên bản trước tuning. Nếu phát triển prompt trên một họ heldout, đổi split/corpus và ghi lại exposure; không tiếp tục gọi nó là heldout chưa thấy.
2. Hai reviewer dùng danh tính khác nhau, gán nhãn độc lập. Điền `annotator_id`, `annotator_role`, `annotation_timestamp`; vai trò được checker nhận: `clinical_pharmacist`, `physician`, `pharmacovigilance_specialist`. Nhóm chịu trách nhiệm xác nhận chuyên môn thật.
3. Với mỗi evidence, ghi source ID/version/hash, quote và locator Unicode, relevance/stance, sáu scope fields, integrity/entailment và lý do. Expected assessment/abstention là nhãn reviewer, không sao chép từ chương trình.
4. Chỉ khi hoàn tất đổi `record_status` thành `completed_independent_expert_review`. Dùng `required_gold_evidence_ids` để trỏ các span được gán nhãn. FAERS không được gán direct support/contradict.
5. Chạy `python scripts/check_person3_annotations.py`. Checker phát hiện thiếu review, stale corpus, quote/locator sai, reviewer trùng nhau, scope bị chặn và bất đồng. Checker **không tự xuất bản gold**.
6. Chuyên gia phân xử bất đồng, giữ nguyên hai file gốc và lưu lý do/phiên bản quyết định. Người 3/4 chốt contract gold với code evaluator của Người 4 rồi mới ghi gold và đóng băng manifest.

Ngay cả các dòng đã đồng thuận vẫn cần nhóm chấp nhận và xác nhận provenance; kiểm tra JSON không xác nhận chuyên môn hay sự đúng đắn y khoa.

## Chưa đủ cho metric clinical

Bộ nguồn không mặc nhiên chứa đủ kết luận trái chiều chính xác. Cần reviewer xác định supported, contradicted, insufficient, mismatch, ambiguity, contradiction; nếu không có nguồn phù hợp, bổ sung corpus trước khi nghiệm thu. Không chia các biến thể cùng family/document sang cả dev và heldout.

Lượt hiện tại chỉ chạy trích xuất/flow trên development metformin. Các báo cáo kỹ thuật không phải recall/citation entailment/clinical accuracy. Không dùng gợi ý từ khóa offline làm baseline RAG hoặc gold.
