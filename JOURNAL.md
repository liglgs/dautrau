# Weekly Journal — Team [Tên Team]

> Ghi lại mỗi tuần: học được gì, khó khăn gì, quyết định gì, kế hoạch tiếp.

---

## Week 1: [Ngày bắt đầu] - [Ngày kết thúc]

### Mục tiêu tuần này
- [ ] [Mục tiêu 1]
- [ ] [Mục tiêu 2]
- [ ] [Mục tiêu 3]

### Đã hoàn thành
- [thành quả 1]
- [thành quả 2]

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| [mô tả] | [cách xử lý] | [output] |

### Bài học
- [bài học 1]
- [bài học 2]

### Kế hoạch tuần sau
- [ ] [task 1]
- [ ] [task 2]

---

## Week 2: [Ngày bắt đầu] - [Ngày kết thúc]

### Mục tiêu tuần này
- [ ] [Mục tiêu 1]

### Đã hoàn thành
-

### Khó khăn & Giải pháp
| Khó khăn | Giải pháp | Kết quả |
|----------|-----------|---------|
| | | |

### Bài học
-

### Kế hoạch tuần sau
-

---

<!-- Tiếp tục copy block trên cho Week 3, 4, 5, 6 -->

## Ghi nhận 03/10/2026 — tách PR Người 4 trên main

Đối chiếu VinhDang `0965747` với main `fa1c1d1`: backend Người 3 và gói connectors/PubMed local/Docker Người 1 đã có, không nhập lại. Tách P26, frontend Draft và handoff P29 thành ba PR độc lập target main. [Status](docs/PERSON4_STATUS.md) ghi phạm vi và phụ thuộc.

Review P26 phát hiện detection thiếu validation và source versions có thể lọt split; thêm 20 regression tests và sửa, review lại không còn Critical/Important. Windows 509 pass+1 skip, Linux Docker 510 pass, đều 28 subtests; replay synthetic 4/4/2/2 rows không lỗi. Không coi fixture authored là chất lượng agent.

Frontend lint/types/API types/29 unit tests/build xanh nhưng browser candidate E2E 4 pass/6 fail sau cache mới, integration 1 fail. Giữ Draft, cần sửa/kiểm chứng navigation và review trước nghiệm thu. GitHub CI bị billing, chưa có jobs chạy; không tuyên bố CI xanh. Media/deck, gold/recordings/agent/session và nghiệm thu nhóm còn thiếu. Không ghi thời gian hoặc hiệu quả reviewer khi chưa đo.
