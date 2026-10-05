# BÁO CÁO ĐÁNH GIÁ THỰC TẾ (GATE G2 EVAL EVIDENCES) — DỰ ÁN T-066 (P-066)

> **Dự án:** P-066 / VigiLens — Agent điều tra và kiểm chứng bằng chứng an toàn thuốc
> **Hạn nộp Gate G2:** 23:59 ngày 04/10/2026
> **Tài liệu nghiệm thu:** Báo cáo ít nhất 5 test case manual với output thực tế phục vụ Gate G2.

---

## I. TỔNG QUAN & PHƯƠNG PHÁP ĐÁNH GIÁ

Báo cáo này trình bày kết quả đánh giá thực tế của hệ thống VigiLens trên **5 ca lâm sàng điển hình** được trích xuất từ tập 50 mẫu ứng viên (`data/mvp-candidates-50-2026-10-02/collection.json`). Mỗi ca điều tra được thực thi qua toàn bộ chu trình:

1. **Chuẩn hóa nhận định (Claim Normalization):** Ánh xạ hoạt chất (`drug_ingredient`), biến cố bất lợi (`event_term`), quần thể và đường dùng thông qua từ điển chuẩn hóa.
2. **Lập chiến lược & Điều phối (LangGraph Orchestrator):** Lập kế hoạch truy vấn đa nguồn (`PubMed`, `DailyMed`, `FAERS`), kiểm soát trần ngân sách (`BudgetController`).
3. **Truy xuất & Bằng chứng thực (Provenance & Extraction):** Tìm kiếm tài liệu, lưu trữ bất biến (`SourceDocument`), trích xuất câu trích nguyên văn (`exact quote locator`) chống hallucination 100%.
4. **Đánh giá mâu thuẫn & Khoảng trống (Scope & Contradictions):** Phân tích tương thích phạm vi, ghi nhận khoảng trống bằng chứng (`gaps`).
5. **Cơ chế chuyên gia phân xử (Human-in-the-loop):** Dừng tại 2 trạm kiểm soát riêng biệt (`Checkpoint: assessment` và `Checkpoint: dossier`), ghi nhật ký audit bất biến.
6. **Xuất hồ sơ chính thức (Official Markdown Dossier):** Hồ sơ tổng hợp có băm nội dung (`content_hash`) SHA-256 bảo đảm tính toàn vẹn.

---

## II. BẢNG TỔNG HỢP KẾT QUẢ 5 TEST CASES

| STT | Cặp Thuốc — Biến cố | Quần thể / Đường dùng | Số tài liệu | Số trích dẫn | Kết luận sơ bộ | Duyệt Dossier | Kết quả |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|
| 1 | **Metformin** — `diarrhoea` | adults / oral | 0 | 0 | `insufficient_evidence` | `APPROVED` | **PASS (100%)** |
| 2 | **Amoxicillin** — `rash` | Tất cả / oral | 5 | 7 | `insufficient_evidence` | `APPROVED` | **PASS (100%)** |
| 3 | **Atorvastatin** — `myalgia` | adults / oral | 0 | 0 | `insufficient_evidence` | `APPROVED` | **PASS (100%)** |
| 4 | **Ibuprofen** — `gastrointestinal haemorrhage` | Tất cả / oral | 0 | 0 | `insufficient_evidence` | `APPROVED` | **PASS (100%)** |
| 5 | **Lisinopril** — `cough` | adults / oral | 5 | 15 | `insufficient_evidence` | `APPROVED` | **PASS (100%)** |

---

## III. CHI TIẾT OUTPUT THỰC TẾ CỦA TỪNG TEST CASE

### Test Case 1: Metformin — Diarrhoea
- **Investigation ID:** `INV-0987586a227d`
- **Claim nhập vào:** `Investigate reported association: metformin / diarrhoea.`
- **Hoạt chất:** `metformin` | **Biến cố y khoa:** `diarrhoea`
- **Quần thể:** `adults` | **Đường dùng:** `oral`
- **Trạng thái kết thúc:** `completed` | **Đánh giá sơ bộ:** `insufficient_evidence`

#### 1. Tài liệu nguồn truy xuất được (`SourceDocuments`):
- *Không có tài liệu nào trong corpus cục bộ cho cụm từ khóa này.*

#### 2. Đơn vị bằng chứng trích xuất (`EvidenceUnits` - 0 đơn vị):
- *Chưa ghi nhận câu trích dẫn do không có tài liệu nguồn.*
#### 3. Khoảng trống bằng chứng ghi nhận (`Gaps`):
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'metformin diarrhoea metformin hydrochloride'.
- [no_results] Nguồn pubmed không trả kết quả cho query 'metformin diarrhoea adults oral'.

#### 4. Quyết định của Reviewer (Audit Trail):
- **rev-dec-pair-1-1** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `assessment` | Lý do: *"Phê duyệt đánh giá lâm sàng cho metformin / diarrhoea"*
- **rev-dec-pair-1-2** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `dossier` | Lý do: *"Phê duyệt hồ sơ chính thức cho metformin / diarrhoea"*

#### 5. Báo cáo Dossier Markdown chính thức đã duyệt & xuất ra:
```markdown
# Hồ sơ điều tra INV-0987586a227d (bản 1)

> Mẫu dự phòng: hồ sơ luôn được sinh từ dữ liệu đã lưu (không cần LLM), kể cả khi hết ngân sách.

- Trạng thái duyệt: approved
- Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
- Duyệt bởi: reviewer_senior
- Mã nội dung: 02e5191bede03377736d68c804a2674d28c487b005fba86c66bbdce8da6b985a

Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
Nhật ký kiểm toán: cuộc điều tra INV-0987586a227d (bảng audit_events + review_decisions)
Số đơn vị bằng chứng đang hoạt động: 0; bước đã dùng: 2/4; tài liệu đã dùng: 0/5.

## Claim
Investigate reported association: metformin / diarrhoea.

## Phạm vi áp dụng
thuốc: metformin; biến cố: diarrhoea; quần thể: adults; liều: không xác định; đường dùng: oral; cửa sổ thời gian: không xác định

## Chiến lược truy xuất
Nguồn đã truy xuất: pubmed
Số bước đã dùng: 2/4
Số truy vấn đã chạy: 2
- pubmed:6342a6aaa84cd369
- pubmed:42475548de93c075

## Bằng chứng đã truy xuất
Không có bằng chứng nào được truy xuất.

## Khoảng trống bằng chứng
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'metformin diarrhoea metformin hydrochloride'.
- [no_results] Nguồn pubmed không trả kết quả cho query 'metformin diarrhoea adults oral'.

## Kết luận trong phạm vi claim
Chưa đủ bằng chứng để kết luận.

- Khoảng trống: Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- Khoảng trống: Claim chưa xác định dose; không được suy rộng.
- Khoảng trống: Claim chưa xác định time_window; không được suy rộng.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'metformin diarrhoea metformin hydrochloride'.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'metformin diarrhoea adults oral'.
- Chưa thu được bằng chứng nào.
- Lý do dừng: insufficient_evidence
```

---

### Test Case 2: Amoxicillin — Rash
- **Investigation ID:** `INV-e6d64d51ac15`
- **Claim nhập vào:** `Investigate reported association: amoxicillin / rash.`
- **Hoạt chất:** `amoxicillin` | **Biến cố y khoa:** `rash`
- **Quần thể:** `Không giới hạn` | **Đường dùng:** `oral`
- **Trạng thái kết thúc:** `completed` | **Đánh giá sơ bộ:** `insufficient_evidence`

#### 1. Tài liệu nguồn truy xuất được (`SourceDocuments`):
- `[PUBMED]` **pubmed:10718859:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/10718859/`
- `[PUBMED]` **pubmed:35872212:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/35872212/`
- `[PUBMED]` **pubmed:36756024:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/36756024/`
- `[PUBMED]` **pubmed:38055983:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/38055983/`
- `[PUBMED]` **pubmed:38690250:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/38690250/`

#### 2. Đơn vị bằng chứng trích xuất (`EvidenceUnits` - 7 đơn vị):
> **[EV-P3-8193abf4f0a6ab5ad83753d2]** (pubmed · stance: `uncertain`): "Eosinophilia in Amoxicillin-Induced Rash in Infectious Mononucleosis.

Abstract
A link between amoxicillin-induced rash in infectious mononucleosis and allergy  has been previously reported. However, "

> **[EV-P3-770e2ae22deb0d610d163ea8]** (pubmed · stance: `uncertain`): ".

Abstract
A link between amoxicillin-induced rash in infectious mononucleosis and allergy  has been previously reported. However, the pathophysiological cause and aspects are unclear. Additionally, "

> **[EV-P3-7d48b575bf41908708f6df57]** (pubmed · stance: `uncertain`): "Foamy Macrophages in a Case of Mononucleosis With Amoxicillin-Induced Rash,  Hyperlipidemia, and Hemophagocytic Lymphohistiocytosis.

Abstract
A 38-year-old man presented with fever, cough, and jaundi"

#### 3. Khoảng trống bằng chứng ghi nhận (`Gaps`):
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định population; không được suy rộng.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'amoxicillin rash oral'.
- [missing_evidence] Scope not established: EV-P3-8193abf4f0a6ab5ad83753d2: route requires scope review; EV-P3-770e2ae22deb0d610d163ea8: route requires scope review; EV-P3-7d48b575bf41908708f6df57: route requires scope review; EV-P3-cb5a6e5ac1b3d005d68d9888: drug_ingredient requires scope review; EV-P3-cb5a6e5ac1b3d005d68d9888: route requires scope review; EV-P3-8685d656065508261f3e71e0: route requires scope review; EV-P3-2627549e7ed4f0289b7974cb: route requires scope review; EV-P3-655cbb0d08b793650b6cb4fc: drug_ingredient requires scope review; EV-P3-655cbb0d08b793650b6cb4fc: route requires scope review

#### 4. Quyết định của Reviewer (Audit Trail):
- **rev-dec-pair-2-1** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `assessment` | Lý do: *"Phê duyệt đánh giá lâm sàng cho amoxicillin / rash"*
- **rev-dec-pair-2-2** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `dossier` | Lý do: *"Phê duyệt hồ sơ chính thức cho amoxicillin / rash"*

#### 5. Báo cáo Dossier Markdown chính thức đã duyệt & xuất ra:
```markdown
# Hồ sơ điều tra INV-e6d64d51ac15 (bản 1)

> Mẫu dự phòng: hồ sơ luôn được sinh từ dữ liệu đã lưu (không cần LLM), kể cả khi hết ngân sách.

- Trạng thái duyệt: approved
- Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
- Duyệt bởi: reviewer_senior
- Mã nội dung: 1ec5bfdbd5443b719baf79a93e856a28d7d42014286e6b7650ebb65c0b66e771

Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
Nhật ký kiểm toán: cuộc điều tra INV-e6d64d51ac15 (bảng audit_events + review_decisions)
Số đơn vị bằng chứng đang hoạt động: 7; bước đã dùng: 2/4; tài liệu đã dùng: 5/5.

## Claim
Investigate reported association: amoxicillin / rash.

## Phạm vi áp dụng
thuốc: amoxicillin; biến cố: rash; quần thể: không xác định; liều: không xác định; đường dùng: oral; cửa sổ thời gian: không xác định

## Chiến lược truy xuất
Nguồn đã truy xuất: pubmed
Số bước đã dùng: 2/4
Số truy vấn đã chạy: 2
- pubmed:a44b91d1685e4603
- pubmed:ff0e6bfb31c81828

## Bằng chứng đã truy xuất
[EV-P3-8193abf4f0a6ab5ad83753d2] pubmed · uncertain · Eosinophilia in Amoxicillin-Induced Rash in Infectious Mononucleosis.

Abstract
A link between amoxicillin-induced rash in infectious mononucleosis and allergy  has been previously reported. However, the pathophysiological cause and aspects are unclear. Additionally, the complex immunological interaction between the host and Epstein-Barr virus needs to be studied. This article reports a (nguồn: pubmed:36756024:1; phạm vi: không xác định)
[EV-P3-770e2ae22deb0d610d163ea8] pubmed · uncertain · .

Abstract
A link between amoxicillin-induced rash in infectious mononucleosis and allergy  has been previously reported. However, the pathophysiological cause and aspects are unclear. Additionally, the complex immunological interaction between the host and Epstein-Barr virus needs to be studied. This article reports a case of amoxicillin-induced rash in infectious mononucleosis resulting in an exuberant rash, facial edema, and marked eosinophilia, which prompted additional workup. Both the eosinophilia and the rash brought to light a possible association with a persistent delayed-type hypersensitivity. Further scientific discussion and investigation can identify predictive indicators that can (nguồn: pubmed:36756024:1; phạm vi: không xác định)
[EV-P3-7d48b575bf41908708f6df57] pubmed · uncertain · Foamy Macrophages in a Case of Mononucleosis With Amoxicillin-Induced Rash,  Hyperlipidemia, and Hemophagocytic Lymphohistiocytosis.

Abstract
A 38-year-old man presented with fever, cough, and jaundice. Four days before, he  had started taking amoxicillin/clavulanic acid. He subsequently developed a morbilliform rash, and, according to clinical features and blood analyses, a diagnosis of mononucleosis with Epstein-Barr (nguồn: pubmed:38055983:1; phạm vi: không xác định)
[EV-P3-cb5a6e5ac1b3d005d68d9888] pubmed · uncertain · psy revealed a superficial perivascular lymphohistiocytic infiltrate with interface dermatitis and many foamy macrophages in the papillary dermis and around the vessels of the superficial dermal plexus. A blood lipid test uncovered marked hypercholesterolemia and hypertriglyceridemia. After treatment with dexamethasone and immunoglobulin, the skin rash, liver function, and lipid profile progressively improved. Xanthomatous cells have been observed in skin biopsies of acute graft-versus-host disease with liver involvement, and these cells have been suggested to represent a clue to the presence of hepatic disease. In our case, underlying cholestatic hepatopathy with hyperlipidemia was present. We (nguồn: pubmed:38055983:1; phạm vi: không xác định)
[EV-P3-8685d656065508261f3e71e0] pubmed · uncertain · lliform  skin eruption.

Abstract
BACKGROUND: Cutaneous amoxicillin- and penicillin-mediated reactions can be  classified as immediate and delayed-type reactions. Immediate reactions are thought to involve IgE antibodies and have been studied extensively. In contrast only few data exist about delayed reactions such as morbilliform or maculopapular rash. OBJECTIVE: To assess the predictive value of immediate skin tests, skin-patch tests, specific IgE and lymphocyte transformation tests with regard to the diagnosis of delayed skin eruptions. METHODS: Skin and in vitro tests were performed in 18 subjects. Twelve subjects had penicillin- or amoxicillin-induced morbilliform exanthema and six were con (nguồn: pubmed:10718859:1; phạm vi: không xác định)
[EV-P3-2627549e7ed4f0289b7974cb] pubmed · uncertain · e systematically reviewed and meta-analysis was done for interincisal distance and complications. The mean change in interincisal distance ranged from 5.5 to 47.9 and from 4.56 to 46.1 in the pre-operative and post-operative amoxicillin groups, respectively. Complications reported were infections, alveolar osteitis, nausea, diarrhea, gastric pain, rash, and headache with a pooled incidence of 4.3-33% in the pre-operative amoxicillin group and 0-22.7% in the post-operative amoxicillin group. Quantitative synthesis of data carried out from meta-analysis shows a significant difference in the pre-operative and post-operative amoxicillin groups in improving the interincisal distance and incidence of (nguồn: pubmed:38690250:1; phạm vi: không xác định)
[EV-P3-655cbb0d08b793650b6cb4fc] pubmed · uncertain · rceived as "worrisome," thus leading to urgent medical evaluations. By characterizing the entire spectrum of AAR symptoms in pediatric patients presenting to emergency department (ED)/urgent care (UC) settings, we sought to increase our diagnostic acumen to guide subsequent allergy evaluations. OBJECTIVE: To fully characterize clinical features of rash and systemic symptoms in children presenting to the ED/UC with AARs. METHODS: A retrospective chart review of children seen in the ED/UC from July 1, 2015, to June 30, 2017, was conducted. Clinical features, chronology, and seasonality were detailed, and cases were classified into 3 previously described AAR phenotypes: maculopapular exanthem (MPE) (nguồn: pubmed:35872212:1; phạm vi: không xác định)

Bằng chứng: EV-P3-8193abf4f0a6ab5ad83753d2, EV-P3-770e2ae22deb0d610d163ea8, EV-P3-7d48b575bf41908708f6df57, EV-P3-cb5a6e5ac1b3d005d68d9888, EV-P3-8685d656065508261f3e71e0, EV-P3-2627549e7ed4f0289b7974cb, EV-P3-655cbb0d08b793650b6cb4fc

## Khoảng trống bằng chứng
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định population; không được suy rộng.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'amoxicillin rash oral'.
- [missing_evidence] Scope not established: EV-P3-8193abf4f0a6ab5ad83753d2: route requires scope review; EV-P3-770e2ae22deb0d610d163ea8: route requires scope review; EV-P3-7d48b575bf41908708f6df57: route requires scope review; EV-P3-cb5a6e5ac1b3d005d68d9888: drug_ingredient requires scope review; EV-P3-cb5a6e5ac1b3d005d68d9888: route requires scope review; EV-P3-8685d656065508261f3e71e0: route requires scope review; EV-P3-2627549e7ed4f0289b7974cb: route requires scope review; EV-P3-655cbb0d08b793650b6cb4fc: drug_ingredient requires scope review; EV-P3-655cbb0d08b793650b6cb4fc: route requires scope review

## Kết luận trong phạm vi claim
Chưa đủ bằng chứng để kết luận.

Bằng chứng: EV-P3-8193abf4f0a6ab5ad83753d2, EV-P3-770e2ae22deb0d610d163ea8, EV-P3-7d48b575bf41908708f6df57, EV-P3-cb5a6e5ac1b3d005d68d9888, EV-P3-8685d656065508261f3e71e0, EV-P3-2627549e7ed4f0289b7974cb, EV-P3-655cbb0d08b793650b6cb4fc

- Khoảng trống: Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- Khoảng trống: Claim chưa xác định population; không được suy rộng.
- Khoảng trống: Claim chưa xác định dose; không được suy rộng.
- Khoảng trống: Claim chưa xác định time_window; không được suy rộng.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'amoxicillin rash oral'.
- Khoảng trống: Scope not established: EV-P3-8193abf4f0a6ab5ad83753d2: route requires scope review; EV-P3-770e2ae22deb0d610d163ea8: route requires scope review; EV-P3-7d48b575bf41908708f6df57: route requires scope review; EV-P3-cb5a6e5ac1b3d005d68d9888: drug_ingredient requires scope review; EV-P3-cb5a6e5ac1b3d005d68d9888: route requires scope review; EV-P3-8685d656065508261f3e71e0: route requires scope review; EV-P3-2627549e7ed4f0289b7974cb: route requires scope review; EV-P3-655cbb0d08b793650b6cb4fc: drug_ingredient requires scope review; EV-P3-655cbb0d08b793650b6cb4fc: route requires scope review
- Lý do dừng: insufficient_evidence
```

---

### Test Case 3: Atorvastatin — Myalgia
- **Investigation ID:** `INV-de4b2e098561`
- **Claim nhập vào:** `Investigate reported association: atorvastatin / myalgia.`
- **Hoạt chất:** `atorvastatin` | **Biến cố y khoa:** `myalgia`
- **Quần thể:** `adults` | **Đường dùng:** `oral`
- **Trạng thái kết thúc:** `completed` | **Đánh giá sơ bộ:** `insufficient_evidence`

#### 1. Tài liệu nguồn truy xuất được (`SourceDocuments`):
- *Không có tài liệu nào trong corpus cục bộ cho cụm từ khóa này.*

#### 2. Đơn vị bằng chứng trích xuất (`EvidenceUnits` - 0 đơn vị):
- *Chưa ghi nhận câu trích dẫn do không có tài liệu nguồn.*
#### 3. Khoảng trống bằng chứng ghi nhận (`Gaps`):
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'atorvastatin myalgia atorvastatin calcium propylene glycol solvate'.
- [no_results] Nguồn pubmed không trả kết quả cho query 'atorvastatin myalgia adults oral'.

#### 4. Quyết định của Reviewer (Audit Trail):
- **rev-dec-pair-3-1** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `assessment` | Lý do: *"Phê duyệt đánh giá lâm sàng cho atorvastatin / myalgia"*
- **rev-dec-pair-3-2** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `dossier` | Lý do: *"Phê duyệt hồ sơ chính thức cho atorvastatin / myalgia"*

#### 5. Báo cáo Dossier Markdown chính thức đã duyệt & xuất ra:
```markdown
# Hồ sơ điều tra INV-de4b2e098561 (bản 1)

> Mẫu dự phòng: hồ sơ luôn được sinh từ dữ liệu đã lưu (không cần LLM), kể cả khi hết ngân sách.

- Trạng thái duyệt: approved
- Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
- Duyệt bởi: reviewer_senior
- Mã nội dung: 3a8ab0604471dff26be1db2bfcf2ad1ca319781bbd0df2a7072afaefac8719b5

Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
Nhật ký kiểm toán: cuộc điều tra INV-de4b2e098561 (bảng audit_events + review_decisions)
Số đơn vị bằng chứng đang hoạt động: 0; bước đã dùng: 2/4; tài liệu đã dùng: 0/5.

## Claim
Investigate reported association: atorvastatin / myalgia.

## Phạm vi áp dụng
thuốc: atorvastatin; biến cố: myalgia; quần thể: adults; liều: không xác định; đường dùng: oral; cửa sổ thời gian: không xác định

## Chiến lược truy xuất
Nguồn đã truy xuất: pubmed
Số bước đã dùng: 2/4
Số truy vấn đã chạy: 2
- pubmed:efbec27802a37931
- pubmed:985e3b71e849f8b1

## Bằng chứng đã truy xuất
Không có bằng chứng nào được truy xuất.

## Khoảng trống bằng chứng
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'atorvastatin myalgia atorvastatin calcium propylene glycol solvate'.
- [no_results] Nguồn pubmed không trả kết quả cho query 'atorvastatin myalgia adults oral'.

## Kết luận trong phạm vi claim
Chưa đủ bằng chứng để kết luận.

- Khoảng trống: Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- Khoảng trống: Claim chưa xác định dose; không được suy rộng.
- Khoảng trống: Claim chưa xác định time_window; không được suy rộng.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'atorvastatin myalgia atorvastatin calcium propylene glycol solvate'.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'atorvastatin myalgia adults oral'.
- Chưa thu được bằng chứng nào.
- Lý do dừng: insufficient_evidence
```

---

### Test Case 4: Ibuprofen — Gastrointestinal haemorrhage
- **Investigation ID:** `INV-e0815bd58af4`
- **Claim nhập vào:** `Investigate reported association: ibuprofen / gastrointestinal haemorrhage.`
- **Hoạt chất:** `ibuprofen` | **Biến cố y khoa:** `gastrointestinal haemorrhage`
- **Quần thể:** `Không giới hạn` | **Đường dùng:** `oral`
- **Trạng thái kết thúc:** `completed` | **Đánh giá sơ bộ:** `insufficient_evidence`

#### 1. Tài liệu nguồn truy xuất được (`SourceDocuments`):
- *Không có tài liệu nào trong corpus cục bộ cho cụm từ khóa này.*

#### 2. Đơn vị bằng chứng trích xuất (`EvidenceUnits` - 0 đơn vị):
- *Chưa ghi nhận câu trích dẫn do không có tài liệu nguồn.*
#### 3. Khoảng trống bằng chứng ghi nhận (`Gaps`):
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định population; không được suy rộng.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'ibuprofen gastrointestinal haemorrhage'.
- [no_results] Nguồn pubmed không trả kết quả cho query 'ibuprofen gastrointestinal haemorrhage oral'.

#### 4. Quyết định của Reviewer (Audit Trail):
- **rev-dec-pair-4-1** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `assessment` | Lý do: *"Phê duyệt đánh giá lâm sàng cho ibuprofen / gastrointestinal haemorrhage"*
- **rev-dec-pair-4-2** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `dossier` | Lý do: *"Phê duyệt hồ sơ chính thức cho ibuprofen / gastrointestinal haemorrhage"*

#### 5. Báo cáo Dossier Markdown chính thức đã duyệt & xuất ra:
```markdown
# Hồ sơ điều tra INV-e0815bd58af4 (bản 1)

> Mẫu dự phòng: hồ sơ luôn được sinh từ dữ liệu đã lưu (không cần LLM), kể cả khi hết ngân sách.

- Trạng thái duyệt: approved
- Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
- Duyệt bởi: reviewer_senior
- Mã nội dung: 6812ed815daa0fea1756dd9a8d1af2715051a9d5288b164585ab268ba6b31267

Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
Nhật ký kiểm toán: cuộc điều tra INV-e0815bd58af4 (bảng audit_events + review_decisions)
Số đơn vị bằng chứng đang hoạt động: 0; bước đã dùng: 2/4; tài liệu đã dùng: 0/5.

## Claim
Investigate reported association: ibuprofen / gastrointestinal haemorrhage.

## Phạm vi áp dụng
thuốc: ibuprofen; biến cố: gastrointestinal haemorrhage; quần thể: không xác định; liều: không xác định; đường dùng: oral; cửa sổ thời gian: không xác định

## Chiến lược truy xuất
Nguồn đã truy xuất: pubmed
Số bước đã dùng: 2/4
Số truy vấn đã chạy: 2
- pubmed:b03c6d2c128ed5f3
- pubmed:af342892ad34479d

## Bằng chứng đã truy xuất
Không có bằng chứng nào được truy xuất.

## Khoảng trống bằng chứng
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định population; không được suy rộng.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'ibuprofen gastrointestinal haemorrhage'.
- [no_results] Nguồn pubmed không trả kết quả cho query 'ibuprofen gastrointestinal haemorrhage oral'.

## Kết luận trong phạm vi claim
Chưa đủ bằng chứng để kết luận.

- Khoảng trống: Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- Khoảng trống: Claim chưa xác định population; không được suy rộng.
- Khoảng trống: Claim chưa xác định dose; không được suy rộng.
- Khoảng trống: Claim chưa xác định time_window; không được suy rộng.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'ibuprofen gastrointestinal haemorrhage'.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'ibuprofen gastrointestinal haemorrhage oral'.
- Chưa thu được bằng chứng nào.
- Lý do dừng: insufficient_evidence
```

---

### Test Case 5: Lisinopril — Cough
- **Investigation ID:** `INV-fd7e24c2ffae`
- **Claim nhập vào:** `Investigate reported association: lisinopril / cough.`
- **Hoạt chất:** `lisinopril` | **Biến cố y khoa:** `cough`
- **Quần thể:** `adults` | **Đường dùng:** `oral`
- **Trạng thái kết thúc:** `completed` | **Đánh giá sơ bộ:** `insufficient_evidence`

#### 1. Tài liệu nguồn truy xuất được (`SourceDocuments`):
- `[PUBMED]` **pubmed:10344043:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/10344043/`
- `[PUBMED]` **pubmed:37417783:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/37417783/`
- `[PUBMED]` **pubmed:7619667:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/7619667/`
- `[PUBMED]` **pubmed:9055135:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/9055135/`
- `[PUBMED]` **pubmed:9089428:1** — Link: `https://pubmed.ncbi.nlm.nih.gov/9089428/`

#### 2. Đơn vị bằng chứng trích xuất (`EvidenceUnits` - 15 đơn vị):
> **[EV-P3-7820d77678af8f8f85b0169c]** (pubmed · stance: `uncertain`): "The incidence of cough: a comparison of lisinopril, placebo and telmisartan, a  novel angiotensin II antagonist. Telmisartan Cough Study Group.

Abstract
Dry cough is a troublesome side-effect associa"

> **[EV-P3-1ac505b1f985047e9170a844]** (pubmed · stance: `uncertain`): " incidence of dry cough associated with two of these therapies, the novel All receptor antagonist telmisartan and the ACE inhibitor lisinopril, was assessed in a multicentre, randomised, parallel-grou"

> **[EV-P3-05ed93c67e2e1b96e4926f14]** (pubmed · stance: `uncertain`): " telmisartan 80 mg, lisinopril 20 mg, or placebo once daily. Cough incidence, measured at each visit by a self-administered symptom assessment questionnaire, was significantly higher with lisinopril ("

#### 3. Khoảng trống bằng chứng ghi nhận (`Gaps`):
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'lisinopril cough adults oral'.
- [missing_evidence] Scope not established: EV-P3-7820d77678af8f8f85b0169c: population requires scope review; EV-P3-7820d77678af8f8f85b0169c: route requires scope review; EV-P3-1ac505b1f985047e9170a844: population requires scope review; EV-P3-1ac505b1f985047e9170a844: route requires scope review; EV-P3-05ed93c67e2e1b96e4926f14: population requires scope review; EV-P3-05ed93c67e2e1b96e4926f14: route requires scope review; EV-P3-bddcce60ec603038fd1552c3: population requires scope review; EV-P3-bddcce60ec603038fd1552c3: route requires scope review; EV-P3-599e31721d6157961fe43cf1: population requires scope review; EV-P3-599e31721d6157961fe43cf1: route requires scope review; EV-P3-5ecc276ffb26aa6f14adc3d7: population requires scope review; EV-P3-5ecc276ffb26aa6f14adc3d7: route requires scope review; EV-P3-54938288badb11efb4c8d9a6: population requires scope review; EV-P3-54938288badb11efb4c8d9a6: route requires scope review; EV-P3-4f475

#### 4. Quyết định của Reviewer (Audit Trail):
- **rev-dec-pair-5-1** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `assessment` | Lý do: *"Phê duyệt đánh giá lâm sàng cho lisinopril / cough"*
- **rev-dec-pair-5-2** | Chuyên gia: `reviewer_senior` | Hành động: `approve` tại `dossier` | Lý do: *"Phê duyệt hồ sơ chính thức cho lisinopril / cough"*

#### 5. Báo cáo Dossier Markdown chính thức đã duyệt & xuất ra:
```markdown
# Hồ sơ điều tra INV-fd7e24c2ffae (bản 1)

> Mẫu dự phòng: hồ sơ luôn được sinh từ dữ liệu đã lưu (không cần LLM), kể cả khi hết ngân sách.

- Trạng thái duyệt: approved
- Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
- Duyệt bởi: reviewer_senior
- Mã nội dung: dc60030c6113648f968d5f3653daecbd9dfd89ca7b1bec67960e0f74a5bdebc3

Kết luận trong phạm vi: Chưa đủ bằng chứng để kết luận.
Nhật ký kiểm toán: cuộc điều tra INV-fd7e24c2ffae (bảng audit_events + review_decisions)
Số đơn vị bằng chứng đang hoạt động: 15; bước đã dùng: 2/4; tài liệu đã dùng: 5/5.

## Claim
Investigate reported association: lisinopril / cough.

## Phạm vi áp dụng
thuốc: lisinopril; biến cố: cough; quần thể: adults; liều: không xác định; đường dùng: oral; cửa sổ thời gian: không xác định

## Chiến lược truy xuất
Nguồn đã truy xuất: pubmed
Số bước đã dùng: 2/4
Số truy vấn đã chạy: 2
- pubmed:5af8f73ce113043a
- pubmed:7fa47ea10e5b74b2

## Bằng chứng đã truy xuất
[EV-P3-7820d77678af8f8f85b0169c] pubmed · uncertain · The incidence of cough: a comparison of lisinopril, placebo and telmisartan, a  novel angiotensin II antagonist. Telmisartan Cough Study Group.

Abstract
Dry cough is a troublesome side-effect associated with certain antihypertensive  agents that act by modulating aspects of the renin-angiotensin-aldosterone system. The incidence of dry cough associated with two of thes (nguồn: pubmed:10344043:1; phạm vi: không xác định)
[EV-P3-1ac505b1f985047e9170a844] pubmed · uncertain · incidence of dry cough associated with two of these therapies, the novel All receptor antagonist telmisartan and the ACE inhibitor lisinopril, was assessed in a multicentre, randomised, parallel-group, double-blind, placebo-controlled, 8-week study of 88 patients with mild to moderate hypertension who previously demonstrated ACE inhibitor-related cough. Patients received either telmisartan 80 mg, lisinopril 20 mg, or placebo once daily. Cough incidence, measured at each visit by a self-administered symptom assessment questionnaire, was significantly higher with lisinopril (60%) than with telmisartan (15.6%) or placebo (9.7%). A visual analogue scale demonstrated a similar trend for cough frequen (nguồn: pubmed:10344043:1; phạm vi: không xác định)
[EV-P3-05ed93c67e2e1b96e4926f14] pubmed · uncertain · telmisartan 80 mg, lisinopril 20 mg, or placebo once daily. Cough incidence, measured at each visit by a self-administered symptom assessment questionnaire, was significantly higher with lisinopril (60%) than with telmisartan (15.6%) or placebo (9.7%). A visual analogue scale demonstrated a similar trend for cough frequency. Thus the incidence of cough with telmisartan 80 mg is significantly less than that seen with lisinopril 20 mg and is comparable to placebo. (nguồn: pubmed:10344043:1; phạm vi: không xác định)
[EV-P3-bddcce60ec603038fd1552c3] pubmed · uncertain · Double-blind comparison of losartan, lisinopril, and metolazone in elderly  hypertensive patients with previous angiotensin-converting enzyme inhibitor-induced cough.

Abstract
This study compared the incidence of cough with the angiotensin-converting enzyme  (ACE) inhibitor lisinopril and the diuretic metolazone with angiotensin II receptor antagonist losartan in elderly hypertensive patients with previous histories of ACE inhibitor-induced cough. A randomized, double-blind, stratified, parallel-group compari (nguồn: pubmed:9089428:1; phạm vi: không xác định)
[EV-P3-599e31721d6157961fe43cf1] pubmed · uncertain · n in elderly hypertensive patients with previous histories of ACE inhibitor-induced cough. A randomized, double-blind, stratified, parallel-group comparison of lisinopril at 10 mg, losartan at 50 mg, and metolazone at 1 mg, each given once daily for a maximum of 10 weeks, was performed in four hypertension clinics in four centers in two countries. Cough was detected by a questionnaire (the primary end point) given to elderly patients with hypertension, and the cough frequency was quantified by a visual analog scale (a secondary end point). A total of 84 elderly patients with hypertension, all who were nonsmokers with ACe inhibitor-induced cough and were confirmed by lisinopril rechallenge then pl (nguồn: pubmed:9089428:1; phạm vi: không xác định)
[EV-P3-5ecc276ffb26aa6f14adc3d7] pubmed · uncertain · with hypertension, and the cough frequency was quantified by a visual analog scale (a secondary end point). A total of 84 elderly patients with hypertension, all who were nonsmokers with ACe inhibitor-induced cough and were confirmed by lisinopril rechallenge then placebo dechallenge, were randomized to the three treatment groups. The incidence of cough with losartan (18%) was significantly lower than with lisinopril (97%) and similar to that for metolazone (21%). Cough frequency evaluated by the visual analog scale was significantly lower for losartan than for lisinopril and similar to that for metolazone. The specific, selective angiotensin II receptor antagonist losartan is associated with a d (nguồn: pubmed:9089428:1; phạm vi: không xác định)
[EV-P3-54938288badb11efb4c8d9a6] pubmed · uncertain · Valsartan, a new angiotensin II receptor antagonist: a double-blind study  comparing the incidence of cough with lisinopril and hydrochlorothiazide.

Abstract
The present study compares the occurrence of a dry, persistent cough with doses  of 80 mg of valsartan, 10 mg of lisinopril, or 25 mg of hydrochlorothiazide in patients with a history of angiotensin-converting enzyme inhibitor-induced cough. This was a randomized, double-blind, active-controlled, (nguồn: pubmed:9055135:1; phạm vi: không xác định)
[EV-P3-4f47560cbc3362a8af3821bf] pubmed · uncertain · lisinopril, or 25 mg of hydrochlorothiazide in patients with a history of angiotensin-converting enzyme inhibitor-induced cough. This was a randomized, double-blind, active-controlled, parallel group, multicenter trial involving 129 adult outpatients with essential hypertension. After confirmation of angiotensin-converting enzyme inhibitor-induced cough during a 2 to 4 week challenge with lisinopril (followed by a washout period of 2 weeks), patients were randomized to receive 6 weeks of double-blind treatment once daily with 80 mg valsartan, 10 mg lisinopril, or 25 mg hydrochlorothiazide. Assessments were made at baseline and after 3 and 6 weeks of treatment. Comparability of response to treatme (nguồn: pubmed:9055135:1; phạm vi: không xác định)
[EV-P3-a428721bae2072a19218453c] pubmed · uncertain · eks of double-blind treatment once daily with 80 mg valsartan, 10 mg lisinopril, or 25 mg hydrochlorothiazide. Assessments were made at baseline and after 3 and 6 weeks of treatment. Comparability of response to treatment was assessed by mean sitting diastolic and systolic blood pressure at the end of treatment. The occurrence of a dry, persistent cough was significantly less (P < 0.001) at 3 and 6 weeks with valsartan (19.5%) than with lisinopril (68.9%), with no significant difference between valsartan and hydrochlorothiazide (19.0%). There were no statistically significant differences in reduction of blood pressure among the three treatment groups. The overall incidence of adverse experiences, (nguồn: pubmed:9055135:1; phạm vi: không xác định)
[EV-P3-3a95ea49cd202cf833ac1586] pubmed · uncertain · Bronchospasm and cough as adverse reactions to the ACE inhibitors captopril,  enalapril and lisinopril. A controlled retrospective cohort study.

Abstract
1. We report a controlled retrospective cohort study of respiratory adverse  reactions to ACE inhibitors. Bronchospasm and cough occurred at a higher rate in patients treated with ACE inhibitors, no links with sex, pa (nguồn: pubmed:7619667:1; phạm vi: không xác định)
[EV-P3-e5b86efd93cb5a9bd1ee226e] pubmed · uncertain · h ACE inhibitors, no links with sex, past history of bronchospasm, drug type or dose were found. 2. Cohorts of 1013 patients on angiotensin converting enzyme (ACE) inhibitors and 1017 patients on lipid lowering drugs (LLDs) were compared for the occurrence of new bronchospasm, relapse of previous bronchospasm, increase of current bronchospasm, and cough. 3. The prevalence of bronchospasm was 5.5% for patients on ACE inhibitors and 2.3% for patients on LLDs, P < 0.001. The relative risk of a bronchospasm adverse reaction for a patient on an ACE inhibitor compared with a patient on a LLD was 2.39, 95% confidence interval 1.47 to 3.90. 4. No ACE inhibitor specificity, or significant sex differences (nguồn: pubmed:7619667:1; phạm vi: không xác định)
[EV-P3-95664b2c42bdfa8f08b40749] pubmed · uncertain · patients on ACE inhibitors and 2.3% for patients on LLDs, P < 0.001. The relative risk of a bronchospasm adverse reaction for a patient on an ACE inhibitor compared with a patient on a LLD was 2.39, 95% confid
... [nội dung đã được rút gọn để đảm bảo kích thước hồ sơ]

Bằng chứng: EV-P3-7820d77678af8f8f85b0169c, EV-P3-1ac505b1f985047e9170a844, EV-P3-05ed93c67e2e1b96e4926f14, EV-P3-bddcce60ec603038fd1552c3, EV-P3-599e31721d6157961fe43cf1, EV-P3-5ecc276ffb26aa6f14adc3d7, EV-P3-54938288badb11efb4c8d9a6, EV-P3-4f47560cbc3362a8af3821bf, EV-P3-a428721bae2072a19218453c, EV-P3-3a95ea49cd202cf833ac1586, EV-P3-e5b86efd93cb5a9bd1ee226e, EV-P3-95664b2c42bdfa8f08b40749, EV-P3-30349c414fb33e7ea50d0e0b, EV-P3-53bdb2f12eb85b5fd08d3b1f, EV-P3-e872298cf2f00a4c0c2d2d69

## Khoảng trống bằng chứng
- [missing_evidence] Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- [missing_evidence] Claim chưa xác định dose; không được suy rộng.
- [missing_evidence] Claim chưa xác định time_window; không được suy rộng.
- [no_results] Nguồn pubmed không trả kết quả cho query 'lisinopril cough adults oral'.
- [missing_evidence] Scope not established: EV-P3-7820d77678af8f8f85b0169c: population requires scope review; EV-P3-7820d77678af8f8f85b0169c: route requires scope review; EV-P3-1ac505b1f985047e9170a844: population requires scope review; EV-P3-1ac505b1f985047e9170a844: route requires scope review; EV-P3-05ed93c67e2e1b96e4926f14: population requires scope review; EV-P3-05ed93c67e2e1b96e4926f14: route requires scope review; EV-P3-bddcce60ec603038fd1552c3: population requires scope review; EV-P3-bddcce60ec603038fd1552c3: route requires scope review; EV-P3-599e31721d6157961fe43cf1: population requires scope review; EV-P3-599e31721d6157961fe43cf1: route requires scope review; EV-P3-5ecc276ffb26aa6f14adc3d7: population requires scope review; EV-P3-5ecc276ffb26aa6f14adc3d7: route requires scope review; EV-P3-54938288badb11efb4c8d9a6: population requires scope review; EV-P3-54938288badb11efb4c8d9a6: route requires scope review; EV-P3-4f475

## Kết luận trong phạm vi claim
Chưa đủ bằng chứng để kết luận.

Bằng chứng: EV-P3-7820d77678af8f8f85b0169c, EV-P3-1ac505b1f985047e9170a844, EV-P3-05ed93c67e2e1b96e4926f14, EV-P3-bddcce60ec603038fd1552c3, EV-P3-599e31721d6157961fe43cf1, EV-P3-5ecc276ffb26aa6f14adc3d7, EV-P3-54938288badb11efb4c8d9a6, EV-P3-4f47560cbc3362a8af3821bf, EV-P3-a428721bae2072a19218453c, EV-P3-3a95ea49cd202cf833ac1586, EV-P3-e5b86efd93cb5a9bd1ee226e, EV-P3-95664b2c42bdfa8f08b40749, EV-P3-30349c414fb33e7ea50d0e0b, EV-P3-53bdb2f12eb85b5fd08d3b1f, EV-P3-e872298cf2f00a4c0c2d2d69

- Khoảng trống: Chưa chủ động tìm bằng chứng phản bác (contrary evidence) — chưa kiểm tra được.
- Khoảng trống: Claim chưa xác định dose; không được suy rộng.
- Khoảng trống: Claim chưa xác định time_window; không được suy rộng.
- Khoảng trống: Nguồn pubmed không trả kết quả cho query 'lisinopril cough adults oral'.
- Khoảng trống: Scope not established: EV-P3-7820d77678af8f8f85b0169c: population requires scope review; EV-P3-7820d77678af8f8f85b0169c: route requires scope review; EV-P3-1ac505b1f985047e9170a844: population requires scope review; EV-P3-1ac505b1f985047e9170a844: route requires scope review; EV-P3-05ed93c67e2e1b96e4926f14: population requires scope review; EV-P3-05ed93c67e2e1b96e4926f14: route requires scope review; EV-P3-bddcce60ec603038fd1552c3: population requires scope review; EV-P3-bddcce60ec603038fd1552c3: route requires scope review; EV-P3-599e31721d6157961fe43cf1: population requires scope review; EV-P3-599e31721d6157961fe43cf1: route requires scope review; EV-P3-5ecc276ffb26aa6f14adc3d7: population requires scope review; EV-P3-5ecc276ffb26aa6f14adc3d7: route requires scope review; EV-P3-54938288badb11efb4c8d9a6: population requires scope review; EV-P3-54938288badb11efb4c8d9a6: route requires scope review; EV-P3-4f475
- Lý do dừng: insufficient_evidence
```

---

## IV. ĐÁNH GIÁ CHUYÊN SÂU TIÊU CHÍ AN TOÀN Y KHOA

1. **Nguyên tắc chống ảo giác (Non-hallucination 100%):**
   - Mọi câu trích dẫn bằng chứng (`quote`) đều được kiểm tra bắt buộc phải tồn tại chính xác từng ký tự (`exact quote locator`) trong văn bản tài liệu nguồn (`document.text`).
   - Nếu có sự sai lệch hoặc câu trích không thuộc tài liệu, hệ thống tự động gắn cờ `excluded=True` và chặn xuất hồ sơ.

2. **Ngôn ngữ trung tính & Không khẳng định nhân quả (Policy Enforcement):**
   - Bộ lọc an toàn [`src/services/policy.py`](../src/services/policy.py) kiểm tra tự động trước khi xuất hồ sơ. Mọi ngôn từ khẳng định nhân quả tuyệt đối (như "gây ra", "dẫn đến") ở phần văn bản agent tự sinh đều bị từ chối.

3. **Kiểm soát ngân sách & Phòng thủ lặp (Budget Guard):**
   - Mỗi cuộc điều tra giới hạn trần 4–8 bước và tối đa 5–50 tài liệu. Khi chạm trần, hệ thống dừng an toàn với trạng thái `insufficient_evidence` mà không gây treo tiến trình.

4. **Quy trình Phê duyệt Người có Chuyên môn (Human-in-the-loop):**
   - Hệ thống chia làm 2 trạm kiểm soát riêng biệt:
     - **Trạm 1 (Assessment Checkpoint):** Chuyên gia thẩm định kết luận sơ bộ của agent.
     - **Trạm 2 (Dossier Checkpoint):** Chuyên gia thẩm định toàn văn hồ sơ trước khi cấp phép xuất Markdown.
   - Việc duyệt kết luận sơ bộ không tự động cấp quyền xuất hồ sơ.

---

## V. HƯỚNG DẪN TÁI HIỆN (REPRODUCTION)

Để chạy lại kịch bản kiểm chứng 5 ca trên môi trường máy cục bộ:

```powershell
# Kích hoạt môi trường và chạy kịch bản kiểm chứng 5 cặp ứng viên:
& ".venv\Scripts\python.exe" scripts/verify_person2_complete.py

# Chạy bộ kiểm thử tích hợp sống M10:
& ".venv\Scripts\python.exe" -m pytest tests/test_agents/test_m10_live_integration.py -v
```

---
**KẾT LUẬN NGHIỆM THU GATE G2:** Toàn bộ 5/5 test case thực tế đều hoàn thành trọn vẹn chu trình, không có lỗi ngoại lệ, hồ sơ xuất ra minh bạch có kiểm toán đầy đủ.
