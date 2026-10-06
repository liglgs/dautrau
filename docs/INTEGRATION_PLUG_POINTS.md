# Điểm cắm tích hợp (M10) — hợp đồng cho Người 1, Người 3 và Người 4

Tài liệu này mô tả **đúng những gì cần cắm vào** để thay mock bằng mã thật mà không phải sửa
`src/agents/graph.py`. Mọi điểm cắm nằm trong `RunContext` (`src/services/runner.py`):

| Trường | Ai cắm | Giao diện bắt buộc |
|---|---|---|
| `ctx.adapters[source]` | Người 1 | `name: str` + `search(action: PlannerDecision, budget: BudgetState) -> SourceSearchResult` |
| `ctx.extractor` | Người 3 | `extract_evidence(document: SourceDocument, claim: NormalizedClaim) -> list[EvidenceUnit]` |
| `ctx.normalizer` | Người 3 | `normalize_claim(claim: ClaimInput) -> NormalizedClaim` |
| `ctx.evidence_analyzer` | Người 3 | `analyze(evidence, claim)` với assessment/scope/gaps; graph gắn budget vào extractor trước mỗi bước |
| `ctx.dossier_builder` | Người 3 (mặc định: `src.services.dossier.build_dossier`) | `(state: InvestigationState) -> Dossier` |

`ctx.adapters` phải có đủ ba khóa `pubmed`, `dailymed`, `faers` (khóa nguồn trùng với
`SourceDocument.source`). Nếu `ctx.adapters` rỗng và không có `ctx.source_factory`, graph tự dùng `FixtureAdapter` (chế độ demo). Với `MVP_SOURCE_MODE=live`, runner gắn `source_factory` để tạo adapters từ normalized claim. `MVP_PUBMED_MODE=local` chọn corpus PubMed đã import; không tự fallback từ API lỗi.

Với `MVP_SOURCE_MODE=warehouse`, runner gắn `source_factory` dùng `src/services/sources/warehouse.py`:
ba adapter cùng tên nguồn truy hồi trên kho ELT (chỉ mục RAG xếp hạng, toàn văn đọc từ PostgreSQL).
Adapter trả `requests_used=0`, giữ provenance trong `SourceDocument.metadata`
(`retrieval_method`, `chunk_id`, `retrieval_score`, `quality_flags`, `matched_excerpt`) và trả
`SourceStatus.ERROR` khi chỉ mục thiếu — graph ghi gap thay vì bịa tài liệu.

## 1. Ví dụ cắm nhanh

Runtime đã ghép Người 3 bằng `MVP_EVIDENCE_MODE=person3` + `MVP_SOURCE_MODE=live`, với `MVP_DICTIONARY_PATH` trỏ dictionary verified. Xem [hướng dẫn](person3/merged_runtime.md). Cấu hình này giữ `source_factory` Người 1 và gọi gateway Người 2; mỗi run/resume được gắn bộ phân tích/hồ sơ mới. Các công cụ patch lịch sử không cần áp dụng lên main tổng hợp.

```python
from src.services.runner import InProcessRunner, RunContext
from src.agents.graph import run_investigation
from src.services.store import MvpStore

store = MvpStore("data/mvp.sqlite3")
runner = InProcessRunner(store)
state = store.get_state(investigation_id)

ctx = runner.context()
ctx.adapters = {
    "pubmed": PubMedConnector(),      # Người 1
    "dailymed": DailyMedConnector(),  # Người 1
    "faers": OpenFdaConnector(),      # Người 1
}
from src.services.evidence.integration import configure_person3
configure_person3(ctx, "data/dictionaries/mvp_candidates_2026_10_02.json")
run_investigation(state, ctx)
```

## 2. Ràng buộc bắt buộc khi cắm

1. **Không tự lưu state/budget.** Adapter chỉ trả `SourceSearchResult`; graph tự gọi
   `budget.commit(...)`, tự lưu tài liệu và tự ghi gap. Adapter gọi API nguồn và *không* ghi DB.
   Adapters thật có `search_with_budget(action, budget, on_request)`; callback do graph cấp lưu từng request trước HTTP, kể cả retry. `requests_used` ghi số request đã dùng; cache/local không gọi HTTP trả 0. Callback đã tính request thì graph không tính lại lúc commit.
2. **`fingerprint` phải dùng `src.services.planner.query_fingerprint(source, query)`.** Cơ chế
   chống lặp truy vấn và bước tìm bằng chứng phản bác dựa vào vân tay này.
3. **Lỗi nguồn trả bằng `status=SourceStatus.ERROR` + `error=...`, không ném exception.** Graph ghi
   gap `GAP-ERROR-*` và tiếp tục; exception chỉ dành cho lỗi lập trình.
4. **`status=SourceStatus.OK` mới được kèm `documents`.** Tài liệu phải có `doc_id` ổn định theo
   `(source, source_id, version)` — store chặn nếu cùng `doc_id` nhưng nội dung khác.
5. **Extractor không được bịa trích dẫn.** Mọi `EvidenceUnit` phải có `quote` là **nguyên văn** trong
   `document.text`; `review._relocate_quote` và `validate_dossier` kiểm lại điều này khi export.
   Bằng chứng không đủ điều kiện thì để `excluded=True` kèm lý do, không loại bỏ âm thầm.
6. **Không gọi LLM trực tiếp trong node/adapter.** Dùng `ctx.gateway.invoke(task, payload, ...)` để
   mọi lượt gọi đi qua cổng có ngân sách, prompt version và kiểm tra ID bằng chứng.
7. **Giữ nguyên ngôn ngữ trung tính.** Không sinh câu khẳng định nhân quả; `src/services/policy.py`
   chặn ở cửa tạo hồ sơ và cửa export.

## 3. Kiểm tra trước khi mở PR tích hợp

```bash
python -m pytest tests/test_agents/test_m10_integration.py -q        # Hợp đồng điểm cắm cơ bản
python -m pytest tests/test_agents/test_m10_live_integration.py -v   # Kiểm thử tích hợp sống Người 1-2-3 (M10)
python scripts/verify_person2_complete.py                            # Nghiệm thu 5/5 cặp ứng viên dữ liệu thật
python -m pytest tests/ -q                                           # Toàn bộ bộ kiểm thử backend
python scripts/demo_d4_replanning.py                                 # Kịch bản demo D4 (đổi query → có bằng chứng)
```

## 4. Phía Người 4 (giao diện gọi API thật)

- Base URL: `/api/v1`.
- **Xác thực:** Hỗ trợ cả 2 chế độ:
  - Header: `X-API-Token: <token>` hoặc `Authorization: Bearer <token>`.
  - Cookie Session: Cookie `access_token` được Next.js Route Handler tự động đính kèm (chế độ `NEXT_PUBLIC_VIGILENS_AUTH_MODE=session`).
- **Phân quyền & Quyền sở hữu (Ownership):**
  - Investigator chỉ thấy và thao tác trên cuộc điều tra do mình tạo (`owner_id` khớp với `client_id`).
  - Reviewer có quyền xem tất cả cuộc điều tra và thực hiện phê duyệt tại các checkpoint.
- **Hủy tác vụ an toàn (Cancel API):**
  - `POST /api/v1/investigations/{id}/cancel`: Hủy ngay lập tức điều tra đang chạy, dừng coroutine và giải phóng runner lock.
- **Tùy biến cấu hình:**
  - `POST /api/v1/investigations` nhận trường `config` (`InvestigationConfig`):
    - `sources`: danh sách nguồn kích hoạt (ví dụ: `["pubmed", "dailymed"]`).
    - `max_steps`, `max_documents`: giới hạn trần ngân sách cho ca điều tra.
    - `stop_when_contradicted`: dừng ngay khi phát hiện bằng chứng mâu thuẫn.
- CORS mặc định đã gồm `http://localhost:3000`, `http://localhost:5173` và `http://localhost:3100` (VigiLens) — đổi bằng `CORS_ORIGINS`.
- **Trình tự gọi đề xuất:**
  `POST /investigations` → poll `GET /investigations/{id}` +
  `GET /investigations/{id}/events?after_id=<số cuối đã nhận>` → `GET /investigations/{id}/evidence`
  → khi `run_status=waiting_for_review` thì `POST /investigations/{id}/reviews` → `POST /{id}/continue`
  → `GET /{id}/dossier` → `GET /{id}/export` (chỉ khi đã duyệt).
