# Danh mục nguồn dữ liệu

Mọi nguồn dưới đây đều được **tải thật** và ghi lại dấu vết trong
`data/elt/manifests/<run_id>.json` (URL, tham số, HTTP status, số byte, `sha256`, thời điểm).

Ba nguồn API chính phục vụ ba mục đích khác nhau. Không nguồn nào thay thế được nguồn khác.

## 1. PubMed (E-utilities) — tra cứu bằng chứng

| Mục | Giá trị |
| --- | --- |
| Điểm cuối | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi` (`db=pubmed`, `retmode=xml`) |
| Khoá | `NCBI_API_KEY` (tuỳ chọn, tăng hạn mức); `NCBI_EMAIL` khai báo trong `.env` |
| Nhịp gọi | 0,35 giây/lần (có khoá API), có `tool=vigilens-elt` |
| Nội dung lấy | tiêu đề, tạp chí, ngày công bố, loại công bố, DOI, tác giả, **tóm tắt** |
| Mức nội dung ghi vào kho | `abstract_only` |
| Bản ghi đi kèm | bảng `pubmed_records` |

**Trả lời được:** có nghiên cứu nào bàn về cặp thuốc–biến cố này không; thiết kế nghiên cứu là gì;
có tóm tắt để trích dẫn nguyên văn không.

**Không trả lời được:** toàn văn bài báo; chất lượng từng nghiên cứu (cỡ mẫu, nguy cơ sai lệch,
chỉnh nhiễu) — cổng chất lượng chỉ kiểm tra *có tóm tắt*, *có tạp chí*, *có bị rút*,
chứ **không** xếp hạng bằng chứng. Vì vậy kết luận của sản phẩm phải nêu rõ "chưa đánh giá chất lượng nghiên cứu".

## 2. DailyMed (NLM) — đối chiếu nhãn thuốc

| Mục | Giá trị |
| --- | --- |
| Điểm cuối | `https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name=...` và `.../spls/{setid}.xml` |
| Nội dung lấy | các mục nhãn SPL: chỉ định, liều, cảnh báo, tác dụng không mong muốn, tương tác |
| Định danh bắt buộc | `SETID` + `version` (ghi vào `dailymed_labels`) |
| Mức nội dung | `label_sections` |

**Trả lời được:** nhãn đã đăng ký của sản phẩm nói gì về biến cố này; cảnh báo nằm ở mục nào;
phiên bản nhãn nào đang được đối chiếu.

**Không trả lời được:** sản phẩm đó có được lưu hành ở Việt Nam hay không; nhãn có được FDA phê duyệt
đầy đủ hay chỉ là nhãn lưu hành; nội dung cảnh báo **vừa mới đổi** — thời điểm `published_date` khác
`effectiveTime` của SPL (ví dụ nhãn pantoprazole `6faf465b-…` v22 có `published_date` 29/09/2026
nhưng `effectiveTime` 19/09/2024). Vì vậy UI hiển thị **cả hai mốc thời gian** và ghi rõ chưa đối chiếu
danh mục lưu hành Việt Nam.

**Kiểm soát chất lượng riêng:** chỉ nhận nhãn **một hoạt chất** và **đường uống** cho bộ ứng viên
(`single_ingredient`, `oral`); nhãn nhiều hoạt chất bị cách ly chứ không bị loại (vẫn có thể là bằng chứng nền).

## 3. openFDA FAERS — báo cáo nghi ngờ ADR

| Mục | Giá trị |
| --- | --- |
| Điểm cuối | `https://api.fda.gov/drug/event.json?search=safetyreportid:"<id>"&limit=1` |
| Truy vấn theo cặp | `search=(patient.drug.openfda.generic_name:"<hoạt chất>"+AND+patient.reaction.reactionmeddrapt:"<biến cố>")` |
| Nội dung lấy | `safetyreportid`, ngày nhận, quốc gia, tuổi/giới, danh sách thuốc, danh sách phản ứng, cờ `serious` |
| Mức nội dung | `spontaneous_report` |

**Trả lời được:** có báo cáo nghi ngờ nào trên thực tế cho cặp thuốc–biến cố này không;
báo cáo đến từ đâu, nghiêm trọng hay không, kèm thuốc nào khác.

**Không trả lời được (đã kiểm chứng trên mẫu thật 15 báo cáo / 182 dòng thuốc):**

| Hạn chế | Bằng chứng đo được |
| --- | --- |
| Một báo cáo thường có nhiều thuốc | 14/15 báo cáo có nhiều thuốc → không ánh xạ chắc cặp thuốc–biến cố |
| Thiếu ngày bắt đầu dùng thuốc | 157/182 dòng thuốc thiếu ngày bắt đầu |
| Thiếu thông tin bệnh nhân | 2 báo cáo thiếu tuổi, 1 báo cáo thiếu giới tính |
| Báo cáo dài | văn bản dài nhất 172.081 ký tự (giới hạn cổng chất lượng 200.000) |
| Nhân quả chưa xác nhận | mọi báo cáo gắn cờ `suspicion_not_causality` |
| Không có lịch sử xử lý của dược sĩ | nguồn không cung cấp |

→ **FAERS chỉ dùng làm bối cảnh phát hiện vấn đề.** Không hiển thị số báo cáo như tỷ lệ mắc,
không suy ra nhân quả, không dùng làm kết luận.

## 4. Gói 50 mẫu đã đóng băng (`mvp-candidates-50-2026-10-02`)

| Mục | Giá trị |
| --- | --- |
| Nguồn | `https://drive.google.com/drive/folders/1G4Xd-Nve_Zs0IN3Eu5Xngrb56uSA1hu-` (tải bằng `gdown`) |
| Tệp | `data/mvp-candidates-50-2026-10-02.zip`, 1.153.367 byte |
| `sha256` | `6fbcfd1970318cb0562e6b260be1da6cfe783c8b9961ddb923a59d0195ad66f7` |
| Kiểm tra toàn vẹn | 44/44 mục trong `files.sha256.json` khớp |
| Nội dung | 5 cặp thuốc–biến cố × (5 PubMed + 2 DailyMed + 3 FAERS) = 50 tài liệu, kèm `review.jsonl` |

**Trạng thái:** `candidate_not_gold`, `review_decision: pending`, `gold_label: null`.
Gói này là **bộ ứng viên**, chưa phải chuẩn vàng và chưa được dùng để chấm điểm.

**Kiểm chứng băm hai chiều:** phân tích lại 30 tệp thô bằng chính bộ phân tích của ứng dụng
cho ra đúng `sha256` văn bản trong JSON đã phát hành — 30/30 khớp, 0 lệch.

## 5. Gói tài liệu tham chiếu (`docs/research/2026-10-05/data-real`)

6 tài liệu **không phải bằng chứng chính**, gắn cờ `reference_material_not_primary_evidence`:

| Tệp | Loại | Dùng để |
| --- | --- | --- |
| `vn-adr-2024.html`, `vn-adr-2025.html` | bản tin cảnh giác dược quốc gia | bối cảnh hoạt động ADR tại Việt Nam |
| `vn-latest-bulletin-index.html` | mục lục bản tin | tra cứu bản tin |
| `openfda-event-docs.html` | tài liệu mô tả nguồn | giải thích giới hạn FAERS |
| `who-umc-causality.pdf` | hướng dẫn đánh giá ca | khung đánh giá nhân quả |
| `adr-cognitive-task-study.txt` | nghiên cứu quy trình | mô tả bối cảnh công việc |

Không dùng nhóm này để kết luận về thuốc–biến cố.

## 6. Nguồn đã thử nhưng chưa lấy được

- **Quyết định 29/QĐ-BYT** (giám sát ADR tại cơ sở khám chữa bệnh): trang của Trung tâm DI & ADR Quốc gia
  chặn truy cập tự động. **Chưa xác nhận** mẫu biểu, thời hạn và tình trạng pháp lý → không mã hoá vào sản phẩm,
  cần lấy bản hiện hành từ đầu mối bệnh viện.
- **Dữ liệu lưu hành thuốc tại Việt Nam** (Danh mục đăng ký): chưa có nguồn mở ổn định → chưa đối chiếu được
  nhãn DailyMed với danh mục Việt Nam.
- **Chuẩn vàng lâm sàng cho 5 cặp ứng viên**: chưa có; đang chờ dược sĩ duyệt (`review.jsonl`).

## 7. Bản đồ tệp trong `data/`

```
data/
  elt/dataset-spec.json          # đặc tả bộ dữ liệu: PMID, SETID, safetyreportid của từng cặp
  elt/raw/<host>/...             # phản hồi thô, giữ nguyên byte
  elt/manifests/<run_id>.json    # dấu vết tải: URL, tham số, sha256, số byte, thời điểm
  elt/staging/<run_id>-documents.jsonl  # bản ghi chuẩn hoá trước khi nạp
  elt/reports/<run_id>-quality.{json,md} # kết quả cổng chất lượng
  chroma/                        # chỉ mục vector ChromaDB
  mvp-candidates-50-2026-10-02/  # gói 50 mẫu đã giải nén
```
