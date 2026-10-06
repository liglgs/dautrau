# R2-3-07 — Hướng dẫn annotation và phân xử

**Trạng thái:** đề xuất, chờ dược sĩ xác nhận. Hướng dẫn này không tạo clinical gold; AI, source machine label và kết quả evaluator không phải nhãn gold.

## Phân vùng và chống lộ

- **Partition 300 cặp:** nguồn giữ nguyên tại `data/gold/drug-event-pairs.jsonl`; index additive chỉ tham chiếu `pair_id`, không sao chép nhãn máy. `development` là 200 cặp của split nguồn `development`; `evaluation` là 100 cặp của split nguồn `test`. Tách theo hoạt chất, không chỉ theo dòng; cấm trùng hoạt chất giữa hai phần.
- **Partition 50 tài liệu:** đây là split riêng của metadata committed trong `eval/person3/corpus/audit.json`, không phải 50 dòng được chọn từ bộ 300 cặp. Gói vật lý `mvp-candidates-50-2026-10-02.zip` không tracked; index chỉ lưu ingredient/doc ID, checksum audit và bundle hash.
- Split tài liệu là **đề xuất, chờ dược sĩ xác nhận**: development gồm đúng các hoạt chất đang có trong pair-development của audit này: `metformin` + `ibuprofen` + `amoxicillin` (30 tài liệu). Evaluation gồm `atorvastatin` (có trong pair-evaluation) + `lisinopril` (không có trong 300 cặp) = 20 tài liệu. Mỗi hoạt chất gồm 10 doc IDs; không hoạt chất hoặc doc ID nào được chồng giữa hai phần.
- Giới hạn còn lại: đây chỉ là tách theo **hoạt chất chính xác**, không chứng minh các partition không chồng theo lớp thuốc/dược lý. Không được diễn giải split này là class-disjoint nếu chưa có danh mục/lý do lâm sàng được dược sĩ xác nhận.
- Prompt/tuning chỉ được nhận pair IDs/document IDs development. Không đưa pair IDs evaluation, doc IDs evaluation, expected labels, machine label, nhãn reviewer hoặc tổng hợp bất đồng vào prompt. Trước chạy, kiểm `prompt_access` trong index và test offline.

## Quy trình hai nhãn độc lập

1. Đóng băng source checksum và phiên bản index trước khi chia việc.
2. Mỗi người gán dùng một ledger riêng từ `r2_annotation_ledger.template.jsonl`; điền `annotator_id`, vai trò, `annotation_date`, `independent_label` và rationale. Không xem ledger còn lại hay model prediction.
3. Ghi `unknown` khi không có bằng chứng đủ; không dùng `false` thay unknown. Nhãn evidence phải tách scope, provenance/citation integrity, entailment, coverage và limitation.
4. So sánh hai ledger sau khi khóa. `disagreement` lưu cả trường, hai giá trị và lý do, không ghi đè nhãn độc lập.
5. Dược sĩ/phân xử ghi decision, date và rationale trong bản adjudication mới. Chỉ quy trình được đơn vị chấp nhận mới có thể phát hành gold; artifact này vẫn là **đề xuất, chờ dược sĩ xác nhận**.

## Nhãn tối thiểu

| Trường | Giá trị cho phép | Lưu ý |
| --- | --- | --- |
| `independent_label` | `listed`, `not_listed`, `insufficient`, `unknown` | Không sao chép `gold_label`/model output; đây là nhãn review đề xuất. |
| `citation_integrity` | `verified`, `failed`, `unavailable` | Quote/locator/version phải kiểm với snapshot. |
| `citation_entailment` | `supported`, `unsupported`, `uncertain` | Quote đúng vị trí chưa đủ chứng minh conclusion. |
| `coverage` | `abstract_only`, `partial`, `complete_for_question`, `unknown` | `abstract_only` không được mô tả là full text. |
| `disagreement.status` | `not_compared`, `none`, `open`, `resolved` | Mẫu trống dùng `not_compared`; chỉ dùng `none` sau khi đã so sánh hai nhãn độc lập. |
| `ai_generated` | `null`, `true`, `false` | Mẫu trống dùng `null`; `true` không bao giờ được dùng làm gold. |

Mọi output từ ledger phải kèm: **đề xuất, chờ dược sĩ xác nhận**.
