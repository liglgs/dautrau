# Thử phần Người 3 qua các kịch bản

> Dữ liệu hư cấu. Code Python Người 3, gateway và SQLite/review của Người 2 được gọi thật; model/nguồn được giả lập. Đây là thử các dịch vụ, chưa chạy toàn LangGraph/API/UI.

| Kịch bản | Kết quả code trả về | Đối chiếu fixture |
|---|---|---|
| Bằng chứng phù hợp | `supported_for_scope` | Đạt |
| Claim oral, nguồn intravenous | `scope_mismatch` | Đạt |
| Nguồn thiếu liều claim yêu cầu | `insufficient_evidence` | Đạt |
| Kết quả null còn bất định | `insufficient_evidence` | Đạt |
| Quote không có trong nguồn | `insufficient_evidence` | Đạt |
| Hai nghiên cứu cùng scope trái chiều | `requires_human_review` | Đạt |
| Brand có hai hoạt chất ứng viên | `requires_human_review` | Đạt |
| Chỉ có báo cáo FAERS | `insufficient_evidence` | Đạt |

## Cách đọc kết quả

Mỗi file JSON chứa input, claim chuẩn hóa, văn bản nguồn, evidence/quote/locator, scope, lý do đánh giá, gaps và ngân sách. File dossier đi kèm là đầu ra nháp.

## Bằng chứng phù hợp

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `supported_for_scope`.
- Evidence: 1; bị loại: 0; LLM mock calls: 1.
- [Input và output đầy đủ](match.json) · [Dossier nháp](match-dossier.md).

**Thử duyệt hồ sơ bằng SQLite tạm:** trước duyệt export bị chặn; sau quyết định duyệt giả lập export được; sửa evidence thì export bị chặn lại. Không phải quyết định duyệt của người dùng.

## Claim oral, nguồn intravenous

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `scope_mismatch`.
- Evidence: 1; bị loại: 0; LLM mock calls: 1.
- [Input và output đầy đủ](route_mismatch.json) · [Dossier nháp](route_mismatch-dossier.md).

## Nguồn thiếu liều claim yêu cầu

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `insufficient_evidence`.
- Evidence: 1; bị loại: 0; LLM mock calls: 1.
- [Input và output đầy đủ](missing_scope.json) · [Dossier nháp](missing_scope-dossier.md).

## Kết quả null còn bất định

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `insufficient_evidence`.
- Evidence: 1; bị loại: 0; LLM mock calls: 1.
- [Input và output đầy đủ](imprecise_null.json) · [Dossier nháp](imprecise_null-dossier.md).

## Quote không có trong nguồn

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `insufficient_evidence`.
- Evidence: 1; bị loại: 1; LLM mock calls: 1.
- [Input và output đầy đủ](fake_quote.json) · [Dossier nháp](fake_quote-dossier.md).

## Hai nghiên cứu cùng scope trái chiều

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `requires_human_review`.
- Evidence: 2; bị loại: 0; LLM mock calls: 2.
- [Input và output đầy đủ](contradiction.json) · [Dossier nháp](contradiction-dossier.md).

## Brand có hai hoạt chất ứng viên

- Claim: `Brand Ambiguous` / `Event Alpha`; route `oral`.
- Kết quả: `requires_human_review`.
- Evidence: 0; bị loại: 0; LLM mock calls: 0.
- [Input và output đầy đủ](ambiguous_brand.json) · [Dossier nháp](ambiguous_brand-dossier.md).

## Chỉ có báo cáo FAERS

- Claim: `Drug Alpha` / `Event Alpha`; route `oral`.
- Kết quả: `insufficient_evidence`.
- Evidence: 1; bị loại: 0; LLM mock calls: 1.
- [Input và output đầy đủ](faers_only.json) · [Dossier nháp](faers_only-dossier.md).
