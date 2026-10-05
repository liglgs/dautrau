> SYNTHETIC DRAFT — chưa duyệt, không phải bằng chứng y khoa.

# Hồ sơ điều tra INV-a124c521c568 (bản 1)

> Mẫu dự phòng: hồ sơ luôn được sinh từ dữ liệu đã lưu (không cần LLM), kể cả khi hết ngân sách.

- Trạng thái duyệt: pending
- Kết luận trong phạm vi: Cần người có chuyên môn phân xử.
- Duyệt bởi: chưa duyệt
- Mã nội dung: fa7a26b28d9e03fd614a874efef0e2c13e196d399a2dafdd2f31af34d5312565

Cần người có chuyên môn phân xử.
Audit: INV-a124c521c568 / audit_events / review_decisions.

## Claim
Fictional demo: Drug Alpha and Event Alpha in the stated scope.

## Phạm vi áp dụng
drug: Drug Alpha
event: Event Alpha
population: adults
dose: 10 mg/day
route: oral
time_window: 30 days

## Chiến lược truy xuất
Sources: pubmed
Steps: 0/8
LLM calls: 2/80


## Bằng chứng đã truy xuất
Drug Alpha increased Event Alpha in a fictional controlled comparison.

- [EV-P3-a717be88db847e2bfb7bfecd v1](https://example.org/synthetic/person3-demo) source=SYNTHETIC-DEMO-A v1; sha256=13cb9c66f503e5da590a2888618461f45230c77f5ba975581c16512c5b3f5ba7

Bằng chứng: EV-P3-a717be88db847e2bfb7bfecd

## Bằng chứng đã truy xuất
Drug Alpha decreased Event Alpha in a fictional controlled comparison.

- [EV-P3-2b6e7471e39f40db4bc342f7 v1](https://example.org/synthetic/person3-demo-b) source=SYNTHETIC-DEMO-B v1; sha256=a8434352f9c5a3fec1a2231bb9a0df5bcaa15e0260eca08e1a5a39fb2b3b588d

Bằng chứng: EV-P3-2b6e7471e39f40db4bc342f7

## Phạm vi và mâu thuẫn
Direct contradiction candidate [EV-P3-2b6e7471e39f40db4bc342f7, EV-P3-a717be88db847e2bfb7bfecd]: opposing findings in the same explicit scope; review required.

## Khoảng trống bằng chứng
Direct contradiction candidate [EV-P3-2b6e7471e39f40db4bc342f7, EV-P3-a717be88db847e2bfb7bfecd]: opposing findings in the same explicit scope; review required.

## Kết luận trong phạm vi claim
Cần người có chuyên môn phân xử.

Bằng chứng: EV-P3-a717be88db847e2bfb7bfecd, EV-P3-2b6e7471e39f40db4bc342f7

- Stop reason: not recorded
- Semantic interpretation requires reviewer approval.
