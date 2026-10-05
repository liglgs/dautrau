# Thử nghiệm RAG có kiểm tra phạm vi

Ngày 03/10/2026. Inference hiện tại `scoped-rag-v3`, bộ kiểm tra `scope-validation-v6`, phát triển sau khi xem kết quả baseline và lỗi trích xuất. Giữ nguyên RAG v4, 20 bản ghi baseline, báo cáo 1/20 và recordings v1/v2/v3. Không thay nhãn AI để tăng điểm.

## Đã thay đổi

- Chuẩn hóa từ trường drug/event bằng dictionary đã pin hash. Không đoán hoạt chất từ claim_text, claim_id hoặc family_id. Biệt dược/biến cố chưa xác định cần human review và không gọi model.
- Truy xuất các cách viết và alias công khai; hợp nhất BM25 bằng reciprocal rank fusion. Cân bằng tối đa 20 đoạn: ưu tiên 8 PubMed, 8 DailyMed, tối đa 4 FAERS; tối đa ba đoạn mỗi tài liệu. Phần dung lượng còn trống chỉ bổ sung PubMed/DailyMed. Không gọi mạng nguồn.
- Model chỉ trích xuất tối đa tám findings, một lượt gọi. Mỗi finding gồm outcome quote, direction/uncertainty/study_type và sáu trường phạm vi có anchor quote riêng. V2 chấp nhận cả `null` và `{"value": null, "quote": null}` cho scope chưa biết; cả hai đều không cung cấp giá trị. Thiếu trường hoặc kiểu dữ liệu khác vẫn là lỗi. Prompt yêu cầu value nguyên văn, không chuyển từ mô tả bệnh sang "adults", không đoán "oral" hoặc sao chép liều/thời gian từ câu hỏi.
- Outcome quote phải nằm nguyên văn trong đoạn được gửi. Anchor phạm vi phải nằm trong đoạn hoặc tiêu đề metadata được gửi, và chứa value. V3 cho phép khôi phục khác biệt chỉ gồm khoảng trắng nếu tìm được duy nhất một span; lưu span nguyên bản và thông tin khôi phục trong trace. Không sửa chữ, dấu câu, chữ hoa/thường hoặc số, không fuzzy matching. Quote sai được giữ trong raw response và ghi excluded với mọi lý do; alias sai/schema sai là lỗi.
- Code quyết định kết luận từ findings sau kiểm tra: không dùng FAERS làm support/rebuttal; unknown hoặc scope chưa khớp chặn kết luận cho chính finding đó. Mô tả population/dose/time khác nhau cần review thay vì tự coi là khoảng không giao nhau. Finding mâu thuẫn chỉ được dùng làm rebuttal khi uncertainty thấp và có thiết kế ngẫu nhiên được trích; không biến thiếu warning thành bằng chứng phản bác.
- Nếu hai phía đều không nêu một trường scope phụ thì ghi `unspecified_in_both`, không tạo giá trị cụ thể. Điều này không chứng minh tổng quát hóa lâm sàng. Có ca đúng phạm vi được support/rebuttal trong test; không ép toàn bộ câu trả lời thành abstain.
- Facts là quote nguyên văn, có statement ID ổn định để phục vụ entailment review sau này. Phân loại direction và attribution vẫn là phán đoán model, chưa được chuyên viên xác nhận.
- Bộ kiểm tra v4 coi các sentinel `unknown`, `unspecified`, `not stated`, `not reported` không kèm quote là scope chưa biết. Giá trị cụ thể thiếu quote vẫn bị loại. Drug/event có thể dùng alias tương đương trong dictionary công khai đã pin, khi chính alias đó xuất hiện nguyên văn trong quote nguồn; ghi mapping trong trace. Không thêm từ đồng nghĩa y khoa để khớp nhãn.
- V5 ánh xạ nhãn thiết kế `cohort` về nhóm rộng `observational`, lưu mapping trong trace và giữ raw nguyên bản. Không chuyển thành RCT hoặc bỏ kiểm tra design quote; nhãn tùy ý khác vẫn bị chặn.
- V6 ánh xạ subtype `meta-analysis` về nhóm `review`, lưu subtype gốc trong trace. Không coi phân tích gộp có chữ "randomized" là RCT trực tiếp. Quote thiết kế thiếu hoặc không khớp vẫn bị loại. Prompt/schema gửi model không đổi; sửa này chỉ đọc lại đầu ra đã lưu.
- Khi pool truy xuất nghiêm ngặt rỗng, dùng fallback trên các đoạn nhìn thấy trước cutoff trong cùng một tài liệu: phải có alias thuốc và ít nhất một token biến cố. Sau đó xếp hạng các đoạn có thuốc hoặc token biến cố, giữ quota và giới hạn context. Protocol ghi `visible_document_literal_drug_event_token_overlap_v1`. Đây là mở rộng truy xuất, không xác nhận tương đương biến cố hoặc phạm vi; không thêm alias y khoa vào dictionary. Pool nghiêm ngặt có kết quả thì không dùng fallback.
- Request hash pin toàn bộ prompt/context/schema/normalization/retrieval/dictionary và code dùng cho protocol. Lưu raw response trước validate. Replay không gọi API khi thiếu bản ghi. Nếu chỉ thay bộ kiểm tra, phản hồi cũ có **toàn bộ đầu vào model giống hệt** và dictionary/retrieval protocol không đổi có thể được đọc lại; usage lưu cả hash request gốc, hash xử lý mới và phiên bản postprocessor. Prompt/schema/context/model thay đổi không được tái sử dụng. Không viết lại raw response.

Đây là phương pháp mới (`scoped_rag`), có nhiều truy vấn từ vựng và local scope gate. Không đổi tên nó thành baseline one-shot cũ để so điểm.

## Kiểm tra trên máy

Preview offline development: tìm được **4/4 đoạn bắt buộc đã chọn**, bản v4 tìm được 0/4. Cả bốn ca hoạt chất xác định lấy chín đoạn, ca biệt dược chưa xác định lấy không đoạn. Xem [provenance và kết quả truy xuất](../../eval/person3/scoped-rag-readiness.json).

Đã ghi đủ năm ca development bằng model thật, chấm offline trước và sau sửa bộ kiểm tra. Kết luận khớp nhãn AI **5/5** ở cả hai lần. Bộ kiểm tra v3 giữ **2/12 findings**; v4 giữ **3/12**, còn chín findings bị loại. Ca 02 vẫn không giữ được finding; ca 03 giữ được một sau xử lý sentinel chưa biết. Scope mismatch recall **0/1** trên key AI đã chọn. Citation entailment chưa đo. Đây chưa phải một kết quả trích xuất tốt; toàn bộ năm tham chiếu đều abstain, nên 5/5 không chứng minh trả lời có bằng chứng đúng. Không dùng để tuyên bố chính xác lâm sàng hoặc hơn Agent.

Báo cáo riêng: [v3 lịch sử](../../eval/person3/scoped-rag-v3-development-report.json), [đọc lại bằng bộ kiểm tra v4](../../eval/person3/scoped-rag-validation-v4-development-report.json). Raw responses và nhãn giữ nguyên; sửa v4 không gọi API. Recall trên đoạn được chọn không xác nhận entailment hoặc precision đầy đủ. Test có cả ca support/rebuttal đúng phạm vi và các ca unknown, broad scope, route mismatch, FAERS, fake quote, alias sai, hash sai, dictionary đổi, cache và replay qua evaluator.

Bộ test backend hiện tại: **560 passed, 1 skipped, 28 subtests passed**, cách ly dotenv và chặn mạng. So sánh phạm vi giữ nguyên dấu ngưỡng/đơn vị: `>=10 mg/day` không được coi bằng `10 mg/day`.

### Kết quả đủ 20 ca sau sửa v6

Đã replay offline 5 development và 15 heldout, **20/20 ca xử lý được, 0 lỗi**, không gọi model/nguồn mới. Báo cáo mới: [scoped RAG đủ 20 ca](../../eval/person3/scoped-rag-final-ai-evaluation-report.json). Baseline RAG cũ 1/20 được giữ nguyên riêng.

| Chỉ số kỹ thuật | Kết quả |
|---|---|
| Kết luận khớp tham chiếu AI | 20/20; toàn bộ tham chiếu đều abstain |
| Findings qua đầy đủ kiểm tra quote/phạm vi | 11/49; 38 bị loại |
| Truy xuất các span bắt buộc đã chọn trong tham chiếu AI | 12/16; bốn ca amoxicillin chưa lấy được span đã chọn |
| Phát hiện key scope mismatch trong tham chiếu AI | 0/4 |
| Citation entailment/chính xác lâm sàng | Chưa đo bằng reviewer độc lập |

Đây là hoàn tất lượt so sánh kỹ thuật sau phân tích. Chất lượng trích xuất vẫn còn yếu; 20/20 agreement không chứng minh câu trả lời có bằng chứng đúng. Người 4 review phần baseline/evaluation và kết quả này trước khi ghép; Người 3 bàn giao phần nhãn/dictionary/trích xuất/phạm vi cùng các giới hạn. Không cần gọi model lại để sửa lỗi định dạng hiện tại.

### Lỗi v1 đã quan sát

Model `gpt-4o-mini-2024-07-18` trả scope chưa biết bằng bare `null` ở ca 01 và 04, khiến schema v1 báo lỗi. Ca 02 và 03 ghi thành công về định dạng nhưng mỗi ca có ba findings bị loại vì anchor phạm vi không được nguồn xác nhận; không coi đó là trích xuất thành công đầy đủ. Ca 05 là checkpoint biệt dược chưa xác định, không gọi API. Xem [chẩn đoán và hash bản ghi giữ nguyên](../../eval/person3/scoped-rag-v1-format-report.json).

V2 xử lý hai cách ghi scope chưa biết và hiện `accepted`, `excluded`, `needs_quote_review`. Ca 01 v2 đã chạy model thật nhưng cả ba findings bị loại. Một finding có anchor `type 2 diabetes mellitus` trong khi nguồn có hai dấu cách trước `mellitus`; hai findings còn lại có design/outcome quote đã bị sửa nội dung/dấu câu.

V3 đọc lại phản hồi v2 của ca 01 offline: **accepted=1, excluded=2**, vẫn `insufficient_evidence` vì population từ nguồn không xác lập phạm vi tổng quát của claim. Không gọi API, không đổi raw response và không giả định prompt v3 đã được gửi. Đây là kiểm tra lại bằng postprocessor mới, chưa phải điểm kết luận cho một lượt inference v3. Xem [kết quả và provenance](../../eval/person3/scoped-rag-v2-format-report.json).

## Chạy 5 ca development

Trên dataset hiện tại đã có nguồn và model cấu hình. Lệnh này gọi API cho ca cần model; không chạy graph Agent:

```powershell
python scripts/record_scoped_rag.py --dataset data/person3/evaluation-ai --split development --allow-provisional --live-model
```

Đã có đủ năm bản ghi development; không cần gọi lại API. Chạy lại với model/prompt/context/schema/dictionary giống hệt sẽ hiện `cached` hoặc `cached_reprocessed` khi bộ kiểm tra đổi. Thay đầu vào model/dictionary/retrieval protocol thì cần bản ghi mới. Bản ghi dùng tên riêng `scoped-rag-v3-development.responses.jsonl`, raw và lịch sử attempts ở cùng thư mục; v1/v2 và baseline cũ không bị ghi đè. Một split chưa có bản ghi có gọi API cho ca hoạt chất xác định; biệt dược chưa xác định vẫn không gọi. Không chạy hai tiến trình ghi cùng file. Không truyền `--live-model` thì chỉ preview và không gọi API.

Để kiểm tra lại toàn bộ development đã lưu bằng postprocessor hiện tại, không trả tiền gọi model mới:

```powershell
python scripts/record_scoped_rag.py --dataset data/person3/evaluation-ai --split development --allow-provisional --replay-recorded data/person3/evaluation-ai/scoped-rag-v3-development.responses.jsonl
```

Lệnh này xác minh hash request, dictionary, claim và toàn bộ context với corpus cố định. Chỉ ghi báo cáo riêng `scoped-rag-v3-development.reparse.report.json`; thiếu bản ghi là lỗi, không gọi API bù. Báo cáo ghi rõ model/prompt/request gốc, postprocessor mới và `new_model_run=false`. Có thể dùng với v1/v2/v3 và ca đã có bản ghi. Không dùng báo cáo reparse thay cho responses của inference mới trong lệnh chấm bên dưới.

Sau khi ghi xong, chấm offline (thay tên model nếu đã cấu hình tên khác; phải trùng model đã ghi):

```powershell
python -m eval.run_evaluation --system scoped_rag --split development --manifest data/person3/evaluation-ai/corpus_manifest.json --claims data/person3/evaluation-ai/claims.jsonl --annotations data/person3/evaluation-ai/annotations.jsonl --recordings data/person3/evaluation-ai/scoped-rag-v3-development.responses.jsonl --model gpt-4o-mini-2024-07-18 --allow-provisional --output .local-preview/person3-ai-evaluation/scoped-rag-v3-validation-v5-development
```

Để đo truy xuất riêng, không gọi model:

```powershell
python scripts/check_scoped_rag_retrieval.py --dataset data/person3/evaluation-ai
```

## Diễn giải và bàn giao

Tập heldout cũ đã được xem. Chạy bản cải tiến trên tập đó chỉ là so sánh sau phân tích, không phải kiểm định mù. Cần một tập mới có nhãn chuyên môn độc lập để xác nhận tổng quát hóa. Baseline 1/20 vẫn giữ riêng.

Lượt heldout đã ghi 15 ca nhưng hai ca lisinopril lỗi schema `cohort`, bốn ca ibuprofen hoạt chất xác định lấy 0 đoạn. Xem [bản ghi lịch sử và hash](../../eval/person3/scoped-rag-heldout-issues-report.json). Sau sửa v5, preflight offline xác nhận **11 bản ghi tái sử dụng được**, gồm hai ca lisinopril đã hết lỗi định dạng. Các quote/scope không hợp lệ vẫn bị loại. Bốn ca ibuprofen nay lấy mỗi ca **9 đoạn: 5 PubMed, 4 FAERS, 0 DailyMed**; không coi số đoạn là bằng chứng đúng phạm vi. Xem [báo cáo sẵn sàng chạy tiếp](../../eval/person3/scoped-rag-heldout-recovery-report.json).

Ở thời điểm báo cáo recovery v5, cần **bốn lượt model mới cho ibuprofen 01–04**; 11 ca còn lại dùng `cached`/`cached_reprocessed`. Người dùng đã chạy đủ bốn lượt mới; phản hồi có context 9 đoạn nhưng báo lỗi `study_type="meta-analysis"`. V6 xử lý subtype này bằng cách ánh xạ có trace, giữ nguyên raw và đọc lại offline. Báo cáo mới tại [heldout đọc lại bằng v6](../../eval/person3/scoped-rag-validation-v6-heldout-report.json). Không cần thêm lượt API nếu giữ nguyên model/dữ liệu/prompt hiện tại. Điểm tổng hợp đủ 20 ca ở mục kết quả v6 phía trên; `needs_quote_review` vẫn là vấn đề chất lượng trích xuất cần ghi nhận.

Replay kiểm tra hash tất cả bản ghi, chỉ chọn bản có context/dictionary khớp corpus hiện tại và ghi rõ các context cũ đã bỏ qua. Checkpoint ibuprofen rỗng cũ không được dùng cho context mới; nó cũng không che mất phản hồi mới có context hợp lệ. Nếu không có bản ghi phù hợp, báo lỗi và không gọi API bù.

Đọc lại heldout offline:

```powershell
python scripts/record_scoped_rag.py --dataset data/person3/evaluation-ai --split heldout --allow-provisional --replay-recorded data/person3/evaluation-ai/scoped-rag-v3-heldout.responses.jsonl
```

```powershell
python scripts/record_scoped_rag.py --dataset data/person3/evaluation-ai --split heldout --allow-provisional --live-model
```

File thêm vào bàn giao:

```powershell
git add -- eval/baselines/scoped_rag.py eval/run_evaluation.py scripts/record_scoped_rag.py scripts/check_scoped_rag_retrieval.py scripts/test_person3_backend.py tests/test_eval/test_scoped_rag.py docs/person3/scoped_rag.md eval/person3/scoped-rag-readiness.json eval/person3/scoped-rag-v1-format-report.json eval/person3/scoped-rag-v2-format-report.json eval/person3/scoped-rag-v3-development-report.json eval/person3/scoped-rag-validation-v4-development-report.json eval/person3/scoped-rag-heldout-issues-report.json eval/person3/scoped-rag-heldout-recovery-report.json eval/person3/scoped-rag-validation-v6-heldout-report.json eval/person3/scoped-rag-final-ai-evaluation-report.json
```

Nguồn/recordings vẫn ở thư mục đã ignore. Không push `.env`, không dùng `git add -f`.
