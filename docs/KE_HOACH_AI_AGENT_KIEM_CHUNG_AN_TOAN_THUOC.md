# Kế hoạch đề tài: AI agent kiểm chứng bằng chứng về tác dụng bất lợi của thuốc

**Tên tiếng Anh dự kiến:** Evidence-Seeking Agent for Drug Safety Verification.

**Ngày lập:** 29/09/2026. **Trạng thái:** đề xuất nghiên cứu và MVP, chưa triển khai, chưa có kết quả thực nghiệm.

> **Đề xuất ngắn:** Xây dựng agent giúp dược sĩ xác minh một nhận định về thuốc–biến cố bằng cách chủ động tra cứu nhãn thuốc và nghiên cứu, phát hiện bằng chứng còn thiếu hoặc không cùng phạm vi, rồi xuất hồ sơ dẫn chứng. Giá trị cần chứng minh là giảm kết luận vượt quá bằng chứng với chi phí tra cứu đo được.

## 1. Bài toán, người dùng và giá trị thực tế

### 1.1. Người dùng chính

- Dược sĩ làm công tác thông tin thuốc, dược lâm sàng hoặc cảnh giác dược.
- Bác sĩ cần một bản tổng hợp bằng chứng để kiểm tra lại.
- Người dùng thử đầu tiên: dược sĩ/giảng viên dược cộng tác với nhóm.

Hệ thống phục vụ tra cứu chuyên môn. Bản MVP không tiếp nhận bệnh án và không đưa lời khuyên thay đổi điều trị cho từng bệnh nhân.

### 1.2. Pain cần xác minh qua phỏng vấn

Khi nhận câu hỏi “thuốc X có liên quan đến biến cố Y không?”, người tra cứu phải:

1. Xác định đúng hoạt chất, chế phẩm và cách gọi biến cố.
2. Tìm thông tin trong nhiều phần của nhãn thuốc và nhiều bài nghiên cứu.
3. Kiểm tra nghiên cứu có đúng thuốc, đối tượng, đường dùng và biến cố đang hỏi không.
4. Phân biệt báo cáo nghi ngờ, mối liên quan trong nghiên cứu và phát biểu về nhân quả.
5. Lưu lại nguồn để đồng nghiệp kiểm tra kết luận.

MALADE xác định biến thể thuật ngữ và thông tin bất lợi nằm rải rác trong văn bản là các khó khăn của khai thác thông tin an toàn thuốc [R1]. Mức thời gian tốn kém và nhu cầu sử dụng tại đơn vị Việt Nam là giả thuyết sản phẩm cần phỏng vấn, chưa có số liệu của nhóm.

**Lợi ích kỳ vọng:** giảm công sức tìm và kiểm tra nguồn; giúp người đọc nhận ra giới hạn của kết luận. Chưa tuyên bố giảm tai biến hay cải thiện kết quả điều trị.

### 1.3. Keypoint

**Agent phải nhận ra khi bằng chứng hiện có chưa trả lời đúng câu hỏi và quyết định tra cứu gì tiếp theo.**

Các tình huống trọng tâm:

| Tình huống | Lỗi hệ thống dễ mắc | Hành vi cần đạt |
|---|---|---|
| Có báo cáo thuốc và biến cố cùng xuất hiện | Kết luận thuốc gây biến cố | Giữ mức “được báo cáo”; tìm thêm bằng chứng |
| Nhãn không nhắc biến cố | Kết luận không có nguy cơ | Ghi “không tìm thấy trong nguồn đã đọc” |
| Bài nghiên cứu về thuốc phối hợp | Quy kết cho một hoạt chất | Nhận diện khác biệt và tìm nghiên cứu phù hợp |
| Nghiên cứu ở một nhóm bệnh nhân hẹp | Tổng quát cho mọi người | Giới hạn phát biểu theo quần thể |
| Hai tài liệu có kết quả khác nhau | Chọn nguồn thuận với câu trả lời ban đầu | So sánh phạm vi, thời điểm, thiết kế và mức độ bất định |
| Tên thương mại/thuật ngữ không khớp | Bỏ cuộc hoặc gộp nhầm thuốc | Chuẩn hóa hoặc yêu cầu làm rõ |

## 2. Tính mới: điều gì đã có và phần nào nhóm đề xuất

### 2.1. Nền tảng đã có

MALADE là công trình MLHC 2024 về agent kết hợp RAG để khai thác quan hệ thuốc–biến cố từ nhãn thuốc FDA. Paper và repository có thể dùng để tham khảo kiến trúc, cách trích xuất và tổ chức đánh giá [R1, R2].

Vì vậy, “chatbot tra cứu tác dụng phụ”, “nhiều agent cùng thảo luận” hoặc “thêm RAG vào dữ liệu FDA” không đủ làm đóng góp mới.

### 2.2. Đóng góp dự kiến của nhóm

**Bài toán hẹp:** kiểm chứng nhận định khi thông tin thiếu, không cùng phạm vi hoặc có khả năng mâu thuẫn, dưới ngân sách truy xuất cố định.

**Cơ chế đề xuất:**

1. Lưu từng bằng chứng kèm phạm vi áp dụng và đoạn nguồn.
2. Tạo danh sách khoảng trống cần giải quyết.
3. Agent chọn hành động theo khoảng trống quan trọng nhất.
4. Kiểm tra xem tài liệu mới có thực sự bổ sung thông tin.
5. Dừng với báo cáo có giới hạn rõ khi hết ngân sách hoặc không còn nguồn phù hợp.

**Câu hỏi nghiên cứu chính:**

> So với RAG và workflow tra cứu cố định, lựa chọn hành động theo khoảng trống bằng chứng có giảm tỷ lệ kết luận quá mức mà vẫn duy trì độ bao phủ câu trả lời không?

**Giả thuyết phụ:** thông tin về quần thể, chế phẩm và thời điểm giúp giảm các trường hợp bị gắn nhầm là mâu thuẫn.

Đây là đóng góp dự kiến, chưa xác lập tính mới toàn cầu. Tuần 1 phải rà soát nghiên cứu liên quan và chốt với mentor. Có thể chứng minh tính mới ở cách đặt bài toán, bộ kiểm thử có nhãn, hoặc cơ chế chọn hành động; không mặc định cả ba đều mới.

### 2.3. Khác bài toán đối chiếu thuốc hiện tại

| Nội dung | Dự án đối chiếu thuốc | Đề tài này |
|---|---|---|
| Đơn vị xử lý | Danh sách thuốc và nguồn của một bệnh nhân | Nhận định thuốc–biến cố |
| Nguồn chính | Hồ sơ/khai báo dùng thuốc | Nhãn thuốc và nghiên cứu công khai |
| Quyết định agent | Làm rõ khác biệt giữa nguồn | Chọn nguồn cần tra tiếp để kiểm chứng nhận định |
| Đầu ra | Vấn đề cần xác nhận trong đối chiếu | Hồ sơ bằng chứng và giới hạn kết luận |
| Đánh giá | Phát hiện và đóng vấn đề | Độ đúng trích dẫn, phạm vi và mức kết luận |

Có thể tái sử dụng phần giao diện, lưu nguồn, audit log và bộ đo chi phí sau khi rà soát code. Không dùng nhãn benchmark cũ để đánh giá bài toán mới.

## 3. Phạm vi MVP

### 3.1. Bắt buộc

- Đầu vào một hoạt chất và một biến cố; ưu tiên tên hoạt chất quốc tế.
- Đầu ra tiếng Việt, giữ nguyên tên khoa học và đoạn dẫn chứng gốc.
- Nguồn chính: openFDA Drug Label và PubMed; DailyMed dùng đối chiếu khi cần.
- Bắt đầu với một nhóm biến cố: **tổn thương thận cấp**; chỉ mở rộng sang **xuất huyết tiêu hóa** nếu thiếu cặp đủ dữ liệu hoặc chuyên gia thấy phù hợp.
- Chuẩn hóa tên bằng danh mục nhỏ và RxNorm.
- Agent có trạng thái, công cụ truy xuất, kiểm tra nguồn và giới hạn tài nguyên.
- Báo cáo có đường dẫn, định danh tài liệu, ngày truy cập và lý do dừng.
- Bộ đánh giá tách khỏi dữ liệu agent được nhìn thấy.

### 3.2. Phần bổ sung có điều kiện

- openFDA Drug Event: dùng để thể hiện thông tin báo cáo nghi ngờ và kiểm tra lỗi suy diễn nhân quả; triển khai sau khi luồng nhãn thuốc + nghiên cứu chạy ổn.
- Bài toàn văn trong PMC Open Access khi abstract không đủ.
- Đối chiếu thông tin cảnh giác dược công khai tại Việt Nam trên một tập nhỏ.
- Nhận tên thương mại Việt Nam sau khi có danh mục được kiểm tra.

### 3.3. Ngoài MVP

- Kê đơn, đổi liều, ngừng thuốc hoặc đánh giá nhân quả cho một bệnh nhân cụ thể.
- Chẩn đoán, đọc ảnh, CV/VLM, voice agent.
- Phát hiện phản ứng có hại hoàn toàn mới hoặc dự báo nguy cơ cá nhân.
- Tự động gửi báo cáo ADR tới cơ quan quản lý.
- Tự tính ROR/PRR, xếp hạng độ an toàn giữa các thuốc hoặc suy ra tỷ lệ mắc từ FAERS.
- Fine-tune/RL trước khi có baseline và dữ liệu đánh giá đủ tốt.

## 4. Input và output

### 4.1. Input tối thiểu

~~~json
{
  "drug_name": "<ten-hoat-chat>",
  "event_name": "<bien-co-can-kiem-chung>",
  "question": "<nhan-dinh-can-xac-minh>",
  "population": null,
  "route": null,
  "as_of_date": "<YYYY-MM-DD>",
  "language": "vi"
}
~~~

Nếu chưa xác định được hoạt chất hoặc chế phẩm, trả câu hỏi làm rõ. Không âm thầm chọn một ứng viên có tên gần giống.

Ngày giới hạn truy xuất là điều kiện lọc nguồn. Nếu thiếu bản lưu lịch sử của nhãn thuốc, hệ thống phải báo không đủ dữ liệu để tái dựng kết luận tại thời điểm quá khứ.

### 4.2. Output cho người dùng

1. **Câu hỏi đã chuẩn hóa:** thuốc, biến cố, đối tượng/phạm vi.
2. **Tóm tắt:** điều nguồn hỗ trợ và điều chưa xác định.
3. **Bảng bằng chứng:** loại nguồn, nội dung, phạm vi, trích dẫn và link.
4. **Điểm chưa thống nhất:** mâu thuẫn thật, khác phạm vi hoặc chưa đủ dữ liệu để phân biệt.
5. **Khoảng trống:** thông tin còn thiếu và nguồn đã tìm.
6. **Trạng thái:** hoàn thành bản tổng hợp / cần người dùng làm rõ / cần chuyên gia xem / chưa hoàn tất vì lỗi hoặc hết ngân sách.

Tách ba trục đánh giá để tránh gộp các khái niệm:

| Trục | Giá trị dự kiến |
|---|---|
| Quan hệ của từng đoạn với nhận định | supports / opposes / not_addressed / unclear |
| Loại bằng chứng | product_label / clinical_study / spontaneous_report / other |
| Khả năng áp dụng | matches_scope / scope_mismatch / scope_unknown |

Các giá trị này là schema nhóm đề xuất, không phải phân loại được FDA công nhận. Quy tắc sử dụng cần dược sĩ rà soát.

**Nguyên tắc:** “không có ý nghĩa thống kê” không tự động là “không có tác dụng”; “không được nhắc” không phải “đã chứng minh không liên quan”. Chỉ ghi mâu thuẫn khi đã kiểm tra hai phát biểu có đang nói về cùng phạm vi hay không.

## 5. Nguồn dữ liệu và cách lấy

### 5.1. Tổng quan

| Nguồn | Vai trò | Truy cập | Ưu tiên |
|---|---|---|---|
| openFDA Drug Label | Nội dung nhãn thuốc dạng JSON | REST API, đăng ký key miễn phí | P0 |
| PubMed | Tìm metadata, abstract, PMID/DOI | NCBI E-utilities | P0 |
| RxNorm | Chuẩn hóa tên và định danh thuốc | RxNav REST API | P0 |
| OMOP reference set | Tập cặp thuốc–biến cố tham chiếu | Gói R MethodEvaluation/OHDSI | P0 |
| DailyMed | Đối chiếu tài liệu SPL và phiên bản | REST API v2 | P1 |
| PMC Open Access | Bổ sung toàn văn có quyền sử dụng phù hợp | Dịch vụ truy xuất được PMC cho phép | P1 |
| openFDA Drug Event | Báo cáo biến cố nghi ngờ | REST API | P1 |
| Trung tâm DI & ADR Quốc gia | Bối cảnh và tài liệu công khai Việt Nam | Website/tài liệu công khai | P2 |

**P0:** phải có cho MVP. **P1:** thêm khi luồng chính ổn. **P2:** mở rộng.

### 5.2. openFDA Drug Label

- Tài liệu: [Drug Labeling Overview][R3].
- Schema: [Searchable Fields][R4].
- Endpoint: https://api.fda.gov/drug/label.json
- Lấy theo hoạt chất; kiểm tra đúng chế phẩm/đường dùng trước khi sử dụng.
- Trường ưu tiên: adverse_reactions, warnings, warnings_and_cautions, boxed_warning, contraindications, drug_interactions.
- Lưu id, set_id, version, effective_time nếu có cùng metadata thuốc.

**Thiết kế thu thập của nhóm:**

- Chỉ tải thuốc trong danh mục MVP.
- Giữ snapshot JSON và bản văn bản đã chuẩn hóa.
- Khử lặp theo định danh và hash; các bản cùng nội dung không tính là nhiều bằng chứng độc lập.
- Thiếu section thì giữ trạng thái thiếu; không thay bằng văn bản do LLM sinh.
- Đọc thông tin phạm vi phê duyệt/loại sản phẩm; sự xuất hiện trong dữ liệu nhãn không tự chứng minh mọi nội dung/sản phẩm đã được FDA phê duyệt.

Nhóm nên đăng ký API key. Tài liệu hiện ghi giới hạn với key là 240 request/phút và 120.000 request/ngày; cần đọc lại khi triển khai [R5]. Áp dụng cache, backoff và hạn mức nội bộ thấp hơn.

### 5.3. PubMed và PMC

PubMed dùng để tìm bài và lấy metadata/abstract qua E-utilities [R6, R7]. Luồng dự kiến:

1. ESearch: truy vấn hoạt chất + từ đồng nghĩa biến cố.
2. EFetch/ESummary: lấy nội dung và metadata của PMID.
3. Lưu tiêu đề, tác giả, thời điểm, loại bài, PMID, DOI, abstract và trạng thái sửa/rút bài nếu có.
4. Xếp hạng theo đúng thuốc, biến cố và phạm vi.
5. Nếu abstract thiếu thông tin cần thiết, tìm toàn văn phù hợp trong PMC Open Access.

Query đầu tiên không bắt buộc chứa các từ “causes” hoặc “increases”, nhằm giảm thiên lệch tìm bằng chứng ủng hộ. Lượt sau mới mở rộng theo khoảng trống cụ thể.

**Chính sách dữ liệu:** abstract và toàn văn có thể có bản quyền. Không mặc định mọi nội dung PubMed/PMC đều được tái phân phối. Lưu giấy phép, sử dụng dịch vụ được phép và ưu tiên phát hành ID/URL/annotation thay vì sao chép toàn văn [R7, R8].

Adapter ban đầu tự giới hạn tối đa 3 request/giây; kèm tên công cụ và email theo hướng dẫn NCBI [R7].

### 5.4. RxNorm và DailyMed

RxNorm hỗ trợ tìm tên, ứng viên gần đúng và quan hệ giữa các khái niệm thuốc [R9]. Dùng nó để gợi ý chuẩn hóa, sau đó kiểm tra loại khái niệm và hoạt chất. Không giả định dữ liệu bao phủ đầy đủ tên thương mại Việt Nam.

DailyMed cung cấp web service cho tài liệu SPL; dùng để tìm bản nhãn phù hợp hoặc đối chiếu định danh [R10]. Hai bản nhãn openFDA/DailyMed có cùng nguồn gốc được gắn cùng nhóm nguồn, tránh đếm đôi.

### 5.5. openFDA Drug Event — chỉ dùng có kiểm soát

Endpoint: https://api.fda.gov/drug/event.json. Tài liệu và schema ở [R11, R12].

FDA nêu rõ các báo cáo không thiết lập quan hệ nhân quả và không dùng để ước tính tỷ lệ mắc. Một báo cáo có thể chứa nhiều thuốc và nhiều phản ứng, không có ánh xạ chắc chắn từ từng thuốc sang từng phản ứng [R11].

**Cách dùng trong đề tài:** tìm xem có thông tin báo cáo phù hợp để lập danh mục nguồn; gắn nhãn “báo cáo nghi ngờ”. Agent cần tìm thêm nguồn nếu nhận định đầu vào mạnh hơn bằng chứng này.

Thiết kế adapter:

- Lưu query, khoảng thời gian, thời điểm tải và tổng số kết quả API trả.
- Phân biệt đếm bản ghi với số người bệnh; không hiển thị thành tỷ lệ nguy cơ.
- Kiểm tra phiên bản báo cáo, khả năng trùng và thuốc dùng kèm.
- Chỉ đưa các trường cần thiết vào ngữ cảnh LLM.
- Khi kiểm tra đồng thời nhiều điều kiện trên mảng thuốc, xác nhận chúng thuộc cùng phần tử thuốc; không tin kết quả search là đủ để kết luận điều này.
- Không xem endpoint là nguồn cập nhật tức thời.

### 5.6. Bộ tham chiếu OMOP: có gì và thiếu gì?

[OMOP reference set của OHDSI][R13] có 399 cặp thuốc–biến cố, gồm 165 đối chứng dương và 234 đối chứng âm, trên bốn nhóm biến cố. Có thể nạp từ gói R MethodEvaluation rồi xuất CSV [R14].

**Cần phân biệt:** repository MALADE có bảng OMOP Ground Truth cho các nhóm thuốc và biến cố riêng [R2]. Bảng đó không đồng nhất với bộ 399 cặp của MethodEvaluation. Phải ghi rõ tên tập, phiên bản, số hàng và đơn vị đánh giá.

Đối với MVP, dùng bộ 399 cặp để chọn ca và đánh giá phụ về quan hệ thuốc–biến cố. Không dùng nhãn âm của bộ tham chiếu để khẳng định một thuốc tuyệt đối an toàn.

Tập này không có sẵn nhãn đoạn trích đúng, mâu thuẫn, thiếu dữ liệu hay hành động tra cứu tiếp theo. Những nhãn phục vụ đóng góp chính phải xây dựng riêng.

### 5.7. Nguồn Việt Nam

Website Trung tâm DI & ADR Quốc gia có kênh báo cáo và tài liệu cảnh giác dược [R15]. Có thể chọn một số tài liệu công khai để đánh giá cách trình bày tiếng Việt hoặc kiểm tra khác biệt bối cảnh.

Không giả định nhóm được quyền truy cập dữ liệu báo cáo ADR cá nhân của Việt Nam. Nguồn này không là điều kiện bắt buộc để hoàn thành MVP.

## 6. Kế hoạch xây dữ liệu

### 6.1. Ba lớp dữ liệu tách biệt

| Lớp | Nội dung | Ai được truy cập |
|---|---|---|
| Kho nguồn | Nhãn, abstract/toàn văn được phép, metadata, snapshot | Retriever và agent |
| Đề bài | Thuốc, biến cố, phạm vi, ngày giới hạn | Agent và evaluator |
| Nhãn đánh giá | Đoạn bằng chứng chuẩn, trạng thái, lỗi cần tránh | Evaluator; không đưa vào retriever |

Không index file nhãn OMOP, annotation hoặc lời giải benchmark vào kho mà agent tìm kiếm.

### 6.2. Quy mô mục tiêu

- **Pilot:** 20 ca để kiểm tra nguồn, schema, chi phí và khả năng gán nhãn.
- **Bộ chính:** mục tiêu 100 ca, phân bổ khoảng 25 development / 25 validation / 50 test.
- Nếu một nhóm biến cố không có đủ ca đa dạng và đủ nguồn, chốt ít ca hơn hoặc mở rộng nhóm thứ hai; công bố số thực tế.
- **Stress test:** tạo tối đa 20 biến thể của ca gốc bằng cách ẩn nguồn hoặc thay cách gọi đầu vào, không sửa nội dung y khoa của tài liệu.

Chia nhóm theo hoạt chất; các biến thể và chế phẩm gần tương đương của cùng ca ở cùng split. Kiểm tra thêm khả năng trùng họ thuốc/tài liệu. Số lượng mỗi split có thể lệch để giữ nguyên tắc này.

### 6.3. Những dạng ca cần bao phủ

1. Có bằng chứng liên quan tương đối rõ.
2. Không đủ bằng chứng trong kho được cung cấp.
3. Có nguồn nhưng khác chế phẩm, quần thể hoặc định nghĩa biến cố.
4. Có hai kết quả cần so sánh phạm vi trước khi kết luận.
5. Tên mơ hồ hoặc lỗi truy xuất.

Không bắt buộc một tỷ lệ cố định “mâu thuẫn thật”: chỉ gán nhãn khi chuyên gia xác nhận. Nếu ít ca, báo thiếu dữ liệu cho nhóm này.

### 6.4. Quy trình gán nhãn

1. Thành viên dữ liệu chuẩn bị gói nguồn và metadata cho từng ca.
2. Người gán nhãn đánh dấu đoạn nguồn, phạm vi và mức phát biểu được phép.
3. Dược sĩ rà soát nhãn chính, đặc biệt các ca âm/thiếu/mâu thuẫn.
4. Ít nhất 20% ca được đánh giá độc lập bởi người thứ hai có chuyên môn phù hợp.
5. Ghi bất đồng và phân xử; ca không đạt đồng thuận giữ nhãn “uncertain”, không ép thành đúng/sai.

**Dự trù công sức chuyên gia:** khoảng 12–20 giờ cho 100 ca là giả định lập lịch; đo thời gian thực trên 10 ca đầu để điều chỉnh. Nhóm phải thương lượng thời gian/chi phí, không coi đây là nguồn lực miễn phí sẵn có.

Nếu không có chuyên gia, chỉ công bố kết quả kiểm chứng phần mềm và trích dẫn; chưa công bố hiệu quả về nhận định an toàn thuốc.

### 6.5. Tái lập và giới hạn

- Manifest gồm URL, source ID, retrieved_at, publication/effective date, version, SHA-256, giấy phép và lỗi tải.
- Dùng snapshot cố định cho thực nghiệm chính; chạy live là thí nghiệm riêng.
- Nhãn phản ánh kho bằng chứng trong phạm vi bài toán, không là tuyên bố biết mọi bằng chứng trên thế giới.
- Không coi benchmark công khai là bằng chứng model chưa từng thấy dữ liệu khi pretrain.
- Stress test thiếu nguồn là điều kiện mô phỏng, không phản ánh tỷ lệ thiếu dữ liệu ngoài thực tế.

## 7. Kiến trúc kỹ thuật và luồng agent

### 7.1. Kiến trúc tối giản

~~~mermaid
flowchart TD
    U["Người dùng: thuốc + biến cố + phạm vi"] --> N["Chuẩn hóa đầu vào"]
    N --> P["Agent chọn hành động"]
    P --> T["Công cụ tìm nguồn / lấy tài liệu"]
    T --> E["Trích xuất bằng chứng có định danh"]
    E --> C["Kiểm tra trích dẫn, phạm vi, khoảng trống"]
    C --> D{"Đủ điều kiện kết thúc?"}
    D -- "Chưa đủ, còn ngân sách" --> P
    D -- "Đủ / hết ngân sách / cần chuyên gia" --> R["Báo cáo + trạng thái + nguồn"]
    S["Snapshot và chỉ mục"] --> T
    P --> L["Log hành động và chi phí"]
    T --> L
~~~

Một agent điều phối cùng các công cụ là đủ cho bản đầu. Bộ kiểm tra có thể kết hợp code và một lượt LLM; chỉ thêm nhiều agent độc lập nếu ablation chứng minh có lợi.

### 7.2. Công cụ dự kiến

| Công cụ | Chức năng | Kiểm soát |
|---|---|---|
| normalize_drug | Trả ứng viên hoạt chất và định danh | Không tự chọn khi mơ hồ |
| search_labels | Tìm nhãn thuốc trong nguồn/snapshot | Lọc đúng sản phẩm, lưu query |
| search_literature | Tìm và xếp hạng tài liệu | Ghi giới hạn ngày và phạm vi |
| fetch_document | Lấy section/abstract/toàn văn phù hợp | Kiểm tra nguồn, loại và quyền sử dụng |
| search_event_reports | Tra báo cáo nghi ngờ; tùy chọn | Không trả điểm nguy cơ lâm sàng |
| compare_evidence | So sánh các đoạn đã lấy | Chỉ dùng evidence ID có thật |
| validate_citations | Kiểm tra vị trí trích dẫn, ID và số liệu | Sai thì không phát hành câu đó |
| finalize_report | Xuất JSON và bản đọc được | Ghi thiếu sót và lý do dừng |

### 7.3. Trạng thái agent

Lưu: normalized_query, retrieved_source_ids, evidence_items, unresolved_gaps, executed_actions, remaining_budget, tool_errors và stop_reason.

Các khoảng trống ban đầu:

- unresolved_drug_identity
- missing_relevant_source
- scope_mismatch
- apparent_disagreement
- unsupported_causal_claim
- missing_full_text

Agent chọn một hành động trong danh sách cho phép. Code kiểm soát giới hạn, loại bỏ truy vấn lặp và xác thực schema.

### 7.4. Điều kiện dừng

- Có đủ bằng chứng để viết bản tổng hợp trong phạm vi đã xác định.
- Không có thêm bằng chứng phù hợp sau hai lượt tìm không mang lại nguồn mới.
- Hết ngân sách lượt gọi/token/chi phí.
- Đầu vào cần làm rõ hoặc bằng chứng cần chuyên gia phân xử.
- Công cụ lỗi đến mức không thể hoàn tất.

Không gộp “không tìm thấy”, “API lỗi”, “hết ngân sách” và “không có nguy cơ” thành một trạng thái.

**Ngân sách ban đầu đề xuất:** tối đa 6 quyết định truy xuất, 12 lần gọi công cụ ngoài, 2 lần thử lại cho mỗi thao tác mạng; retry vẫn tính vào tổng giới hạn. Lượt LLM dành cho trích xuất/kiểm tra cũng phải được cộng vào chi phí. Điều chỉnh trên pilot rồi khóa trước test.

### 7.5. Stack đề xuất

- Python + FastAPI; schema typed bằng Pydantic.
- SQLite cho prototype hoặc PostgreSQL nếu tận dụng backend đang có.
- Tìm kiếm lexical/BM25 làm baseline; thử embedding y sinh nếu có cải thiện.
- LLM có structured output/tool calling; chọn sau pilot theo độ đúng, token và độ trễ.
- React cho giao diện; tái sử dụng thành phần hiện tại sau kiểm tra.
- Lưu file JSON/JSONL và hash snapshot; chưa cần hạ tầng phân tán.

Đây là lựa chọn thiết kế đề xuất, chưa là danh sách dependency đã cài.

### 7.6. Các phương pháp AI nên thử

| Phương pháp | Cách áp dụng | Điều kiện giữ lại |
|---|---|---|
| BM25 | Baseline tìm đoạn theo tên thuốc/biến cố | Luôn có để đo giá trị của phương pháp phức tạp hơn |
| MedCPT retriever/reranker | Thử truy xuất ngữ nghĩa y sinh trên tài liệu tiếng Anh; paper và code ở [R17, R18] | Recall bằng chứng trên dev tăng với chi phí chấp nhận được |
| Trích xuất có cấu trúc | LLM trả claim, phạm vi và evidence ID theo schema | Giảm lỗi gộp nguồn và dễ kiểm tra hơn văn bản tự do |
| Kiểm tra quan hệ nhận định–bằng chứng | So sánh từng phát biểu với đoạn nguồn và phạm vi | Đối chiếu được với nhãn chuyên gia, không chỉ tự chấm |
| Planner theo khoảng trống | Chọn công cụ/query từ trạng thái thiếu thông tin | Hơn B2 về chất lượng hoặc chi phí trong thực nghiệm |

MedCPT là phương án thử có sẵn, không yêu cầu nhóm huấn luyện từ đầu. Phải đo riêng hiệu quả trên nhãn thuốc vì kết quả truy xuất bài y sinh không đảm bảo chuyển nguyên sang loại văn bản này. Truy vấn tiếng Việt cần được ánh xạ sang thuật ngữ nguồn tiếng Anh có kiểm tra.

Không hiển thị điểm tự tin do LLM tự sinh như xác suất nguy cơ hay xác suất kết luận đúng. Nếu nghiên cứu calibration, phải có tập validation và định nghĩa sự kiện được dự đoán riêng.

## 8. Schema dữ liệu và sản phẩm bàn giao

### 8.1. Các bảng/đối tượng chính

| Đối tượng | Trường chính |
|---|---|
| verification_case | case_id, drug, event, population, route, as_of_date |
| source_document | source_id, source_type, external_id, URL, date, version, hash, license |
| evidence_item | source_id, section, offsets, quote, claim, relation, applicability |
| agent_run | run_id, case_id, model, prompt_hash, corpus_hash, config, status |
| action_log | action, inputs, returned_ids, elapsed_ms, tokens, cost, error |
| report | summary, evidence_ids, unresolved_gaps, stop_reason, reviewer_status |
| evaluation_label | expected_evidence, allowed_claims, forbidden_claims, annotator_status |

Văn bản gốc và văn bản đã chuẩn hóa phải có mapping vị trí để kiểm tra trích dẫn. Chỉ kiểm tra quote tồn tại chưa đủ chứng minh quote hỗ trợ kết luận; cần chấm quan hệ ngữ nghĩa riêng.

### 8.2. Cấu trúc thư mục dự kiến khi triển khai

~~~text
drug_safety_agent/
  adapters/
  retrieval/
  agent/
  schemas/
  reporting/
  evaluation/
data/
  manifests/
  raw/
  processed/
  annotations/
  splits/
experiments/
  configs/
  results/
docs/
  annotation_guide.md
  dataset_card.md
  evaluation_protocol.md
~~~

Đây là cấu trúc đề xuất; tài liệu này không tạo các module đó.

### 8.3. Đầu ra cuối kỳ

- Demo nhập câu hỏi và nhận bảng bằng chứng có thể mở nguồn.
- Agent trace giải thích hành động ngắn gọn: tra gì, tìm được gì, còn thiếu gì.
- Dataset card, annotation guide, danh sách ID nguồn và manifest.
- Benchmark runner cho các baseline và agent.
- Báo cáo kết quả, chi phí, lỗi và phạm vi áp dụng.
- Slide/pitch với một ca thành công và một ca agent phải dừng.

## 9. Thực nghiệm: chứng minh agent có ích

### 9.1. Baseline bắt buộc

| Mã | Phương pháp | Câu hỏi được kiểm tra |
|---|---|---|
| B0 | LLM trực tiếp, không truy xuất | Kiến thức sẵn có làm được tới đâu? |
| B1 | RAG: lấy top-k theo một truy vấn rồi trả lời | Tra cứu một lượt đã đủ chưa? |
| B2 | Workflow cố định: chuẩn hóa → nhãn → PubMed → tổng hợp → kiểm tra | Có cần agent chọn thứ tự/hướng tra không? |
| A | Agent chọn hành động theo khoảng trống bằng chứng | Có giảm lỗi hoặc chi phí so với B2 không? |

B0 chỉ là tham chiếu phụ. So sánh chính là A với B2 và B1, cùng model, snapshot, công cụ sẵn có và giới hạn tài nguyên. B2 nên dùng cùng bộ trích xuất/kiểm tra để tránh gán lợi ích của checker cho planner.

MALADE là baseline tham khảo thêm nếu chạy lại được. Ghi rõ thay đổi model, nguồn, schema và tập đánh giá; không gọi là tái lập nguyên bản nếu đã thay điều kiện.

### 9.2. Chỉ số chính

| Chỉ số | Cách đo |
|---|---|
| Tỷ lệ ca kết luận quá mức | Số ca có ít nhất một phát biểu mạnh hơn bằng chứng / tổng ca; báo thêm trên các ca đã trả lời |
| Citation validity | Tỷ lệ trích dẫn khớp đúng tài liệu và vị trí |
| Citation support | Tỷ lệ phát biểu thực sự được đoạn dẫn hỗ trợ, có xét phạm vi |
| Coverage | Tỷ lệ ca có câu trả lời nội dung thay vì chỉ từ chối/chưa hoàn tất |
| Chất lượng nhận diện thiếu/mismatch | Precision, recall, F1 trên ca đã có nhãn chuyên gia |
| Hiệu quả tài nguyên | Số request, token, chi phí USD và latency p50/p95 mỗi ca |

Đánh giá phụ: quan hệ thuốc–biến cố trên cặp OMOP được chọn. Không dùng độ đúng nhãn OMOP thay cho chất lượng trích dẫn hoặc kiểm chứng phạm vi.

Phải báo coverage cùng tỷ lệ lỗi để tránh hệ thống “ít sai” chỉ vì từ chối hầu hết câu hỏi.

### 9.3. Thí nghiệm loại bỏ thành phần

- A bỏ thông tin phạm vi quần thể/chế phẩm.
- A bỏ bước nhận diện khoảng trống, giữ nguyên công cụ.
- A dùng 2, 4 và 6 lượt quyết định.

Chỉ chạy đủ để trả lời câu hỏi nghiên cứu. Khóa lựa chọn trên validation; không sửa prompt theo lỗi test rồi báo lại cùng tập như kết quả độc lập.

### 9.4. Quy trình chấm và thống kê

- Trộn và ẩn tên phương pháp khi chuyên gia chấm.
- LLM judge có thể sàng lọc lỗi để giảm công, nhưng không là trọng tài duy nhất.
- Chấm các phương pháp trên cùng ca; báo số đếm, mẫu số và khoảng tin cậy.
- Bootstrap theo cụm hoạt chất/ca gốc khi có nhiều biến thể; không coi mọi biến thể là quan sát độc lập.
- Có thể dùng McNemar cho kết quả nhị phân ghép cặp nếu thiết kế mẫu phù hợp.
- Báo riêng lỗi mạng, parse, hết ngân sách và từ chối.
- Với tập test nhỏ, kết luận là thăm dò; không khẳng định ưu thế rộng chỉ từ vài ca.

### 9.5. Mục tiêu nghiệm thu đề xuất

Các mốc dưới đây là mục tiêu kỹ thuật, không phải chuẩn an toàn lâm sàng:

- 100% báo cáo có nguồn và lý do dừng; citation ID không tồn tại bị chặn.
- Không phát hành khuyến nghị tự đổi/ngừng thuốc.
- Citation validity mục tiêu ít nhất 95% trên tập chuyên gia chấm.
- Báo đủ coverage, citation support, lỗi kết luận quá mức và chi phí.
- Mục tiêu nghiên cứu: A giảm lỗi kết luận quá mức so với B2 ở coverage gần tương đương, hoặc đạt chất lượng tương đương với ít tài nguyên hơn.

Nếu A không hơn B2, báo trung thực rằng workflow cố định phù hợp hơn trong phạm vi thử nghiệm. Việc triển khai thành công một agent không tự chứng minh cần dùng agent.

## 10. An toàn và phạm vi chuyên môn

- Mọi phát biểu về thuốc phải gắn nguồn hoặc được đánh dấu chưa xác minh.
- Không để model tự tạo PMID, DOI, số báo cáo hay tỷ lệ.
- Kiểm tra số liệu bằng code từ dữ liệu nguồn; không để LLM tính nhẩm.
- Không dùng số báo cáo tự nguyện làm nguy cơ cá nhân hoặc bằng chứng nhân quả.
- Không diễn giải khác biệt do phạm vi như mâu thuẫn khoa học đã xác nhận.
- Lưu rõ tài liệu chỉ đọc abstract hay đã đọc toàn văn.
- Nội dung tài liệu là dữ liệu không đáng tin về mặt chỉ dẫn: không được phép thay system prompt, yêu cầu đọc secret hoặc gọi công cụ ngoài danh sách.
- Chỉ fetch miền/API cho phép; bảo vệ trước URL nội bộ và tài liệu chèn lệnh.
- API key nằm trong biến môi trường; không ghi vào URL/log công khai.

Nhóm vẫn cần học một số khái niệm: ADR/ADE, association/causation, nguồn báo cáo tự nguyện, loại nghiên cứu, khoảng tin cậy và phạm vi áp dụng. Dược sĩ giúp chốt quy tắc gán nhãn; nhóm IT chịu trách nhiệm truy xuất, kiểm chứng nguồn và đo lỗi.

## 11. Chi phí và tài nguyên

### 11.1. Cách kiểm soát

- Dùng API LLM ở MVP để tránh yêu cầu GPU huấn luyện.
- Chạy local cho giao diện, database và lexical retrieval nếu máy đáp ứng.
- Cache tài liệu và kết quả chuẩn hóa; chỉ gửi đoạn liên quan.
- Có trần token cho mỗi lượt và trần chi phí cho mỗi run.
- Đo toàn bộ lượt trích xuất, planner, checker, retry; không chỉ tính lượt trả lời cuối.
- Nếu dùng proxy chưa rõ đơn giá, ghi token và để USD là “chưa xác định”.

### 11.2. Công thức

~~~text
Chi phí LLM mỗi ca =
  (tổng input token / 1.000.000) × giá input
  + (tổng output token / 1.000.000) × giá output
  + phí công cụ/cache/embedding nếu nhà cung cấp tính riêng
~~~

**Ví dụ tính toán giả định, không phải báo giá của model cụ thể:**

Giả sử tổng mỗi ca dùng 25.000 input token và 4.000 output token:

| Kịch bản giả định | Giá input / 1M | Giá output / 1M | Chi phí/ca | 600 lượt ca |
|---|---:|---:|---:|---:|
| A | 0,50 USD | 2 USD | 0,0205 USD | 12,30 USD |
| B | 2 USD | 8 USD | 0,082 USD | 49,20 USD |

600 lượt ca có thể tương ứng 100 ca × 3 phương pháp × 2 lần chạy. Con số chưa gồm xây dữ liệu, tuning, lỗi, embedding, hosting và thời gian chuyên gia. Thay bằng token thực từ pilot và bảng giá được kiểm tra tại thời điểm chạy.

**Ngân sách đề xuất để nhóm cân nhắc:** dành trần 100–200 USD cho LLM/thử nghiệm trong 8 tuần, chia theo tuần; đây là ngân sách quản lý, không cam kết tổng chi phí sẽ nằm trong khoảng đó. Phần công chuyên gia lập riêng. Nếu pilot vượt khả năng chi trả, giảm model, số biến thể và số lượt trước khi mở rộng.



## 14. Rủi ro và phương án xử lý

| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Trùng nghiên cứu đã có | Cơ chế/bộ đánh giá tương tự paper gần nhất | Điều chỉnh câu hỏi, ghi rõ tái lập và phần mở rộng |
| Khó xác nhận mâu thuẫn | Người gán nhãn bất đồng nhiều | Ưu tiên thiếu dữ liệu/scope mismatch; giữ nhãn uncertain |
| Chỉ toàn ca dễ | RAG một lượt đã giải được hầu hết | Báo kết quả; bổ sung challenge có nguồn thật, không tạo lỗi y khoa giả |
| API trả thiếu/lỗi | Nguồn live không ổn định | Snapshot, cache, retry có giới hạn, trạng thái lỗi riêng |
| Sai hoạt chất | Tên gần giống hoặc chế phẩm phối hợp | Kiểm tra định danh; hỏi lại nếu chưa rõ |
| Nhãn và abstract không đủ | Kết luận phụ thuộc toàn văn không có | Chuyển chuyên gia/insufficient; không suy diễn phần không đọc |
| Agent tốn hơn workflow | Nhiều lượt lặp mà không thêm nguồn | Giới hạn lượt và chấm hiệu quả từng bước |
| Dữ liệu tham chiếu cũ | Nhãn OMOP khác bằng chứng mới | Ghi phiên bản, rà chuyên gia, tách phân tích bất đồng |
| Dịch tiếng Việt làm tăng mức chắc chắn | “associated” thành “gây ra” | Giữ thuật ngữ gốc và kiểm tra mức phát biểu |
| Không có chuyên gia | Không xác thực được nhãn y khoa | Chỉ tuyên bố kết quả kỹ thuật đã đo được |

## 16. Nguồn tham khảo và cách dùng

Các nguồn dưới đây đã được kiểm tra ở mức trang tài liệu/paper/repository khi lập kế hoạch. Việc kiểm tra này không đồng nghĩa đã tải bộ dữ liệu, chạy API có key hoặc tái lập paper. Khi triển khai cần ghi phiên bản/commit và ngày truy xuất thực tế.

| Mã | Nguồn | Vai trò trong đề tài |
|---|---|---|
| R1 | Choi và cộng sự, **MALADE**, MLHC/PMLR 2024 — [paper][R1] | Cơ sở nghiên cứu; đọc task, architecture, evaluation và limitations |
| R2 | Nhóm tác giả — [MALADE repository][R2] | Tham khảo tool/critic/schema; kiểm tra điều kiện tái sử dụng code trước khi tích hợp |
| R3 | FDA — [Drug Labeling Overview][R3] | Hiểu nguồn và giới hạn của dữ liệu nhãn |
| R4 | FDA — [Label searchable fields][R4] | Thiết kế adapter và schema |
| R5 | FDA — [Authentication and limits][R5] | Key, hạn mức, truy cập |
| R6 | NCBI — [PubMed Help: download data][R6] | Truy xuất PubMed và metadata |
| R7 | NCBI — [Usage policies][R7] | Scripting, bản quyền và sử dụng abstract |
| R8 | NCBI — [PMC Open Access Subset][R8] | Chọn toàn văn và cách tải được phép |
| R9 | NLM — [RxNorm API][R9] | Chuẩn hóa định danh thuốc |
| R10 | NLM — [DailyMed web services][R10] | Tìm/đối chiếu tài liệu SPL |
| R11 | FDA — [Drug Adverse Event Overview][R11] | Hiểu vì sao báo cáo không chứng minh nhân quả |
| R12 | FDA — [Event searchable fields][R12] | Thiết kế adapter báo cáo |
| R13 | OHDSI — [OMOP reference set documentation][R13] | Chọn cặp tham chiếu và đọc định nghĩa nhãn |
| R14 | OHDSI — [MethodEvaluation repository][R14] | Nguồn gói R/dữ liệu, kiểm tra phiên bản và license |
| R15 | Trung tâm DI & ADR Quốc gia — [Báo cáo ADR][R15] | Bối cảnh Việt Nam và biểu mẫu công khai |
| R16 | FDA — [Query parameters][R16] | Giới hạn phân trang và câu truy vấn |
| R17 | Jin và cộng sự, **MedCPT**, Bioinformatics 2023 — [paper/PMID][R17] | Phương pháp retrieval/reranking y sinh để so sánh |
| R18 | NCBI — [MedCPT repository][R18] | Code/model tham khảo cho phương án retrieval |

### Thứ tự đọc đề xuất

1. **Đọc R1 + R2:** xác định MALADE làm gì và nhóm sẽ khác ở đâu.
2. **Đọc R3 + R11:** thống nhất các giới hạn của nguồn.
3. **Đọc R13:** chốt bộ tham chiếu, không nhầm với nhãn challenge.
4. **Đọc R4–R10 + R12 + R16:** triển khai adapter.
5. **Rà soát bổ sung trong tuần 1:** tìm các cụm “pharmacovigilance evidence synthesis agents”, “drug safety conflicting evidence LLM”, “uncertainty-aware retrieval pharmacovigilance”, “scope-aware medical claim verification”.

Lập related_work.csv với các cột: paper, năm, task, dữ liệu, công cụ, cơ chế agent, xử lý bất định/mâu thuẫn, metric, code, khác biệt dự kiến. Chỉ giữ tuyên bố mới sau khi đối chiếu các công trình gần nhất.

## 17. Bản mô tả ngắn để trình mentor

Nhóm đề xuất xây dựng AI agent hỗ trợ dược sĩ kiểm chứng nhận định về tác dụng bất lợi của thuốc. Đầu vào là cặp thuốc–biến cố và phạm vi cần kiểm tra; đầu ra là hồ sơ bằng chứng có nguồn, phạm vi áp dụng và những điều chưa thể kết luận. Agent chủ động lựa chọn bước tra cứu tiếp theo khi gặp bằng chứng thiếu, khác phạm vi hoặc chưa thống nhất. Nhóm sử dụng nhãn thuốc FDA, PubMed và tập tham chiếu OMOP; xây thêm một tập đánh giá nhỏ được dược sĩ rà soát. Phần nghiên cứu so sánh agent với RAG và workflow cố định, đo lỗi kết luận quá mức, độ đúng trích dẫn, coverage và chi phí. MVP tập trung vào dữ liệu văn bản, không dùng CV/VLM và không quyết định điều trị. Đóng góp mới dự kiến nằm ở cơ chế chọn hành động theo khoảng trống bằng chứng và cách đánh giá nó, cần được xác nhận qua rà soát tài liệu và thực nghiệm.

[R1]: https://proceedings.mlr.press/v252/choi24a.html
[R2]: https://github.com/jihyechoi77/malade
[R3]: https://open.fda.gov/apis/drug/label/
[R4]: https://open.fda.gov/apis/drug/label/searchable-fields/
[R5]: https://open.fda.gov/apis/authentication/
[R6]: https://pubmed.ncbi.nlm.nih.gov/help/#download-pubmed-data
[R7]: https://www.ncbi.nlm.nih.gov/home/about/policies/
[R8]: https://pmc.ncbi.nlm.nih.gov/tools/openftlist/
[R9]: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
[R10]: https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
[R11]: https://open.fda.gov/apis/drug/event/
[R12]: https://open.fda.gov/apis/drug/event/searchable-fields/
[R13]: https://ohdsi.github.io/MethodEvaluation/reference/omopReferenceSet.html
[R14]: https://github.com/OHDSI/MethodEvaluation
[R15]: https://www.canhgiacduoc.org.vn/CanhGiacDuoc/ADROnline.aspx
[R16]: https://open.fda.gov/apis/query-parameters/
[R17]: https://pubmed.ncbi.nlm.nih.gov/37930897/
[R18]: https://github.com/ncbi/MedCPT
