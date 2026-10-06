# R2-3-06 — Đặc tả trường ca ADR và mẫu nháp

**Trạng thái:** đề xuất, chờ dược sĩ xác nhận. Đặc tả chuẩn bị để pilot theo SOP của đơn vị; không phải mẫu báo cáo được chấp nhận, không tự tính Naranjo/WHO-UMC và không yêu cầu rechallenge.

## Định danh và phiên bản

- `case_id`: mã nội bộ đã khử định danh, bất biến. Bổ sung cùng `case_id` không tạo ca mới.
- `case_version`: số tăng dần; `supersedes_version` trỏ bản trước. Mỗi bổ sung ghi `received_at`, `entered_by`, `source_ref`.
- `record_kind`: `initial`, `follow_up`, `correction`, hoặc `duplicate_candidate`. `duplicate_candidate` chỉ là cờ để dược sĩ đối chiếu, không gộp/xóa tự động.
- `synthetic`: bắt buộc `true` ở tình huống kỹ thuật. Không dùng dữ liệu bệnh nhân thật trong tài liệu này.

## Trường cần thu và trạng thái thiếu

| Nhóm | Trường đề xuất | Quy tắc |
| --- | --- | --- |
| Exposure | thuốc tên gốc/nguồn mapping, dạng, hàm lượng, route, liều, administrations bắt đầu/kết thúc | Giữ tên gốc và candidate; ngày/giờ `unknown` là hợp lệ. Không suy route/hàm lượng. |
| Outcome | mô tả observed, thời điểm bắt đầu/kết thúc, kết quả hiện tại, seriousness và severity riêng | `severity`, `seriousness`, `causality`, `expectedness` là trục độc lập. `unknown` không phải `false`. |
| Timeline | các events có time value hoặc `unknown`, timezone nếu biết, nguồn dữ kiện | Không chèn giờ giả để sắp thứ tự; có thể ghi thứ tự không xác định. |
| Evidence ca | labs với giá trị/đơn vị/thời điểm, observations, ảnh/tài liệu chỉ khi được phép, `source_ref` từng trường | Bài PubMed/nhãn là bối cảnh, không là diễn biến của ca. |
| Alternative causes | chẩn đoán, bệnh nền, thuốc đồng thời, xét nghiệm hoặc `unknown` | Không điền “không có” nếu chưa được đánh giá. |
| Dechallenge/rechallenge | `observed`, `not_observed`, `not_done`, hoặc `unknown`, cùng nguồn/ thời điểm | Không yêu cầu dùng lại thuốc; `unknown` khác `not_observed`. |
| Assessment | người đánh giá, thời điểm, framework theo SOP (nếu có), reasoning, gaps | Không sinh category/score khi dữ kiện thiếu. |
| Reporting | report form/version, receiving endpoint, submission status, follow-up need | Chỉ đặt trạng thái gửi khi SOP/đầu mối xác nhận. |

## Checklist trước khi hiển thị mẫu báo cáo nháp

1. Liên kết đúng `case_id` và `case_version`; rà soát `duplicate_candidate` với con người.
2. Hiển thị từng trường `unknown/not_recorded/not_assessed`, không thay bằng phủ định.
3. Tách observation ca, fact từ nguồn, inference và việc cần bổ sung.
4. Chỉ hiển thị seriousness/causality/expectedness khi người có thẩm quyền đã đánh giá; nếu không ghi “chưa đánh giá”.
5. Gắn provenance cho field có giá trị: người/nguồn, thời điểm nhận và phiên bản.

Mọi mẫu nháp và tình huống ở đây phải mang nhãn: **đề xuất, chờ dược sĩ xác nhận**.
