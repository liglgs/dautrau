# R2-3-01 — Glossary trường câu hỏi và normalization

**Trạng thái:** đề xuất, chờ dược sĩ xác nhận. Đây là rubric cho tiếp nhận và thẩm định bằng chứng; không phải contract bệnh viện, không tự xác nhận chỉ định hay thay thế đánh giá ca.

## Hai ngưỡng bắt buộc

| Ngưỡng | Mục tiêu | Trường bắt buộc | Khi thiếu |
| --- | --- | --- | --- |
| `required-for-intake` | Nhận đúng loại yêu cầu, lập câu hỏi tra cứu và xin bổ sung | `purpose`; ít nhất một trong `drug_or_exposure`, `event_or_outcome`, `indication`; `requester_context` hoặc `setting` nếu người gửi đã biết | Giữ `unknown`, ghi câu hỏi bổ sung; yêu cầu DI chung không bị ép thành ca ADR. |
| `required-for-conclusion` | Kết luận về khả năng áp dụng của một nguồn cho câu hỏi cụ thể | `purpose`, `drug_or_exposure`, `outcome`, `population`, `setting`, `route`, `comparator`, `time` | Không kết luận applicability đầy đủ; nêu rõ chiều nào `unknown` và chỉ trả lời tạm theo phạm vi đã biết. |

`indication` hữu ích để chọn nguồn nhưng không phải điều kiện bắt buộc ở `required-for-conclusion` khi câu hỏi là an toàn không phụ thuộc chỉ định; lý do miễn phải được ghi. Với câu hỏi ca ADR, `case_id`/phiên bản ca là điều kiện nhận diện bổ sung, không thay thế tám trường trên.

## Field glossary

| Trường | Định nghĩa/giá trị cần giữ | `required-for-intake` | `required-for-conclusion` | Không được làm |
| --- | --- | ---: | ---: | --- |
| `purpose` | Loại quyết định: `general_DI`, `literature_appraisal`, `suspected_ADR_case`, `label_product_check`, hoặc `safety_update`. | Có | Có | Không suy `suspected_ADR_case` chỉ vì có tên thuốc và biến cố. |
| `indication` | Bệnh/tình huống điều trị hoặc lý do dùng thuốc, nguyên văn nếu có. | Có, trừ khi người gửi nói rõ chưa biết | Có điều kiện theo mục đích | Không đổi `unknown` thành chỉ định “thường gặp”. |
| `population` | Tuổi/nhóm tuổi, thai kỳ, giới, bệnh kèm, tiêu chí vào/ra khi nguồn hoặc yêu cầu nêu. | Không | Có | Không suy quần thể từ quốc gia hay cơ sở điều trị. |
| `setting` | Ngoại trú/nội trú/cấp cứu, quốc gia/cơ sở hoặc loại dữ liệu. | Có nếu đã biết | Có | Không coi dữ liệu bảo hiểm là diễn biến một ca. |
| `route` | Đường dùng của sản phẩm/phơi nhiễm: uống, tiêm, nhỏ tai… | Không | Có | Không tự match sản phẩm khác đường; `unknown` khác `oral`. |
| `comparator` | Không phơi nhiễm, placebo, hoạt chất/nhóm điều trị so sánh, hay `none_reported`. | Không | Có | Không đặt comparator mặc định khi abstract không nêu. |
| `outcome` | Biến cố/kết quả và định nghĩa/cửa sổ đo nếu có. | Có | Có | Không thay outcome bằng một từ đồng nghĩa chưa được kiểm. |
| `time` | Ngày/giờ dùng thuốc và diễn biến ca, hoặc risk/follow-up window của nghiên cứu; kèm timezone nếu có. | Không | Có | Không bịa thời điểm; thời gian nghiên cứu không phải timeline của ca. |

### Quy tắc normalized name và trạng thái chưa biết

1. Giữ `source_term`/tên gốc; `candidate_normalized` chỉ là đề xuất và có `confirmation_required: true`.
2. `unknown`, `not_recorded`, `not_applicable`, `not_assessed` là các trạng thái riêng. Không chuyển bất cứ trạng thái nào thành `false`, `negative`, hay “không có”.
3. Khi có nhiều candidate hoặc tên biệt dược chưa đối chiếu, giữ tất cả candidates, `normalization_status: ambiguous`, và chỉ định người xác nhận là dược sĩ.
4. Phạm vi nguồn phải ghi độc lập từng chiều `matched`, `mismatched`, hoặc `unknown`; không suy `matched` từ claim.

## Ví dụ intake (đều là đề xuất, chờ dược sĩ xác nhận)

| Tình huống | Dữ liệu nhận được | Intake hợp lệ | Có thể kết luận? | Việc cần xin bổ sung |
| --- | --- | --- | --- | --- |
| DI chung | “Nguy cơ AA/AD của fluoroquinolone?” | `purpose=general_DI`, `outcome=AA/AD`; `route/population/comparator/time=unknown` | Chưa kết luận áp dụng cho một người bệnh | Mục đích dùng, quần thể, đường và bối cảnh nếu cần trả lời cho ca cụ thể. |
| Kiểm nhãn sản phẩm | “Pantoprazole tiêm có cùng cảnh báo viên uống không?” | `purpose=label_product_check`, route tiêm và sản phẩm đích | Chưa; cần đúng SETID/dạng/hàm lượng | Tên gốc, hàm lượng, dạng bào chế, hãng/SETID nếu có. |
| Nghi ngờ ADR | “Sau ciprofloxacin, đau bụng; không nhớ giờ dùng.” | `purpose=suspected_ADR_case`, outcome nguyên văn; `time=unknown` | Không; không tạo dechallenge/rechallenge hay causality score | Case ID, phiên bản, administrations, outcome/timeline, nguyên nhân khác, lab và nguồn từng dữ kiện. |
| So sánh nghiên cứu | FQ so macrolide ở người lớn Đức, 60 ngày | Đủ intake | Chỉ có thể kết luận trong population/setting/route/comparator/outcome/time trích được | Xác minh đúng sản phẩm và khả năng áp dụng tại nơi dùng. |

Mọi đầu ra sử dụng rubric này phải hiển thị: **đề xuất, chờ dược sĩ xác nhận**.
