# Đánh giá sơ bộ của AI cho Người 3

Ngày 03/10/2026. Nhóm chưa có chuyên gia; người dùng yêu cầu AI đọc nguồn và chuẩn bị nhãn.

## Đã làm

- Tạo 20 phiếu tham chiếu AI: 5 development, 15 heldout.
- Chọn 9 đoạn từ 9 tài liệu, kiểm tra nguyên văn, phiên bản, SHA256, vị trí Unicode và ánh xạ vào 727 đoạn truy xuất cố định. Ghi từng trường phạm vi và bối cảnh abstract/nhãn.
- Theo rubric bảo thủ hiện tại: 16 `insufficient_evidence`, 4 `requires_human_review` vì biệt dược chưa xác định. Thiếu bằng chứng ở đây liên quan đến **toàn bộ phạm vi được hỏi**, không phủ nhận association đã ghi nhận trong nguồn.
- Khai rõ tác giả AI, chưa có chuyên gia duyệt. Giữ nguyên hai phiếu reviewer và file gold chuyên môn; không tự duyệt hồ sơ.
- Thêm cờ `--allow-provisional` cho replay/recording. Dataset AI bị chặn nếu chưa bật. Báo cáo ghi rõ agreement với nhãn AI, chưa đo độ chính xác lâm sàng.

Bản giải thích từng ca: `data/person3/evaluation-ai/ai-reference-review.md`; JSON cùng tên có locator và scope. Dataset này nằm trong data đã ignore. File `eval/person3/ai-reference-spec.json` chứa nội dung đã đánh giá để tái tạo, không gọi model để tự thay đổi nhãn.

## Những điểm đã đối chiếu

- Metformin: 6% ngừng tablet vì tiêu chảy không phải tỷ lệ tiêu chảy nói chung hoặc tỷ lệ đo riêng cho oral solution. IR/ER khác nhau không tự tạo mâu thuẫn.
- Lisinopril: thử nghiệm chọn bệnh nhân từng có ACEI-induced cough không đại diện cho mọi adults. Số 2,5% trong nhãn là phần cao hơn placebo, không phải tỷ lệ tuyệt đối.
- Amoxicillin: dữ liệu trẻ em không xác lập adults; dung nạp khi dùng lại không phủ nhận phản ứng đã ghi nhận. Ca amoxicillin/clavulanate kèm EBV cần xét nhiễu.
- Ibuprofen: nguy cơ thấp hơn NSAID khác không có nghĩa không có nguy cơ. [Nhãn FDA lịch sử về ibuprofen IV](https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/022348s021lbl.pdf) xác nhận dạng truyền tĩnh mạch tồn tại; nhãn oral trong corpus chỉ cho phép đánh dấu lệch route của chính nguồn đó. Nguồn kiểm tra bên ngoài không được thêm vào đáp án truy xuất.
- Chưa có đoạn đã kiểm tra xác lập đồng thời kết quả đúng `1000 mg/day` và `90 days`. Các liều này là ca thử kỹ thuật, không phải hướng dẫn sử dụng.
- FAERS không được xem là bằng chứng nhân quả hoặc tỷ lệ mắc.

## Kiểm tra đã chạy

`eval/person3/ai-reference-report.json` lưu provenance/hash và kết quả keyword trên cả 20 ca: 0 lỗi kỹ thuật. Recall@20 trên **các đoạn tham chiếu được chọn**: development 0/4, heldout 12/12. Bốn ca biệt dược không có required evidence và không được tính là truy xuất hoàn hảo.

Đây chưa phải relevance inventory toàn corpus; precision trên đoạn được chọn không xác nhận precision thực. Citation entailment, accuracy lâm sàng và tiết kiệm thời gian đều chưa đo. Báo cáo trên ghi kết quả keyword ở thời điểm tạo dataset; kết quả development với agent/RAG thật được cập nhật bên dưới.

### Development với bản ghi model thật — 03/10/2026

Đã replay và chấm cả ba hệ thống với `gpt-4o-mini-2024-07-18`: **15 dòng kết quả, 0 lỗi xử lý**, mạng bị chặn và không gọi thêm API lúc chấm. Bản ghi agent đã xác minh; RAG dùng prompt v4 và ánh xạ alias đã kiểm tra. Bản ghi/báo cáo lỗi ở các lần trước vẫn giữ nguyên.

| Hệ thống | Ca xử lý thành công | Kết luận khớp tham chiếu AI | Recall@20 trên đoạn bắt buộc đã chọn |
| --- | --- | --- | --- |
| Keyword | 5/5 | Không đo: chỉ truy xuất | 0/4 |
| RAG một lượt | 5/5 | 0/5 | 0/4 |
| Agent | 5/5 | 5/5 | 4/4 |

Ca 05 chưa xác định được biệt dược, không có required evidence nên không tính vào recall. Agent dừng ở `insufficient_evidence` cho ca 01–04 và `requires_human_review` cho ca 05. RAG đưa `supported_for_scope` cho ca 01, 02, 03, 05 và `out_of_scope` cho ca 04; cả năm khác rubric AI. Bản ghi hợp lệ về định dạng/ID không xác nhận kết luận đúng.

**5/5 chỉ là agreement với tham chiếu AI trong năm ca này.** Toàn bộ tham chiếu development đều yêu cầu abstain nên chưa chứng minh xử lý tốt ca đủ bằng chứng. Agent chưa khớp chú thích scope mismatch ở mức ID đoạn: precision 0/3 và recall 0/1 trên các key được chấm. Semantic statement–citation và cặp mâu thuẫn vẫn chưa có đánh giá chuyên môn.

Báo cáo development ban đầu: [development-evaluation-report.json](../../eval/person3/development-evaluation-report.json), hiện vật tại `.local-preview/person3-ai-evaluation/all-development/`. Lượt chấm cuối cả hai split và kiểm tra code mới nằm tại `all-development-final/` và `all-heldout/` trong cùng thư mục.

### Cả 20 ca đã hoàn tất

15 ca heldout đã ghi model thật và replay đạt, không còn ca đang dở. Kết quả cuối: **60 dòng/0 lỗi replay**, Agent khớp AI **20/20**, RAG **1/20**. Recall trên đoạn bắt buộc đã chọn: Agent 16/16, keyword/RAG 12/16. Phát hiện scope mismatch ở mức ID đoạn vẫn chưa khớp các key được chọn; các metric ngữ nghĩa và chuyên môn còn N/A. Xem [báo cáo bàn giao và giới hạn](evaluation_results.md), [JSON cuối](../../eval/person3/final-ai-evaluation-report.json).

Bộ test backend mới nhất: **537 passed, 1 skipped, 28 subtests passed**, offline, không gọi nguồn/model thật.

## Chạy tiếp với model của bạn

Dataset `data/person3/evaluation-ai` đã tạo tại máy. Lệnh tái tạo dưới chỉ dùng khi thư mục chưa tồn tại; script không ghi đè:

```powershell
python scripts/build_person3_ai_reference.py
```

**Hai split trên máy này đã chạy xong, không cần gọi lại.** Hai lệnh sau dành cho một lượt mới ở dataset chưa có recordings; chúng **gọi API model**, có thể tính phí. Bạn dùng `MODEL_NAME` và key đã tự cấu hình trong `.env`. Nguồn chỉ đọc từ snapshot; nhãn AI không được đưa vào prompt:

```powershell
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-ai --split development --allow-provisional --live-model
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-ai --split heldout --allow-provisional --live-model
```

Đọc `recording-report-<split>.json` để biết từng ca thành công/lỗi và tên model. Giữ bản ghi lỗi; lần thử mới cần thư mục dataset mới. Thay `TEN_MODEL_DA_GHI` dưới bằng đúng tên đó:

**Tiếp tục sau khi bấm Ctrl+C hoặc tắt máy:** dùng đúng model, corpus và ngân sách của lần trước, thêm `--resume`:

```powershell
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-ai --split heldout --allow-provisional --live-model --resume
```

Chế độ này kiểm tra manifest/claims/model/prompt/ngân sách và replay ca agent hoàn tất trước khi gọi thêm API. Ca hoàn tất hiện `agent=cached_verified; RAG=cached`; ca đang dở dùng lại phản hồi agent khớp toàn bộ request hash, chỉ gọi phần thiếu. Nhật ký model nối thêm, không xóa phản hồi cũ; báo cáo trước khi resume được giữ nguyên tại `recording-history-<split>/<sha256>.json`. Checkpoint tiến độ được thay thế atomically sau mỗi ca. Bản ghi hỏng hoặc điều kiện chạy thay đổi sẽ bị chặn; không tự sửa/xóa để bỏ qua kiểm tra. Không chạy hai tiến trình ghi cùng dataset đồng thời. Request đang ở máy chủ khi Ctrl+C mà chưa nhận/lưu phản hồi có thể vẫn tính phí và cần gọi lại.

**Trường hợp development đã ghi xong agent nhưng RAG lỗi schema/citation:** đã bổ sung schema `Statement` với `text`, `kind` (`fact/inference/hypothesis`) và `evidence_ids`. Prompt v4 cho model chọn mã ngắn `E01`, `E02`, ...; chương trình chỉ ánh xạ đúng mã đã cấp về ID đầy đủ. Không đoán `P3U-13` là nguồn thứ 13, không bỏ trích dẫn sai để biến một lượt lỗi thành thành công. Schema liệt kê các alias hợp lệ, hash pin cả ánh xạ lẫn prompt/context thực sự được gửi. Nguồn/doc/version/hash vẫn giữ nguyên.

Chạy thử một ca trước để tránh gọi lại cả batch khi vẫn còn lỗi:

```powershell
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-ai --split development --allow-provisional --live-model --rag-only --claim-id P3-METFORMIN-01
```

Nếu ca thử đạt, chạy riêng RAG cho đủ 5 ca. Ca đã đạt với cùng request hash được tái sử dụng:

```powershell
python scripts/record_person3_evaluation.py --dataset data/person3/evaluation-ai --split development --allow-provisional --live-model --rag-only
```

Chế độ này kiểm tra 5 agent đã hoàn tất, model/hash corpus trùng và bản ghi agent còn hợp lệ; không gọi lại agent. RAG thành công chỉ được tái sử dụng khi request hash trùng prompt/schema/context hiện tại. Bản ghi v2/v3 giữ như lịch sử; prompt v4 cần bản ghi v4, kể cả ca 05 đã có một bản v3 hợp lệ. Lưu raw response cả khi sai schema, giữ nguyên báo cáo lỗi ban đầu, ghi kết quả bổ sung tại `rag-recording-report-development.json` và lịch sử ở `rag-attempts-development.jsonl`. `processed_claims=1` chỉ là ca thử, chưa phải batch 5 ca. Báo cáo bổ sung là lần thử mới, không biến lỗi lần đầu thành thành công. V2 không lưu raw response/token của phản hồi RAG lỗi nên chi phí phần đó chưa xác định.

```powershell
python -m eval.run_evaluation --system all --split development --manifest data/person3/evaluation-ai/corpus_manifest.json --claims data/person3/evaluation-ai/claims.jsonl --annotations data/person3/evaluation-ai/annotations.jsonl --recordings data/person3/evaluation-ai/recordings-development.jsonl --model TEN_MODEL_DA_GHI --agent-hook eval.person3_agent:predict --allow-provisional --output .local-preview/person3-ai-evaluation/all-development
python -m eval.run_evaluation --system all --split heldout --manifest data/person3/evaluation-ai/corpus_manifest.json --claims data/person3/evaluation-ai/claims.jsonl --annotations data/person3/evaluation-ai/annotations.jsonl --recordings data/person3/evaluation-ai/recordings-heldout.jsonl --model TEN_MODEL_DA_GHI --agent-hook eval.person3_agent:predict --allow-provisional --output .local-preview/person3-ai-evaluation/all-heldout
```

## Giới hạn nghiệm thu

AI đã đọc heldout để tạo tham chiếu. Split chỉ còn nghĩa tách family, **không phải kiểm định mù trên tập chưa từng xem**. Cần bộ mới nếu muốn đo khả năng tổng quát như vậy.

Chưa đủ sáu loại kết luận, chưa duyệt toàn bộ cặp mâu thuẫn, mọi đoạn liên quan hoặc từng statement–citation. Không tạo nhãn để lấp độ phủ. Chế độ này hoàn thiện phần **tham chiếu và chạy kỹ thuật bằng AI**; yêu cầu M09 về hai lượt chuyên môn độc lập trong kế hoạch gốc vẫn chưa đáp ứng. Nếu nhóm nộp demo bằng nhãn AI, phải nêu thay đổi tiêu chí trong báo cáo.

Keyword/RAG lấy 20 đoạn; agent có thể đọc đầy đủ snapshot và tìm nhiều lần. Cùng corpus chưa có nghĩa cùng lượng context; ghi rõ khác biệt này khi so sánh.

## File mới cần bàn giao

Ngoài danh sách trong `finish_all.md`, thêm:

```powershell
git add -- docs/person3/ai_review.md eval/person3/ai-reference-spec.json eval/person3/ai-reference-report.json eval/person3_provisional.py scripts/build_person3_ai_reference.py
git add -- eval/person3/development-evaluation-report.json
git add -- docs/person3/evaluation_results.md eval/person3/final-ai-evaluation-report.json eval/person3/resume-verification-report.json
```

ZIP nguồn, dataset sinh, recordings và `.env` ở đường dẫn đã ignore. Không dùng `git add -f`.
