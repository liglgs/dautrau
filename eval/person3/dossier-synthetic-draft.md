# Hồ sơ điều tra bằng chứng — SYN-PERSON3-PREVIEW

> **NHÁP SYNTHETIC — dữ liệu giả lập, chưa được chuyên viên duyệt**
> Chế độ: synthetic (offline). Phiên bản: draft-0.1. Phê duyệt hồ sơ: pending.

## 1. Nhận định và phạm vi

Nhận định kỹ thuật giả lập về ingredient_alpha / event_alpha. Tuổi 18–65, oral, 10 mg/day, 0–30 days. Các giá trị không mô tả thuốc thật.

## 2. Đánh giá

- Đề xuất: requires_human_review (minh họa; không phải output của Agent)
- Assessment đã được reviewer xác nhận: null — chưa có assessment review
- Lý do dừng hoặc chưa thể kết luận: Preview kết thúc sau kiểm tra kỹ thuật; chưa có truy xuất nguồn thật hoặc đánh giá chuyên môn.

## 3. Chiến lược tìm kiếm

Không có truy vấn live. Đọc fixture đã lưu trong tests/fixtures/mvp/person3/cases.json.

## 4. Bằng chứng

| ID | Nguồn | Stance | Citation |
|---|---|---|---|
| SYN-E-001 | Synthetic excerpt | background | SYN-SOURCE-001 v1; entailment pending |

## 5. Phạm vi áp dụng và mâu thuẫn

Các ca S01–S08/C01–C04 có output trong technical-results.json. Đây là các tình huống độc lập, không phải bằng chứng của cùng một cuộc điều tra.

## 6. Phần còn thiếu và giới hạn

- Chưa có corpus thật, LLM extraction, gateway hoặc gold chuyên môn.
- Quote/hash đúng chỉ xác nhận vị trí; statement entailment vẫn pending.
- Dictionary hoàn toàn synthetic.
- Không có approval hoặc export chính thức.

## 7. Citations

SYN-SOURCE-001 v1 · synthetic_excerpt · document SYN-DOC-001

> Participants were aged 18 to 65 years.

Locator: Unicode offsets [72, 110).

Parsed-text SHA-256: `c520ac3833cd9f046b5ba7ded2e612d7eed7969c07d6e9fcee0d0061ba29cb69`.

Source URL: `https://example.invalid/synthetic/person3/SYN-SOURCE-001` — placeholder synthetic, không phải nguồn đã truy xuất.

## 8. Quyết định của reviewer

Chưa có quyết định. Không gán reviewer giả hoặc trạng thái approved.

## 9. Audit và provenance

technical-results.json lưu fixture hash, dictionary version và output từng ca. Đây là trace kiểm tra kỹ thuật, chưa phải audit log của Agent.

Prototype hỗ trợ tổ chức bằng chứng; đánh giá cuối cùng thuộc chuyên viên.
