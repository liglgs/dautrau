# AI Agent chủ động điều tra bằng chứng cảnh giác dược

## Tài liệu đặc tả đề tài chi tiết

**Tên tiếng Việt đề xuất:** AI Agent chủ động điều tra và kiểm chứng nhận định an toàn thuốc bằng chiến lược truy xuất bằng chứng thích ứng  
**Tên tiếng Anh đề xuất:** Adaptive Evidence Investigation Agent for Pharmacovigilance Safety Claims  
**Ngày cập nhật:** 30/09/2026  
**Phạm vi:** Pharmacovigilance, drug-safety evidence investigation, human-in-the-loop  
**Mức đề xuất:** Phù hợp cho đồ án nghiên cứu và prototype sinh viên

---

## 1. Tóm tắt đề tài

Đề tài xây dựng một AI Agent hỗ trợ chuyên viên cảnh giác dược kiểm tra một nhận định an toàn thuốc.

Ví dụ nhận định đầu vào:

> “Thuốc X có liên quan đến biến cố Y ở nhóm bệnh nhân Z trong điều kiện C.”

Agent không chỉ tìm kiếm và tóm tắt tài liệu. Agent phải:

1. Phân rã nhận định thành các thành phần có thể kiểm tra.
2. Xác định bằng chứng nào đang có và bằng chứng nào còn thiếu.
3. Lập kế hoạch truy xuất từ nhiều nguồn.
4. Thay đổi kế hoạch khi tìm thấy dữ liệu mới hoặc mâu thuẫn.
5. Kiểm tra phạm vi áp dụng của từng bằng chứng.
6. Tách bằng chứng ủng hộ, phản bác và không liên quan.
7. Đánh giá mức đầy đủ của hồ sơ.
8. Tạo evidence dossier có nguồn gốc rõ ràng.
9. Abstain khi chưa đủ bằng chứng.
10. Đưa kết quả cho chuyên viên quyết định.

Agent không xác nhận quan hệ nhân quả. Agent không thay thế signal-management process của cơ quan quản lý hoặc doanh nghiệp dược.

---

## 2. Tại sao bài toán này tồn tại?

### 2.1. Khối lượng dữ liệu lớn

EudraVigilance xử lý **831.365 spontaneous individual case safety reports trong năm 2024**. Số lượng báo cáo lớn làm tăng nhu cầu sàng lọc, chuẩn hóa và tổng hợp bằng chứng.

Nguồn:  
https://www.ema.europa.eu/system/files/documents/report/2024-annual-report-eudravigilance-en.pdf

### 2.2. Bằng chứng phân tán

Một nhận định an toàn có thể liên quan đến:

- Spontaneous adverse-event reports.
- Nhãn thuốc hiện hành và nhãn cũ.
- Case report trong literature.
- Clinical trial.
- Observational study.
- Meta-analysis.
- Regulatory communication.
- Known class effect.
- Dữ liệu về liều, thời gian và quần thể.

Không có một nguồn đơn lẻ đủ để xác nhận toàn bộ claim.

### 2.3. Dữ liệu không hoàn chỉnh

FAERS có các hạn chế chính thức:

- Báo cáo có thể thiếu dữ liệu.
- Có thể có báo cáo trùng.
- Không phải mọi báo cáo đều được xác minh.
- Không thể suy luận quan hệ nhân quả.
- Không thể tính incidence vì không có denominator phù hợp.
- Harmonized `openfda` fields không có trên mọi record.

Nguồn:

- https://open.fda.gov/apis/drug/event/
- https://www.fda.gov/drugs/fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-public-dashboard

### 2.4. Claim thường quá rộng

Một câu như “Thuốc X gây biến cố Y” có thể bỏ qua:

- Chỉ định sử dụng.
- Nhóm tuổi.
- Giới tính.
- Thai kỳ.
- Liều.
- Đường dùng.
- Thời gian tiếp xúc.
- Bệnh nền.
- Thuốc dùng kèm.
- Loại outcome.
- Mức nghiêm trọng.

Agent phải xác định claim nào có thể kiểm tra và claim nào cần thu hẹp.

### 2.5. Signal không phải kết luận nhân quả

WHO định nghĩa signal là thông tin về một quan hệ nhân quả có thể có giữa adverse event và thuốc, khi quan hệ đó chưa được biết hoặc chưa được ghi nhận đầy đủ.

Signal là giả thuyết cần điều tra. Signal không phải bằng chứng xác nhận thuốc gây biến cố.

Nguồn:

- https://who-umc.org/pharmacovigilance-communications/glossary/
- https://who-umc.org/media/wjfbsuhf/who-pv-indicators.pdf

---

## 3. Pain point cụ thể

### 3.1. Pain point của chuyên viên cảnh giác dược

Chuyên viên phải thực hiện nhiều công việc thủ công:

- Chuẩn hóa tên thuốc và tên biến cố.
- Xác định từ đồng nghĩa và thuật ngữ MedDRA.
- Tìm literature liên quan.
- Loại tài liệu ngoài phạm vi.
- Kiểm tra nhãn thuốc hiện hành.
- Tìm báo cáo trùng.
- So sánh quần thể giữa các nghiên cứu.
- Phân biệt association và causation.
- Ghi lại bằng chứng phản bác.
- Chứng minh nguồn của mọi kết luận.
- Viết assessment có thể kiểm toán.

### 3.2. Pain point của tổ chức

- Khối lượng case và literature tăng.
- Reviewer có thể dùng tiêu chí không nhất quán.
- Search strategy khó tái lập.
- Tài liệu có thể bị bỏ sót.
- Dossier có thể không ghi rõ vì sao loại tài liệu.
- Thời gian từ signal đến assessment có thể dài.
- Công cụ hiện tại thường tách rời case intake, literature review và signal analytics.

### 3.3. Pain point về an toàn

- Agent hoặc reviewer có thể overclaim causality.
- Một thống kê disproportionality có thể bị hiểu sai thành risk estimate.
- Bằng chứng từ quần thể khác có thể bị áp dụng sai.
- Nhãn thuốc lỗi thời có thể dẫn đến kết luận sai.
- False negative có thể bỏ sót tài liệu quan trọng.
- False positive có thể làm tăng khối lượng review.

---

## 4. Người dùng mục tiêu

### 4.1. Người dùng chính

- Pharmacovigilance specialist.
- Drug-safety scientist.
- Signal-management reviewer.
- Medical reviewer.
- Regulatory-affairs specialist.

### 4.2. Người dùng phụ

- Literature-surveillance team.
- Clinical-safety team.
- Benefit-risk team.
- Quality-assurance reviewer.
- Academic drug-safety researcher.

### 4.3. Người không nên dùng trực tiếp

- Bệnh nhân tự diễn giải nguy cơ thuốc.
- Nhân viên không được đào tạo về pharmacovigilance.
- Hệ thống tự động thay đổi nhãn thuốc.
- Hệ thống tự động đưa ra quyết định điều trị.

---

## 5. Job-to-be-done

> Khi nhận một drug-safety claim, chuyên viên cần nhanh chóng biết bằng chứng nào ủng hộ, bằng chứng nào mâu thuẫn, claim áp dụng trong phạm vi nào và dữ liệu nào còn thiếu, để quyết định bước đánh giá tiếp theo.

Agent phải giảm thời gian tìm và tổ chức bằng chứng. Agent không được thay thế đánh giá y khoa hoặc quyết định regulatory.

---

## 6. Phạm vi claim

### 6.1. Claim chuẩn

Claim nên có cấu trúc:

```text
Drug + Adverse event + Population + Exposure context + Time window
```

Ví dụ tổng quát:

```text
Drug X is associated with Event Y in Population Z within Time Window T.
```

### 6.2. Claim tối thiểu

- Tên thuốc hoặc active ingredient.
- Adverse event.

### 6.3. Claim nên có thêm

- Population.
- Indication.
- Dose.
- Route.
- Duration.
- Concomitant medication.
- Severity.
- Outcome.

### 6.4. Claim không phù hợp

- “Thuốc X an toàn tuyệt đối.”
- “Thuốc X chắc chắn gây tử vong.”
- “Thuốc X tốt hơn tất cả thuốc khác.”
- Claim không xác định adverse event.
- Claim không xác định sản phẩm hoặc hoạt chất.

Agent phải yêu cầu thu hẹp hoặc trả về `out_of_scope`.

---

## 7. Câu hỏi nghiên cứu chính

### RQ1

Agent có tìm được bằng chứng quan trọng với recall tương đương hoặc cao hơn single-shot RAG không?

### RQ2

Agent có phát hiện scope mismatch tốt hơn LLM tóm tắt thông thường không?

### RQ3

Agent có phát hiện bằng chứng mâu thuẫn mà không làm tăng quá nhiều false positive không?

### RQ4

Agent có abstain đúng khi dữ liệu chưa đủ không?

### RQ5

Agent có giảm thời gian chuyên viên tạo evidence dossier không?

### RQ6

Agent có cung cấp audit trail đủ để reviewer tái lập quá trình điều tra không?

---

## 8. Input chi tiết

### 8.1. Input bắt buộc

```json
{
  "drug": "Drug X",
  "event": "Adverse Event Y",
  "claim_text": "Drug X is associated with Event Y"
}
```

### 8.2. Input khuyến nghị

```json
{
  "drug": {
    "name": "Drug X",
    "active_ingredient": "Ingredient X",
    "route": "oral",
    "dose": "optional"
  },
  "event": {
    "name": "Event Y",
    "severity": "serious",
    "meddra_term": "optional"
  },
  "population": {
    "age_group": "adult",
    "sex": "all",
    "indication": "Condition Z",
    "comorbidities": []
  },
  "time_window": "optional",
  "claim_text": "full natural-language claim",
  "investigation_cutoff_date": "YYYY-MM-DD"
}
```

### 8.3. Input nguồn dữ liệu

- openFDA FAERS API.
- DailyMed label API.
- PubMed E-utilities.
- ClinicalTrials.gov API v2.
- EMA signal-management documents.
- FDA Drug Safety Communications.
- WHO-UMC public guidance.
- Curated local knowledge base.

### 8.4. Input cấu hình

- Allowed sources.
- Date cutoff.
- Language.
- Maximum search budget.
- Maximum number of agent steps.
- Required evidence types.
- Minimum citation threshold.
- Human-review checkpoints.

---

## 9. Output chi tiết

### 9.1. Kết luận được phép

```text
supported_for_scope
contradicted_for_scope
insufficient_evidence
scope_mismatch
out_of_scope
requires_human_review
```

Không dùng kết luận `causal` hoặc `not_causal`.

### 9.2. Evidence dossier

Dossier gồm:

1. Claim ban đầu.
2. Claim đã chuẩn hóa.
3. Scope được đánh giá.
4. Search strategy.
5. Nguồn đã truy xuất.
6. Bằng chứng ủng hộ.
7. Bằng chứng mâu thuẫn.
8. Bằng chứng không xác định.
9. Evidence gaps.
10. Duplicate candidates.
11. Limitations.
12. Abstention reason.
13. Reviewer decision.
14. Audit log.

### 9.3. Output JSON đề xuất

```json
{
  "claim_id": "claim-001",
  "normalized_claim": {
    "drug": "Ingredient X",
    "event": "Event Y",
    "population": "Adults with Condition Z",
    "time_window": "30 days"
  },
  "status": "insufficient_evidence",
  "confidence": 0.61,
  "scope_assessment": {
    "matched": ["adult", "oral route"],
    "mismatched": ["available evidence uses higher dose"],
    "unknown": ["time to onset"]
  },
  "supporting_evidence": [],
  "contradicting_evidence": [],
  "evidence_gaps": [],
  "next_actions": [],
  "limitations": [],
  "citations": [],
  "audit_log_id": "audit-001"
}
```

---

## 10. Vì sao cần AI Agent thay vì LLM hoặc RAG?

### 10.1. LLM một lần

LLM một lần thường:

- Trả lời dựa trên prompt hiện tại.
- Không quản lý ngân sách tìm kiếm.
- Không bảo đảm đã tìm đủ loại bằng chứng.
- Không theo dõi các giả thuyết cạnh tranh.
- Không tự kiểm tra search gap.
- Có thể dừng quá sớm.

### 10.2. RAG thông thường

RAG thông thường:

- Nhận truy vấn.
- Truy xuất top-k documents.
- Tạo câu trả lời từ documents.

RAG không nhất thiết:

- Tạo nhiều truy vấn thích ứng.
- Kiểm tra scope từng tài liệu.
- Tìm evidence phản bác.
- Thay đổi nguồn khi truy xuất thất bại.
- Biết khi nào cần abstain.

### 10.3. Agent đề xuất

Agent:

1. Tạo investigation plan.
2. Chọn nguồn phù hợp cho từng evidence gap.
3. Tạo query theo ontology và synonym.
4. Đánh giá kết quả sau mỗi bước.
5. Cập nhật evidence state.
6. Tìm contradiction có chủ đích.
7. Dừng theo stopping rule.
8. Tạo dossier có provenance.

### 10.4. Bảng so sánh

| Năng lực | LLM một lần | RAG | Agent đề xuất |
|---|---:|---:|---:|
| Tóm tắt tài liệu | Có | Có | Có |
| Truy xuất nhiều nguồn | Không ổn định | Có | Có |
| Lập kế hoạch | Hạn chế | Không | Có |
| Replanning | Không | Không | Có |
| Tìm contradiction chủ động | Hạn chế | Hạn chế | Có |
| Scope checking | Hạn chế | Hạn chế | Có |
| Stopping rule | Không | Không | Có |
| Abstention có lý do | Hạn chế | Hạn chế | Có |
| Audit trail theo bước | Không | Hạn chế | Có |

---

## 11. Sản phẩm hiện có và bằng chứng thị trường

### 11.1. ArisGlobal LifeSphere Safety

ArisGlobal công bố LifeSphere Safety có hơn 300 khách hàng và xử lý hơn 7 triệu safety case mỗi năm.

NavaX là lớp AI được dùng trong hệ sinh thái LifeSphere. Cần phân biệt tổng số case của LifeSphere với số case được NavaX xử lý.

Nguồn:

- https://www.arisglobal.com/lifesphere/safety/
- https://www.arisglobal.com/media/press-release/arisglobals-lifesphere-safety-solidifies-market-leading-position-in-pharmacovigilance-with-over-300-customers-and-more-than-7-million-safety-cases-processed-annually/

### 11.2. Oracle Empirica Signal

Oracle Empirica hỗ trợ khai phá post-marketing safety data, tính statistical score và signal-management workflow.

Nguồn:

- https://docs.oracle.com/health-sciences/empirica-signal-90/ESIUG/Home_page_1.htm
- https://www.oracle.com/life-sciences/safety-solutions/empirica-safety-signal-management/

### 11.3. Veeva Safety và Safety.AI

Veeva hỗ trợ literature review, literature-to-case intake, case intake và duplicate detection trong safety workflow.

Nguồn:

- https://www.veeva.com/resources/faster-literature-review-to-case-intake/
- https://safety.veevavault.help/en/gr/01239/
- https://www.veeva.com/products/veeva-safety/

### 11.4. Khoảng trống thị trường phù hợp với đề tài

Các sản phẩm lớn tập trung vào:

- Safety case management.
- Case intake.
- Literature-to-case extraction.
- Signal analytics.
- Regulatory workflow.

Prototype nên tập trung vào:

- Adaptive evidence acquisition.
- Evidence-gap planning.
- Scope mismatch detection.
- Contradiction-first search.
- Explainable abstention.
- Reproducible investigation trace.

Đây là phạm vi hẹp hơn enterprise safety platform nhưng thể hiện agent rõ hơn.

---

## 12. Nguồn dữ liệu khả thi

### 12.1. openFDA FAERS

**Vai trò:** Tìm spontaneous adverse-event reports.

**Endpoint:**  
https://open.fda.gov/apis/drug/event/

**Ưu điểm:**

- Công khai.
- Có API.
- Có nhiều trường dữ liệu.
- Phù hợp demo signal-supporting observations.

**Hạn chế:**

- Không xác nhận causality.
- Không tính incidence.
- Có duplicate và follow-up reports.
- Dữ liệu có thể thiếu.
- OpenFDA harmonization không bao phủ mọi record.

### 12.2. DailyMed

**Vai trò:** Truy xuất nhãn thuốc Structured Product Labeling.

**Base API:**  
https://dailymed.nlm.nih.gov/dailymed/services/v2/

**Endpoint quan trọng:**

- `/spls`
- `/spls/{SETID}`
- `/spls/{SETID}/ndcs`
- `/rxcuis`
- `/drugclasses`

Tài liệu:  
https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm

### 12.3. PubMed E-utilities

**Vai trò:** Tìm case report, observational study, review và meta-analysis.

**Giới hạn chính thức:**

- 3 request/second khi không có API key.
- 10 request/second với API key mặc định.

Tài liệu:  
https://www.ncbi.nlm.nih.gov/books/NBK25497/

### 12.4. ClinicalTrials.gov API v2

**Vai trò:** Tìm safety outcome và adverse-event information từ clinical trial.

Tài liệu:  
https://clinicaltrials.gov/data-api/api

### 12.5. EMA signal documents

**Vai trò:** Tạo retrospective benchmark và tham chiếu regulatory process.

Nguồn:

- https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/pharmacovigilance-post-authorisation/signal-management
- https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/pharmacovigilance-post-authorisation/signal-management/prac-recommendations-safety-signals

### 12.6. MedDRA

MedDRA hỗ trợ chuẩn hóa adverse-event terminology.

Academic và non-commercial organization có thể đăng ký gói non-profit/non-commercial miễn phí nếu đáp ứng điều kiện.

Nguồn:

- https://www.meddra.org/subscription/subscription-type
- https://www.meddra.org/subscription-rates

Nếu không thể dùng MedDRA, prototype có thể dùng:

- UMLS nếu có quyền truy cập.
- SNOMED CT theo điều kiện giấy phép.
- Dictionary nhỏ do nhóm quản lý.
- Từ đồng nghĩa lấy từ nhãn thuốc và literature.

---

## 13. Kiến trúc hệ thống đề xuất

### 13.1. Thành phần chính

1. Claim Intake Service.
2. Claim Normalizer.
3. Investigation Planner.
4. Source Router.
5. Search Tool Adapters.
6. Document Parser.
7. Evidence Extractor.
8. Scope Matcher.
9. Contradiction Analyzer.
10. Duplicate Detector.
11. Evidence Grader.
12. Stopping and Abstention Controller.
13. Dossier Generator.
14. Human Review Interface.
15. Audit and Provenance Store.

### 13.2. Sơ đồ logic

```text
Claim
  ↓
Claim Normalizer
  ↓
Evidence Checklist
  ↓
Investigation Planner
  ↓
Source Router ──→ PubMed
             ├─→ DailyMed
             ├─→ openFDA FAERS
             ├─→ ClinicalTrials.gov
             └─→ EMA/FDA documents
  ↓
Evidence Extraction
  ↓
Scope + Contradiction Analysis
  ↓
Evidence State Update
  ↓
Continue Search? ── Yes → Replan
        │
        No
        ↓
Dossier or Abstain
  ↓
Human Review
```

### 13.3. Công nghệ tham khảo

- Backend: Python và FastAPI.
- Agent orchestration: LangGraph hoặc state machine tự xây.
- Database: PostgreSQL.
- Vector search: pgvector hoặc Qdrant.
- Object storage: MinIO hoặc S3.
- Queue: Redis hoặc Celery.
- Frontend: Next.js hoặc React.
- Citation rendering: document span + source URL + retrieved timestamp.

Không bắt buộc dùng LangGraph. Một state machine minh bạch có thể phù hợp hơn cho nghiên cứu và audit.

---

## 14. Agent state

```json
{
  "claim": {},
  "normalized_claim": {},
  "investigation_plan": [],
  "evidence_checklist": [],
  "queries_executed": [],
  "documents_retrieved": [],
  "supporting_evidence": [],
  "contradicting_evidence": [],
  "scope_mismatches": [],
  "evidence_gaps": [],
  "duplicate_candidates": [],
  "budget": {
    "max_steps": 20,
    "steps_used": 0,
    "max_documents": 100,
    "documents_used": 0
  },
  "stop_reason": null,
  "abstention_reason": null,
  "human_review_status": "pending"
}
```

---

## 15. Tool contract đề xuất

### 15.1. `search_pubmed`

```json
{
  "query": "string",
  "date_from": "YYYY-MM-DD",
  "date_to": "YYYY-MM-DD",
  "article_types": [],
  "max_results": 20
}
```

### 15.2. `get_dailymed_label`

```json
{
  "drug_name": "string",
  "set_id": "optional",
  "label_version_date": "optional"
}
```

### 15.3. `query_faers`

```json
{
  "drug": "string",
  "event": "string",
  "date_range": {},
  "limit": 100
}
```

### 15.4. `search_clinical_trials`

```json
{
  "drug": "string",
  "condition": "optional",
  "status": [],
  "max_results": 20
}
```

### 15.5. `extract_evidence`

```json
{
  "document_id": "string",
  "claim_id": "string",
  "required_fields": [
    "population",
    "exposure",
    "event",
    "comparator",
    "time_window",
    "result",
    "limitations"
  ]
}
```

### 15.6. `request_human_review`

```json
{
  "reason": "string",
  "evidence_ids": [],
  "question": "string",
  "priority": "low|medium|high"
}
```

---

## 16. Evidence model

Mỗi evidence unit nên có cấu trúc:

```json
{
  "evidence_id": "ev-001",
  "source_id": "pmid-123",
  "source_type": "observational_study",
  "stance": "support|contradict|uncertain|background",
  "population": "string",
  "drug": "string",
  "dose": "string",
  "route": "string",
  "event": "string",
  "time_window": "string",
  "effect_measure": "string",
  "effect_value": "string",
  "limitations": [],
  "scope_match_score": 0.82,
  "quality_score": 0.70,
  "quoted_span": "exact source text",
  "source_url": "https://...",
  "retrieved_at": "timestamp"
}
```

### 16.1. Evidence hierarchy tham khảo

Agent không nên áp dụng hierarchy tuyệt đối. Một cấu hình tham khảo:

1. Regulatory assessment.
2. Systematic review hoặc meta-analysis.
3. Randomized trial safety data.
4. Observational comparative study.
5. Case series.
6. Case report.
7. Spontaneous reporting pattern.
8. Mechanistic hoặc class-effect evidence.

Chất lượng phụ thuộc claim và nguồn dữ liệu. Serious rare event có thể được kích hoạt bởi một số ít case chất lượng cao.

---

## 17. Scope-matching engine

### 17.1. Trường cần so khớp

- Active ingredient.
- Product hoặc formulation.
- Dose.
- Route.
- Indication.
- Population.
- Comorbidity.
- Concomitant medication.
- Event definition.
- Severity.
- Time to onset.
- Outcome.

### 17.2. Loại mismatch

```text
drug_mismatch
formulation_mismatch
dose_mismatch
route_mismatch
population_mismatch
indication_mismatch
event_definition_mismatch
time_window_mismatch
outcome_mismatch
```

### 17.3. Quy tắc

- Không loại tài liệu chỉ vì một mismatch nhỏ.
- Ghi rõ mismatch và ảnh hưởng đến khả năng áp dụng.
- Mismatch nghiêm trọng phải ngăn agent dùng tài liệu làm bằng chứng trực tiếp.
- Reviewer có quyền override.

---

## 18. Contradiction engine

### 18.1. Contradiction thật

Hai bằng chứng dùng phạm vi tương đương nhưng cho kết quả trái ngược.

### 18.2. Contradiction giả

Hai bằng chứng khác nhau về:

- Liều.
- Quần thể.
- Thời gian theo dõi.
- Event definition.
- Study design.
- Comparator.

Agent phải kiểm tra scope trước khi gắn nhãn contradiction.

### 18.3. Output contradiction

```json
{
  "evidence_a": "ev-001",
  "evidence_b": "ev-002",
  "contradiction_type": "direct|apparent|methodological",
  "explanation": "string",
  "requires_human_review": true
}
```

---

## 19. Planning policy

### 19.1. Evidence checklist ban đầu

Agent tạo checklist:

- Claim có trong nhãn thuốc không?
- Có regulatory communication không?
- Có systematic review không?
- Có comparative study không?
- Có case report hoặc case series không?
- FAERS có đủ record phù hợp để mô tả pattern không?
- Có bằng chứng phản bác không?
- Scope có nhất quán không?
- Có alternative explanation không?

### 19.2. Next-best action

Agent chọn bước tiếp theo theo:

```text
Expected information gain
× Evidence importance
× Source reliability
÷ Search cost
```

Không cần xây mô hình toán học phức tạp. Prototype có thể dùng rule-based score kết hợp LLM explanation.

### 19.3. Ví dụ replanning

- PubMed không có study phù hợp → tìm regulatory communication.
- Claim dùng brand name → chuẩn hóa active ingredient.
- Event term quá hẹp → mở rộng synonym.
- Nhiều false positive → thêm population hoặc indication filter.
- Bằng chứng chỉ có ở route khác → ghi scope mismatch và tìm route đúng.
- Tìm thấy contradiction → tạo sub-plan để giải thích khác biệt.

---

## 20. Stopping rule và abstention

### 20.1. Điều kiện dừng thành công

- Các evidence type bắt buộc đã được kiểm tra.
- Không còn evidence gap nghiêm trọng.
- Citation coverage đạt ngưỡng.
- Contradiction đã được giải thích hoặc chuyển human review.
- Search mới không tạo thông tin đáng kể.

### 20.2. Điều kiện abstain

- Không xác định được thuốc hoặc event.
- Claim quá rộng và người dùng không thu hẹp.
- Bằng chứng quá ít.
- Bằng chứng chỉ có ở quần thể khác.
- Nguồn chính không truy cập được.
- Contradiction chưa giải quyết.
- Dữ liệu FAERS bị hiểu nhầm thành causality hoặc incidence.
- Agent vượt search budget.

### 20.3. Abstention output

Agent phải trả:

- Lý do abstain.
- Bằng chứng hiện có.
- Dữ liệu còn thiếu.
- Bước tiếp theo cho reviewer.

---

## 21. Human-in-the-loop

### 21.1. Checkpoint bắt buộc

- Sau khi chuẩn hóa claim có độ mơ hồ cao.
- Trước khi kết luận `supported_for_scope`.
- Khi có contradiction quan trọng.
- Khi agent dùng regulatory interpretation.
- Trước khi xuất dossier chính thức.

### 21.2. Quyền của reviewer

- Sửa normalized claim.
- Loại evidence.
- Thêm evidence.
- Đổi stance.
- Đổi quality score.
- Yêu cầu agent tìm thêm.
- Override stop decision.
- Chấp nhận hoặc từ chối dossier.

### 21.3. Reviewer feedback

Feedback được lưu để:

- Phân tích lỗi.
- Điều chỉnh query template.
- Cải thiện scope matcher.
- Cải thiện calibration.

Không tự fine-tune model bằng dữ liệu nhạy cảm trong prototype.

---

## 22. Giao diện người dùng đề xuất

### 22.1. Trang nhập claim

- Claim text.
- Drug.
- Event.
- Population.
- Date cutoff.
- Allowed sources.
- Search budget.

### 22.2. Investigation timeline

Hiển thị:

- Bước agent đã thực hiện.
- Tool đã gọi.
- Query đã dùng.
- Tài liệu đã nhận.
- Lý do chọn bước tiếp theo.

### 22.3. Evidence matrix

Cột:

- Source.
- Evidence type.
- Population.
- Drug và dose.
- Event.
- Stance.
- Scope match.
- Quality.
- Citation.

### 22.4. Contradiction view

Hiển thị hai bằng chứng cạnh nhau và lý do khác biệt.

### 22.5. Dossier view

- Executive summary.
- Evidence map.
- Gaps.
- Limitations.
- Reviewer comments.
- Export Markdown hoặc PDF.

---

## 23. Thiết kế benchmark

### 23.1. Mục tiêu benchmark

Đánh giá ba hệ thống:

1. Keyword search baseline.
2. Single-shot RAG baseline.
3. Adaptive evidence investigation agent.

### 23.2. Bộ claim

Đề xuất 20–30 claim cho prototype.

Phân tầng:

- 5 claim có bằng chứng ủng hộ rõ.
- 5 claim có bằng chứng mâu thuẫn.
- 5 claim không đủ bằng chứng.
- 5 claim có scope mismatch.
- 5 claim chứa ambiguity hoặc synonym khó.
- 5 claim cần abstain.

Một claim có thể thuộc nhiều nhóm.

### 23.3. Nguồn tạo ground truth

Ưu tiên:

- Historical PRAC signal recommendations.
- FDA Drug Safety Communications.
- Label changes có ngày rõ ràng.
- Systematic review được chuyên viên chọn.
- Bộ claim do hai reviewer độc lập gán nhãn.

### 23.4. Retrospective time-slice evaluation

Để tránh data leakage:

1. Chọn một signal lịch sử.
2. Đặt investigation cutoff trước regulatory conclusion.
3. Chỉ cho agent truy cập tài liệu trước cutoff.
4. So sánh dossier với tài liệu sau đó và assessment chính thức.

Cách này đánh giá agent trong điều kiện gần với điều tra thật hơn.

### 23.5. Double-review protocol

- Hai reviewer đánh giá độc lập.
- Reviewer thứ ba xử lý bất đồng.
- Ghi Cohen’s kappa hoặc Krippendorff’s alpha.
- Tách gold evidence và optional evidence.

---

## 24. Chỉ số đánh giá

### 24.1. Retrieval

- Evidence Recall@K.
- Evidence Precision@K.
- Mean Reciprocal Rank.
- Coverage theo evidence type.
- Tỷ lệ truy xuất tài liệu ngoài cutoff.

### 24.2. Citation

- Citation precision.
- Citation completeness.
- Citation entailment.
- Source freshness.
- Source-authority distribution.

### 24.3. Scope

- Scope-match accuracy.
- Scope-mismatch recall.
- Field-level F1 cho population, dose, route và time window.

### 24.4. Contradiction

- Contradiction precision.
- Contradiction recall.
- Tỷ lệ contradiction giả do scope mismatch.

### 24.5. Abstention

- Abstention accuracy.
- Coverage-risk curve.
- Brier score.
- Expected calibration error.
- False-confidence rate.

### 24.6. Agent behavior

- Tool-selection accuracy.
- Replanning success rate.
- Average steps per claim.
- Unnecessary tool-call rate.
- Search-budget violations.
- Stop-decision accuracy.

### 24.7. Human impact

- Reviewer time per dossier.
- Tỷ lệ dossier được chấp nhận không cần sửa lớn.
- Số tài liệu reviewer phải mở lại.
- Reviewer trust score.
- NASA-TLX hoặc thang workload tương đương.

### 24.8. Safety

- Unsupported-claim rate.
- Causality-overclaim rate.
- Incidence-overclaim rate.
- Missing-citation rate.
- Stale-label rate.
- Human-approval bypass rate.

---

## 25. Acceptance criteria cho prototype

Một mốc tham khảo:

- Evidence Recall@20 ≥ 0,85 trên bộ claim thử nghiệm.
- Citation precision ≥ 0,95.
- Unsupported-claim rate ≤ 0,02.
- Scope-mismatch recall ≥ 0,80.
- Agent không dùng FAERS để kết luận incidence.
- Agent không dùng từ `causal` trong kết luận tự động.
- 100% dossier có audit log.
- 100% kết luận rủi ro cao có human approval.
- Reviewer time giảm ít nhất 25% so với baseline thủ công trong thử nghiệm nhỏ.

Các ngưỡng trên là mục tiêu thiết kế, không phải chuẩn regulator.

---

## 26. Demo scenario chi tiết

### 26.1. Scenario A: Claim quá rộng

**Input:**

```text
Drug X causes Event Y.
```

**Agent behavior:**

1. Phát hiện thiếu population, route và time window.
2. Chuẩn hóa active ingredient.
3. Tìm label và literature.
4. Phát hiện bằng chứng chỉ ở liều cao.
5. Gắn `dose_mismatch`.
6. Thu hẹp claim hoặc yêu cầu reviewer xác nhận.
7. Trả `insufficient_evidence` cho claim ban đầu.

**Điểm demo:** Scope checking và abstention.

### 26.2. Scenario B: Contradiction giả

**Input:** Một nghiên cứu cho kết quả tăng risk; một nghiên cứu không tăng risk.

**Agent behavior:**

1. So sánh population.
2. Phát hiện nghiên cứu thứ nhất ở người cao tuổi.
3. Phát hiện nghiên cứu thứ hai ở người trưởng thành trẻ.
4. Gắn `apparent_contradiction`.
5. Không gộp hai kết quả thành mâu thuẫn trực tiếp.

**Điểm demo:** Contradiction sau scope normalization.

### 26.3. Scenario C: FAERS bị hiểu sai

**Input:** FAERS có nhiều báo cáo Drug X–Event Y.

**Agent behavior:**

1. Kiểm tra duplicate candidate.
2. Ghi rõ reporting bias.
3. Không tính incidence.
4. Không kết luận causality.
5. Tìm label, literature và trial data.
6. Trả spontaneous-report pattern như evidence type riêng.

**Điểm demo:** Guardrail.

### 26.4. Scenario D: Replanning

**Input:** PubMed query ban đầu có quá nhiều kết quả không liên quan.

**Agent behavior:**

1. Phân tích false positive.
2. Thêm event synonym hoặc indication filter.
3. Chuyển từ brand name sang active ingredient.
4. Giới hạn article type.
5. Tìm regulatory source nếu literature vẫn yếu.

**Điểm demo:** Adaptive search.

---

## 27. MVP đề xuất

### 27.1. Phạm vi MVP

- Một drug-event pair tại một thời điểm.
- Ba nguồn: PubMed, DailyMed và openFDA FAERS.
- Một language: English.
- Tối đa 20 agent steps.
- Tối đa 50–100 documents mỗi investigation.
- Reviewer duyệt kết quả cuối.
- Export Markdown.

### 27.2. Tính năng bắt buộc

- Claim normalization.
- Evidence checklist.
- Multi-query search.
- Citation extraction.
- Scope checking.
- Contradiction detection cơ bản.
- Abstention.
- Audit log.

### 27.3. Tính năng không làm trong MVP

- Tự động regulatory submission.
- Causality assessment tự động.
- Real-time enterprise case ingestion.
- Multilingual literature review.
- Full MedDRA coding automation.
- Production-grade duplicate detection.
- Patient-level clinical recommendation.

---

## 28. Dữ liệu synthetic đề xuất

### 28.1. Synthetic claim set

Mỗi claim gồm:

- Claim text.
- Gold normalized fields.
- Required evidence list.
- Expected scope mismatches.
- Expected contradiction pairs.
- Expected stop status.

### 28.2. Synthetic case report

```json
{
  "case_id": "case-001",
  "age": 67,
  "sex": "F",
  "drug": "Drug X",
  "dose": "10 mg",
  "route": "oral",
  "indication": "Condition Z",
  "event": "Event Y",
  "time_to_onset_days": 14,
  "concomitant_drugs": [],
  "outcome": "recovered",
  "reporter_type": "physician"
}
```

### 28.3. Không dùng dữ liệu bệnh nhân thật

Prototype nên dùng:

- Public de-identified records.
- Synthetic case reports.
- Public regulatory documents.
- Public literature metadata.

Không nhập PHI hoặc confidential safety case narratives.

---

## 29. Duplicate detection

### 29.1. Mục tiêu

Tìm các report có thể mô tả cùng một case.

### 29.2. Feature tham khảo

- Age và sex.
- Event.
- Drug.
- Country.
- Event date.
- Report date.
- Dose.
- Outcome.
- Reporter type.
- Narrative similarity nếu có quyền dùng.

### 29.3. Output

- Duplicate candidate pair.
- Similarity score.
- Matching fields.
- Conflicting fields.
- Human-review requirement.

### 29.4. Giới hạn

Open public data có thể không đủ trường để xác nhận duplicate. Prototype chỉ nên gắn `duplicate_candidate`, không tự xóa case.

---

## 30. Prompt và policy design

### 30.1. System policy cốt lõi

```text
You are a pharmacovigilance evidence investigation assistant.
You do not establish causality.
You do not estimate incidence from spontaneous reports.
Every factual claim must cite a retrieved source.
Separate fact, inference, and hypothesis.
Abstain when evidence is insufficient or scope is mismatched.
Require human review for final assessment.
```

### 30.2. Structured output

Mọi node dùng JSON schema. Không cho phép free-text output ở bước điều khiển workflow.

### 30.3. Source hierarchy

Ưu tiên:

1. Official regulator.
2. Peer-reviewed literature.
3. Trial registry.
4. Product label.
5. Public spontaneous-report data.
6. Vendor material chỉ dùng cho market evidence.

### 30.4. Prompt-injection defense

Tài liệu truy xuất có thể chứa câu lệnh độc hại. Hệ thống phải:

- Xem document text là dữ liệu, không phải instruction.
- Loại script và hidden text.
- Không làm theo URL hoặc action trong document.
- Không để retrieved document thay đổi system policy.
- Ghi nguồn của mỗi extracted span.

---

## 31. Security và privacy

### 31.1. Dữ liệu

- Mã hóa dữ liệu lưu trữ.
- Mã hóa truyền tải.
- Không log PHI.
- Không gửi confidential case data sang public model API.
- Tách public evidence và internal evidence.

### 31.2. Phân quyền

- Viewer.
- Investigator.
- Medical reviewer.
- Quality reviewer.
- Administrator.

### 31.3. Audit

Lưu:

- User.
- Timestamp.
- Claim version.
- Query.
- Tool call.
- Source version.
- Evidence extraction.
- Reviewer edit.
- Final decision.

### 31.4. Reproducibility

Một investigation phải chạy lại được với:

- Cùng model version.
- Cùng prompt version.
- Cùng source cutoff.
- Cùng query configuration.

Kết quả có thể thay đổi nếu nguồn bên ngoài thay đổi. Vì vậy, hệ thống nên lưu document snapshot hoặc hash khi giấy phép cho phép.

---

## 32. Regulatory framing

### 32.1. EMA GVP Module IX

Signal-management process gồm:

- Signal detection.
- Validation.
- Confirmation.
- Analysis và prioritisation.
- Assessment.
- Recommendation for action.

Nguồn:  
https://www.ema.europa.eu/en/documents/scientific-guideline/guideline-good-pharmacovigilance-practices-gvp-module-ix-signal-management-rev-1_en.pdf

Prototype chỉ hỗ trợ evidence investigation. Prototype không tuyên bố tuân thủ đầy đủ GVP.

### 32.2. EMA AI reflection paper

EMA nhấn mạnh:

- Risk-based development.
- Data governance.
- Performance evaluation.
- Transparency.
- Human oversight.
- Lifecycle monitoring.

Nguồn:  
https://www.ema.europa.eu/system/files/documents/scientific-guideline/reflection-paper-use-artificial-intelligence-ai-medicinal-product-lifecycle-en.pdf

### 32.3. Tuyên bố sản phẩm an toàn

Prototype phải ghi rõ:

> Research decision-support prototype. Not for autonomous causality assessment, regulatory submission, or clinical decision-making.

---

## 33. Rủi ro chính và biện pháp giảm thiểu

| Rủi ro | Tác động | Biện pháp |
|---|---|---|
| Hallucinated citation | Dossier không đáng tin | Chỉ cho phép citation từ retrieved source |
| Causality overclaim | Sai an toàn nghiêm trọng | Hard rule cấm kết luận causal |
| Scope mismatch | Áp dụng sai quần thể | Field-level scope matcher |
| Search incompleteness | Bỏ sót bằng chứng | Evidence checklist và recall benchmark |
| False contradiction | Làm reviewer hiểu sai | Chuẩn hóa scope trước contradiction |
| Duplicate FAERS reports | Thổi phồng pattern | Duplicate candidate detection |
| Stale label | Kết luận lỗi thời | Lưu version date và retrieval time |
| Prompt injection | Thay đổi hành vi agent | Treat documents as untrusted data |
| Excessive tool use | Chi phí và độ trễ cao | Search budget và stopping rule |
| Automation bias | Reviewer quá tin hệ thống | Hiển thị uncertainty và alternative evidence |

---

## 34. Failure-mode test suite

### Test 1: Không có citation

Hệ thống phải chặn câu kết luận.

### Test 2: FAERS count được dùng làm incidence

Hệ thống phải từ chối và ghi limitation.

### Test 3: Claim không có event

Hệ thống phải yêu cầu làm rõ.

### Test 4: Evidence khác route

Hệ thống phải gắn route mismatch.

### Test 5: Hai nghiên cứu khác population

Hệ thống không được gọi contradiction trực tiếp.

### Test 6: Retrieved document chứa prompt injection

Hệ thống phải bỏ qua instruction trong tài liệu.

### Test 7: Source API unavailable

Agent phải dùng fallback hoặc abstain.

### Test 8: Search budget exhausted

Agent phải dừng, ghi evidence gap và không tự kết luận.

---

## 35. Kế hoạch triển khai 10 tuần

### Tuần 1: Problem framing

- Chốt claim schema.
- Chốt source list.
- Chọn 20–30 benchmark claim.
- Viết safety policy.

### Tuần 2: Data connectors

- PubMed connector.
- DailyMed connector.
- openFDA connector.
- Source cache.

### Tuần 3: Claim normalization

- Drug normalization.
- Event normalization.
- Synonym expansion.
- Scope schema.

### Tuần 4: Retrieval baseline

- Keyword baseline.
- Single-shot RAG baseline.
- Citation storage.

### Tuần 5: Agent planner

- Evidence checklist.
- Tool routing.
- Search budget.
- State machine.

### Tuần 6: Scope và contradiction

- Scope matcher.
- Contradiction pair generation.
- Human-review trigger.

### Tuần 7: Abstention và dossier

- Stopping rule.
- Abstention reason.
- Dossier generator.
- Audit log.

### Tuần 8: Reviewer UI

- Investigation timeline.
- Evidence matrix.
- Dossier export.

### Tuần 9: Evaluation

- Run baseline.
- Run agent.
- Reviewer assessment.
- Error analysis.

### Tuần 10: Hardening và demo

- Failure-mode tests.
- Prompt-injection tests.
- Cost profiling.
- Demo recording.
- Final report.

---

## 36. Phân công nhóm tham khảo

### Thành viên 1: Data và API

- PubMed.
- DailyMed.
- openFDA.
- Cache và provenance.

### Thành viên 2: Agent orchestration

- State machine.
- Planner.
- Tool routing.
- Stopping rule.

### Thành viên 3: Evidence intelligence

- Claim normalization.
- Scope matching.
- Contradiction detection.
- Evidence grading.

### Thành viên 4: UI và evaluation

- Reviewer interface.
- Benchmark.
- Metrics.
- Demo.

---

## 37. Chi phí prototype

### 37.1. Chi phí có thể bằng 0

- PubMed API.
- DailyMed API.
- openFDA API.
- ClinicalTrials.gov API.
- PostgreSQL local.
- Qdrant hoặc pgvector local.
- Open-source embedding model.

### 37.2. Chi phí phát sinh

- LLM API.
- Hosting.
- Object storage.
- Domain.
- MedDRA nếu không đủ điều kiện non-commercial miễn phí.

### 37.3. Ước tính sinh viên

- Local prototype: 0–100 USD.
- Hosted demo nhỏ: 50–300 USD.
- Evaluation lớn: phụ thuộc model và số document.

Giảm chi phí bằng:

- Cache search result.
- Dùng model nhỏ cho extraction.
- Chỉ dùng model mạnh cho planning và final synthesis.
- Giới hạn document và step budget.

---

## 38. So sánh ba lựa chọn phạm vi

| Lựa chọn | Ưu điểm | Nhược điểm | Khuyến nghị |
|---|---|---|---|
| Full signal detection | Tác động lớn | Quá rộng, khó ground truth | Không chọn MVP |
| Literature screening agent | Dễ đánh giá | Agent behavior chưa rõ | Dùng làm baseline |
| Adaptive evidence investigation | Agent rõ, mới, có dữ liệu mở | Cần thiết kế benchmark tốt | Nên chọn |

---

## 39. Điểm mới của đề tài

Không nên tuyên bố “chưa ai làm”. Điểm mới nên được mô tả có giới hạn:

1. Agent lập evidence-gap map trước khi tìm kiếm.
2. Agent chọn nguồn tiếp theo theo evidence gap.
3. Agent kiểm tra scope trước khi tổng hợp.
4. Agent tìm contradiction có chủ đích.
5. Agent có stopping rule và abstention có giải thích.
6. Agent tạo audit trail có thể tái lập.
7. Agent được đánh giá trực tiếp với keyword search và single-shot RAG.

### Câu phát biểu novelty đề xuất

> Nghiên cứu tập trung vào adaptive evidence investigation cho pharmacovigilance safety claims, trong đó agent chủ động xác định evidence gap, lập lại kế hoạch truy xuất, kiểm tra scope và contradiction, sau đó tạo dossier có provenance hoặc abstain.

---

## 40. Câu pitch 30 giây

> Chuyên viên cảnh giác dược phải ghép bằng chứng từ báo cáo bất lợi, nhãn thuốc và literature để kiểm tra một nhận định an toàn. Công cụ hiện tại thường tìm kiếm, trích xuất hoặc thống kê riêng lẻ. Nhóm xây dựng một AI Agent tự xác định bằng chứng còn thiếu, chọn nguồn cần tìm tiếp, kiểm tra phạm vi và mâu thuẫn, rồi tạo evidence dossier có trích nguồn hoặc từ chối kết luận. Chuyên viên vẫn quyết định cuối cùng.

---

## 41. Câu trả lời phản biện thường gặp

### “Đây chỉ là RAG phải không?”

Không. RAG là một tool trong hệ thống. Agent duy trì investigation state, lập kế hoạch nhiều bước, thay đổi query, đổi nguồn, tìm contradiction và quyết định dừng hoặc abstain.

### “FAERS có chứng minh thuốc gây biến cố không?”

Không. FAERS chỉ cung cấp spontaneous-report evidence. Agent phải ghi rõ không thể suy luận causality hoặc incidence.

### “Tại sao không dùng ChatGPT?”

ChatGPT không bảo đảm search coverage, source version, scope matching, stopping rule và reproducible audit trail.

### “Sản phẩm đã có rồi thì đề tài còn mới không?”

Enterprise product đã chứng minh nhu cầu. Đề tài không cạnh tranh toàn bộ safety platform. Đề tài tập trung vào adaptive evidence-gap investigation và explainable abstention.

### “Ai chịu trách nhiệm khi agent sai?”

Chuyên viên giữ quyền quyết định. Agent chỉ là decision-support tool. Mọi kết luận quan trọng cần human approval.

### “Đánh giá như thế nào?”

So sánh agent với keyword search và single-shot RAG trên cùng bộ claim. Đo retrieval, citation, scope, contradiction, abstention, thời gian reviewer và safety violations.

---

## 42. Deliverable cuối kỳ

1. Web application.
2. Agent workflow.
3. Ba data connectors.
4. Evidence dossier export.
5. Benchmark dataset.
6. Baseline RAG.
7. Evaluation report.
8. Safety test suite.
9. Demo scenario.
10. Technical documentation.

---

## 43. Tiêu chí go/no-go

### Go

- Nhóm truy cập được PubMed, DailyMed và openFDA.
- Có ít nhất 20 claim có reviewer label.
- Citation correctness đạt mức cao.
- Agent chứng minh replanning.
- Agent abstain được.
- Có reviewer UI và audit log.

### No-go hoặc cần thu hẹp

- Không có reviewer am hiểu dược hoặc y khoa.
- Không tạo được gold evidence set.
- Agent chỉ tóm tắt top-k document.
- Không kiểm soát causality overclaim.
- Không có human-in-the-loop.
- Không đo được lợi ích so với RAG.

---

## 44. Kết luận cuối

Đây là đề tài mạnh nếu nhóm xác định đúng phạm vi.

Không nên xây một hệ thống “AI phát hiện thuốc nguy hiểm”. Cách mô tả đó quá rộng và không an toàn.

Nên xây:

> AI Agent điều tra bằng chứng cho một drug-safety claim, có khả năng lập kế hoạch, kiểm tra scope, tìm contradiction, quản lý provenance và abstain.

Đề tài có ba lợi thế:

- Pain point và thị trường đã được chứng minh.
- Dữ liệu public đủ cho prototype.
- Năng lực agent khác LLM và RAG có thể đo được.

Rủi ro lớn nhất là overclaim causality. Vì vậy, thiết kế phải đặt citation, uncertainty, abstention và human review làm yêu cầu cốt lõi.

---

## 45. Nguồn tham khảo

### Cơ quan quản lý và dữ liệu

- EMA 2024 EudraVigilance Annual Report: https://www.ema.europa.eu/system/files/documents/report/2024-annual-report-eudravigilance-en.pdf
- EMA signal management: https://www.ema.europa.eu/en/human-regulatory-overview/post-authorisation/pharmacovigilance-post-authorisation/signal-management
- EMA GVP Module IX: https://www.ema.europa.eu/en/documents/scientific-guideline/guideline-good-pharmacovigilance-practices-gvp-module-ix-signal-management-rev-1_en.pdf
- EMA AI reflection paper: https://www.ema.europa.eu/system/files/documents/scientific-guideline/reflection-paper-use-artificial-intelligence-ai-medicinal-product-lifecycle-en.pdf
- FDA openFDA drug event API: https://open.fda.gov/apis/drug/event/
- FDA FAERS Public Dashboard: https://www.fda.gov/drugs/fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-public-dashboard
- WHO pharmacovigilance: https://www.who.int/teams/regulation-prequalification/regulation-and-safety/pharmacovigilance
- WHO-UMC glossary: https://who-umc.org/pharmacovigilance-communications/glossary/

### API và terminology

- DailyMed API: https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- ClinicalTrials.gov API v2: https://clinicaltrials.gov/data-api/api
- MedDRA subscription: https://www.meddra.org/subscription/subscription-type
- MedDRA rates: https://www.meddra.org/subscription-rates

### Sản phẩm

- ArisGlobal LifeSphere Safety: https://www.arisglobal.com/lifesphere/safety/
- ArisGlobal scale statement: https://www.arisglobal.com/media/press-release/arisglobals-lifesphere-safety-solidifies-market-leading-position-in-pharmacovigilance-with-over-300-customers-and-more-than-7-million-safety-cases-processed-annually/
- Oracle Empirica Signal: https://docs.oracle.com/health-sciences/empirica-signal-90/ESIUG/Home_page_1.htm
- Veeva literature review: https://www.veeva.com/resources/faster-literature-review-to-case-intake/
- Veeva Safety: https://www.veeva.com/products/veeva-safety/

### Nghiên cứu AI trong pharmacovigilance

- LLM literature-screening study: https://public-pages-files-2025.frontiersin.org/journals/drug-safety-and-regulation/articles/10.3389/fdsfr.2024.1379260/pdf
- AI in pharmacovigilance review: https://www.jmir.org/2024/1/e50274/
- Review of AI development in pharmacovigilance: https://pmc.ncbi.nlm.nih.gov/articles/PMC12858747/

---
