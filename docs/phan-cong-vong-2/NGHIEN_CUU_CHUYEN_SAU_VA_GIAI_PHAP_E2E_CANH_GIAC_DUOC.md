# Nghiên cứu chuyên sâu và giải pháp E2E: VigiLens cho dược sĩ bệnh viện

Ngày nghiên cứu: 05/10/2026. Người dùng chính theo lựa chọn của nhóm: dược sĩ bệnh viện / thông tin thuốc / cảnh giác dược. Phạm vi: toàn sản phẩm và toàn nhóm.

**Bản hợp nhất trong P-066:** nghiên cứu sản phẩm, thẩm định báo cáo agent khác và phân công vòng hai. Tài liệu này là bản chính để nhóm đọc và cập nhật; hai bản ban đầu được lưu trong `docs/research/2026-10-05/archive/` để đối chiếu. Kế hoạch chưa phải tính năng đã triển khai hoặc tiến độ đã xác nhận của từng người.

**Đọc nhanh:** mục 1–9: công việc/pain/dữ liệu/luồng/giao diện; mục 10–13: nền MVP và pilot; mục 14: phần giữ/sửa/loại từ bản agent; mục 15: từng task của bốn người; mục 16: phụ thuộc và thứ tự bàn giao; mục 17–18: ownership và định nghĩa xong; mục 19: việc kế tiếp của Người 2.

**Tài liệu kèm:** [manifest nguồn](../research/2026-10-05/data-real/manifest.json), [backlog theo feature](../research/2026-10-05/BACKLOG_VA_TIEU_CHI_NGHIEM_THU.md), [prototype đã render](../research/2026-10-05/preview.html), [kết quả kiểm tra](../research/2026-10-05/KIEM_TRA_DELIVERABLE.md). Bốn phiếu giao việc nằm trong các thư mục `nguoi-1/` đến `nguoi-4/` ngay cạnh plan, là bản trích từ mục 15, không phải kế hoạch độc lập.


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

Đã lưu **18 snapshot nguồn công khai kiểm tra payload và SHA-256**, cùng một lần lấy nguồn thất bại trong manifest. Bảy snapshot PubMed là metadata/abstract thật (3 nghiên cứu thuốc và 4 khảo sát workflow); ba SPL là văn bản nhãn thật; hai index nhãn; tổng kết Việt Nam 2024/2025; index bản tin mới; WHO-UMC; tài liệu openFDA; nghiên cứu workflow bản PDF tác giả. Index/tài liệu kỹ thuật không được tính như nghiên cứu lâm sàng độc lập.

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

Đã có tài liệu khác trong repo về đánh giá chuyên môn, nhưng nghiên cứu này không lấy danh xưng tác giả hoặc số liệu không dẫn nguồn trong tài liệu đó làm chứng cứ. Bản agent trong file này đã được thẩm định và thay bằng bản hợp nhất; quyết định giữ/sửa/loại ghi ở mục 14. Tài liệu chuyên môn khác trong repo được giữ nguyên.

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

Phân công theo đúng bốn vai cũ, từng task và thứ tự phụ thuộc được cụ thể hóa ở mục 15–19. Không ấn định số tuần khi chưa biết nhân lực, mẫu dữ liệu và thời gian chuyên viên. Mỗi giai đoạn có bản trình diễn dùng data thật và điều kiện nghiệm thu; test kỹ thuật là một phần, không thay nghiệp vụ.

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

## 14. Kết quả thẩm định bản nghiên cứu của agent khác

Đã đọc toàn bộ bản gốc 351 dòng. Bản gốc được giữ tại `docs/research/2026-10-05/archive/agent-original.md` để đối chiếu; **nội dung trong bản lưu không còn là đề xuất được chấp nhận**. Không xác nhận danh xưng chuyên gia tự ghi trong bản đó. Các quyết định dưới đây thay thế các kết luận tương ứng của bản gốc.

| Nội dung bản gốc | Quyết định | Lý do và cách xử lý trong kế hoạch này |
|---|---|---|
| Timeline nhiều thuốc, dechallenge, nguyên nhân thay thế, bổ sung dữ liệu | Giữ và bổ sung | Lưu điều thực sự đã xảy ra, nguồn từng trường và dữ liệu chưa biết. Literature không thay hồ sơ ca; không đề nghị dùng lại thuốc để thử nhân quả. |
| Nhãn đúng sản phẩm, đối chiếu cảnh báo, truy xuất đoạn nguồn | Giữ có điều kiện | Thêm dạng/đường, SETID/version, phạm vi quốc gia và trạng thái chưa tìm thấy/chưa đọc. Không tìm thấy trong một đoạn không chứng minh không có trong nhãn. |
| Workbench, phiếu phản hồi, phê duyệt, truy vết | Giữ và đổi trọng tâm | Tập trung nhu cầu DI/PV bệnh viện; thêm người nhận, việc bổ sung, phản hồi và lý do khép hồ sơ. |
| Bảng năm ca với ROR 4,2/3,8/2,9/2,4/2,1; Chi-square; điểm Naranjo; tỷ lệ lisinopril | **Loại khỏi bằng chứng và seed** | Không có truy vấn/snapshot, bốn ô số đếm, hồ sơ ca, lời giải từng câu hoặc nguồn định danh đủ để tái lập. Không được gọi là data thật. Không kết luận các thuốc không có nguy cơ; chỉ bác việc dùng các con số không kiểm chứng này. |
| Tính Naranjo cho một cặp thuốc–biến cố từ PubMed | **Loại** | Đánh giá ca cần dữ kiện người bệnh. Nội dung bài báo chung không thể cung cấp dechallenge, liều, diễn biến và nguyên nhân khác của ca đang xử lý. Nếu đơn vị chọn thang này, chỉ làm công cụ hỗ trợ ca với dữ kiện và reviewer. |
| Năm đầu ra mặc định: ROR, Naranjo, nhãn, literature, CIOMS | **Loại yêu cầu bắt buộc** | Sai trọng tâm người dùng đã chọn. Đầu ra ưu tiên là phiếu trả lời, hồ sơ nghi ngờ ADR có phần thiếu và theo dõi. CIOMS/E2B/MedWatch chỉ xem khi đầu mối nhận và SOP thực sự yêu cầu. |
| Dashboard tín hiệu/ROR là tính năng trung tâm sau MVP | Hoãn | Cần câu hỏi chuyên biệt, quần thể dữ liệu, loại trùng/phiên bản, bốn nhóm đếm nhất quán, khoảng tin cậy và reviewer phương pháp. Report counts/ROR không cho tỷ lệ mắc hay chứng minh nhân quả. |
| Pseudo-query openFDA rồi tự động tính ROR | **Loại khỏi chỉ dẫn triển khai** | Bản gốc chưa đặc tả mẫu số, scope, trùng và phiên bản; field path ví dụ không khớp query adapter hiện có. Tái sử dụng adapter đã lưu provenance, không đưa pseudo-code vào production. |
| Hạn 7/15/30 ngày áp dụng chung cho ca bệnh viện | **Loại hardcode** | ICH E2A đặt chuẩn báo cáo nhanh trong bối cảnh phát triển thuốc/nghiên cứu, không đủ để suy hạn cho mọi ca bệnh viện Việt Nam. Hạn nội bộ và hạn pháp lý phải tách; chỉ cấu hình quy định khi đã xác nhận văn bản, loại báo cáo, chủ thể và SOP. |
| “Unlabeled” tự trở thành tín hiệu mới và báo cáo khẩn | **Loại suy luận tự động** | Chưa xác nhận đúng nhãn/coverage có thể chỉ là gap. Seriousness, expectedness và causality là các trục riêng; quyết định báo cáo theo quy trình đã xác nhận. |
| Bệnh viện quyết định thay boxed warning/thu hồi giấy phép | **Loại khỏi đầu ra nghiệp vụ** | Đề xuất hành động của bệnh viện là xem tác động, cập nhật SOP/truyền thông và chuyển đầu mối; không giả định quyền quản lý cấp phép. |
| “Bốn giai đoạn EMA” là mô tả đầy đủ signal management | Sửa cách dẫn | Không sử dụng như workflow chuẩn bốn bước cho bệnh viện. GVP IX là tài liệu tham khảo signal management trong bối cảnh của nó; luồng E2E ở đây là thiết kế đề xuất cần pilot. |
| Label lag 1–3 năm, hàng nghìn báo cáo/tuần, tiết kiệm 2–3 ngày xuống 15 phút | **Loại các con số/cam kết** | Chưa có nghiên cứu hoặc baseline cho nhóm mục tiêu. Đo thời gian chủ động, thời gian chờ và mức sửa trong pilot trước khi đặt mục tiêu. |
| RCT luôn cao nhất, case report luôn thấp nhất nên ít giá trị | Sửa | Hiển thị thiết kế và đánh giá giới hạn theo câu hỏi, outcome, độ hiếm, comparator và phạm vi. Không thay thẩm định harms bằng một thứ hạng cứng. |
| Hash/quote đúng 100% đồng nghĩa đúng chuyên môn | **Loại** | Hash và locator kiểm tra tính toàn vẹn/vị trí; còn cần kiểm tra đoạn có hỗ trợ nhận định và áp dụng được hay không. |
| Hash + approval = chữ ký số/đủ 21 CFR Part 11 | **Loại tuyên bố tuân thủ** | Chưa có đánh giá pháp lý và validation liên quan. Audit/version hiện có là năng lực kỹ thuật, không tự tạo chữ ký số hay chứng nhận tuân thủ. |
| openFDA bao phủ từ 1969; mọi DailyMed là nhãn pháp lý áp dụng trực tiếp | Sửa | Tài liệu API event mô tả dữ liệu từ 2004 và độ trễ cập nhật; phải xem metadata lần lấy. DailyMed/SPL cần xác nhận đúng sản phẩm và không thay nhãn Việt Nam. |
| MVP không có phân loại RCT/case report | **Bác nhận định về code** | `EvidenceType` trong `src/models/schemas.py` đã có RCT, observational, case_report, label, faers_report, review, other. Cần nâng chất lượng extraction/hiển thị, không mô tả là chưa có enum. |
| Xóa tất cả mock/fixture | **Loại** | Giữ cho phát triển và test offline, gắn nhãn rõ. Skip khi đánh giá chuyên môn và chặn nhầm chế độ trong pilot; không lấy mock làm bằng chứng thật. |
| Mặc định model cụ thể và pool nhiều API key | Không đưa vào yêu cầu sản phẩm | Không có kiểm chứng cấu hình/quota/hiệu quả cần thiết ở đây. Người 2 quản lý provider, budget và chất lượng; không đưa bí mật hoặc quota giả vào tài liệu. |
| MedDRA/VigiBase/EudraVigilance được coi như nguồn mở luôn có sẵn | Sửa thành phụ thuộc | Xác nhận quyền truy cập, thuật ngữ/phiên bản và điều kiện sử dụng. Không hứa có dữ liệu ca hoặc full-text không được cấp quyền. |

Căn cứ cho các chỉnh sửa chính: [WHO-UMC](https://www.who.int/publications/m/item/WHO-causality-assessment), [ICH E2A](https://database.ich.org/sites/default/files/E2A_Guideline.pdf), [openFDA event](https://open.fda.gov/apis/drug/event/), [DailyMed web services](https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm), [FDA — phạm vi Part 11](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application), [Oxford — sử dụng levels of evidence](https://www.cebm.ox.ac.uk/resources/levels-of-evidence/levels-of-evidence-introductory-document), [MedDRA](https://www.meddra.org/). Những nguồn này không được dùng để suy ra sản phẩm đã được nghiệm thu tại Việt Nam.

## 15. Phân công bốn người: giữ vai cũ, thay mục tiêu thành công việc bệnh viện

Đối chiếu phân công cũ trong `docs/QUY_TAC_PHOI_HOP_4_NGUOI.md`, mục 4, và `docs/planMVPfinal.md`. **Đây là kế hoạch mới đề xuất, không phải xác nhận bốn người đã nhận hoặc đã hoàn thành việc.**

| Người | Vai cũ giữ nguyên | Đầu việc vòng hai | Kết quả chịu trách nhiệm |
|---|---|---|---|
| 1 | Nguồn, database, provenance, môi trường/vận hành/deploy | Dữ liệu thật đúng sản phẩm, lưu trữ hồ sơ, pipeline nguồn, môi trường pilot và phục hồi | Dữ liệu truy được nguồn/phiên bản; hồ sơ không mất; triển khai kiểm tra được trên đúng SHA |
| 2 — bạn | Contract, worker, LLM gateway, agent, auth, API, tích hợp | Mô hình yêu cầu/ca/phiếu phản hồi/theo dõi; agent theo nhu cầu; API và chuyển trạng thái | Một yêu cầu đi E2E; agent biết thiếu gì; duyệt/xuất/gửi/theo dõi không bị gộp |
| 3 | Normalize, evidence, scope, contradiction, dossier, gold | Rubric chuyên môn, applicability, nhận định–nguồn, nội dung phiếu trả lời và đánh giá ca | Bằng chứng đọc được, đúng phạm vi; phần không biết giữ nguyên; bộ đánh giá được chuyên viên thẩm định |
| 4 | Frontend, baseline, evaluation, tài liệu/demo | Giao diện người báo/dược sĩ, trải nghiệm hoàn thành công việc, thử người dùng và báo cáo pilot | Người dùng nhập–đọc–sửa–duyệt–theo dõi được; đo chất lượng và lỗi, không chỉ demo đẹp |

**Quy ước đọc phần chi tiết:** A = lát cắt DI và tiếp nhận ADR ngắn; B = thẩm định ca ADR đầy đủ khi có SOP/ca được phép; C = cập nhật an toàn và tái sử dụng sau khi A ổn. Các mã `R2-*` là công việc được đề xuất vòng hai, không phải ID đã có trên tracker. “Phụ thuộc” ghi phần đầu vào cụ thể; không có nghĩa phải chờ toàn bộ người đó hoàn thành.

### 15.1 Người 1 — dữ liệu, nguồn, lưu trữ và deploy

#### R2-1-01 — Lập gói dữ liệu và provenance [A; làm ngay]

- **Làm:** kiểm tra manifest nguồn đã lưu; tách abstract/SPL/bản tin/tài liệu kỹ thuật; ghi URL, ngày lấy, coverage, hash và lỗi. Tạo danh sách dữ liệu BV cần xin: SOP, mẫu DI/ADR, danh mục, yêu cầu đã khử định danh và quyền sử dụng. Không lấy hồ sơ người bệnh trước khi đơn vị cho phép.
- **Bàn giao:** source manifest/schema, data inventory và báo cáo nguồn lấy được/không lấy được cho 3; packet công khai cho 2/4. Bộ hiện có nằm trong `docs/research/2026-10-05/data-real`.
- **Phụ thuộc:** không cần agent/API mới. Dữ liệu nội bộ phụ thuộc đầu mối BV; 3 xác nhận phần nghiệp vụ cần xin. Có thể hoàn thành nhánh công khai trong khi chờ.
- **Nghiệm thu:** mở được payload và tái kiểm hash; abstract không gắn full-text; failure không biến thành no-result; dữ liệu bệnh viện chưa có được ghi rõ. **Review:** 3 nội dung/coverage, 2 định dạng tích hợp.

#### R2-1-02 — Danh mục thuốc và chọn nhãn đúng sản phẩm [A]

- **Làm:** đặc tả import mã BV, tên gốc, hoạt chất, hàm lượng/dạng/đường/hãng; mapping giữ tên gốc và mức xác nhận. Người 1 xây import/index/lưu trữ; Người 3 viết quy tắc chuyên môn và xác nhận mapping. Thiếu danh mục thì dùng dữ liệu sản phẩm công khai để kiểm tra pipeline, không gọi là danh mục BV.
- **Bàn giao:** dữ liệu/index cho 3 normalize và 2 lookup API; kết quả mapping gồm candidate và unknown cho 4 hiển thị.
- **Phụ thuộc:** rubric mapping `R2-3-01`; hình dạng response thống nhất trong `R2-2-01`. Import/mẫu CSV có thể làm trước API.
- **Nghiệm thu:** pantoprazole tiêm không tự trở thành nhãn viên; ciprofloxacin nhỏ tai không tự khớp đường uống; chưa xác nhận không tự approved. **Review:** 3 mapping, 2 API/storage.

#### R2-1-03 — Lưu trữ WorkItem/Response/FollowUp có migration [A]

- **Làm:** thiết kế bảng/quan hệ cho yêu cầu, liên kết investigation, bản phiếu trả lời, công việc bổ sung, bản xuất và bản chuyển giao. Dùng nền storage/migration hiện có; chỉ đổi database khi có nhu cầu được chứng minh. Tách dữ liệu nghiệp vụ khỏi raw snapshot và log kỹ thuật.
- **Bàn giao:** migration, repository methods và ghi chú transaction/version cho 2. Quyền truy cập do 2 kiểm soát tại service/API; cấu trúc và backup do 1.
- **Phụ thuộc:** contract tối thiểu `R2-2-01`; ràng buộc chuyên môn từ 3. Có thể làm mapping và migration nháp, nhưng không merge schema persistence trái public contract.
- **Nghiệm thu:** dữ liệu MVP vẫn đọc được; restart giữ hồ sơ; history còn nguyên; hai cập nhật không âm thầm mất nội dung; migration và rollback/restore có kịch bản kiểm tra. **Review:** 2 transaction/version, 3 không mất nguồn dữ kiện.

#### R2-1-04 — Connector/snapshot với coverage và lỗi thật [A]

- **Làm:** tái sử dụng PubMed/DailyMed/FAERS adapters; bổ sung metadata sản phẩm, version, ngày xuất bản/hiệu lực/ngày lấy; phân biệt timeout, HTTP lỗi, empty, giới hạn/chưa đọc đủ. Full text chỉ ingest khi có quyền; giữ cache/replay và hạn nguồn.
- **Bàn giao:** SourceResult theo contract cho 2 runner và 3 extractor; tình huống lỗi ổn định cho 4 UI. Chưa cần mô-đun tính ROR.
- **Phụ thuộc:** `R2-2-01` cho fields giao tiếp, `R2-3-02` cho metadata cần để thẩm định. Có thể kiểm connector live độc lập trước agent mới.
- **Nghiệm thu:** nguồn 404 vẫn là gap nguồn; abstract-only hiện đúng; nhãn có ngày đăng khác ngày hiệu lực giữ cả hai; provenance tái lập được. **Review:** 2 contract/retry, 3 coverage.

#### R2-1-05 — Tài liệu nội bộ và dữ kiện ca [B]

- **Làm:** nhận SOP/mẫu và ca theo quyền đơn vị; version văn bản, lưu tệp được phép, mã ca và nguồn dữ kiện, import ngày/giờ/đơn vị lab có trường unknown. Tránh đưa dữ liệu nhận dạng không cần thiết vào source corpus/LLM trace.
- **Bàn giao:** inventory được phép dùng, mẫu dữ liệu và repository cho 2 case API, 3 rubric/case review, 4 giao diện. Dùng synthetic có nhãn để kiểm kỹ thuật khi chưa có ca thật.
- **Phụ thuộc:** BV cho phép; `R2-3-06` xác định trường cần; `R2-2-07` quyền và `R2-2-09` case contract. Không chặn lát cắt DI công khai.
- **Nghiệm thu:** trường thiếu vẫn thiếu; bản bổ sung cùng ca không tạo bệnh nhân mới; tệp/ca chỉ thấy theo quyền đã chốt. **Review:** 2 quyền, 3 ngữ nghĩa ca.

#### R2-1-06 — Môi trường staging/pilot và cấu hình mode [A]

- **Làm:** chuẩn hóa cách chạy backend/frontend hiện có, env mẫu không chứa key; tách fixture/replay/live; health/readiness; cấu hình origin/cookie theo môi trường. Trang kỹ thuật ghi commit SHA, runtime mode và version dữ liệu; UI nghiệp vụ chỉ hiện nhãn nguồn/chế độ cần thiết.
- **Bàn giao:** URL staging, runbook, env template và checklist release cho cả nhóm. Đây tiếp tục là phần deploy của Người 1.
- **Phụ thuộc:** có thể dựng từ main hiện tại; pilot mới cần API của 2, UI của 4 và cấu hình nguồn của 1. Không cần đợi hoàn thiện ADR/B/C để dựng staging.
- **Nghiệm thu:** khởi động từ hướng dẫn trên máy/môi trường sạch; mode pilot được kiểm chứng; không có secret trong repo/log; lỗi cấu hình không âm thầm fallback sang bằng chứng giả. **Review:** 2 backend/mode, 4 frontend.

#### R2-1-07 — CI, smoke, backup/restore và phát hành [A, sau đó B/C]

- **Làm:** cập nhật checks theo lát cắt, source smoke giới hạn, phân biệt test fixture với live; backup hồ sơ/snapshot theo nhu cầu, thực hành restore và xác nhận cùng SHA/code/data. Mỗi người vẫn viết test module của mình; 1 không phải người viết toàn bộ test sản phẩm.
- **Bàn giao:** release checklist, artifact smoke/restore và runbook xử lý failure cho 2/4.
- **Phụ thuộc:** build/tích hợp từ 2+4, rubric/chất lượng từ 3. Công cụ backup và CI khung làm ngay; release pilot chờ gate tích hợp/chuyên môn.
- **Nghiệm thu:** restore mở được hồ sơ và bản duyệt đúng; restart không mất trạng thái; frontend gọi đúng backend; ghi rõ test nào live và test nào synthetic. **Review:** 2 trạng thái/idempotency, 4 smoke E2E.

#### R2-1-08 — Nguồn cập nhật và diff version [C]

- **Làm:** kiểm nguồn an toàn/nhãn theo danh sách đã chọn; lưu lần lấy và nội dung/version; chỉ thông báo có thay đổi cần xem, tránh coi mọi lần fetch là cảnh báo mới.
- **Bàn giao:** ChangeSet cho 3 đánh giá và 2 tạo việc; payload cho 4 hàng chờ cập nhật.
- **Phụ thuộc:** A đã ổn; nguồn được phép, danh mục `R2-1-02`, rubric `R2-3-08`, update contract `R2-2-09`.
- **Nghiệm thu:** không đổi nội dung thì không tạo việc trùng; đổi nhãn có đoạn diff/provenance; thiếu danh mục không tự dựng tác động BV. **Review:** 3 ý nghĩa thay đổi, 2 dedup.

### 15.2 Người 2 — bạn: agent, contract, backend và tích hợp

#### R2-2-01 — Chốt contract nhỏ cho lát cắt DI [A; ưu tiên đầu tiên]

- **Làm:** cùng 1/3/4 chốt RequestContext, WorkItem, InvestigationLink, EvidenceBundle, ProfessionalResponse, FollowUp và Version/ReviewRef; quy định unknown, draft, lỗi, coverage. Tách status công việc khỏi status chạy agent và status duyệt. Không mở schema ADR/C đầy đủ trong lần chốt đầu.
- **Bàn giao:** `docs/contracts-hospital-v2.md` đề xuất mới, OpenAPI và JSON examples hợp lệ cho tất cả; cập nhật `docs/mvp-contracts.md`/`src/models/schemas.py` khi triển khai thật. Schema mới là additive hoặc có kế hoạch tương thích.
- **Phụ thuộc:** 3 gửi trường/rubric tối thiểu; 4 gửi hành trình và form; 1 gửi provenance/storage constraints. Đây là điểm phối hợp ngắn đầu đợt, không phải yêu cầu 2 viết xong agent.
- **Nghiệm thu:** 1 lưu, 3 xử lý và 4 render cùng examples; ví dụ có unknown/error/abstract-only; generated types đồng bộ; MVP không vỡ. **Review:** 1/3/4 cùng xác nhận contract.

#### R2-2-02 — WorkItem service và API tiếp nhận/làm rõ [A]

- **Làm:** tạo/lưu nháp yêu cầu, gán owner, cập nhật câu hỏi/phạm vi, yêu cầu bổ sung và liên kết investigation. Dùng repository của 1; chưa đủ thông tin vẫn tiếp nhận được. Luồng chuyển trạng thái đề xuất cần chốt với 3/4, không tự ép mọi yêu cầu phải tra cứu mới.
- **Bàn giao:** API hoạt động, examples và error/version semantics cho 4; context object cho runner của 2 và analysis của 3.
- **Phụ thuộc:** `R2-2-01`, storage `R2-1-03` cho persistence thật. Có thể làm service/contract tests với repository tạm cùng interface trước khi migration xong.
- **Nghiệm thu:** sửa scope tạo revision; nhiều investigation vẫn gắn đúng yêu cầu; draft không tự thành câu trả lời; quyền cập nhật/owner đúng. **Review:** 1 lưu trữ, 4 luồng người dùng.

#### R2-2-03 — Planner/agent tìm theo quyết định cần hỗ trợ [A]

- **Làm:** mở planner từ drug/event sang mục đích, chỉ định, setting, comparator và thời gian; ghi kế hoạch tra cứu và coverage. Node của 3 vẫn sở hữu extraction/scope/contradiction; 2 sở hữu graph/state/điều phối. Có điểm người dùng xác nhận mapping/phạm vi khi mơ hồ.
- **Bàn giao:** run context và evidence results cho 3; tiến độ/gaps và cách tiếp tục cho 4. Không tự gán ca nhân quả từ stance của literature.
- **Phụ thuộc:** `R2-2-01/02`; connector `R2-1-04`; interfaces/rubric `R2-3-01/02`. Có thể dựng graph với adapters test ghi nhãn, nhưng live acceptance phải dùng nguồn thật.
- **Nghiệm thu:** giữ comparator/chỉ định của bài; thiếu mapping hỏi xác nhận; source failure ghi gap; kết thúc bằng thiếu dữ liệu có lý do/việc tiếp theo, không bịa kết luận. **Review:** 3 kết quả/phạm vi, 1 source budget.

#### R2-2-04 — Checkpoint người dùng, resume và trạng thái thiếu dữ liệu [A]

- **Làm:** chuyển checkpoint hiện có thành điểm dược sĩ xem/sửa câu hỏi, mapping, bằng chứng và draft; lưu phiên bản xác nhận. Người dùng bổ sung mới phải có quyết định chạy lại phần nào; chống double-submit/retry tạo run trùng.
- **Bàn giao:** API pause/resume/cancel hoặc năng lực tương đương trong kiến trúc hiện tại, version conflict và pending action cho 4.
- **Phụ thuộc:** `R2-2-02/03`; storage/version của 1; coverage/gap của 3. Không yêu cầu thêm worker framework chỉ vì có resume.
- **Nghiệm thu:** restart/retry không mất dữ kiện, không duyệt nhầm version; người dùng thấy việc cần làm; hủy/timeout vẫn giữ bằng chứng đã lấy và phần chưa hoàn thành. **Review:** 1 recovery, 4 thao tác.

#### R2-2-05 — Phiếu phản hồi: draft, sửa, duyệt, xuất [A]

- **Làm:** điều phối generator theo template/rubric của 3; lưu statement/source links và reviewer edits; kiểm quyền, version và trạng thái duyệt trước export theo policy đã chốt. Bản nháp có thể xuất khi nghiệp vụ cho phép nhưng phải ghi nháp.
- **Bàn giao:** Response/Review/Export API cho 4; bản đầu ra có nguồn, phần chưa biết, người chịu trách nhiệm và revision.
- **Phụ thuộc:** nội dung/validator `R2-3-04/05`, storage `R2-1-03`, form/view của 4. Template có thể chuẩn bị trước; không chờ UI mới test được render server.
- **Nghiệm thu:** quote/nguồn đã loại không còn được dùng hợp lệ; đổi scope/nhận định trọng yếu sau duyệt khiến revision mới cần duyệt; bản cũ vẫn truy được; export không tự ghi sent. **Review:** 3 nội dung, 4 bản xem/xuất.

#### R2-2-06 — Theo dõi, chuyển giao và khép công việc [A]

- **Làm:** thêm request bổ sung, hạn nội bộ, người nhận, ghi nhận hành động gửi/nhận/feedback, lý do đóng/mở lại. Hành động gửi thật ngoài hệ thống có thể được người dùng ghi nhận với bằng chứng; chưa tích hợp email thì không giả auto-send.
- **Bàn giao:** FollowUp/Submission APIs và business rules cho 4; storage records cho 1. Không trộn submission status và response approval.
- **Phụ thuộc:** `R2-2-02/05`, storage `R2-1-03`; mẫu nghiệp vụ 3 và màn hình 4.
- **Nghiệm thu:** export≠sent≠received≠closed; chưa có biên nhận thì unknown; reopen giữ lịch sử và lý do; không hardcode hạn pháp lý chưa xác nhận. **Review:** 3 workflow, 4 E2E.

#### R2-2-07 — Quyền, phiên bản và audit phục vụ pilot [A trước dữ liệu nội bộ; B mở rộng]

- **Làm:** dựa auth hiện có, chốt vai người báo/dược sĩ/người duyệt và phạm vi đơn vị; kiểm read/update/review/export server-side; audit sự kiện quan trọng; đồng bộ version conflict. Cấu hình retention/nhận dạng theo lựa chọn đơn vị; không tự tuyên bố tuân thủ hay chữ ký số.
- **Bàn giao:** permission matrix, API denial examples và event schema cho 1 storage/ops, 4 UI, 3 review policy.
- **Phụ thuộc:** BV xác nhận vai/quyền; 1 data policy; 3 approval rules. Có thể kiểm quyền bằng tài khoản synthetic trước khi có dữ liệu thật.
- **Nghiệm thu:** người ngoài phạm vi không đọc được hồ sơ bằng gọi API trực tiếp; UI ẩn nút không thay kiểm quyền; stale revision bị từ chối có cách tải lại. **Review:** 1 deploy/data isolation, 4 permission scenarios.

#### R2-2-08 — Budget, trace và tích hợp lát cắt đầu [A]

- **Làm:** cấu hình provider/model qua gateway, token/request/timeout budget và retry có trần; ghi mode/coverage/error không lộ nội dung ca không cần thiết. Điều phối integration harness cho toàn luồng; mỗi người cung cấp test phần mình. Chỉ chạy rộng hơn khi có thay đổi/failure cần giải quyết.
- **Bàn giao:** run trace đã giảm dữ liệu nhạy cảm, API smoke và checklist tích hợp cho 1/3/4; contract version đang dùng.
- **Phụ thuộc:** 1 nguồn/môi trường; 3 pipeline analysis; 4 client. Trace/harness khung làm song song từ `R2-2-01`.
- **Nghiệm thu:** nguồn/model lỗi không fallback thành kết luận mock trong pilot; quota/timeout giữ kết quả từng phần và gap; cùng SHA/API/data tạo được kết quả để reviewer kiểm. **Review:** 1 vận hành, 3 fidelity, 4 E2E.

#### R2-2-09 — Mở rộng CaseRecord và cập nhật an toàn [B/C; không chặn A]

- **Làm B:** nhiều thuốc, administrations/timeline, lab có đơn vị, observations, case assessments và report revisions. Gọi rubric/validator 3; giữ case causality riêng literature stance. **Làm C:** ChangeSet→ImpactReview→FollowUp, kho phiếu trả lời và revision cần rà soát.
- **Bàn giao:** contract nhỏ riêng B rồi C; case/update APIs cho 1/3/4. Không làm cả hai module trước khi lát cắt A được review.
- **Phụ thuộc:** B cần `R2-1-05`, `R2-3-06`, BV SOP/ca; C cần `R2-1-08`, `R2-3-08`, danh mục. Chuẩn bị contract với synthetic được, nghiệm thu lâm sàng thì chưa.
- **Nghiệm thu:** không tự sinh Naranjo/WHO category khi thiếu dữ kiện; bổ sung cùng ca không thành ca mới; thiếu danh mục không dựng impact; update không tự ghi hành động đã triển khai. **Review:** 3 nghiệp vụ, 1 persistence, 4 giao diện.

### 15.3 Người 3 — bằng chứng, phạm vi và nội dung chuyên môn

#### R2-3-01 — Rubric câu hỏi và normalization [A; làm ngay]

- **Làm:** chốt trường cần cho từng loại câu hỏi: mục đích, indication, population, setting, route, comparator, outcome, time; phân biệt bắt buộc để tiếp nhận và để kết luận. Quy tắc tên thuốc/biến cố giữ nguyên tên gốc, candidate, unknown và người xác nhận; không mở rộng dictionary bằng alias chưa kiểm.
- **Bàn giao:** rubric, field glossary và examples cho 2 contract, 1 mapping/import, 4 form. Nêu rõ trường có thể vắng và cách xin bổ sung.
- **Phụ thuộc:** có thể làm từ nghiên cứu/packet hiện có; mẫu BV giúp hiệu chỉnh, không phải chờ agent mới.
- **Nghiệm thu:** câu hỏi general DI không bị ép thành ca; sai đường dùng không auto-match; unknown không bị chuyển thành false; dược sĩ đọc hiểu được yêu cầu bổ sung. **Review:** 2 contract, 4 wording; chuyên viên pilot khi có.

#### R2-3-02 — Extraction và chất lượng nghiên cứu theo câu hỏi [A]

- **Làm:** tái sử dụng evidence pipeline; giữ thiết kế, quần thể/setting, comparator, exposure/outcome windows, estimate/CI/đơn vị, limitation và coverage. Nêu field lấy từ đâu hoặc chưa có; tránh suy methodological details ngoài abstract. Kiểm khả năng hai bài dùng chung quần thể/data khi thông tin cho phép.
- **Bàn giao:** EvidenceBundle/units và fixtures gắn nguồn thật cho 2 node interface, 4 bảng thẩm định; yêu cầu metadata nguồn cho 1.
- **Phụ thuộc:** packet `R2-1-01`, schema `R2-2-01`; connector live không cần xong mới làm extraction trên snapshot.
- **Nghiệm thu:** PMID 39975698/40285433 giữ comparator/setting; CI/đơn vị không bị mất; case report/label không bị coi là RCT; abstract-only không mô tả như full-text đã đọc. **Review:** 2 interface; chuyên viên xem nội dung.

#### R2-3-03 — Scope/applicability và giải thích khác biệt [A]

- **Làm:** so câu hỏi với từng chiều phạm vi; trả khớp/khác/chưa rõ kèm lý do và dữ kiện. Phân biệt khác kết quả do thiết kế/phạm vi với contradiction trực tiếp; cảnh báo nhãn và estimate nghiên cứu có vai trò khác nhau.
- **Bàn giao:** assessment có cấu trúc cho 2 tổng hợp và 4 panel; ví dụ accepted/rejected/needs-context.
- **Phụ thuộc:** `R2-3-01/02`; câu hỏi đã chốt từ `R2-2-02`. Có thể dùng câu hỏi nghiên cứu công khai được ghi là đề xuất, không giả người hỏi BV.
- **Nghiệm thu:** không đếm bài để bỏ phiếu; phạm vi khác không gọi conflict trực tiếp; chưa biết comparator hiển thị chưa biết. **Review:** 2 integration, 4 khả năng hiểu; chuyên viên validation.

#### R2-3-04 — Nhận định–nguồn và chất lượng citation [A]

- **Làm:** tách fact từ nguồn, inference chuyên môn, dữ kiện ca và gap; đối chiếu locator/hash rồi kiểm đoạn có hỗ trợ nhận định. Nhãn giữ nguyên lỗi chữ có flag; không làm sạch quote rồi gọi nguyên văn. Khi loại nguồn/đổi version, đánh dấu statement cần rà soát.
- **Bàn giao:** citation/entailment rubric, validator và examples cho 2 review policy và 4 inspector.
- **Phụ thuộc:** source snapshot `R2-1-04` và evidence `R2-3-02`; contract `R2-2-01`. Không cần đợi response API mới kiểm trên packet.
- **Nghiệm thu:** locator đúng nhưng entailment sai vẫn bị phát hiện; nguồn vắng/quote lệch không hợp lệ; coverage giới hạn hiện rõ. **Review:** 2 validation orchestration, 4 source navigation; reviewer chuyên môn.

#### R2-3-05 — Phiếu trả lời và nội dung dossier [A]

- **Làm:** template ngắn gồm câu hỏi chốt, câu trả lời, phạm vi, căn cứ, chưa xác định, thông tin cần bổ sung, người chịu trách nhiệm/ngày rà soát. Dossier phía sau để đọc chi tiết; có câu trả lời tạm chờ bổ sung. Nội dung cảnh báo không tự chuyển thành hướng dẫn điều trị cá thể.
- **Bàn giao:** templates, prompts/rules nội dung và ví dụ được chuyên viên sửa cho 2 generator/export và 4 editor/preview. Người 3 sở hữu nội dung; 2 sở hữu API/phê duyệt/version; 4 sở hữu bố cục.
- **Phụ thuộc:** `R2-3-01/03/04`; mẫu đầu ra BV cho bản chính thức. Có thể dựng template đề xuất trước và ghi chưa chốt với đơn vị.
- **Nghiệm thu:** trang đầu trả lời đúng nhu cầu; statements truy được; gaps không bị ẩn; không có điểm nhân quả ca giả, không có cam kết ROR/15 phút. **Review:** 4 độ dễ đọc, 2 API/export; chuyên viên nội dung.

#### R2-3-06 — Checklist ca ADR và mẫu báo cáo [B; chuẩn bị rubric ngay]

- **Làm:** cùng dược sĩ pilot chốt timeline nhiều thuốc, các trục severity/seriousness/causality/expectedness, nguyên nhân khác, nguồn mỗi dữ kiện và phần còn thiếu. Chọn rubric ca theo SOP; không bắt buộc Naranjo/WHO-UMC cho mọi đơn vị. Xác nhận mẫu báo cáo và quy trình bổ sung/gửi.
- **Bàn giao:** case field specification cho 1/2, checklist và mẫu nháp cho 4; bộ tình huống missing-data/trùng/phiên bản.
- **Phụ thuộc:** mẫu/SOP/chuyên viên BV; `R2-1-05` ca được phép cho validation. Viết checklist đề xuất trước được; chưa ký clinical acceptance.
- **Nghiệm thu:** ghi observed dechallenge khác unknown; không lấy bài PubMed làm diễn biến ca; không yêu cầu rechallenge; trường chưa có không bị bịa để đủ mẫu. **Review:** chuyên viên pilot quyết định; 2/4 kiểm thực thi.

#### R2-3-07 — Bộ đánh giá và adjudication chuyên môn [A, mở rộng B/C]

- **Làm:** định nghĩa tiêu chí relevance/applicability/entailment/coverage/usefulness/critical errors; chọn tập phát triển và tập đánh giá riêng; tạo annotation guide và ledger. Khi có reviewer thật, ghi nhãn độc lập và cách xử lý bất đồng; AI-generated reference không tự trở thành gold.
- **Bàn giao:** case IDs, source versions, rubric và nhãn có người/ngày cho 4 metric, 2 evaluation runner, 1 versioned corpus.
- **Phụ thuộc:** nguồn 1; reviewer/SOP nội bộ cho clinical labels. Rubric và source-grounded test set công khai làm ngay; clinical gold chờ bên ngoài và ghi riêng.
- **Nghiệm thu:** không leak tập đánh giá vào prompt; phân biệt source citation check/technical pass/clinical label; thiếu reviewer ghi “chưa nghiệm thu”. **Review:** 4 evaluation design; dược sĩ độc lập adjudication.

#### R2-3-08 — Tác động cảnh báo và tái sử dụng câu trả lời [C]

- **Làm:** rubric change significance, product/route/population fit, jurisdiction và local applicability; nội dung bản tin/impact note; điều kiện phiếu trả lời cần rà soát khi nhãn/phạm vi đổi.
- **Bàn giao:** content rules cho 2 workflow và 4 UI; yêu cầu diff/metadata cho 1.
- **Phụ thuộc:** `R2-1-02/08`, SOP/danh mục được xác nhận; A ổn và output template `R2-3-05`.
- **Nghiệm thu:** thiếu danh mục ghi chưa đối chiếu; bản tin là draft cho chuyên viên duyệt; không tự nói bệnh viện đã sửa quy trình. **Review:** chuyên viên BV, 2 state rules, 4 rendering.

### 15.4 Người 4 — UI, evaluation, pilot và demo

#### R2-4-01 — Quan sát công việc và prototype hai bố cục [A; làm ngay]

- **Làm:** chuẩn bị walkthrough/phỏng vấn theo mục 12, mẫu đo baseline và test hai bố cục: bàn thẩm định/theo bước. Xác định người báo nhập gì và dược sĩ cần thấy gì; giữ màn hình rỗng khi chưa có dữ liệu. Prototype đã có trong packet là điểm khởi đầu, chưa phải UI chính.
- **Bàn giao:** flow, field map, lỗi hiểu/điểm tốn công cho 2 contract, 3 wording/rubric và 1 data inventory. Không dùng câu “thích AI” thay quan sát tác vụ.
- **Phụ thuộc:** không chờ backend mới; dùng packet thật + form trống. Việc quan sát người dùng thật phụ thuộc đầu mối BV, không giả đã phỏng vấn.
- **Nghiệm thu:** phân biệt người báo/dược sĩ/người duyệt; người thử biết bước tiếp theo và phần chưa biết; ghi rõ đâu là giả thuyết. **Review:** 3 nghiệp vụ, 2 khả năng API.

#### R2-4-02 — Công việc của tôi và tiếp nhận nhanh [A]

- **Làm:** mở rộng frontend hiện hành `frontend/`; hàng chờ theo owner/status/next action; form DI và cửa nhận nghi ngờ ADR ngắn; lưu nháp và unknown. Không bắt người báo đi qua màn hình agent hoặc chứng minh causality.
- **Bàn giao:** UI và contract-backed test cases cho 2 API; feedback missing fields cho 3. Có thể làm UI bằng JSON example cố định gắn nhãn development.
- **Phụ thuộc:** contract `R2-2-01`; nối thật cần `R2-2-02/07`. Fixture development giúp bắt đầu, không được nghiệm thu pilot từ mock.
- **Nghiệm thu:** lưu khi chưa đủ thông tin; không dựng count/KPI; không mất nội dung khi API lỗi; biết ai nhận và việc cần bổ sung. **Review:** 2 API/quyền, 3 field relevance.

#### R2-4-03 — Bàn bằng chứng và đối chiếu phạm vi [A]

- **Làm:** bảng study/source/coverage/comparator/estimate/CI/limitations; chọn dòng mở nguồn và đánh giá applicability bên cạnh; distinction nguồn lỗi/no-result/partial. Mapping mơ hồ có bước xác nhận.
- **Bàn giao:** views/inspector và interaction cases cho 2+3; lỗi source rendering cho 1.
- **Phụ thuộc:** contract `R2-2-01`, payload `R2-3-02/03/04`; live API từ `R2-2-03/04`. Layout/source pane làm trên snapshot trước được.
- **Nghiệm thu:** đọc được FQ hai nghiên cứu khác scope; nhãn viên/tiêm rõ; abstract-only không bị ẩn; dẫn nguồn tới đúng đoạn/version. **Review:** 3 interpretation, 2 runtime.

#### R2-4-04 — Phiếu trả lời, sửa và duyệt [A]

- **Làm:** response editor/preview, nguồn từng statement, gaps, revision history, người duyệt; thao tác review/export theo quyền; cảnh báo stale response và nguồn thay đổi. Bố cục bản xuất không làm mất ý nghĩa chuyên môn.
- **Bàn giao:** UI và output sample cho 3 xem nội dung, 2 API integration; trường hợp sửa sau duyệt cho regression.
- **Phụ thuộc:** template `R2-3-05`, API `R2-2-05/07`. Preview có thể làm trước API với examples thống nhất.
- **Nghiệm thu:** người dùng đọc trang đầu hiểu câu trả lời/giới hạn; draft nhìn rõ; đổi nội dung trọng yếu cần duyệt lại; export không hiện như đã gửi. **Review:** 3 chuyên môn, 2 review/version.

#### R2-4-05 — Theo dõi, phản hồi và đóng/mở lại [A]

- **Làm:** next-action list, người cần trả lời, hạn nội bộ, log chuyển giao/nhận/feedback, lý do đóng; thao tác reopen. Thông tin model/token để ở trang kỹ thuật, không lấn màn hình công việc.
- **Bàn giao:** screens/workflow scenarios cho 2 và 3; ghi nhận vấn đề người dùng coi “xong” khác status kỹ thuật.
- **Phụ thuộc:** API `R2-2-06`; mẫu nội dung của 3. Flow/UI skeleton làm song song ngay sau contract.
- **Nghiệm thu:** người dùng phân biệt xuất/gửi/nhận/đóng; thiếu biên nhận không có badge received; công việc chờ bên ngoài có owner/next action; reopen không mất lịch sử. **Review:** 2 state integrity, 3 workflow.

#### R2-4-06 — Generated types, error states và kiểm UI tích hợp [A]

- **Làm:** sinh client types theo OpenAPI của 2, không tự sửa generated output; kiểm quyền/loading/empty/partial/error/conflict/mode; bàn phím và màn hình hẹp; ổn định luồng E2E với real backend và nguồn thật có kiểm soát. Replay/synthetic chỉ kiểm kỹ thuật.
- **Bàn giao:** integration scenarios và lỗi tái lập cho 1/2/3; ghi commit/API/data version. Sửa UI thuộc 4, lỗi API/analysis chuyển đúng owner.
- **Phụ thuộc:** `R2-2-01/02/05/06/07`, môi trường `R2-1-06`; không đợi B/C để kiểm A.
- **Nghiệm thu:** không crash khi thiếu field cho phép; conflict có cách phục hồi; mock mode không bị nhận nhầm là live; thao tác trên màn hình hẹp không mất nội dung/nguồn. **Review:** 2 integration, 3 source presentation.

#### R2-4-07 — Evaluation, pilot, tài liệu và demo [A; baseline chuẩn bị ngay]

- **Làm:** chuẩn bị đo trước/sau, active time và waiting time riêng; đánh giá chất lượng theo rubric 3, lưu lỗi/số lần sửa và khả năng hoàn thành công việc. Tổ chức buổi thử với reviewer thật và báo cáo giới hạn; làm demo một yêu cầu E2E, không ghép clip mock thành bằng chứng pilot.
- **Bàn giao:** protocol/baseline template từ đầu; evaluation report/demo/run instructions khi tích hợp xong; issue list có owner cho cả nhóm.
- **Phụ thuộc:** `R2-3-07` rubric/labels, `R2-2-08` runner, `R2-1-06/07` môi trường; BV/reviewer cho pilot. Không chờ agent để chuẩn bị protocol hoặc thu baseline.
- **Nghiệm thu:** report tách dữ liệu nguồn thật/test synthetic/hồ sơ BV; denominator/sample và thời gian chờ rõ; chưa có clinical review không báo clinical pass; không cam kết accuracy/15 phút thiếu baseline. **Review:** 3 metrics/clinical errors, 1 reproducibility, 2 runner.

#### R2-4-08 — Timeline ADR, mẫu báo cáo và cập nhật an toàn [B/C]

- **Làm B:** nhiều thuốc/lab/timeline, nguyên nhân thay thế, checklist/unknown, mẫu báo cáo nháp, log bổ sung cùng ca. **Làm C:** hàng chờ nguồn đổi, phiếu tác động, kho phản hồi có trạng thái cần rà soát.
- **Bàn giao:** UI theo contract từng lát cắt và E2E scenarios cho 2/3.
- **Phụ thuộc:** B `R2-2-09`, `R2-3-06`, `R2-1-05`; C `R2-1-08`, `R2-3-08`, update APIs. Không tự thêm ROR dashboard hoặc thang causality để lấp màn hình.
- **Nghiệm thu:** timeline không tạo giờ giả; chuyên viên chọn/giải thích assessment; ca bổ sung không tăng ca mới; thiếu danh mục/scope hiện unknown. **Review:** 3 nghiệp vụ, 2 API, 1 data.

## 16. Phụ thuộc, thứ tự làm và cách tránh chờ Người 2

### 16.1 Những việc bốn người có thể bắt đầu ngay

| Người | Việc không phải chờ API/agent mới | Việc chưa thể nghiệm thu cuối |
|---|---|---|
| 1 | Manifest/source smoke; data inventory; mẫu import; provenance; runbook staging/backup khung | Migration nghiệp vụ thật chờ contract nhỏ; release chờ code tích hợp và review |
| 2 | Contract tối thiểu, adapter interfaces, permission matrix, harness; thiết kế WorkItem wrapper giữ MVP | Agent live cần source và rubric; E2E cần UI/storage; clinical pass cần reviewer |
| 3 | Rubric, template, mapping rules, extraction trên snapshot, annotation guide | Evaluation chuyên môn chờ reviewer/ca được phép; case reporting chờ SOP |
| 4 | Prototype, walkthrough, field map, baseline protocol, UI với examples sau contract | Nối thật chờ endpoint tương ứng; pilot chờ chuyên viên và môi trường |

**Điểm chờ 2 là contract nhỏ ban đầu và từng API cần tích hợp, không phải toàn bộ backend.** Ngược lại 2 cũng cần 1 nguồn/persistence, 3 rubric/output và 4 xác nhận trải nghiệm. Không quy toàn bộ chậm trễ cho một người chỉ vì API là điểm nối.

### 16.2 Các gói bàn giao bắt buộc

| Gói | Bên giao → bên nhận | Nội dung đủ để bên nhận tiếp tục | Điều kiện chấp nhận |
|---|---|---|---|
| H0 — yêu cầu và field glossary | 3+4, 1 constraints → 2 | Flow DI, tiếp nhận ADR ngắn, trường unknown, mẫu output, data/provenance constraints | Không đòi điểm ca/ROR để tiếp nhận; có ví dụ thiếu thông tin |
| H1 — contract lát cắt A | 2 → 1/3/4 | OpenAPI/schema/version, JSON examples success/error/partial, state transitions, source adapter/node interfaces | Mỗi người đọc/render/parse được examples; có owner và compatibility notes |
| H2 — dữ liệu/nguồn | 1 → 2/3/4 | Payload thật, manifest, metadata product/version/date/coverage, source failure cases | Hash và định danh đúng; không gọi snapshot replay là fetch live |
| H3 — nội dung thẩm định | 3 → 2/4 | Evidence/scope/gap/statement output, template/validator, rubric | Interface khớp H1; phần chưa biết không bị bịa; source links kiểm được |
| H4 — API theo lát cắt | 2 → 4, 1 đối chiếu storage | Endpoint hoạt động, examples, version/error/auth, link tới run trace | Không chỉ endpoint stub; behavior khớp H1; persistence test trên migration thật |
| H5 — UI tích hợp | 4 → 2/3/1 | Một đường đi E2E, cases lỗi/quyền, UI build và API version | Không gọi mock khi trình diễn real mode; lỗi tái lập có owner |
| H6 — release candidate | 1+2+3+4 → pilot | SHA/code/data/config, smoke/restore, review ledger và hướng dẫn | Technical checks xong; giới hạn chưa nghiệm thu ghi rõ; có người duyệt chuyên môn |

Mỗi gói kèm checklist “đã có/chưa có”, link artifact, người nhận kiểm và lỗi còn mở. Thay contract phải báo người tiêu thụ trước khi merge. Không để người 4 tự đoán field, người 3 tự trả shape mới, hay người 1 tự đổi schema khiến người 2 xử lý lỗi ở cuối.

### 16.3 Triển khai theo đợt bàn giao, không theo bốn module tách rời

| Đợt | Người 1 | Người 2 | Người 3 | Người 4 | Gate trước đợt tiếp |
|---|---|---|---|---|---|
| 0 — chốt lát cắt nhỏ | Inventory/provenance/storage constraints | H1 contract A tối thiểu | H0 rubric/fields/template nháp | H0 flow/form/protocol | Bốn bên xác nhận H1; chưa cần agent hoàn chỉnh |
| 1 — tiếp nhận/làm rõ | Persistence WorkItem/mapping | Request API + owner/version | Normalize/gaps rules | Inbox/form/context | Tạo→lưu→mở lại→bổ sung hoạt động với DB/API thật |
| 2 — bằng chứng/thẩm định | SourceResult live/snapshot và coverage | Planner/runner/checkpoint | Extraction/scope/citations | Evidence table/source pane | Một câu hỏi dùng nguồn thật; khác scope và nguồn lỗi hiện đúng |
| 3 — trả lời/theo dõi | Response/FollowUp storage | Draft/review/export/followup APIs | Nội dung/validator/annotation | Editor/review/followup | Một yêu cầu A E2E; version và gửi/nhận/đóng không bị gộp |
| 4 — release/pilot A | Staging/smoke/restore | Integration faults/budget/quyền | Reviewer content/adjudication | Pilot/report/demo | Technical pass và clinical/user acceptance được ghi riêng |
| 5 — ADR B | Case/document storage theo quyền | Case API/workflow | Rubric/mẫu ca theo SOP | Timeline/report/update UI | Có SOP/ca được phép; ca thật được chuyên viên review |
| 6 — cập nhật C | ChangeSet/danh mục | Impact/reuse workflow | Nội dung impact/review rules | Update queue/library | Local impact có căn cứ; quyết định/hành động truy được |

Đợt 1 và chuẩn bị đợt 2 có thể song song sau H1. Không mở B/C đến mức làm chậm đường DI A. Không đưa ngày/tuần cố định khi chưa có capacity và reviewer; ước lượng sau khi từng owner đọc phạm vi, báo effort và các phụ thuộc đang thiếu.

### 16.4 Nếu một người hoặc bên ngoài chưa bàn giao

- **2 chưa có H1:** 1 tiếp tục nguồn/inventory; 3 tiếp tục rubric/annotation; 4 tiếp tục flow/prototype/baseline. 2 ưu tiên giảm contract xuống lát cắt A và chốt examples, không mở thêm tính năng.
- **2 có H1 nhưng API chưa chạy:** 4 phát triển với contract examples có nhãn development; 1/3 kiểm module riêng. Khi báo tiến độ phải ghi “chưa tích hợp API”, không coi UI mock là E2E done.
- **1 chưa có live connector:** 2/3/4 tích hợp replay snapshot thật có provenance; đánh dấu replay. Gate live chưa đạt; không dùng replay để tuyên bố nguồn live thành công.
- **3 chưa có clinical labels:** 1/2/4 hoàn thành kỹ thuật/citation trace theo rubric nháp. Không tự tạo gold hoặc gán clinical pass. Giảm scope pilot tới câu hỏi có reviewer sẵn.
- **4 chưa xong UI:** 1/2/3 dùng API harness kiểm persistence/evidence/response; technical integration có tiến triển, nhưng workflow người dùng chưa nghiệm thu.
- **BV chưa giao SOP/ca/danh mục:** tiếp tục DI nguồn công khai và các test synthetic ghi nhãn; giữ case/impact ở mức proposal. Không đánh giá bệnh nhân hoặc báo cáo chính thức từ dữ liệu tưởng tượng.

## 17. Quyền sở hữu và quy tắc tích hợp để hạn chế conflict

Các đường dẫn dưới đây đối chiếu repo hiện tại. Tên model/tài liệu mới trong mục 15 là **đề xuất**, chưa được tạo thành tính năng chỉ vì xuất hiện trong kế hoạch.

| Vùng | Owner | Người phối hợp / quy tắc |
|---|---|---|
| `src/models/schemas.py`, public contract/OpenAPI, `src/agents/graph.py`, state, API routes | 2 | 1/3/4 đề xuất field qua contract; chỉ owner merge thay đổi giao tiếp sau consumer review |
| `src/services/store.py`, migrations, sources/snapshots, config/env, backend locks, Docker/CI | 1 | 2 chốt service/repository interface; source metadata 3 xem; không để hai người đồng thời sửa store transaction theo hai hướng |
| `src/services/evidence/*`, normalization/extraction/scope/contradiction/citation, nội dung template/rubric | 3 | 2 sở hữu integration/graph; 3 không tự đổi public API shape; 4 phản hồi về cách hiểu output |
| `src/services/dossier.py`, review/export điều phối và policy boundary | 2 tích hợp, 3 nội dung | Định rõ nội dung template/validator do 3, orchestration/version/quyền do 2; PR nhỏ theo seam, tránh hai người cùng sửa toàn tệp |
| `frontend/app/*`, components, `frontend/lib/api/*`, `frontend/generated/api-types.ts`, frontend locks | 4 | Types sinh từ contract 2; không sửa generated file để che lỗi API; 3 review wording/source presentation |
| Corpus/benchmark annotation và evaluation | 3 nhãn/rubric; 4 protocol/report; 1 dữ liệu; 2 runner | Nguồn/nhãn/metric/code version ghi riêng. Person 3 sign-off kỹ thuật nội bộ không thay chữ ký reviewer hành nghề |
| Runbook/release/demo | 1 deploy; 4 hướng dẫn người dùng/demo | 2 xác nhận runtime/API; 3 xác nhận giới hạn chuyên môn được trình bày đúng |

Quy tắc merge đề xuất: branch/PR theo một task hoặc lát cắt nhỏ; nêu contract version và người tiêu thụ; test phần thay đổi + kiểm contract có ý nghĩa; không merge cả bốn branch rất lớn vào cuối. Nhánh chỉ docs/rubric/source packet có thể review độc lập; nhánh contract/API cần consumer review trước tích hợp. Kế hoạch này không tự tạo nhánh, gửi tin, commit hay merge code.

## 18. Định nghĩa “xong”, nghiệm thu và cập nhật tiến độ

### 18.1 Ba mức xong phải ghi riêng

1. **DEV_DONE — xong phần riêng:** module có artifact/code, test phù hợp, ghi rõ inputs/outputs, lỗi và giới hạn. Người nhận đọc được handoff. Test synthetic được nhưng có nhãn. Chưa khẳng định E2E.
2. **INTEGRATED — đã nối thật:** chạy với storage/API/UI/analysis của các bên trên cùng contract/SHA; không dùng stub che phần chưa làm; kiểm các failure/version/auth cases liên quan. Nguồn snapshot hay live được ghi chính xác.
3. **PILOT_ACCEPTED — được nghiệm thu sử dụng:** người dùng/reviewer được chỉ định làm tác vụ trên dữ liệu được phép, xem nội dung và output; lưu lỗi quan trọng, thay đổi, quyết định và giới hạn. Chưa có reviewer thì không đạt mức này dù mọi test pass.

“Chờ bên khác” là trạng thái phụ thuộc cho một task cụ thể. Không kết luận cả người đó chưa làm gì hoặc đã xong tất cả. Người 2 có thể DEV_DONE planner nhưng chưa INTEGRATED response vì 3 chưa giao template, hoặc ngược lại; phải ghi task, đầu vào thiếu và người cần giao.

### 18.2 Bộ kiểm nhận bắt buộc cho lát cắt A

| Ca kiểm | Bên chủ trì | Bên cùng kiểm | Kỳ vọng |
|---|---|---|---|
| Tạo DI thiếu thông tin; bổ sung và mở lại sau restart | 2 | 1/4, 3 fields | Không bịa context; lưu dữ liệu/owner/history; biết việc tiếp theo |
| Pantoprazole tiêm vs viên | 1 | 3 mapping, 2/4 luồng chọn | Không auto-match sai dạng/đường; version/date đúng |
| FQ: nghiên cứu UTI vs comparator khác | 3 | 2 synthesis, 4 presentation | Giữ indication/comparator/coverage; không vote-count hoặc false direct conflict |
| Nguồn 404/timeout/abstract-only | 1 | 2 recovery, 3 evidence, 4 UI | Failure/partial khác negative evidence; user biết phần chưa đọc |
| Quote locator đúng nhưng nhận định không được hỗ trợ | 3 | 2 validator, 4 inspector | Technical quote match không tạo clinical correctness giả |
| Duyệt rồi đổi scope/statement/nguồn trọng yếu | 2 | 3 policy, 4 UI, 1 persistence | Bản mới cần review; bản cũ truy được; stale approval không được dùng như hiện hành |
| Export chưa gửi; gửi chưa nhận; đóng/mở lại | 2 | 4 E2E, 3 workflow | Bốn trạng thái/action riêng; không có biên nhận giả |
| Người không có quyền và hai phiên cập nhật | 2 | 1 isolation, 4 handling | API từ chối quyền; version conflict không mất thay đổi |
| Backup/restore và fixture-mode gate | 1 | 2 runtime, 4 E2E | Đúng hồ sơ/version; pilot không tự fallback mock |
| Người nhận hiểu và dùng phiếu trả lời | 4 | Dược sĩ pilot, 3 content | Review câu trả lời/giới hạn; ghi mức sửa và lỗi; không lấy tính đẹp làm kết quả chuyên môn |

Các ca source công khai là kiểm thử có căn cứ nguồn, **chưa phải clinical gold**. Ca update/version/quyền có thể dùng synthetic có nhãn cho kiểm kỹ thuật. Nghiệm thu cá thể ADR và hồ sơ BV cần dữ liệu ca được phép và reviewer thật.

### 18.3 Mẫu cập nhật tiến độ cho từng task

`Task ID | Owner | Trạng thái (TODO/DOING/WAITING/DEV_DONE/INTEGRATED/PILOT_ACCEPTED) | Artifact/SHA | Đã kiểm gì, bằng data nào | Thiếu đầu vào gì | Ai giao/ai nhận | Việc có thể làm tiếp | Người review/kết quả`.

Ví dụ **minh họa cách ghi, không phải tiến độ thật**: `R2-4-03 | 4 | WAITING | UI branch… | render contract examples | thiếu checkpoint endpoint R2-2-04 | 2→4 | tiếp tục source pane/error states | 3 đã xem wording, chưa E2E`.

Mỗi phụ thuộc có một owner phía giao, một người phía nhận và artifact cụ thể. Nếu task đã DEV_DONE nhưng chờ tích hợp, owner vẫn hỗ trợ consumer xử lý lỗi thuộc interface của mình; không đóng việc chỉ bằng câu “code xong”.

## 19. Việc tiếp theo riêng của bạn — Người 2

1. **Nhận H0 từ 1/3/4 và chốt R2-2-01 trước:** chỉ contract của DI, tiếp nhận ADR ngắn, evidence, response và follow-up. Phát schema/examples sớm để 1 làm persistence, 3 làm output và 4 làm UI; chưa cần hoàn thiện graph mới.
2. **Làm R2-2-02 cùng storage của 1:** một yêu cầu tạo được, lưu được, làm rõ được và gắn engine MVP. Mời 4 nối form ngay khi endpoint này chạy; không chờ mọi endpoint.
3. **R2-2-03/04 cùng 1+3:** planner nhận bối cảnh, source có provenance, analysis giữ applicability; có checkpoint/gaps/resume. 4 tích hợp evidence pane cùng thời điểm.
4. **R2-2-05/06:** dùng template/validator của 3 để draft/review/export, rồi phản hồi/theo dõi. Quyền/version của R2-2-07 triển khai cùng từng API, không dồn cuối.
5. **R2-2-08 và gate A với cả nhóm:** xử lý lỗi tích hợp/timeout/budget, xác nhận đúng mode, smoke trên staging của 1 và luồng UI của 4; 3/chuyên viên kiểm nội dung.
6. **Chỉ sau đó mở R2-2-09 B/C:** mở case/update contract khi có SOP/data/reviewer. Không tự ôm mapping lâm sàng, annotation, deploy và UI; đó vẫn là đầu việc 1/3/4 như phân công cũ.

Bạn cần bàn giao sớm **contract và từng API nhỏ**; bạn cần nhận lại **nguồn/storage từ 1, rubric/nội dung từ 3, flow và lỗi UX từ 4**. Khi thiếu một đầu vào, ghi đúng task và tiếp tục phần độc lập. Chưa có dữ liệu bệnh viện/reviewer là phụ thuộc bên ngoài của cả nhóm, không phải việc Người 2 tự giải quyết bằng thêm agent.

## 20. Nhật ký tiến độ thực thi (cập nhật 05/10/2026)

Tiến độ thật của từng task `R2-1-*`, `R2-2-*`, `R2-3-*`, `R2-4-*` được ghi tại
[`TIEN_DO_THUC_THI.md`](TIEN_DO_THUC_THI.md) theo đúng mẫu 18.3, kèm artifact, lệnh kiểm chứng và danh sách
việc còn thiếu. Tài liệu mô tả dữ liệu thật (nguồn, tiền xử lý, cổng chất lượng, cấu trúc kho) nằm trong
[`docs/data/`](../data/README.md).

Tóm tắt đợt này (chi tiết và bằng chứng trong nhật ký):

- **Dữ liệu và kho:** dựng xong pipeline ELT (PubMed, DailyMed, FAERS, gói 50 mẫu, gói tham chiếu) với
  manifest ghi URL/tham số/mã HTTP/số byte/sha256; nạp 66 tài liệu vào PostgreSQL `vigilens_elt` (cổng 5433)
  và 1.832 đoạn vào ChromaDB; kiểm chứng 30/30 băm văn bản khớp gói đã phát hành.
- **API kho:** thêm 7 điểm cuối (`/api/v1/drugs/lookup`, `/warehouse/*`, `/rag/search`, `/ingestion/*`)
  có phân quyền theo vai trò, mã lỗi rõ ràng và tự hạ cấp sang từ điển tĩnh khi PostgreSQL chưa chạy.
- **Tái lập một lệnh:** `scripts/setup_elt.sh` (tạo venv, cài phụ thuộc, dựng PostgreSQL, tải dữ liệu,
  nạp kho, dựng chỉ mục, kiểm tra, sinh tài liệu) chạy lại nhiều lần không lỗi.
- **Kiểm thử:** 32 bài kiểm thử ngoại tuyến mới cho cổng chất lượng, bộ phân tích, kho, RAG và API.
- **Sự cố đã sửa:** 6 lỗi được ghi ở mục 1.1 của nhật ký, gồm lỗi chạy lại ELT vi phạm khoá ngoại và
  lỗi đọc nhầm cột khi dùng `engine.connect()` với ORM.
- **Còn thiếu:** chuẩn vàng, dữ liệu bệnh viện, dược sĩ duyệt, nối RAG vào agent — ghi rõ ở mục 6 nhật ký,
  **không** coi là đã nghiệm thu.
