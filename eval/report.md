# Báo cáo P26 — kiểm tra kỹ thuật, 02/10/2026

Đã triển khai BM25, single-shot RAG qua recording, replay adapter theo nguồn/cutoff, shared prediction contract, metrics, kiểm tra corpus/split và CLI có raw output/manifest. **Chưa có benchmark chuyên môn hoặc kết quả agent.**

Kiểm tra khi tách PR trên main `fa1c1d1`, 03/10/2026: sau sửa detection schema/provenance và leakage xuyên source versions, toàn bộ Python đạt **509 passed, 1 skipped, 28 subtests** trên Windows/Python 3.14; **510 passed, 28 subtests** trên Docker Linux/Python 3.11. Ruff trong phạm vi backend/tests/evaluation, pip check trong Docker và OpenAPI đạt. CLI keyword và recorded RAG chạy lại trên cả development/heldout synthetic với 4/4/2/2 dòng, không lỗi. Hai lỗi integrity đã được review lại, 20 test hồi quy bổ sung. Workflow `Person 4 evaluation` bổ sung lint/tests và replay fixture trên Python 3.11; GitHub runner còn bị billing/spending limit, chưa có kết quả CI. Các bảng/raw metrics ngày 02/10 bên dưới được giữ như kết quả fixture lịch sử, không đổi thành kết quả model thật.

## Dữ liệu và protocol

`scripts/seed_demo.py` tạo corpus và nhãn synthetic bằng thuốc/biến cố hư cấu: 4 claims development, 2 claims heldout không trùng family/tài liệu. Recording `synthetic-fixture-v1` do tác giả viết, không phải output từ cuộc gọi model. Nhãn chưa qua hai reviewer độc lập. Dữ liệu này chỉ kiểm tra pipeline.

Mỗi hệ dùng cùng corpus/cutoff/index, trần 8 bước/50 tài liệu và top-20. BM25 dùng NFKC/casefold, `k1=1.2`, `b=0.75`. RAG truy xuất một lượt rồi khớp recording theo hash model/prompt/claim/context; không đọc gold để truy xuất. Bộ chạy chặn network và không fallback live khi thiếu recording. Claim/family/split/gold không vào model payload.

## Kết quả chạy thực tế

| Split synthetic | Hệ | Thành công / tổng | Recall@20 macro | Citation precision |
|---|---|---:|---:|---:|
| Development | Keyword | 4 / 4 | 1,00 | N/A |
| Development | Single-shot RAG | 4 / 4 | 1,00 | 1,00 |
| Development | Agent | 0 / 4 | N/A | N/A |
| Heldout | Keyword | 2 / 2 | 1,00 | N/A |
| Heldout | Single-shot RAG | 2 / 2 | 1,00 | 1,00 |
| Heldout | Agent | 0 / 2 | N/A | N/A |

Development có 12 dòng, 4 lỗi; heldout có 6 dòng, 2 lỗi. Cả hai lệnh `--system all` trả exit code **1** vì thiếu agent hook, không phải do runner âm thầm thay agent bằng fixture. Chưa có live model calls; usage replay là lịch sử trong fixture, không có chi phí xác minh. Các điểm số hoàn hảo trên dữ liệu nhỏ tự tạo không có ý nghĩa chứng minh tính tổng quát hay agent tốt hơn baseline.

Macro loại các metric N/A: ở heldout, claim `heldout-empty` không có gold retrieval/citation nên hai điểm 1,00 chỉ dựa trên **một** claim có denominator, dù cả hai claim chạy thành công. Mẫu số cụ thể được lưu trong aggregate; không coi N/A là 0 hoặc 1.

Raw results và cấu hình/hashes:

- Development: [manifest](results/person4-technical/manifest.json), [per-claim](results/person4-technical/per-claim.jsonl), [aggregate](results/person4-technical/aggregate.json), [report](results/person4-technical/report.md).
- Heldout synthetic: [manifest](results/person4-technical-heldout/manifest.json), [per-claim](results/person4-technical-heldout/per-claim.jsonl), [aggregate](results/person4-technical-heldout/aggregate.json), [report](results/person4-technical-heldout/report.md).

31 evaluation tests đạt trong lượt Python đầy đủ 295 tests. Các ca biết đáp án kiểm tra recall 3/4, precision citation 9/10, denominator 0 trả N/A, snapshot hash/span/cutoff, overlap split, ranking, chặn TCP/DNS/UDP, payload không chứa gold và lỗi thiếu recording/hook. Tests mới còn xác nhận entrypoint Python ghi report từ working directory khác, yêu cầu synthetic opt-in, cấu hình sai không ghi output và recording hỏng không làm mất kết quả keyword.

## Bổ sung lần tiếp tục

Giao tiếp `run_evaluation(config: EvaluationConfig) -> EvaluationReport` đã có, cùng protocol với CLI. Report trả rows/summaries/manifest/Markdown/output và số lỗi/exit code. RAG báo số query và replay calls; code hashes dùng đường dẫn tương đối POSIX. Thiếu file recording, JSON hỏng hoặc sai model được ghi thành lỗi trên từng claim RAG, không dừng cả benchmark. Các raw results bên trên đã được tái tạo bằng mã mới.

## Phân tích lỗi và bước bàn giao

Toàn bộ lỗi agent là `Agent integration missing`: cần Người 2/3 cung cấp `--agent-hook module:function` ghép graph với cùng replay index, extraction/normalization recordings, usage/trace và protocol dừng trước human approval. Không tự dùng scenario lookup hay giả quyết định reviewer để tạo kết quả agent.

Để chạy benchmark thật, cần Người 1/3 bàn giao snapshots/hash/version/cutoff/quyền lưu, claims/splits/family, gold và statement citation review độc lập, cùng recordings model đã chốt. Chấm safety violations và mức giảm thời gian reviewer vẫn **chưa đo**; không suy ra từ tests hoặc tỷ lệ citation. Chi tiết hợp đồng và lệnh tái tạo ở [README](README.md).
