# VigiLens sau MVP: bàn làm việc thông tin thuốc và an toàn thuốc bệnh viện

Ngày nghiên cứu: 05/10/2026. Người dùng chính theo lựa chọn của nhóm: dược sĩ bệnh viện / thông tin thuốc / cảnh giác dược. Phạm vi: toàn sản phẩm và toàn nhóm.

## 1. Kết luận sản phẩm

Đề xuất định vị: **giúp dược sĩ chuyển một vấn đề an toàn thuốc thành câu trả lời được thẩm định, hồ sơ có căn cứ và công việc theo dõi được khép lại**.

Đối tượng làm việc chính nên là **yêu cầu chuyên môn hoặc ca nghi ngờ ADR**. Một nhận định “thuốc X liên quan biến cố Y” là phần phục vụ thẩm định bên trong hồ sơ. Một hồ sơ có thể chứa nhiều câu hỏi, nhiều thuốc và nhiều lần cập nhật.

Chọn ba luồng liên kết:

1. Trả lời câu hỏi thông tin thuốc/an toàn thuốc từ khoa lâm sàng.
2. Tiếp nhận, bổ sung và thẩm định ca nghi ngờ ADR; chuẩn bị báo cáo và lưu phản hồi.
3. Đánh giá thông tin an toàn mới đối với danh mục thuốc bệnh viện; soạn bản tin hoặc tài liệu cho Hội đồng Thuốc và Điều trị.

Lát cắt triển khai đầu tiên: **yêu cầu thông tin thuốc về an toàn + hồ sơ bằng chứng + phiếu phản hồi + theo dõi**, đồng thời có cửa tiếp nhận nghi ngờ ADR ngắn để không buộc điều dưỡng làm toàn bộ công việc thẩm định. Sau đó mở rộng hồ sơ ca khi có dữ liệu bệnh viện được phép sử dụng.

Đây là nghiên cứu tài liệu và đề xuất thiết kế từ góc nhìn mô phỏng dược sĩ; chưa phải phỏng vấn người dùng, xác nhận của dược sĩ hành nghề hay nghiệm thu lâm sàng. Các feature, mức ưu tiên và tiêu chí pilot bên dưới là đề xuất của nghiên cứu này.

## 2. Căn cứ thực tế và giới hạn diễn giải

| Căn cứ đã kiểm tra | Điều có thể rút ra | Điều chưa được chứng minh |
|---|---|---|
| Khảo sát Việt Nam 2026, 372 nhân viên y tế tại 3 bệnh viện công: khó nhận diện thuốc nghi ngờ 80,1%; khó phân độ mức độ 54,3%; biểu mẫu phức tạp 30,1%; mong có hỗ trợ đồng nghiệp và phản hồi sau gửi | Việc nhận diện, hỗ trợ phối hợp và phản hồi cần được đặt trong luồng ADR | Không đại diện mọi bệnh viện; chỉ 9,6% mẫu là dược sĩ; mới đọc abstract |
| Khảo sát Việt Nam 2015 tại 10 bệnh viện, công bố 2019/2020 | Thiếu thời gian, biểu mẫu và hiểu quy trình là những trở ngại đã được ghi nhận | Không dùng số liệu cũ để ước tính nhu cầu hay hiệu quả sản phẩm năm 2026 |
| Khảo sát hoạt động dược lâm sàng Việt Nam, công bố 2022; dữ liệu 2017–2018 | Thông tin thuốc, cảnh giác dược và xây dựng quy trình là các hoạt động được khảo sát; thực hành theo từng bệnh nhân khác nhau giữa bệnh viện | Không suy ra bệnh viện mục tiêu có HIS tích hợp hoặc dược sĩ theo dõi đầy đủ mọi ca |
| Nghiên cứu nhận thức tại một trung tâm VA Hoa Kỳ, phỏng vấn 10 bác sĩ và 10 dược sĩ | Quyết định ADR gồm phát hiện, tìm nguyên nhân, cân nhắc lợi ích/nguy cơ, lập kế hoạch và theo dõi | Không chuyển nguyên trạng quy trình Mỹ sang Việt Nam; phần lớn tình huống nghiên cứu ở ngoại trú |
| Tổng kết ADR Việt Nam 2025, bản tin 2/2026 | Có hoạt động báo cáo, phản hồi khẩn và cập nhật an toàn; ghi nhận thất lạc một số báo cáo qua bưu điện | Số báo cáo không phải số bệnh nhân mắc ADR và không cho tỷ lệ mắc |

Nguồn tương ứng: [khảo sát 2026](https://pubmed.ncbi.nlm.nih.gov/41943791/), [khảo sát 10 bệnh viện](https://pubmed.ncbi.nlm.nih.gov/31486525/), [khảo sát hoạt động dược lâm sàng](https://pubmed.ncbi.nlm.nih.gov/35799184/), [nghiên cứu nhận thức, bản tác giả lưu tại đại học](https://scholarworks.indianapolis.iu.edu/server/api/core/bitstreams/3b49a2aa-2432-4b51-8bee-2b4a1268e778/content), [tổng kết Việt Nam 2025](https://magazine.canhgiacduoc.org.vn/Magazine/Details/335).

ASHP mô tả việc làm rõ câu hỏi, lấy bối cảnh, tra cứu, đánh giá, trả lời, ghi nhận và theo dõi. Với yêu cầu khẩn, cách làm đầy đủ có thể cần rút gọn. Hướng dẫn ADR nhấn mạnh giám sát, tài liệu hóa, báo cáo và cải tiến thực hành. Dùng hai hướng dẫn này làm tài liệu tham khảo nghề nghiệp, không coi là quy định áp dụng bắt buộc tại Việt Nam. [Thông tin thuốc](https://academic.oup.com/ajhp/article/72/7/573/5111728), [giám sát ADR](https://academic.oup.com/ajhp/article/79/1/e83/6363907).

Trung tâm DI & ADR Quốc gia liệt kê Quyết định 29/QĐ-BYT ngày 05/01/2022 về giám sát ADR tại cơ sở khám chữa bệnh. Chưa lấy được toàn văn từ liên kết của Trung tâm do vấn đề truy cập/chứng chỉ; vì vậy chưa xác nhận chi tiết mẫu biểu, thời hạn hay tình trạng pháp lý để mã hóa vào sản phẩm. Nhóm cần lấy bản hiện hành từ đầu mối bệnh viện trước khi xuất biểu mẫu chính thức. [Danh mục văn bản của Trung tâm](https://enquiry.canhgiacduoc.org.vn/GioiThieuChung/Vanbanphapquy.aspx).

## 3. Chuyên viên thực sự đang cố hoàn thành việc gì?

Mô phỏng cách nghĩ của dược sĩ: “Tôi cần biết khoa đang cần quyết định gì, cần trả lời lúc nào, thông tin nào còn thiếu và nguồn nào áp dụng được. Tôi muốn kiểm tra lập luận trước khi ký câu trả lời. Sau đó tôi cần biết người nhận đã làm gì và hồ sơ có cần cập nhật không.”

| Công việc | Người khởi tạo / người nhận | Quyết định cần hỗ trợ | Sản phẩm công việc cần lưu |
|---|---|---|---|
| Trả lời câu hỏi an toàn thuốc | Bác sĩ, điều dưỡng, dược sĩ khoa → đơn vị thông tin thuốc | Thông tin có liên quan bối cảnh hiện tại không? Cần kiểm tra thêm gì? | Phiếu trả lời ngắn có căn cứ, giới hạn áp dụng, người duyệt, ngày trả lời |
| Tiếp nhận nghi ngờ ADR | Người phát hiện → đầu mối dược/PV | Ca cần bổ sung gì; cần chuyển xử lý khẩn theo quy trình nào? | Phiếu tiếp nhận, lịch sử liên hệ, dữ liệu ca được bổ sung |
| Thẩm định ca ADR | Dược sĩ cùng bác sĩ điều trị | Thuốc, bệnh nền hoặc nguyên nhân khác giải thích ra sao? | Dòng thời gian, đánh giá có lý do, dữ kiện ủng hộ/chống lại, phần chưa xác định |
| Chuẩn bị báo cáo | Đầu mối PV → đơn vị nhận báo cáo | Bản nào được duyệt, đã gửi/nhận chưa? | Báo cáo đã kiểm tra, bản gửi, mã/biên nhận và phản hồi khi thực sự có |
| Xem cảnh báo mới | Dược sĩ DI/PV → khoa / Hội đồng Thuốc và Điều trị | Có thuốc trong danh mục bị ảnh hưởng? Cần sửa quy trình hay truyền thông? | Bản đánh giá tác động, dự thảo bản tin, quyết định và người phụ trách |
| Học từ hồ sơ đã xử lý | Đầu mối dược → đội chất lượng / đào tạo | Có vấn đề lặp lại hoặc phần quy trình cần cải tiến? | Bộ hồ sơ tái sử dụng có ngày rà soát, báo cáo chất lượng với mẫu số rõ |

Đầu mối chuyên môn thường là dược sĩ, nhưng sản phẩm phải phục vụ cộng tác. Điều dưỡng cần nhập phát hiện nhanh; bác sĩ cung cấp bối cảnh điều trị; dược sĩ thẩm định; người phụ trách phê duyệt; người quản lý theo dõi quá trình. Không mặc định cùng một người làm tất cả.

## 4. Pain → feature → dữ liệu → đầu ra

Các pain có căn cứ khảo sát được đánh dấu **tài liệu**; các pain cụ thể về màn hình, hệ thống hoặc luồng là **giả thuyết cần pilot**.

| Pain | Feature đề xuất | Dữ liệu cần | Đầu ra người dùng nhìn thấy | Ưu tiên |
|---|---|---|---|---|
| Khó xác định thuốc nghi ngờ (**tài liệu**) | Hồ sơ nhiều thuốc, dòng thời gian và bảng nguyên nhân thay thế | Thuốc đã dùng thực tế, ngày/giờ dùng và khởi phát, bệnh/lab liên quan | Dữ kiện theo từng thuốc; phần còn thiếu; đánh giá do chuyên viên chọn và giải thích | P0 phần tiếp nhận, P1 thẩm định ca |
| Biểu mẫu và thiếu thời gian (**tài liệu**) | Phiếu phát hiện ngắn, lưu nháp, bổ sung sau, tái sử dụng dữ liệu | Đơn vị/người liên hệ, mô tả biến cố, thuốc biết được, thời điểm nếu có | Hồ sơ được tiếp nhận với danh sách cần bổ sung; không giả định các ô trống | P0 |
| Cần hỗ trợ/feedback (**tài liệu**) | Giao việc bổ sung, phản hồi cho người báo, lưu biên nhận | Đầu mối, nội dung yêu cầu, hạn nội bộ, phản hồi thật | Ai đang xử lý gì; phản hồi đã nhận; trạng thái khép hồ sơ | P0/P1 |
| Câu hỏi ban đầu thiếu mục đích (**tham khảo nghề nghiệp**) | Làm rõ nhu cầu trước tra cứu; mẫu theo loại câu hỏi | Người hỏi, quyết định cần hỗ trợ, hạn trả lời, bối cảnh chung/cá thể | Câu hỏi đã thống nhất; thông tin còn thiếu có lý do | P0 |
| Khó chọn bằng chứng phù hợp (**giả thuyết UI**) | Bảng so sánh phạm vi gồm chỉ định và đối chứng | Quần thể, setting, thuốc/đường dùng, comparator, outcome, thời gian | Khớp/khác/chưa rõ theo từng chiều; người đọc thấy lý do | P0 |
| Nguồn thật cho kết quả khác nhau (**ca nghiên cứu thật**) | Thẩm định khác biệt phương pháp thay vì đếm bài ủng hộ | Thiết kế, ước lượng, CI, giới hạn, khả năng trùng quần thể dữ liệu | Nhận định có điều kiện; khác biệt được giải thích; gap chưa giải quyết | P0 |
| Câu trả lời dài khó dùng (**giả thuyết cần pilot**) | Phiếu phản hồi ngắn, mở rộng được sang hồ sơ bằng chứng | Câu hỏi chốt, kết luận chuyên viên, nguồn và dữ kiện còn thiếu | Trang đầu có câu trả lời; phần sau là lập luận/nguồn; đọc được trên điện thoại | P0 |
| “Đã xuất” chưa có nghĩa “đã xử lý” (**giả thuyết luồng**) | Phân biệt duyệt, chuyển giao, nhận phản hồi, theo dõi và đóng | Người nhận, quyết định chuyên môn, lịch theo dõi, lý do đóng | Bằng chứng kết thúc công việc; hồ sơ có thể mở lại | P0 |
| Biệt dược/nhãn nước ngoài không khớp thuốc bệnh viện (**giả thuyết dữ liệu**) | Danh mục nội bộ và xác nhận tên thuốc | Mã thuốc BV, hoạt chất, dạng/hàm lượng, đường, hãng, nhãn địa phương | Ánh xạ được xác nhận; lựa chọn nhãn phù hợp; giữ tên gốc | P0 nền dữ liệu |
| Cảnh báo khó chuyển thành hành động địa phương (**giả thuyết**) | Hàng chờ cảnh báo theo danh mục và phiếu tác động | Nguồn/version/ngày cảnh báo, danh mục, SOP nội bộ | Thuốc bị ảnh hưởng; khác biệt cần xem; dự thảo bản tin; quyết định lưu | P1 |
| Các ca cùng lô hoặc vấn đề chất lượng (**hoạt động được ghi nhận**) | Lọc cụm cùng thuốc/lô và khoảng thời gian, chuyển kiểm tra | Lô, hãng, thời gian, đơn vị, báo cáo trùng | Danh sách ca cần xem chung; không tự tuyên bố tín hiệu nhân quả | P1 khi có dữ liệu |
| Trả lời cũ cần cập nhật (**giả thuyết**) | Kho câu trả lời có phạm vi, lịch rà soát, nguồn thay đổi | Phiên bản hồ sơ và nguồn, nhãn hiệu lực, người chịu trách nhiệm | Câu trả lời còn phù hợp/chờ rà soát; không tái dùng âm thầm | P1 |
| Câu hỏi liều/pha truyền/TDM có ích thực tế (**mở rộng nghiệp vụ**) | Mô-đun theo câu hỏi và dữ liệu chuyên ngành đã thẩm định | Nhãn đúng sản phẩm, tài liệu tương hợp có quyền, thời điểm lấy mẫu/nồng độ, SOP | Câu trả lời hoặc tính toán chuyên biệt đã kiểm chứng; chặn khi thiếu dữ kiện | P2 sau pilot |

P0 = lát cắt đầu tiên để làm được một hồ sơ thật trọn vẹn; P1 = tiếp theo khi dữ liệu/luồng đã xác nhận; P2 = mở rộng sau. P0 không đồng nghĩa mọi mục phải xây đủ trong một sprint.

## 5. Dữ liệu vào: có gì mới trả lời được việc gì?

### 5.1 Yêu cầu thông tin thuốc

Tối thiểu để tiếp nhận: câu hỏi bằng ngôn ngữ người hỏi; khoa/đầu mối; mục đích; cần trước thời điểm nào; câu hỏi chung hay liên quan một ca. Cho phép lưu khi chưa đủ; làm rõ trước khi đưa ra câu trả lời cá thể.

Thêm theo câu hỏi: tên thuốc gốc và hoạt chất đã xác nhận; chỉ định; dạng/đường dùng; nhóm bệnh nhân; biến cố/kết quả cần xem; thuốc/phương án đối chứng; thời gian phơi nhiễm và theo dõi. Với một bệnh nhân cụ thể, chỉ lấy dữ liệu liên quan như nhóm tuổi, chức năng thận/gan, bệnh nền, thuốc cùng dùng, diễn biến và lab có ngày/đơn vị/khoảng tham chiếu.

Đầu ra: câu hỏi đã làm rõ; tóm tắt nguồn; câu trả lời theo bối cảnh; điều không thể suy ra; câu hỏi bổ sung; lựa chọn cần bác sĩ/dược sĩ quyết định; người chịu trách nhiệm và thời điểm cập nhật.

### 5.2 Hồ sơ nghi ngờ ADR

Phiếu tiếp nhận ngắn: mã ca nội bộ hoặc thông tin nhận dạng theo quy trình được duyệt; mô tả điều quan sát được; thuốc nghi ngờ nếu biết; thời điểm; người liên hệ; có tình huống khẩn theo đánh giá người báo hay không. Không chặn tiếp nhận vì chưa xác định nhân quả hay chưa có toàn bộ xét nghiệm.

Phiếu bổ sung cho dược sĩ: thuốc nghi ngờ và thuốc cùng dùng; chỉ định; liều/đường; **thực tế đã dùng** phân biệt y lệnh; bắt đầu/dừng/thay đổi; giờ khởi phát; diễn biến; xử trí đã xảy ra; kết quả; lab có dấu thời gian; bệnh/thuốc/nguyên nhân thay thế; thông tin lô/nhà sản xuất khi liên quan.

**Tách bốn trục:** mức độ biểu hiện (severity), tiêu chí nghiêm trọng (seriousness), liên quan thuốc (causality), đã được mô tả trong nhãn tham chiếu hay chưa (expectedness, nếu nghiệp vụ có dùng). Lưu tiêu chí và nguồn theo từng trục; không dùng một điểm AI thay tất cả.

WHO-UMC xem xét quan hệ thời gian, nguyên nhân khác và diễn biến sau ngừng thuốc trong đánh giá ca; phương pháp này không cho xác suất nhân quả chính xác và không biến bất định thành chắc chắn. Vì vậy đề xuất checklist có tài liệu chứng minh và lựa chọn “chưa đánh giá/thiếu dữ liệu”, với chuyên viên kết luận. Không thiết kế yêu cầu dùng lại thuốc để chứng minh ADR. [WHO-UMC](https://www.who.int/publications/m/item/WHO-causality-assessment).

Đầu ra: dòng thời gian có dữ liệu nguồn; thông tin cần bổ sung; đánh giá từng thuốc; bản báo cáo nháp đúng mẫu đã được bệnh viện chốt; lịch sử duyệt; tệp đã gửi và biên nhận nếu có; phản hồi cho người phát hiện. Trạng thái “đã gửi” chỉ khi có ghi nhận hành động gửi, không tự đổi sau xuất tệp.

### 5.3 Thông tin an toàn mới

Đầu vào: cơ quan/đơn vị phát hành; quốc gia; loại văn bản; ngày ban hành/hiệu lực/ngày lấy; nội dung và bản gốc; thuốc/đường/quần thể liên quan; danh mục bệnh viện; nhãn và SOP nội bộ được đối chiếu.

Đầu ra: nội dung thay đổi; thuốc trong danh mục có thể liên quan; chỗ cần xác minh; ảnh hưởng dự kiến do dược sĩ thẩm định; dự thảo thông báo có người nhận/mục đích; việc cần cập nhật; quyết định và lý do.

Thông báo của FDA, bản tin chuyên môn Việt Nam và SOP của bệnh viện phải có loại nguồn khác nhau. Nhãn Hoa Kỳ không mặc nhiên thay nhãn sản phẩm lưu hành tại Việt Nam. Nếu không có danh mục bệnh viện thì hiển thị “chưa đối chiếu được tác động nội bộ”, không tạo danh sách thuốc bị ảnh hưởng.

## 6. Ba hành trình E2E

### A. Yêu cầu thông tin thuốc về an toàn

1. Khoa nhập câu hỏi → lưu yêu cầu, thời hạn và người chịu trách nhiệm.
2. Dược sĩ làm rõ mục đích → chốt câu hỏi/phạm vi; tạo yêu cầu bổ sung nếu cần.
3. Hệ thống tìm nguồn hoặc nhận tài liệu do người dùng cung cấp → lưu tìm kiếm, nguồn, phiên bản, thời điểm và coverage.
4. Dược sĩ đọc bảng bằng chứng → kiểm tra trích đoạn, thiết kế, đối chứng, applicability và phần chưa đọc.
5. Hệ thống hỗ trợ soạn phiếu trả lời → mỗi nhận định liên kết nguồn hoặc đánh dấu là suy luận/đề xuất chuyên môn.
6. Dược sĩ sửa/duyệt → lưu phiên bản và lý do; sửa nội dung trọng yếu khiến bản duyệt cũ cần xem lại.
7. Xuất/chuyển theo kênh bệnh viện → ghi nhận người nhận và phương thức; không đồng nhất xuất tệp với gửi.
8. Nhận phản hồi và ghi hành động/thông tin mới → đóng hoặc mở lại hồ sơ; lưu trong kho câu trả lời với ngày rà soát.

Điểm dừng hợp lệ: câu hỏi ngoài phạm vi; nguồn không lấy được; dữ liệu không đủ; câu trả lời tạm thời chờ bổ sung. Có lý do và việc tiếp theo, không chỉ badge “insufficient”.

### B. Nghi ngờ ADR ở một bệnh nhân

1. Người phát hiện nhập phiếu ngắn. Tình huống khẩn đi theo quy trình lâm sàng bệnh viện; việc nhập hồ sơ không thay xử trí.
2. Đầu mối tiếp nhận → kiểm tra trùng và gán người phụ trách, giữ báo cáo gốc.
3. Dược sĩ lấy dữ kiện liên quan → tạo timeline; lưu thiếu thông tin và đầu mối cần hỏi.
4. Xem xét từng thuốc và nguyên nhân khác → tham khảo hồ sơ bằng chứng chung nhưng đánh giá ca riêng.
5. Hoàn thiện biểu mẫu/đánh giá → người có trách nhiệm kiểm tra; có thể báo cáo nghi ngờ dù chưa xác định chắc nhân quả theo quy trình áp dụng.
6. Người phụ trách gửi qua kênh đã được đơn vị cho phép → lưu bản gửi và bằng chứng nhận thật.
7. Ghi nhận thông tin bổ sung/phản hồi → nối với cùng ca; cập nhật bản báo cáo theo quy trình, không đếm thành ca độc lập.
8. Hoàn tất theo dõi; liên kết các việc như cập nhật hồ sơ dị ứng, truyền thông khoa hoặc xem xét quy trình khi chuyên viên quyết định.

Đây là luồng đề xuất. Chi tiết biểu mẫu, quyền gửi và thời hạn phải được đầu mối PV bệnh viện xác nhận trước pilot.

### C. Cảnh báo mới cần đánh giá tại bệnh viện

1. Nhận nguồn mới → phân loại loại nguồn và đối chiếu nội dung với bản đã lưu.
2. Kiểm tra thuốc/dạng/đường trong danh mục nội bộ; không có mapping thì tạo việc xác nhận.
3. Xác định câu hỏi chuyên môn → liên kết hồ sơ bằng chứng và SOP/nhãn hiện hành.
4. Soạn phiếu tác động: điều thay đổi, ai cần biết, phương án cần xem xét, giới hạn.
5. Chuyên viên/Hội đồng chốt quyết định → lưu lý do và bản tin/SOP được duyệt.
6. Giao việc, ghi nhận hoàn tất và đặt thời điểm rà soát.

Đích đến là quyết định và việc theo dõi có người phụ trách. Số lượng tin mới chỉ là thông tin phụ.

## 7. Tình huống thật để thiết kế và nghiệm thu

### 7.1 Fluoroquinolone và phình/tách động mạch chủ: bằng chứng khác nhau theo bối cảnh

Đây là chủ đề công khai thật. Câu hỏi dùng để thử giao diện do nghiên cứu đề xuất: “Dược sĩ cần giải thích các kết quả khác nhau và khả năng áp dụng khi cập nhật tài liệu an toàn fluoroquinolone như thế nào?” Không phải yêu cầu thật từ một bệnh viện.

| Nguồn thật | Dữ kiện đã kiểm tra | Điều giao diện cần giữ |
|---|---|---|
| Janetzki và cộng sự 2025, PMID 39975698 | UTI ngoại trú, ≥35 tuổi; 60 ngày; FQ vs TMP: calibrated HR 0,91 (CI 0,73–1,10); vs cephalosporin: 1,01 (0,82–1,25) | Chỉ định/setting và comparator; “không thấy tăng” trong bối cảnh này không tương đương không có nguy cơ ở mọi nhóm |
| Wicherski và cộng sự 2025, PMID 40285433 | Dữ liệu Đức; FQ vs macrolide: aHR 1,52 (1,33–1,74); vs cephalosporin: 1,23 (1,10–1,37); cửa sổ 60 ngày | Khác biệt đối chứng và population; không lấy trung bình các HR để làm điểm AI |
| Rosenbusch và cộng sự 2025, PMID 40988034 | Một nghiên cứu Đức khác ghi nhận liên quan tăng nguy cơ | Cần xem quần thể, dữ liệu nền và khả năng trùng dữ liệu; không coi mỗi bài là nguồn hoàn toàn độc lập |
| Nhãn ciprofloxacin uống, SETID c47250c2-bece-46b5-8b3b-b7c97d9005d8, v3 | Có mục 5.9 về nguy cơ động mạch chủ; published 28/09/2026; SPL effectiveTime 25/09/2026 | Loại nguồn/đường dùng/phiên bản; đây là nhãn Mỹ của một sản phẩm, không phải toàn bộ nhãn thuốc BV |

Nguồn: [PMID 39975698](https://pubmed.ncbi.nlm.nih.gov/39975698/), [PMID 40285433](https://pubmed.ncbi.nlm.nih.gov/40285433/), [PMID 40988034](https://pubmed.ncbi.nlm.nih.gov/40988034/), [nhãn DailyMed được lấy](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c47250c2-bece-46b5-8b3b-b7c97d9005d8).

Mẫu đầu ra mong muốn: giải thích khác biệt; ghi rõ phạm vi được hỗ trợ; trình bày cảnh báo nhãn riêng với kết quả nghiên cứu; yêu cầu nhãn/danh mục/SOP của bệnh viện để đánh giá tác động nội bộ. Chưa có hồ sơ bệnh nhân nên không tạo khuyến nghị điều trị cá thể.

**Phát hiện chất lượng nguồn:** nhãn ciprofloxacin đã lấy có lỗi chữ ngay trong mục 5.9 (ví dụ từ “reverse”). Giữ nguyên bản gốc và đánh dấu cần đối chiếu phiên bản/nhãn chuẩn; không sửa âm thầm rồi gọi bản sửa là trích dẫn nguyên văn. Một nguồn chính thức vẫn cần kiểm tra chất lượng văn bản.

### 7.2 PPI và hạ magnesi: nhãn thuốc chưa đủ để kết luận một ca

Lấy được nhãn pantoprazole dạng tiêm và dạng viên. Bản viên SETID 6faf465b-c3a3-4ae7-9e16-1ba758f6962a v22 có published_date 29/09/2026 nhưng SPL effectiveTime 19/09/2024; mục về hạ magnesi nằm trong cảnh báo. Vì vậy “vừa lấy” hoặc “vừa đăng” không có nghĩa nội dung cảnh báo vừa đổi. [Nhãn viên đã lấy](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=6faf465b-c3a3-4ae7-9e16-1ba758f6962a).

Thiết kế thử: mở phiếu nghi ngờ ADR trống gắn với chủ đề PPI/hạ magnesi. Chưa có bệnh nhân, lab hay thuốc cùng dùng nên chưa được gán ca là possible/probable, chưa có timeline lâm sàng. Hệ thống chỉ gợi ý dữ liệu cần thu thập: thời gian dùng PPI, dạng/đường thực tế, xét nghiệm có đơn vị và ngày, thuốc khác và nguyên nhân thay thế. Giá trị là giúp dược sĩ hỏi đủ thông tin, rồi đánh giá; không suy một ca từ việc nhãn đã mô tả biến cố.

Không lấy nhãn dạng tiêm mới nhất trong kết quả tìm kiếm làm nguồn mặc định cho câu hỏi về dùng viên dài ngày. Đây là tình huống nghiệm thu mapping sản phẩm và đường dùng.

### 7.3 Một báo cáo quốc gia thật để thiết kế follow-up

Tổng kết ADR năm 2025 có các phản hồi khẩn và các chuỗi báo cáo cùng lô trong thời gian ngắn; đồng thời nêu vấn đề thất lạc báo cáo qua bưu điện. [Nguồn Trung tâm](https://magazine.canhgiacduoc.org.vn/Magazine/Details/335).

Thiết kế thử: hồ sơ báo cáo cần lưu bản xuất, hành động gửi do người dùng ghi nhận, biên nhận và phản hồi. Dữ liệu tổng kết công khai chỉ minh họa nhu cầu hệ thống; không tạo hồ sơ bệnh nhân, số lô hay cụm ca giả dưới nhãn “data thật”.

## 8. Nguồn dữ liệu và kế hoạch có data thật

Đã lưu **17 snapshot nguồn công khai kiểm tra payload và SHA-256**, cùng một lần lấy nguồn thất bại trong manifest. Sáu snapshot PubMed là metadata/abstract thật (3 nghiên cứu thuốc và 3 khảo sát workflow); ba SPL là văn bản nhãn thật; hai index nhãn; tổng kết Việt Nam 2024/2025; index bản tin mới; WHO-UMC; tài liệu openFDA; nghiên cứu workflow bản PDF tác giả. Index/tài liệu kỹ thuật không được tính như nghiên cứu lâm sàng độc lập.

| Lớp dữ liệu | Dùng vào việc gì | Hiện có | Nhóm cần bổ sung |
|---|---|---|---|
| Văn bản chuyên môn công khai | Bằng chứng, nhãn, bối cảnh nghiệp vụ | Snapshot có provenance; nguồn trong manifest | Full text được phép dùng; thêm ca trái chiều; mapping chuẩn hóa do chuyên viên xem |
| Danh mục thuốc BV và nhãn đúng sản phẩm | Cảnh báo nào liên quan BV, loại bỏ nhãn sai dạng/đường | Chưa có | File xuất chính thức, mã thuốc, hãng, dạng/hàm lượng/đường, nhãn và người xác nhận |
| SOP/mẫu phiếu của đơn vị | Mẫu trả lời, đánh giá, báo cáo và phân quyền nghiệp vụ | Chưa có | Bản hiện hành, người phụ trách, phiên bản và quy trình gửi/nhận |
| Yêu cầu DI lịch sử | Nhu cầu thật và kết quả trước đây | Chưa có | Đề xuất xin 10–20 yêu cầu đã khử định danh, câu trả lời và phản hồi |
| Hồ sơ nghi ngờ ADR nội bộ | Timeline và dữ kiện ca | Chưa có | Đề xuất 10 ca được phép dùng, giữ dữ liệu thiếu và lần bổ sung, không biến thành gold tự động |
| Sử dụng thuốc/đợt điều trị | Mẫu số cho chỉ số theo dõi | Chưa có | Chỉ thu khi cần đo; xác định đơn vị phân tích, kỳ thời gian và chất lượng dữ liệu |
| Nhãn chuyên gia | Đánh giá applicability, entailment và câu trả lời | Chưa có trong packet này | Hai người xem độc lập, giải quyết bất đồng, ghi người/ngày/phiên bản |

openFDA/FAERS là dữ liệu báo cáo nghi ngờ; có thể nhiều thuốc và nhiều biến cố trong một báo cáo, không ánh xạ chắc cặp thuốc–biến cố. Không dùng số báo cáo để suy nhân quả hay tỷ lệ mắc. Chỉ dùng làm bối cảnh phát hiện vấn đề; chưa lấy dữ liệu bệnh nhân FAERS trong packet này. [Tài liệu openFDA](https://open.fda.gov/apis/drug/event/).

DailyMed cung cấp API và phiên bản SPL; phải lưu SETID/version và chọn đúng sản phẩm. PubMed metadata/abstract không chứng minh đã đọc full text. Nguồn trả HTML thay JSON hoặc lỗi truy cập phải ghi lỗi, không coi là “không có bằng chứng”. [Tài liệu DailyMed](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm).

URL FDA cho thông báo fluoroquinolone 2018 được công cụ tìm kiếm lập chỉ mục, nhưng lượt HTTP trực tiếp trả 404. Manifest ghi thất bại và không có snapshot PDF. Không dùng liên kết hỏng để chứng minh đã nạp nguồn, hay coi nhãn lấy được là thông báo 2018. Bộ nguồn này chưa phải rà soát hệ thống đầy đủ của chủ đề.

### Gói pilot nội bộ đề xuất

- Chọn một bệnh viện/đơn vị DI-PV và một nhóm câu hỏi; xác nhận người duyệt và kênh làm việc đang dùng.
- Xin yêu cầu DI, hồ sơ ADR, SOP và danh mục thuốc theo quyền của đơn vị; loại thông tin nhận dạng không cần cho thử nghiệm.
- Ghi nguồn từng trường: người nhập, trích hồ sơ nào, ngày nào, có được xác nhận chưa. Giữ dữ liệu gốc và bản chỉnh.
- Để trống khi không biết; không dựng liều, giờ, lab, kết quả hoặc phản hồi cho demo.
- Bộ tài liệu công khai dùng để thử truy xuất/citation. Bộ hồ sơ nội bộ dùng để thử workflow. Bộ nhãn chuyên gia dùng để đánh giá chất lượng. Ba bộ có nguồn gốc và mục tiêu khác nhau.
- Dùng một phần để phát triển; đóng băng phần đánh giá trước khi chỉnh prompt/rules. Không để câu trả lời được chuyên gia sửa đi vào tập đánh giá như đầu ra độc lập của hệ thống.

## 9. Giao diện đề xuất

### Kiến trúc màn hình

1. **Công việc của tôi:** yêu cầu được giao, hạn trả lời, chờ bổ sung/chờ duyệt/chờ phản hồi; mỗi dòng cho biết việc tiếp theo. Chưa có data thì hiển thị trạng thái rỗng, không dựng KPI.
2. **Tạo yêu cầu:** chọn thông tin thuốc / nghi ngờ ADR / đánh giá thông tin mới. Người báo chỉ thấy trường cần cho loại việc; khối thông tin ca chi tiết xuất hiện sau.
3. **Hồ sơ làm việc:** tóm tắt mục tiêu và bối cảnh; dữ liệu thiếu; tabs bối cảnh, bằng chứng, đánh giá, phản hồi, theo dõi.
4. **Bàn bằng chứng:** mỗi dòng có source type, scope, kết quả/CI, coverage, giới hạn và vai trò trong lập luận. Bấm dòng mở chi tiết cạnh nội dung, không buộc nhảy khỏi hồ sơ.
5. **Phiếu phản hồi:** câu trả lời ngắn phía trên; căn cứ và phạm vi phía dưới; phần chưa xác định nổi rõ; người duyệt/ngày/phiên bản.
6. **Theo dõi:** ai cần cung cấp gì, hạn nội bộ, phản hồi và lý do đóng/mở lại. Dùng ngôn ngữ công việc, đưa chi tiết agent/model/budget vào trang kỹ thuật.
7. **Kho chuyên môn:** tìm theo chủ đề và phạm vi, nhận biết bản chờ rà soát, liên kết các yêu cầu đã dùng.

### Hai bố cục để thử

**Bàn thẩm định:** điều hướng trái; bằng chứng giữa; phạm vi/đầu ra bên phải. Phù hợp dược sĩ quen tra cứu, cần đối chiếu nhiều nguồn.

**Theo từng bước:** làm rõ → nguồn → thẩm định → phản hồi → theo dõi. Phù hợp người mới hoặc tác vụ ít thường xuyên; giúp nhận biết phần thiếu, nhưng không buộc hồ sơ khẩn đi hết các màn hình trước khi phản hồi tạm.

Bản thử giao diện kèm nghiên cứu dùng thông tin công khai thật và các bước/nháp do nghiên cứu đề xuất. Chưa có người hỏi hoặc bệnh nhân nên các trường nội bộ trống. Các thao tác là thử bố cục, không tạo hồ sơ, duyệt chuyên môn hoặc gửi báo cáo trên hệ thống chính.

## 10. Đánh giá nền MVP hiện tại trên Git mới nhất

Đã fetch ngày 05/10/2026: main và origin/main cùng **b57219384ca2591b1801843fa8c4a32d17aefe59**, chênh lệch 0/0. Backend 8000 và frontend 3100 đang lắng nghe. Tài liệu hợp đồng và runtime đã kiểm tra: `docs/mvp-contracts.md`, `docs/person3/merged_runtime.md`, `src/api/mvp_runtime.py`, `src/config.py`.

| Nền hiện có | Giá trị sử dụng lại | Khoảng cách đến công việc bệnh viện |
|---|---|---|
| Claim và normalize tên thuốc/biến cố | Cấu trúc câu hỏi bằng chứng | Cần nằm trong yêu cầu chuyên môn; thêm mục đích, chỉ định, comparator, setting |
| Bằng chứng, scope, quote locator và provenance | Dược sĩ kiểm tra căn cứ | Cần so sánh thiết kế/đối chứng/khả năng áp dụng; đọc được phần coverage thiếu |
| Checkpoint review, version, export | Nền duyệt và truy vết | Cần phiếu trả lời theo loại việc; chuyển giao/phản hồi/theo dõi riêng |
| Connector và runtime `person3`/`live` trong code | Nền nguồn thật có thể tái sử dụng | Không đồng nghĩa mode hiện chạy hoặc kết luận đã được chuyên gia nghiệm thu |
| Dictionary MVP với các cặp giới hạn | Nền xác nhận mapping | Chưa phủ thuốc/biệt dược tiếng Việt/danh mục BV; cần quy trình mở rộng |

**Mock/fixture — tạm skip chuyên môn:** cấu hình đọc tại lượt này là `MVP_EVIDENCE_MODE=fixture`, `MVP_SOURCE_MODE=fixture`, `MVP_PUBMED_MODE=api`. Kết luận demo và bằng chứng giả không được coi là đáp án chuyên môn. Test tích hợp với HTTP/model tự soạn kiểm tra kỹ thuật, không là test nguồn/model live hay clinical gold. Các chế độ corpus/snapshot có văn bản thật vẫn khác tìm kiếm live, và khác dữ liệu ca bệnh viện.

Đã có tài liệu khác trong repo về đánh giá chuyên môn, nhưng nghiên cứu này không lấy danh xưng tác giả hoặc số liệu không dẫn nguồn trong tài liệu đó làm chứng cứ. Không thay nội dung của tài liệu đang tồn tại.

### Thay đổi mô hình miền cần thiết sau MVP

- `WorkItem/DrugInformationRequest`: loại yêu cầu, mục đích, requester, owner, urgency, due date, trạng thái công việc.
- `CaseRecord`: nhiều thuốc, quan sát/lab, timeline, nguyên nhân thay thế, đánh giá chuyên viên; tách dữ liệu ca khỏi bằng chứng quần thể.
- `EvidenceInvestigation`: tái sử dụng engine hiện tại; một yêu cầu có thể có nhiều investigation và phạm vi sửa đổi.
- `ProfessionalResponse`: phiếu trả lời, các statement/source link, applicability, phần chưa xác định, người duyệt và phiên bản.
- `FollowUp/SubmissionRecord`: yêu cầu bổ sung, phản hồi, bản gửi/biên nhận, lý do đóng và mở lại.
- `HospitalDrug/PolicyDocument`: mapping thuốc và văn bản nội bộ đã được đơn vị xác nhận.

Không cần viết lại engine ngay. Cần đặt nó vào mô hình công việc rộng hơn và giữ quan hệ giữa đối tượng rõ ràng. Literature stance, WHO-UMC case assessment và status “đã gửi báo cáo” không được dùng chung một trường.

## 11. Lộ trình cho cả nhóm theo năng lực, không theo một cá nhân

| Giai đoạn | Kết quả phải có | Các mảng phối hợp | Điều kiện qua giai đoạn |
|---|---|---|---|
| Chốt pilot và dữ liệu | SOP/mẫu phiếu, yêu cầu mẫu, danh mục, reviewer thật | Sản phẩm/nghiệp vụ + dữ liệu + người dùng BV | Biết người dùng, việc cần hoàn thành, dữ liệu được phép dùng và cách đánh giá |
| Lát cắt thông tin thuốc | Một yêu cầu thật đi từ tiếp nhận → làm rõ → bằng chứng → phiếu trả lời → duyệt → phản hồi | Dữ liệu/connector + engine/domain + UI + evaluation | Người dùng hoàn thành công việc, nguồn/nhận định được chuyên viên kiểm tra, biết phần thiếu |
| Lát cắt ADR | Tiếp nhận nhanh → bổ sung ca → timeline → đánh giá → báo cáo nháp → ghi nhận gửi/nhận | Domain + UI người báo/dược sĩ + dữ liệu ca + chuyên viên | Không bịa trường; nhiều thuốc/nguyên nhân khác; draft đúng mẫu đã chốt; traceable |
| Cập nhật và tái sử dụng | Cảnh báo theo danh mục, kho phản hồi và lịch rà soát | Connector/versioning + UI công việc + nhóm chất lượng | Nhìn được thay đổi và việc cần làm; quyết định do người phụ trách chốt |
| Mở rộng theo nhu cầu quan sát | Tương hợp/pha truyền, TDM, rà soát sử dụng thuốc, tích hợp HIS | Chủ sở hữu dữ liệu + dược sĩ chuyên ngành + kỹ thuật | Có nhu cầu đủ thường xuyên, nguồn được phép, dữ liệu và validation phù hợp |

Không ấn định số tuần khi chưa biết nhân lực, mẫu dữ liệu và thời gian chuyên viên. Mỗi giai đoạn có bản trình diễn dùng data thật và điều kiện nghiệm thu; test kỹ thuật là một phần, không thay nghiệp vụ.

**Chưa ưu tiên mặc định:** dashboard ROR/PRR, kê đơn tự động, tính liều đa chuyên khoa, quét mọi EHR, nhiều agent hoạt họa, auto-send báo cáo quốc gia. ROR là công cụ chuyên biệt có yêu cầu dữ liệu/phương pháp, không phải tính năng bắt buộc của mọi bàn thông tin thuốc bệnh viện. Có thể mở rộng khi nghiên cứu người dùng chứng minh nhu cầu.

## 12. Kiểm chứng đề xuất trước khi đầu tư sâu

Đề xuất quan sát/phỏng vấn 5–8 người tại đơn vị pilot, gồm dược sĩ DI/PV, dược sĩ tại khoa, người phụ trách, bác sĩ và điều dưỡng. Đây là kế hoạch, chưa thực hiện.

Nhờ mỗi người mở một yêu cầu hoặc ca gần nhất đã khử định danh: bắt đầu từ đâu; quyết định nào cần hỗ trợ; thiếu gì; mất công ở đâu; dùng tài liệu nào; ai duyệt; khi nào họ coi xong. Quan sát thực tế trước khi hỏi “có thích AI không”. Xin mẫu phiếu/câu trả lời/SOP họ đang dùng.

Đo trước và trong pilot:

- Thời gian thao tác chủ động từ yêu cầu đủ thông tin đến bản trả lời được duyệt; tách thời gian chờ phản hồi bên ngoài.
- Số lần nhập lại và số trường thiếu cần bổ sung, phân theo loại yêu cầu.
- Tỷ lệ nhận định có căn cứ đúng và phù hợp phạm vi qua reviewer; lỗi quan trọng được mô tả từng ca.
- Khả năng hoàn thành việc và hiểu đúng điều chưa biết; không đo bằng số quote hoặc số agent calls.
- Hồ sơ chờ phản hồi/chưa khép lại; tỷ lệ có lý do đóng được xác nhận.
- Độ hữu ích theo người nhận và lượng sửa chuyên môn cần thiết; không chỉ “trông có vẻ tin cậy”.

Mục tiêu số học về giảm thời gian hoặc accuracy phải chốt sau baseline với đơn vị; chưa có bằng chứng tiết kiệm X giờ/ngày. Chưa dùng giảm ADR/tử vong làm cam kết vì cần thiết kế nghiên cứu và dữ liệu khác.

## 13. Các quyết định nên chốt tiếp theo

1. Chọn một đơn vị pilot và người duyệt chuyên môn.
2. Chọn lát cắt thông tin thuốc/an toàn trước; mở cửa nhận ADR ngắn song song, chưa làm toàn bộ PV platform.
3. Xin gói dữ liệu thật và mẫu đầu ra của đơn vị.
4. Thử hai bố cục; xem người dùng làm rõ, so sánh nguồn và hoàn thành phản hồi được không.
5. Chốt backlog theo kết quả quan sát; triển khai một hồ sơ thật E2E trước khi mở rộng.

Bộ nguồn và thiết kế đã đủ để thảo luận sản phẩm có căn cứ. Chưa đủ để xác nhận độ an toàn lâm sàng, nhu cầu mua hoặc phù hợp workflow của một bệnh viện cụ thể.
