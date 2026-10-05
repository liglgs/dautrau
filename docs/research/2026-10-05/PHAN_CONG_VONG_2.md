# Phụ lục phân công vòng hai — bản nguồn để hợp nhất

Nội dung này được ghép vào báo cáo chính, mục 14–19. Báo cáo chính là nơi cập nhật kế hoạch; các phiếu giao việc riêng là bản trích để từng người nhận việc.

## 14. Kết quả thẩm định bản nghiên cứu của agent khác

Đã đọc toàn bộ bản gốc 351 dòng. Bản gốc được giữ tại `research/2026-10-05/archive/agent-original.md` để đối chiếu; **nội dung trong bản lưu không còn là đề xuất được chấp nhận**. Không xác nhận danh xưng chuyên gia tự ghi trong bản đó. Các quyết định dưới đây thay thế các kết luận tương ứng của bản gốc.

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
