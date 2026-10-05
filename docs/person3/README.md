# Người 3 — trên code tổng hợp

Ngày 2026-10-03, `tiendat` đã nhận `origin/main` tại `75b015d` qua merge `6d760d4`. Máy đã có code bàn giao của cả bốn người. Tích hợp runtime Người 3 ở commit `4bf3d71`; phần bổ sung trong working tree nối corpus/agent với bộ đánh giá của Người 4.

## Chạy và kiểm tra

- [Runtime tổng hợp](merged_runtime.md): `MVP_EVIDENCE_MODE=person3` + `MVP_SOURCE_MODE=live`, dictionary có nguồn, model qua gateway và hai checkpoint duyệt.
- [Corpus 50 tài liệu](real_sources.md): nguồn đóng băng, kiểm tra citation/model và bản nháp 20 claim.
- [Demo synthetic](backend_demo.md): tám tình huống hồi quy, không gọi nguồn/model thật.
- [Bản xuất UI đã đối chiếu](../../eval/person3/corpus/manual-ui/README.md): một ca development với nguồn snapshot/model thật đã đi đến export. Đây là kiểm tra quy trình, chưa phải duyệt chuyên môn.
- [Isolation pytest](environment_isolation.md): import script không nạp dotenv, test mặc định chặn mạng ngoài loopback.
- [Tham chiếu AI](ai_review.md): 20 ca, 9 trích dẫn khớp nguồn, đánh giá kỹ thuật có provenance; heldout đã được AI đọc, chưa có chuyên gia duyệt.
- [Kết quả cuối trên tham chiếu AI](evaluation_results.md): đã ghi/replay 20 ca và chấm ba hệ thống, 60 dòng/0 lỗi replay; Agent khớp AI 20/20, RAG 1/20; scope mismatch chưa khớp các key đã chọn. Backend 537 test đạt. Chưa xác nhận accuracy lâm sàng.
- [RAG có kiểm tra phạm vi](scoped_rag.md): thí nghiệm riêng sau baseline; development khớp AI 5/5 nhưng chỉ 3/12 findings qua đầy đủ kiểm tra, scope mismatch recall 0/1. Không coi là chất lượng trích xuất tốt hay độ chính xác lâm sàng. Giữ nguyên baseline RAG v4 1/20.

## Phần kỹ thuật đã triển khai

| Phần | Đầu ra |
|---|---|
| M04 normalization | Dictionary năm hoạt chất/năm biến cố có provenance; giữ unknown; tên chưa xác định hoặc nhiều ứng viên cần review |
| Extraction | Structured output qua gateway Người 2, budget/trace, một repair, cửa sổ tài liệu và cache theo run/claim/document |
| Scope/contradiction | Kiểm tra target/phạm vi; không điền scope nguồn từ claim; FAERS và null bất định không thành direct evidence |
| Citation/dedup | Quote nguyên văn, locator Unicode, hash/version; quote sai giữ excluded; nguồn/version trùng không tính lại |
| M06 dossier | Typed quote statements gắn evidence/document version/hash/URL; validator khi duyệt và export |
| Review | Duyệt assessment riêng dossier; sửa evidence vô hiệu approval/context; resume giữ counters |
| Runtime | Connectors Người 1 → graph/gateway Người 2 → phân tích/hồ sơ Người 3 → API dùng bởi VigiLens |
| M09 | Rubric, 20 claim, hai form review/checker, exporter P26, agent replay hook và nhãn AI riêng; gold chuyên môn vẫn rỗng |

## Còn cần để nghiệm thu toàn bộ

1. Hai reviewer chuyên môn gán nhãn độc lập, chốt phạm vi và phân xử bất đồng. Không dùng output model làm gold.
2. Người 3/4 chốt coverage và split theo họ drug–event/tài liệu. Người 4 chạy baseline/evaluation cùng corpus, cutoff và ngân sách khi có gold.
3. Smoke cấu hình model/nguồn thực tế của nhóm. Test runtime tổng hợp mới dùng HTTP/model giả lập; không xác nhận kết nối live từ máy này. PubMed API bị redirect trong lần kiểm tra Người 1; local PubMed là lựa chọn chủ động.

Giới hạn: tối đa ba cửa sổ 10.000 ký tự, overlap 2.000, có gap khi chưa đọc hết; scope rules bảo thủ, chưa đổi đơn vị/so sánh interval tự động; confidence chưa hiệu chuẩn. Dossier tự sinh quote; facts/inferences/hypotheses cần entailment review riêng. Test kỹ thuật không xác nhận accuracy lâm sàng.

## Công cụ patch cũ

`integration.patch`, `apply_person3_integration.py` và `test_person3_on_main.py` là công cụ lịch sử xây trên main `7c559e4`. Không áp dụng lên main tổng hợp `fa1c1d1` hoặc mới hơn: shared files đã có tích hợp và đã thay đổi. Kiểm tra checkout hiện tại bằng `python scripts/test_person3_backend.py --all`; báo cáo mới tại `eval/person3/merged-runtime-report.json`. Các báo cáo cũ giữ mốc kiểm chứng của chúng.

## Hoàn tất M09 trên bản tổng hợp

Xem [các bước hoàn tất và gói chuyên viên](finish_all.md). Đã có exporter, agent replay hook và recordings thật cho 20 ca trên tham chiếu AI. [Báo cáo cuối](evaluation_results.md) hoàn tất phần chạy so sánh kỹ thuật; gold chuyên môn, độ phủ và đánh giá ngữ nghĩa vẫn thiếu để nghiệm thu toàn bộ theo tiêu chí gốc.
