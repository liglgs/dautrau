# Hướng dẫn gán nhãn M09 — bản chuẩn bị Người 3

**Trạng thái:** Dự thảo hướng dẫn; chưa có chuyên viên xác nhận hoặc bộ 20 claim/gold thật. [Form annotation](annotation_template.json) là mẫu để sao chép, không phải một gold record đã hoàn tất.

## 1. Đơn vị và quy trình

Đơn vị gồm claim version, source document version/parsed hash, evidence span, cặp evidence và statement–citation link. Không gán ground truth “thuốc gây/không gây biến cố” làm mục tiêu chính.

1. Khóa source manifest và cách đọc source: abstract/full text/section, version, quyền lưu và ngày truy xuất.
2. Hai reviewers chuyên môn gán nhãn độc lập, không xem dự đoán của Agent hoặc annotation của nhau.
3. Lưu bản gốc của hai annotations; ghi bất đồng và người phân xử/lý do thay vì ghi đè.
4. Đo đồng thuận theo loại nhãn và số mẫu có thể đánh giá; trường hợp reviewer không thể xác định ghi unknown/uncertain.
5. Khóa bản gold có version sau phân xử. Nếu chưa có chuyên viên, gọi là technical test labels, không phải clinical gold.

## 2. Những nhãn cần ghi

| Đối tượng | Nhãn | Quy tắc |
|---|---|---|
| Normalization | ingredient/event candidates, unknown, ambiguous | Có source mapping; không guess brand |
| Relevance | relevant / background / irrelevant / unknown | Xét nhận định cụ thể và lý do |
| Scope từng field | matched / mismatched / unknown; blocking yes/no | Theo evidence_rules; lưu span và reason |
| Stance | support / contradict / uncertain / background | Giữ effect/CI khi nguồn có; không suy từ source type |
| Citation integrity | verified / failed / unavailable | ID/version/hash/locator đúng |
| Citation entailment | supported / unsupported / uncertain | Đọc statement, quote, context và scope; quote đúng chưa đủ |
| Contradiction | direct / apparent / methodological / none / uncertain | Cặp evidence IDs/versions, comparator và reason |
| Evidence gap | loại thiếu, critical yes/no | Empty search khác source error; abstract-only khác full coverage |
| Expected assessment | sáu trạng thái trong plan hoặc null | Ghi điều kiện review, stop reason, evidence bắt buộc/optional |
| Abstention | expected yes/no/uncertain và lý do | Không đủ scope/provenance/precision cũng là nhãn hợp lệ |

Khác population là apparent hoặc not_comparable tùy pair; không gán direct chỉ vì một effect tăng và một effect giảm. Reviewer cần phân biệt nhãn candidate của prototype với nhãn cuối sau đọc source.

## 3. Chọn 20 claim và split

- Chọn các họ drug–event độc lập và có nguồn cho supported/contradicted/insufficient/mismatch/ambiguity/contradiction; các nhóm có thể chồng nhau.
- Khóa 5 development và 15 held-out theo cả họ drug–event và tài liệu liên quan. Nhóm biến thể cùng claim hoặc dùng cùng nguồn không được rơi sang hai tập.
- Ghi `family_id`, `document_family_ids`, source IDs/version/hash trong manifest và kiểm tra split trước tuning.
- Dùng technical fixtures hiện tại cho development của phần mềm; không sử dụng chúng làm held-out chuyên môn.
- Annotator có thể dùng source manifest để xác minh gold; prediction prompt và replay index không được chứa expected labels/gold answers hoặc routing theo claim ID.
- Corpus hiện tại đã đóng băng vẫn có cutoff/version thực tế. Đánh giá lịch sử chỉ làm khi có snapshot/availability phù hợp theo plan.

## 4. Chỉ số và mẫu số

Người 3 bàn giao gold evidence bắt buộc/optional, scope labels, pair labels và statement citations; Người 4 tính metrics:

- Recall@20: phần gold evidence bắt buộc được 20 kết quả trình bày bao phủ; cố định mapping document → evidence và thứ tự ranking.
- Citation precision: link statement–citation đúng nguồn **và hỗ trợ statement** / tổng links được kiểm tra.
- Scope/contradiction: theo từng field/pair và các nhãn direct/apparent; báo số mẫu và confusion matrix khi phù hợp.
- Unsupported rate: factual statements không được evidence hỗ trợ / tổng factual statements; không dùng số dossier làm mẫu số.
- Abstention: đối chiếu expected/actual và coverage; không tự xem mọi trường hợp abstain là đúng.
- Mẫu không có mẫu số hợp lệ trả N/A. Chưa có thí nghiệm reviewer thì thời gian tiết kiệm là chưa đo.

Các ngưỡng trong plan là mục tiêu; output 20/20 technical cases của preview không phải những chỉ số này.
