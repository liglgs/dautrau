# Kết quả đánh giá kỹ thuật Người 3

Ngày 03/10/2026. Model: `gpt-4o-mini-2024-07-18`. Nguồn: 50 snapshot thật, 727 đoạn cố định. Tham chiếu: **AI sơ bộ**, chưa có reviewer chuyên môn độc lập.

## Kết quả đã hoàn tất

Đã ghi model cho cả 20 ca: 5 development, 15 heldout. Ba ca ibuprofen đầu được giữ lại khi resume; các phản hồi của ca dở được dùng lại theo request hash. Đã chấm keyword, RAG một lượt và graph Agent bằng replay: **60 dòng kết quả, 0 lỗi replay**, không gọi thêm API lúc chấm.

| Hệ thống | Development: kết luận khớp AI | Heldout: kết luận khớp AI | Tổng | Recall@20 trên đoạn bắt buộc được chọn |
| --- | --- | --- | --- | --- |
| Keyword | Không đo | Không đo | Không đo | 12/16 |
| RAG một lượt | 0/5 | 1/15 | 1/20 | 12/16 |
| Agent | 5/5 | 15/15 | 20/20 | 16/16 |

Keyword chỉ truy xuất, không đưa kết luận. Bốn ca biệt dược chưa xác định không có required evidence nên không được tính vào recall.

RAG khớp ca `P3-AMOXICILLIN-04`; 19 ca còn lại khác tham chiếu AI. Agent trả `insufficient_evidence` ở 16 ca và `requires_human_review` ở bốn ca biệt dược chưa xác định. Đây là so sánh kết luận với rubric AI bảo thủ; không khẳng định association trong nguồn bị phủ nhận.

Backend: **537 passed, 1 skipped, 28 subtests passed**. Test cách ly dotenv, chặn mạng ngoài loopback; không gọi model/nguồn thật. UI/browser chưa được kiểm chứng bởi bộ test này.

## Giới hạn và phần chưa đạt

- Mọi tham chiếu đều yêu cầu abstain. Kết quả Agent 20/20 không chứng minh xử lý tốt các ca đủ bằng chứng hoặc đủ sáu loại kết luận.
- Phát hiện scope mismatch ở mức ID đoạn chưa khớp tham chiếu được chọn: Agent precision 0/10 và recall 0/4 theo tổng số key được chấm. RAG không báo key mismatch và recall 0/4. Cần phân tích lỗi/phạm vi và kiểm chứng trên một phiên bản đánh giá mới trước khi tuyên bố cải thiện; giữ nguyên kết quả này.
- Relevance chỉ gồm các đoạn được chọn, chưa duyệt toàn corpus. Recall không chứng nhận hỗ trợ ngữ nghĩa; precision theo các đoạn được chọn không phải precision lâm sàng đầy đủ.
- Chưa đo statement–citation entailment, citation precision/completeness, unsupported claim rate, độ chính xác lâm sàng, hiệu năng phát hiện mâu thuẫn hoặc thời gian tiết kiệm cho reviewer. Các metric chưa có nhãn được giữ N/A.
- AI đã đọc các family heldout để gán nhãn. Đây là tập kỹ thuật tách family, **không phải kiểm định mù trên dữ liệu chưa xem**.
- Agent tìm nhiều lần và đọc snapshot đầy đủ; keyword/RAG lấy một lượt BM25 tối đa 20 đoạn. Lượng context khác nhau nên không suy ra ưu thế tổng quát từ bảng này.
- Các lần RAG lỗi trước đây vẫn được lưu. 0 lỗi replay của các bản ghi hiện tại không có nghĩa mọi lần gọi API trước đó đều thành công. Chi phí toàn bộ các lần gọi chưa đo đầy đủ.

## Hiện vật bàn giao

- [Báo cáo cuối dạng JSON](../../eval/person3/final-ai-evaluation-report.json): cả hai split, kết quả từng ca, aggregate, provenance/hash và giới hạn.
- [Báo cáo test backend](../../eval/person3/merged-runtime-report.json).
- [Kiểm tra resume](../../eval/person3/resume-verification-report.json): kiểm chứng ba ca đã lưu ở thời điểm bổ sung resume; không phải báo cáo cuối 15 ca.
- [Tham chiếu và lệnh tái tạo/chạy](ai_review.md).

Báo cáo replay đầy đủ ở `.local-preview/person3-ai-evaluation/all-development-final/` và `all-heldout/`. Snapshot, recordings, lịch sử resume và dữ liệu AI ở `data/person3/evaluation-ai/`. Các thư mục này được ignore; không dùng `git add -f`. Giữ bản ghi lỗi và toàn bộ lịch sử nếu gửi hiện vật riêng cho nhóm. Không gửi `.env` hoặc API key.

## Trạng thái bàn giao

**Đã hoàn tất lượt chạy và so sánh kỹ thuật trên tham chiếu AI.** Yêu cầu nghiệm thu gốc M09 về hai reviewer chuyên môn độc lập, phân xử, độ phủ kết luận và các metric chuyên môn vẫn chưa đáp ứng. Hai phiếu chuyên môn và gold gốc được giữ nguyên, không tự chuyển nhãn AI thành phê duyệt.

Tin nhắn có thể gửi Người 1/4:

> Mình đã nối và kiểm thử phần Người 3 trên bản tổng hợp. Đã ghi/replay 20 ca bằng model thật, so sánh keyword/RAG/Agent trên snapshot chung và tham chiếu AI; 60 kết quả, 0 lỗi replay. Backend đạt 537 test. Báo cáo ở docs/person3/evaluation_results.md. Agent khớp tham chiếu AI 20/20, RAG 1/20; scope mismatch ở mức đoạn chưa khớp. Chưa có gold chuyên môn và không coi đây là accuracy lâm sàng. Nhờ Người 4 đưa kết quả và giới hạn này vào báo cáo tổng hợp.
