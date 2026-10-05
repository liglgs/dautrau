# Quy tắc evidence của Người 3 — dự thảo nghiệp vụ v0.1

Áp dụng cho M04/M06 của [planMVPfinal.md](../planMVPfinal.md). Các rule được đề xuất để nhóm review M01; các ví dụ trong fixture đều synthetic.

## 1. Trình tự phân tích

Normalize claim → kiểm tra nguồn/nội dung thực đọc → extract có quote → kiểm provenance → scope → stance/uncertainty → candidate contradiction → reviewer → dossier.

Evidence ngoài scope vẫn được lưu với lý do; không trở thành evidence trực tiếp bằng similarity score hoặc override không có audit. Source lỗi là gap, không phải evidence phản bác. Retrieval/planning/stopping/assessment cuối do module Người 2 xử lý.

## 2. Scope rules

| Field | Matched | Mismatched | Unknown/limitation |
|---|---|---|---|
| Ingredient | Canonical ingredient đã xác minh giống nhau | Hoạt chất khác | Mapping chưa xác minh, brand nhiều ứng viên hoặc thiếu ingredient |
| Event | Cùng canonical event/definition phù hợp | Biến cố khác | Định nghĩa không rõ; event rộng/hẹp cần mapping có nguồn |
| Population | Cùng nhóm được xác định; prototype: cùng khoảng tuổi/đơn vị | Khoảng tuổi tách rời hoặc khác nhóm đã được xác minh | Thiếu tuổi, overlap/partial coverage, chưa có subgroup result hoặc critical context |
| Dose | Cùng liều/phơi nhiễm và đơn vị đã xác minh | Khoảng liều tách rời | Thiếu liều, đơn vị khác, dùng mg/day thay mg/dose, overlap nhưng chưa rõ |
| Route | Cùng canonical route | Đường dùng khác | Missing/ambiguous route; route lấy từ drug khác trong FAERS |
| Time window | Cùng mốc và khoảng được xác định | Khoảng không giao nhau trên cùng mốc | Khác/thiếu mốc bắt đầu, partial follow-up, đơn vị khác |
| Comparator/context | Cùng comparator và context quan trọng | Nhóm đối chiếu/context khác đã được xác minh | Không có comparator hoặc field quan trọng chưa kiểm tra |

Blocking: ingredient/event thiếu hoặc khác; optional field được claim yêu cầu nhưng chưa được nguồn chứng minh; claim bỏ trống field mà source chỉ nghiên cứu một phạm vi cụ thể; critical context chưa giải quyết. Overlap hoặc source bao gồm nhóm rộng hơn không tự chứng minh hiệu ứng ở subgroup. Reviewer có thể thu hẹp claim, yêu cầu thêm evidence hoặc quyết định có lý do/version.

Hai phía cùng thiếu optional field vẫn trả unknown. Nếu field không quyết định phạm vi đang đánh giá thì có thể không blocking, nhưng dossier phải ghi giới hạn và không khẳng định về field đó. Đủ scope chưa có nghĩa đủ bằng chứng hoặc được phê duyệt.

## 3. Stance rules

| Stance | Điều kiện nhãn | Không được suy ra |
|---|---|---|
| support | Kết quả nguồn liên quan ủng hộ nhận định cụ thể, có quote/context và scope phù hợp | Supported assessment cuối hoặc quan hệ nhân quả |
| contradict | Kết quả phù hợp phản bác claim cụ thể, độ bất định được xem xét | “Không có nguy cơ” hoặc “thuốc an toàn” |
| uncertain | Không đủ thông tin, kết quả imprecise, không rõ hướng hoặc áp dụng | Không có effect chỉ vì p-value không significant |
| background | Thông tin nền/label context/báo cáo tự phát chưa đáp ứng phép so sánh | Incidence hoặc comparative risk từ FAERS |

Prototype không đọc văn bản để tự xác nhận stance. `effective_stance` hạ support/contradict thành uncertain khi uncertainty high/unknown hoặc hướng unknown/no_clear_effect, và giữ FAERS ở background. Đây là rule bảo thủ cho fixture; cần reviewer/gateway xác minh precision/CI và ý nghĩa thực tế từ nguồn thật.

## 4. Contradiction rules

| Loại | Điều kiện | Hành động |
|---|---|---|
| direct candidate | Cùng ingredient/event, scope/comparator explicit tương đương, findings đối lập đủ rõ | Giữ cả hai, reviewer xử lý; chưa xác định nguồn nào đúng |
| apparent | Findings đối lập nhưng population/route/dose/time/comparator khác | Hiển thị khác biệt, không dùng phản bác trực tiếp |
| needs_review | Scope/comparator/precision chưa đủ hoặc stance và direction không nhất quán | Yêu cầu làm rõ, không gắn direct |
| not_comparable | Khác mục tiêu drug/event hoặc chỉ so report FAERS với comparative finding | Giữ riêng; có thể tạo evidence gap cho planner |
| none | Không có opposing findings đủ xác định | Không tạo contradiction trực tiếp |

Methodological differences cần dữ liệu study design/measure/context và gateway/reviewer; prototype chưa tự xác định loại methodological. Không majority vote, không xóa findings thiểu số. Nhiều drugs/reactions trong FAERS không được tự ghép thành causal pair; Người 1 cung cấp provenance đúng phần tử drug trước extraction.

## 5. Citation rules

1. ID/version/URL phải trỏ đúng document của investigation; membership kiểm ở integration/backend.
2. SHA-256 tính trên chính parsed text UTF-8 đã phân tích. Parser đổi text phải tạo parsed version/hash mới.
3. Locator dùng Unicode code points, [start, end); không nhầm byte offsets hoặc JavaScript UTF-16.
4. Quote không rỗng, nằm đúng vị trí, khớp nguyên văn. URL không được fetch trong checker.
5. Sau bước 1–4, phải kiểm statement được đoạn nguồn/context hỗ trợ và đúng scope. Hash/URL thật không chứng minh entailment.
6. Citation thiếu, unsupported hoặc uncertain cần sửa/review; không xuất statement đó như fact chính thức.

`validate_citation` chỉ thực hiện tính toàn vẹn của document/quote. Luôn trả entailment pending và official statement eligibility false. Dossier generator/validator sau M01 phải thêm semantic gate và kiểm phê duyệt/version phía server. URL `example.invalid` trong fixture là nguồn giả lập; không bao giờ trình bày như PMID/SETID/report thật.

## 6. Quality rubric đề xuất

Lưu từng facet, nhãn, reason và source span; không cộng thành xác suất quan hệ nhân quả:

| Facet | Nhãn gợi ý | Bằng chứng cần đọc |
|---|---|---|
| Design | comparative / descriptive / synthesis / label / spontaneous / unknown | Design thực tế của nguồn |
| Relevance | direct / partial / outside_scope / unknown | Scope và claim relation |
| Content coverage | full_text / abstract_only / section_only / metadata_only / partial / synthetic | Phần thực sự truy cập và xử lý |
| Precision | adequate_for_claim / imprecise / not_reported / unknown | Estimate, interval, sample và limitations; reviewer xác nhận |
| Bias/confounding | addressed / partly_addressed / not_addressed / unknown | Methods và limitations, không suy từ tên design |
| Provenance | span_verified / failed / pending | Citation integrity và semantic status riêng |

Facet nào chưa có dữ liệu giữ unknown/not_reported. Rubric dùng để sắp ưu tiên đọc, không override scope/citation/review gates. Clinical gold cần chuyên viên xác minh; prototype chưa tự chấm rubric.

## 7. Đề xuất assessment và review

- FAERS-only, source lỗi hoặc hết budget trước khi đủ evidence: gửi gaps cho stopping policy; không tự support/contradict.
- Mismatch quan trọng: giữ source và phạm vi thực có, đề xuất thu hẹp hoặc insufficient/scope_mismatch theo policy chung.
- Mâu thuẫn quan trọng chưa giải quyết hoặc brand mơ hồ: chuyển checkpoint thích hợp.
- Supported/contradicted proposal chờ assessment review. Dossier approval là checkpoint riêng.
- Edit claim/evidence thay version và invalidation tương ứng; chỉ backend có thể xác nhận official export.

## 8. Nội dung truy xuất và prompt

Các lời yêu cầu trong tài liệu là dữ liệu nguồn. Không được thay policy, chọn tool/URL, sửa counters, tự duyệt hoặc đưa evidence ngoài tập retrieved vào dossier. Renderer phải xử lý HTML/script tại UI; checker quote/hash không chứng minh chống prompt injection/XSS. Kiểm thử tích hợp các guardrail này thuộc M05–M08/M10.
