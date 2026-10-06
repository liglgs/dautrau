# Chuẩn vàng giai đoạn 1 — phương pháp, số liệu và giới hạn

**Ngày:** 2026-10-06 · **Trạng thái:** `candidate_not_gold` (máy đề xuất, chưa có dược sĩ duyệt)
**Tệp dữ liệu:** `data/gold/drug-event-pairs.jsonl` (300 cặp) · **Đặc tả:** `data/gold/spec.json` · **Băm và thống kê:** `data/gold/manifest.json`
**Cách dựng:** `python -m scripts.gold.build_gold_dataset [--force|--offline]`

## 1. Mục tiêu

Bộ dữ liệu này là **chuẩn vàng ứng viên** cho bài toán kiểm chứng an toàn thuốc: mỗi dòng là một cặp
thuốc–biến cố bất lợi, kèm bằng chứng nhãn thuốc (có URL và câu trích) và số liệu báo cáo FAERS.
Quyết định thiết kế: dựng từ **nguồn công khai quốc tế trước** (dùng được ngay, kiểm chứng được bằng
URL), mở rộng sang tiếng Việt ở giai đoạn 2 khi có nguồn và người duyệt.

## 2. Phương pháp

1. **Ma trận cố định:** 30 hoạt chất × 10 biến cố bất lợi nghiêm trọng = 300 cặp. Cặp âm tính sinh tự
   động từ ma trận, không lấy từ output của hệ thống (tránh thiên lệch lựa chọn).
2. **Bằng chứng nhãn:** truy vấn openFDA Drug Label API theo tên chung; ưu tiên nhãn **một hoạt chất**
   (bỏ qua thuốc phối hợp như "ASPIRIN AND DIPYRIDAMOLE"), chọn nhãn có `effective_time` lớn nhất.
   Khớp từ đồng nghĩa không phân biệt hoa thường trong sáu mục an toàn: `boxed_warning`,
   `contraindications`, `warnings`, `warnings_and_cautions`, `precautions`, `adverse_reactions`.
   Ghi lại mục khớp, từ khớp và **câu trích nguyên văn**.
3. **Số liệu FAERS:** hai truy vấn đếm cho mỗi cặp (mẫu số theo hoạt chất, tử số theo hoạt chất + PT).
   HTTP 404 của openFDA được ghi là "không có kết quả" (0 báo cáo) kèm ghi chú, không phải lỗi.
4. **Chia tập theo hoạt chất** (tránh rò rỉ): 20 hoạt chất → `development` (200 cặp), 10 hoạt chất → `test` (100 cặp).
5. **Không bịa dữ liệu:** thiếu nhãn ⇒ `no_label` và `gold_label = null`; lỗi mạng ⇒ dừng và ghi lỗi vào
   `manifest.errors`, không sinh nhãn âm tính giả.

## 3. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Tổng số cặp | 300 |
| Nhãn dương tính (`label_listed`) | 159 (53,0%) |
| Nhãn âm tính (`label_not_listed`) | 141 (47,0%) |
| Không tìm thấy nhãn (`no_label`) | 0 |
| Nhãn không có mục an toàn (`no_section`) | 0 |
| Lỗi mạng | 0 |
| Nhãn khác nhau được dùng | 30 |
| Chia tập | development 200 · test 100 |

Phân bố theo biến cố (dương tính / âm tính):

| Biến cố | Dương | Âm |
|---|---|---|
| Anaphylaxis (PT: `ANAPHYLACTIC REACTION`) | 24 | 6 |
| Stevens-Johnson syndrome | 22 | 8 |
| Acute kidney injury | 21 | 9 |
| Hepatotoxicity | 20 | 10 |
| Agranulocytosis | 19 | 11 |
| Pancreatitis | 19 | 11 |
| Angioedema | 17 | 13 |
| Gastrointestinal haemorrhage | 8 | 22 |
| Rhabdomyolysis | 5 | 25 |
| QT prolongation | 4 | 26 |

Mục nhãn khớp: `adverse_reactions` 74 · `warnings_and_cautions` 38 · `contraindications` 20 ·
`warnings` 16 · `boxed_warning` 7 · `precautions` 4.

## 4. Phát hiện kỹ thuật đáng ghi nhớ

- **`ANAPHYLAXIS` không phải PT của MedDRA.** Cả 30 truy vấn FAERS với chuỗi này trả HTTP 404. PT đúng
  là `ANAPHYLACTIC REACTION` (kiểm chứng 2026-10-06: ibuprofen + PT này = 2.163 báo cáo). Đặc tả đã
  ghi lại lý do sửa; trường `meddra_pt_note` giữ dấu vết.
- **openFDA trả HTTP 404 khi truy vấn không khớp bản ghi nào.** Bộ dựng coi 404 là "0 kết quả" kèm ghi
  chú, và vẫn lưu bản thô để chạy lại offline.
- **Thuốc phối hợp lẫn trong kết quả theo tên chung.** Ví dụ truy vấn `aspirin` trả về nhãn
  "ASPIRIN AND EXTENDED-RELEASE DIPYRIDAMOLE". Nếu không lọc, quy kết thuốc–biến cố bị mờ.
- **Chạy lại offline cho kết quả trùng khớp:** với 360 bản thô đã lưu, `--offline` dựng lại đúng tệp mà
  không gọi mạng (đã kiểm chứng trong lần dựng này).

## 5. Giới hạn (giữ nguyên trong từng bản ghi)

1. **Nhãn do máy đề xuất.** Chưa có dược sĩ/chuyên gia cảnh giác dược duyệt. Trạng thái mỗi dòng là
   `candidate_not_gold`; trường `review.approval_required` ghi rõ ai phải duyệt.
2. **Dương tính ≠ nhân quả.** "Được nhãn nêu tên" là bằng chứng văn bản, không phải bằng chứng quan hệ
   nhân quả hay tần suất.
3. **Âm tính ≠ an toàn.** Biến cố có thể được nêu ở mục khác không kiểm tra, hoặc trong nhãn khác của
   cùng hoạt chất. Mọi bản ghi đều ghi danh sách mục đã kiểm tra.
4. **Chỉ nhãn Hoa Kỳ.** Chưa đối chiếu với tờ hướng dẫn sử dụng thuốc của Việt Nam.
5. **FAERS không có mẫu số.** Số báo cáo tự nguyện, có trùng lặp, không dùng để tính tỉ lệ mắc.
6. **Ảnh chụp theo thời điểm.** Nhãn và số FAERS thay đổi theo thời gian; `retrieved_at` và băm bản thô
   cho phép truy vết nhưng không bảo đảm tái lập sau này nếu không có `raw/`.
7. **Chưa có MedDRA.** Chuỗi PT chưa đối chiếu từ điển có bản quyền; chỉ kiểm chứng bằng việc chuỗi đó
   có xuất hiện trong dữ liệu FAERS (`term_observed`).
8. **Chưa bao phủ tiếng Việt.** Giai đoạn 2 mới bổ sung nguồn Việt Nam (xem khảo sát bộ dữ liệu).

## 6. Quy trình duyệt đề xuất

1. Dược sĩ mở `label_url` từng dòng, đối chiếu `matched_quote` với `matched_section`; kiểm tra `label_title`
   có đúng hoạt chất (không phải thuốc phối hợp).
2. Sửa nhãn sai; ghi `review.reviewer_id`, `review.reviewed_at`, `review.notes`; đổi `review.status`
   thành `expert_reviewed`.
3. Hai người duyệt độc lập cho các dòng thuộc tập `test`; bất đồng do người thứ ba phân xử (ghi lý do).
4. Chỉ khi toàn bộ dòng đã duyệt mới chuyển `manifest.status` sang `gold` và đóng băng băm.

## 7. Liên hệ với các tài liệu khác

- Khảo sát bộ dữ liệu 20+ quốc gia: `docs/data/khao-sat-bo-du-lieu-canh-giac-duoc-2026-10.md`.
- Gói 50 mẫu ứng viên hiện có (5 cặp, 50 tài liệu): `data/benchmark/README.md` — vẫn là
  `draft_not_frozen_not_gold`, độc lập với bộ 300 cặp này.
- Kho ELT và chỉ mục RAG: `docs/data/cau-truc-kho.md`, `docs/data/nguon-du-lieu.md`.
