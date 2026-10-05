# Phiếu giao việc vòng hai — Người 1

Đề xuất ngày 05/10/2026. Bản trích để nhận việc; cập nhật kế hoạch tại [báo cáo chính](../NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). Đọc thêm mục 16–18 trong báo cáo để biết handoff, thứ tự tích hợp và ba mức nghiệm thu. A = DI/tiếp nhận ADR ngắn; B = ca ADR đầy đủ; C = cập nhật/tái sử dụng. B/C phụ thuộc dữ liệu/SOP/reviewer; không chặn lát cắt A.

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
