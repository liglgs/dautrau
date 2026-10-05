# Phiếu giao việc vòng hai — Người 3

Đề xuất ngày 05/10/2026. Bản trích để nhận việc; cập nhật kế hoạch tại [báo cáo chính](../NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). Đọc thêm mục 16–18 trong báo cáo để biết handoff, thứ tự tích hợp và ba mức nghiệm thu. A = DI/tiếp nhận ADR ngắn; B = ca ADR đầy đủ; C = cập nhật/tái sử dụng. B/C phụ thuộc dữ liệu/SOP/reviewer; không chặn lát cắt A.

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
