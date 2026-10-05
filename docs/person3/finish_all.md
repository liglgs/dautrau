# Hoàn tất phần Người 3 trên bản tổng hợp

**Cập nhật 03/10:** đã hoàn tất ghi model/replay cả 20 ca, chấm ba hệ thống và test backend 537 ca đạt. Xem [kết quả cuối và giới hạn](evaluation_results.md), [nhãn AI và lệnh chạy](ai_review.md). Dataset `data/person3/evaluation-ai` vẫn chưa phải gold chuyên môn. Các bước dưới đây giữ lại cho quy trình hai reviewer trong kế hoạch gốc.

## Hiện đã có

- Chuẩn hóa tên, trích xuất có schema, đối chiếu scope, phát hiện mâu thuẫn, kiểm tra trích dẫn, hồ sơ và chặn xuất khi chưa duyệt.
- Kết nối nguồn của Người 1 với graph/budget/review của Người 2.
- `scripts/export_person3_evaluation.py`: chuyển ZIP thật sang `Corpus` của Người 4; đoạn truy xuất cố định 2.000 ký tự Unicode, không chọn đoạn theo gold hoặc dự đoán model.
- `eval.person3_agent:predict`: chạy graph thật trên BM25/snapshot chung, dừng trước duyệt của con người. Không dùng fixture hoặc tự duyệt checkpoint.
- `scripts/record_person3_evaluation.py`: ghi phản hồi model cho agent và one-shot RAG; agent được replay ngay để kiểm tra. Replay thiếu bản ghi hoặc sai request hash là lỗi, không gọi mạng để bù.
- Chuyển nhãn được phân xử sang `annotations.jsonl`, kiểm tra nguồn/version/hash/locator, split và mốc thời gian. Phiếu trống không được công bố thành gold.
- Báo đồng thuận và Cohen kappa cho assessment/abstention; khi chưa có nhãn, kết quả là N/A.

Gói thực tế trên máy: `data/person3/evaluation-review/`. Các file chứa toàn văn và phản hồi model ở đây được `.gitignore` loại khỏi Git. Code và báo cáo nhỏ có thể push.

## 1. Việc bạn cần nhờ nhóm trưởng ngay

Gửi gói `person3-review-package.zip` đã chuẩn bị trong `.local-preview/`, kèm tin nhắn:

> Mình đã nối xong phần Người 3 với source, graph và bộ đánh giá. Đã chuẩn bị 50 tài liệu nguồn và 20 nhận định (5 development, 15 heldout). Để nghiệm thu M09 cần hai người có chuyên môn duyệt độc lập, sau đó phân xử và khóa gold. Nhờ bạn tìm hai dược sĩ lâm sàng/bác sĩ/chuyên viên cảnh giác dược và một người phân xử. Người 4 giúp chốt split, đơn vị truy xuất, độ phủ các loại ca và chạy so sánh keyword/RAG/agent khi có gold. Hiện chưa có số đo độ chính xác lâm sàng.

Không gửi `.env`, token, database hoặc kết quả model cho hai người đang gán nhãn độc lập.

## 2. Hai người duyệt làm gì

Mỗi người làm riêng `reviewer_a.jsonl` hoặc `reviewer_b.jsonl`. Không xem phiếu của nhau hoặc dự đoán model. Giữ bản gốc khi nhận lại.

| Trường | Nội dung |
|---|---|
| `record_status` | `completed_independent_expert_review` khi thực sự hoàn tất |
| `annotator_id`, `annotator_role`, `annotation_timestamp` | Danh tính, vai trò chuyên môn và thời gian có múi giờ; nhóm xác minh tư cách |
| `evidence_annotations` | Mã tự đặt, document/source ID/version/hash, quote nguyên văn và locator Unicode |
| `relevance`, `stance`, `citation_integrity`, `citation_entailment` | Nhãn và lý do theo hướng dẫn, không sao chép nhãn model |
| `scope_fields` | Sáu trường `drug_ingredient`, `event_term`, `population`, `dose`, `route`, `time_window`; `outcome`, `blocking`, `reason` |
| `required_gold_evidence_ids`, `optional_gold_evidence_ids` | Mã span bắt buộc và liên quan khác trong chính phiếu |
| `contradiction_annotations` | `evidence_ids` gồm hai mã khác nhau; `kind` và `reason` |
| `expected_assessment_status`, `expected_abstention`, `critical_gaps` | Kết luận đúng phạm vi, có từ chối kết luận không và còn thiếu gì |

Các tài liệu nằm trong `snapshots/`; nguồn/version/hash nằm trong `corpus_manifest.json`. Xem `annotation_guidelines.md` và `annotation_template.json` trong gói. Không đánh giá FAERS là bằng chứng nhân quả hoặc tính tỷ lệ mắc.

Nhóm cần chốt lại độ phủ sáu loại kết luận/các cặp mâu thuẫn. Nếu 50 tài liệu chưa đủ, bổ sung nguồn và lập phiên bản/split mới **trước** khi thử heldout; không điền nhãn để đủ số lượng.

## 3. Nhận phiếu và phân xử

Sao lưu hai bản trả về, rồi cập nhật đúng hai file trong `data/benchmark/`. Kiểm tra:

```powershell
python scripts/check_person3_annotations.py
```

Người phân xử xử lý tất cả 20 ca, gồm các ca hai reviewer đồng ý. Lưu `freeze_approval.json` theo mẫu trong gói:

- Khai danh tính/vai trò/thời gian/lý do, xác nhận split và cutoff.
- Cập nhật SHA256 của bốn đầu vào sau khi nhận phiếu (`Get-FileHash -Algorithm SHA256`).
- Giữ hash manifest truy xuất và `evaluation_cutoff` của gói đã được xem.
- `final_annotations`: 20 phiếu cuối đầy đủ; mỗi phiếu có `adjudication.status=resolved`, `adjudicator_id`, `resolution_reason`.
- Giữ hai phiếu độc lập và các lý do xử lý bất đồng. Đây là xác nhận khai báo của nhóm; chương trình không tự chứng nhận chuyên môn.

Xuất sang một thư mục mới, giữ nguyên gói đã duyệt:

```powershell
python scripts/export_person3_evaluation.py --approval data/benchmark/freeze_approval.json --output data/person3/evaluation-frozen
```

Chỉ khi toàn bộ kiểm tra đạt, file `annotations.jsonl` được tạo và manifest chuyển sang `independently_reviewed`. Bản xuất lỗi vẫn là pending, không dùng để đánh giá.

**Mốc thời gian:** manifest ứng viên cũ ghi thời điểm bắt đầu thu thập 08:29 UTC. Tài liệu cuối được lưu 08:45 UTC. Bản xuất dùng thời điểm snapshot cuối làm cutoff, giữ mốc ban đầu riêng; không coi đây là lịch sử xuất bản hoặc kiểm tra nguồn bên ngoài.

## 4. Ghi model và đánh giá với Người 4

Lệnh dưới **gọi model thật**, có thể tính phí. Bạn tự cấu hình `MODEL_NAME` và API key trong `.env`. Script chỉ đọc nguồn đã lưu, không gọi PubMed/DailyMed/FAERS. Nó không tự điền gold.

Có thể ghi 5 ca development trên bản draft. Với heldout, phải chốt split/gold/protocol trước và không sửa prompt sau khi xem kết quả.

```powershell
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-frozen --split development --live-model
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-frozen --split heldout --live-model
```

Không ghi đè file có sẵn. Nếu ngắt giữa batch, dùng cùng lệnh và thêm `--resume`; snapshot/hash/model/prompt/ngân sách phải trùng. Nếu có lỗi, đọc `recording-report-<split>.json`; giữ lần lỗi để báo độ phủ. Lượt mới có thay đổi protocol dùng thư mục mới.

Chạy đánh giá replay (thay `TEN_MODEL_DA_CAU_HINH` bằng đúng model đã ghi):

```powershell
python -m eval.run_evaluation --system all --split development --manifest data/person3/evaluation-frozen/corpus_manifest.json --claims data/person3/evaluation-frozen/claims.jsonl --annotations data/person3/evaluation-frozen/annotations.jsonl --recordings data/person3/evaluation-frozen/recordings-development.jsonl --model TEN_MODEL_DA_CAU_HINH --agent-hook eval.person3_agent:predict --output eval/results/person3-development
python -m eval.run_evaluation --system all --split heldout --manifest data/person3/evaluation-frozen/corpus_manifest.json --claims data/person3/evaluation-frozen/claims.jsonl --annotations data/person3/evaluation-frozen/annotations.jsonl --recordings data/person3/evaluation-frozen/recordings-heldout.jsonl --model TEN_MODEL_DA_CAU_HINH --agent-hook eval.person3_agent:predict --output eval/results/person3-heldout
```

Protocol cần Người 4 chấp nhận: keyword và RAG lấy 20 đoạn BM25; agent có thể tìm nhiều lần, đọc snapshot đầy đủ theo `ReplayAdapter` có sẵn. Agent báo mọi đoạn của tài liệu đã lộ ra, theo thứ tự truy xuất; không chỉ báo các đoạn trích thành công. Ngân sách tài liệu/bước/calls được giữ. **Cùng corpus chưa có nghĩa cùng lượng context**; lưu khác biệt này và chốt trước heldout. Nhãn gold quote được ánh xạ vào tất cả đoạn cố định nó giao nhau; đây là đo truy xuất đoạn, không chứng nhận hỗ trợ ngữ nghĩa.

Citation precision/unsupported rate cần chuyên viên duyệt từng statement–citation của kết quả sau khi chạy. Người 4 dùng `statement_reviews` gắn với đúng `statement_id`, text và evidence IDs; chưa có đánh giá này thì N/A. Không dùng kiểm tra quote đúng nguồn thay cho entailment. Tiết kiệm thời gian reviewer vẫn chưa đo nếu chưa làm nghiên cứu cặp.

Prompt RAG v4 đưa schema chi tiết cho statement (`text`, `kind`, `evidence_ids`) và các alias nguồn ngắn vào yêu cầu/hash. Ánh xạ alias về ID đầy đủ là cố định; mã ngoài danh sách vẫn bị chặn. Các bản ghi v1/v2/v3 cũ là hiện vật lịch sử; không dùng với prompt mới. Agent đã ghi thành công có thể giữ lại và bổ sung RAG bằng `--rag-only`; thử một ca bằng `--claim-id` trước, xem `ai_review.md`. Fixture CI được tạo lại theo code hiện tại.

## 5. Chốt bàn giao

```powershell
python scripts/test_person3_backend.py --all
git status --short
```

Push code/báo cáo nhỏ, không dùng `git add -f` với ZIP/nguồn/key. Vì PR #7 cũ đã merge, lần cập nhật mới cần PR `tiendat` → `main`. `.git` ở phiên làm việc này chỉ cho đọc; bạn thực hiện commit/push.

Các file đã thay đổi trong lượt hoàn thiện này có thể commit bằng:

```powershell
git add -- docs/person3/README.md docs/person3/finish_all.md eval/contracts.py eval/baselines/single_shot_rag.py eval/run_evaluation.py eval/person3_handoff.py eval/person3_agent.py eval/person3_dataset.py eval/person3/evaluation-readiness.json eval/person3/merged-runtime-report.json src/services/evidence/annotation_review.py scripts/export_person3_evaluation.py scripts/record_person3_evaluation.py tests/test_evidence/test_person3_evaluation.py
git add -- docs/person3/ai_review.md docs/person3/evaluation_results.md eval/person3/ai-reference-spec.json eval/person3/ai-reference-report.json eval/person3/development-evaluation-report.json eval/person3/final-ai-evaluation-report.json eval/person3/resume-verification-report.json eval/person3_provisional.py scripts/build_person3_ai_reference.py
git add -- eval/baselines/scoped_rag.py scripts/record_scoped_rag.py scripts/check_scoped_rag_retrieval.py scripts/test_person3_backend.py tests/test_eval/test_scoped_rag.py docs/person3/scoped_rag.md eval/person3/scoped-rag-readiness.json eval/person3/scoped-rag-v1-format-report.json eval/person3/scoped-rag-v2-format-report.json eval/person3/scoped-rag-v3-development-report.json eval/person3/scoped-rag-validation-v4-development-report.json eval/person3/scoped-rag-heldout-issues-report.json eval/person3/scoped-rag-heldout-recovery-report.json eval/person3/scoped-rag-validation-v6-heldout-report.json eval/person3/scoped-rag-final-ai-evaluation-report.json
git diff --cached --check
git commit -m "Complete Person 3 evaluation handoff and replay integration"
git push origin tiendat
```

Sau push, tạo PR mới và gửi link cho Người 1/4. Gói tài liệu chuyên viên gửi riêng cho nhóm, không push ZIP lên Git.

Chỉ báo “Người 3 đã hoàn tất” khi: code/test đạt; hai phiếu chuyên môn và phân xử xong; corpus/split/gold được chấp nhận; model recordings và so sánh ba hệ thống chạy đạt; các metric chưa đo được nêu rõ. Người 4 tiếp tục chịu trách nhiệm UI/browser và báo cáo đánh giá tổng hợp.
