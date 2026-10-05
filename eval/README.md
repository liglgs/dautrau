# Đánh giá nhận định an toàn thuốc — P26

Thư mục này tách khỏi benchmark MedReview trong `research/`. Không dùng nhãn VMEC-03 để chấm claim cảnh giác dược.

## Kiểm tra độc lập bằng fixture

Từ gốc repo, dùng Python đã cài dependencies trong `requirements.txt`:

```powershell
python scripts/seed_demo.py
python -m pytest tests/test_eval -q
python -m eval.run_evaluation --system all --split development --mode replay --manifest data/demo/person4/corpus_manifest.json --claims data/demo/person4/claims.jsonl --annotations data/demo/person4/annotations.jsonl --recordings data/demo/person4/recordings.jsonl --model synthetic-fixture-v1 --allow-synthetic --output eval/results/person4-technical
```

Lệnh `all` hiện trả mã **1**, với 8 dự đoán keyword/RAG thành công và 4 lỗi thiếu agent hook. Đây là kết quả mong đợi khi chưa ghép agent, không phải ba hệ thống đều đã nghiệm thu. Chọn `--system keyword` hoặc `--system single_shot_rag` để kiểm tra riêng phần đã có. `--split heldout` dùng hai claim synthetic khác family; không đại diện cho tập held-out chuyên môn.

Fixture dùng thuốc/biến cố **hư cấu**, model ID `synthetic-fixture-v1` và output do tác giả fixture viết. Không có cuộc gọi model thực. Script tạo lại được corpus, recording, manifest và sáu hồ sơ minh họa; `data/demo/` vẫn nằm trong quy tắc bỏ qua dữ liệu của repo.

## Hợp đồng corpus cần Người 1/3 bàn giao

Bộ candidate của `tiendat` hiện ở `data/benchmark/`: 20 claim đề xuất, hai bộ review chưa hoàn thành, gold rỗng; ZIP nguồn không nằm trong Git. Chạy `python -X utf8 -m eval.person3_handoff --output eval/results/person4-tiendat-handoff/readiness.json` để kiểm tra blocker; thêm `--bundle <path>` khi có nguồn. Candidate manifest/annotation chưa cùng schema với P26; không truyền trực tiếp chúng vào runner hoặc dùng kết quả lexical corpus demo làm benchmark. Xem [hướng dẫn corpus Người 3](../docs/person3/real_sources.md) và hợp đồng P26 bên dưới để chuẩn bị shared retrieval-unit index, gold đã adjudicate và recordings.

`corpus_manifest.json`:

```json
{
  "schema_version": 1,
  "mode": "replay",
  "synthetic": false,
  "annotation_status": "independently_reviewed",
  "cutoff": "2026-09-30T00:00:00Z",
  "versions": {"dictionary": "...", "parser": "...", "policy": "..."},
  "documents": [{
    "doc_id": "doc-1", "source": "pubmed", "source_id": "...", "version": 1,
    "title": "...", "path": "snapshots/doc-1.txt", "sha256": "...",
    "available_at": "2026-09-29T00:00:00Z",
    "units": [{"unit_id": "unit-1", "start": 0, "end": 5, "text": "quote"}]
  }]
}
```

Mỗi claim JSONL có `claim_id`, `family_id`, `split` (`development` hoặc `heldout`), `claim_text`, `drug`, `event`, optional scope/cutoff và `related_doc_ids`. Claim IDs/split/family/gold không vào model payload. Mỗi annotation có `claim_id`, `required_evidence_ids`, `relevant_evidence_ids`, `assessment_status`, `abstained`; thêm `scope_mismatches` dạng `unit_id:field`, `contradictions` dạng `direct:unit_a|unit_b` hoặc `apparent:unit_a|unit_b`. Sắp xếp hai unit ID trong pair theo thứ tự từ điển khi nhóm chốt nhãn.

`schema_version` bắt buộc là integer 1, `synthetic`/`abstained` là boolean thật; document version integer dương, locator integer Unicode code points, source/unit IDs không rỗng. Gold assessment phải thuộc enum và refs là list IDs không trùng. Runner kiểm cả tài liệu trong gold để chặn dùng chung document giữa development/heldout ngay cả khi `related_doc_ids` bị bỏ; refs/hints sai hoặc không có trong corpus chặn trước inference/ghi report. Bộ kiểm tra ở `tests/test_eval/test_dataset_integrity.py` không thay việc chuyên viên xác minh nhãn.

Detection keys phải là list string không trùng; scope field thuộc `drug`, `event`, `population`, `dose`, `route`, `time_window`, `study_type`. Contradiction cần hai ID khác nhau theo thứ tự từ điển. Gold detection chỉ tham chiếu evidence hiển thị tại cutoff; prediction chỉ tham chiếu evidence đã retrieve. Kiểm tra split dùng `(source, source_id)` xuyên mọi version, bao gồm hints, retrieval gold và detection gold. Prediction `null` nghĩa là chưa đo; gold bỏ field nghĩa là list rỗng, gold `null` bị từ chối.

Citation support cần reviewer chấm **statement cụ thể**, gồm `statement_id`, `text`, `evidence_ids`, `supporting_evidence_ids`. Đổi text hoặc citation làm mất hiệu lực chấm cũ. ID hợp lệ không tự chứng minh statement được hỗ trợ. Citation completeness và unsupported-claim rate trả N/A nếu chưa chấm hết các factual statement. Nhãn chuyên môn, nguồn/quyền lưu, hai lượt annotation độc lập và adjudication do Người 3 cung cấp; cờ `annotation_status` không thay thế quy trình đó.

## Baseline và tích hợp agent

Keyword dùng [BM25](https://www.elastic.co/blog/practical-bm25-part-2-the-bm25-algorithm-and-its-variables), `k1=1.2`, `b=0.75`, tokenizer NFKC/casefold/Unicode word. Tính thống kê trên corpus được phép thấy; tie-break theo unit ID. Ranking không đọc gold. Keyword chỉ có metric retrieval.

RAG lấy top-20 một lần rồi đọc một recording synthesis. Recording gắn SHA-256 của **model + prompt + public claim + toàn bộ context** bằng `request_hash(request_payload(...))`, không dùng claim ID làm shortcut. Sai model, thiếu recording hoặc citation ngoài context gây lỗi; không tự gọi live API. Nếu budget tài liệu giảm thì recording phải tương ứng context mới.

`ReplayAdapter(source, BM25(corpus), manifest_path, cutoff=...)` đã khớp `RunContext.adapters`: tìm đúng nguồn qua cùng index, trả `SourceSearchResult`, tài liệu nguyên văn/hash/version và giới hạn số tài liệu còn lại. Adapter không có extractor/normalizer giả. Người 2/3 cần ghép graph với extraction/normalization đã ghi nhận trên cùng corpus và cấp hàm:

```python
def evaluate_agent(*, claim, index, config):
    # claim chỉ có thông tin công khai; không có claim_id/gold.
    # index là BM25 chung; config có model, budgets, recordings, mode.
    # Trả eval.contracts.Prediction hoặc dict tương ứng.
    # retrieved_ids là thứ tự evidence unit hiển thị cho reviewer.
    ...
```

Chạy bằng `--agent-hook your_package.module:evaluate_agent`. Hàm được gọi trong context chặn socket mạng. Không dùng `FixtureExtractor`/`scenario_for_claim` để thay agent trong benchmark thật. Agent phải báo usage/trace, versions, stop reason và bảo đảm budget trong quá trình chạy; bộ chạy còn kiểm tra document/step ceilings của kết quả. Graph hiện tại dừng ở human checkpoint; nhóm phải chốt protocol đánh giá đề xuất trước review, không tự giả chữ ký phê duyệt.

## Báo cáo và giới hạn

Ngoài CLI, giao tiếp Python đúng P26 đã có:

```python
from pathlib import Path
from eval.run_evaluation import EvaluationConfig, run_evaluation

result = run_evaluation(
    EvaluationConfig(
        manifest=Path("data/demo/person4/corpus_manifest.json"),
        claims=Path("data/demo/person4/claims.jsonl"),
        annotations=Path("data/demo/person4/annotations.jsonl"),
        recordings=Path("data/demo/person4/recordings.jsonl"),
        model="synthetic-fixture-v1",
        system="keyword",
        allow_synthetic=True,
        output=Path("eval/results/local-keyword"),
    )
)
print(result.errors, result.exit_code, result.summaries)
```

Hàm trả `EvaluationReport` gồm rows, summaries, manifest, Markdown và đường dẫn output. CLI dùng cùng hàm, không có protocol khác. Sai cấu hình/corpus làm fail trước khi ghi kết quả; thiếu/hỏng recording chỉ tạo lỗi ở các dòng RAG, không làm mất keyword hoặc lỗi agent. Chế độ keyword không đọc recording RAG. Manifest dùng đường dẫn code tương đối dạng POSIX và tìm code từ repo thay vì current working directory.

Replay chặn TCP connect, DNS và UDP sendto trong tiến trình Python khi dự đoán. Đây là guard chống gọi nhầm mạng, không phải sandbox cho hook không tin cậy hoặc tiến trình con. Hook tích hợp phải dùng replay adapters, không khởi chạy công cụ/source live. RAG báo một query và một replay synthesis call, keyword báo một query/không LLM; cost vẫn unknown.

Output gồm `per-claim.jsonl`, `aggregate.json`, `manifest.json`, `report.md`. Manifest giữ corpus/claim/annotation/recording/prompt/code hashes, commit, cutoff, model, tokenizer và ngân sách. Macro average có số mẫu/mẫu số; denominator bằng 0 trả N/A. Lỗi được giữ trong raw output và coverage. Usage recording là lịch sử; không có đơn giá xác minh thì cost là unknown.

Chưa có nguồn/gold chuyên môn, recordings model thực, agent hook, chấm safety violation độc lập hoặc thử nghiệm thời gian reviewer. Không suy ra độ giảm thời gian, hiệu quả lâm sàng, superiority của agent hay đạt các mục tiêu đề tài từ fixture.
