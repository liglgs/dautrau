# Contract dự thảo Người 3 — lưu để đối chiếu

Adapter đã chuyển sang public models của Người 2 trên main. Xem [README.md](README.md) và [integration.patch](integration.patch) cho triển khai hiện tại; các kiểu dự thảo bên dưới không phải contract API mới.

## 1. Đầu vào cần từ Người 1 và Người 2

| Dữ liệu | Trường cần có | Cần thống nhất |
|---|---|---|
| Normalized claim | claim ID/version, canonical ingredient/event, population, dose, route, time window, unknowns, ambiguities | Phân biệt null, ambiguous và giá trị đã xác minh; giữ nguyên original claim |
| Source document | document ID, source, source ID/version/URL, retrieved_at, raw/parsed hash, parser version, text, content level, license | Hash trên đúng parsed text; không tự làm sạch text lần nữa khi kiểm quote |
| Locator | parsed-text offsets; section ID nếu có | Unicode code points, start inclusive/end exclusive; chuyển từ byte offsets hoặc JS UTF-16 bằng mapping |
| LLM gateway | schema-validated output, model/prompt hash, usage/error | Người 2 quản lý reserve/counters; extraction không tự retry không giới hạn |

`ScopeDraft` hiện minh họa canonical ingredient/event, age interval (years), dose interval, route, time interval, comparator và unresolved critical fields. Đây chưa phải mô hình population đầy đủ: sex, comorbidity, indication, event severity/definition và concomitant medications phải được giữ nếu có, hoặc tạo critical unknown khi ảnh hưởng áp dụng.

Không tự chuyển prose như “trẻ em”, “liều tiêu chuẩn”, “30 ngày đầu” thành khoảng số nếu chưa có normalization rule/source. Khoảng draft là inclusive và không tự chuyển mg sang g hoặc giờ sang ngày. Những giới hạn này tránh bịa dữ liệu trong lúc chưa có parser/gateway.

## 2. Đầu ra từ Người 3

| Giao tiếp | Contract cần chốt | Prototype hiện có |
|---|---|---|
| Normalization | Input drug/event/claim → canonical candidates, unknowns, ambiguities, dictionary version | `normalize_claim(drug, event, dictionary, allow_synthetic=False)`; lookup exact, chưa parse claim text |
| Extraction | `extract_evidence(document, claim) -> list[EvidenceUnit]` | Prompt và expected behavior; chờ gateway |
| Scope | `assess_scope(evidence, claim) -> ScopeAssessment` | `assess_scope(ScopeDraft, ScopeDraft)`; adapter cần lấy scope từ EvidenceUnit |
| Contradiction | Evidence list → candidate pairs, type/reason/fields, review flag | `compare_evidence(left, right)`; chưa có batch selection hoặc model adjudication |
| Citation integrity | SourceDocument + citation → lỗi provenance/span | `validate_citation(DocumentDraft, CitationDraft)` |
| Citation entailment | Statement + quote/context + scope → supported/unsupported/uncertain và reason | Chờ review chuyên môn hoặc gateway riêng; không suy từ URL/hash |
| Dossier | `build_dossier(state) -> Dossier` với typed statements/evidence version refs | Template Markdown và preview synthetic; chờ state/approval/version |

Scope eligibility chỉ là một điều kiện để dùng evidence trực tiếp, không phải assessment supported/contradicted. `unknown` không bao giờ được đổi thành `matched`. Unknown ở field không được claim yêu cầu và không có trong source có thể là limitation không blocking; phải trình bày phạm vi không biết, không đưa kết luận bao phủ field đó.

## 3. Field chuẩn bị cho EvidenceUnit

- evidence_id/version, claim_id/version, document_id/version, parsed content_hash.
- stance: support/contradict/uncertain/background, kèm claim relation và lý do.
- normalized scope và raw source values; effect measure/value/CI khi có; không suy ra từ source type.
- quoted_span, span_locator, source ID/URL/version, content_level và limitations.
- field-level ScopeAssessment, eligibility, semantic citation review status, reviewer reason/version.
- quality facets có lý do; không có causal probability.

Không dùng dict tùy ý do LLM trả để điều hướng graph. Prototype dùng dataclass local; public request/output dùng Pydantic và field validation sau M01.

## 4. Các quyết định cần M01 xác nhận

1. Cách biểu diễn age, dose và time window; đơn vị, dấu < / <= và nhóm gồm nhiều population.
2. Bộ scope field bắt buộc để evidence đủ điều kiện trực tiếp; partial coverage là unknown hoặc mismatch có subtype. Hiện prototype dùng unknown + blocking cho overlap/claim rộng.
3. Comparator và event definition/outcome cần explicit khi xác nhận contradiction trực tiếp. Hiện comparator thiếu chuyển needs_review.
4. Tên field canonical (`checkpoint_kind`, stance, locator/hash/version) và cấu trúc errors/review flags.
5. Sửa stance/scope/evidence phải invalidation assessment/dossier; Người 2 thực hiện transaction/version.
6. Việc source error, FAERS-only, budget exhaustion và critical unknown được chuyển thành gap/assessment nào trong stopping policy.
7. Cách đánh giá entailment, người duyệt, cách lưu kết quả và việc xử lý uncertain.

Không gửi token/keys trong contract, fixture hoặc prompt. Mọi source URL production được adapter allowlist tạo và truy xuất; citation checker chỉ so sánh provenance, không thay adapter/network validation.
# Cập nhật sau khi Người 2 đưa code lên main

Phần bên dưới là proposal giai đoạn chuẩn bị. Adapter hiện dùng public models Người 2; xem [README.md](README.md) và [integration.patch](integration.patch) để review thay đổi cụ thể. Không dùng kiểu `Draft` bên dưới làm contract API mới. Context chưa có trong schema chung tạm lưu JSON có version trong `EvidenceUnit.notes`.

