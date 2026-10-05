# Bàn giao Người 3 cho Người 4

Cập nhật 03/10/2026 trên main `fa1c1d1`. Lượt lịch sử VinhDang nhập 75 file từ tiendat `8c369c8` được ghi ở [manifest](person4_tiendat_import.json). Backend evidence/dossier/graph/API và dữ liệu proposal đã có trên main; các PR Người 4 không nhập lại gói backend đó. Hash trong manifest là lịch sử lượt nhập, không phải hash main hiện tại.

## Frontend và full-stack integration

[Nhánh frontend Draft](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/tree/codex/pr-person4-frontend) thêm annotation mapping/quote comparator và uncertainty, giữ scope/exclusion/version/Unicode locator, cùng launcher/test browser. Chưa merge; browser hồi quy hiện thất bại ở navigation sau create. Kết quả 402 Python/29 Vitest/1 integration xanh từ lượt VinhDang cũ chỉ là lịch sử, không dùng để nghiệm thu main mới.

Sau checkout nhánh frontend (hoặc sau khi merge), cài backend dependencies rồi chạy:

```powershell
cd frontend
$env:PERSON4_TEST_PYTHON=(Resolve-Path ../.venv/Scripts/python.exe).Path
$env:MVP_SOURCE_MODE='fixture'
npm.cmd exec playwright install chromium
npm.cmd run test:integration
```

Linux dùng `PERSON4_TEST_PYTHON=python npm run test:integration`. Mặc định config là `.tools/venv/Scripts/python.exe` cục bộ Windows; clone khác phải đặt biến interpreter. Launcher dùng DB tạm riêng, FastAPI 8203/Next 3103 và Person 3 synthetic graph; browser không stub API, nhưng nguồn/model vẫn synthetic. Token test và role chọn trong UI không chứng minh session/ownership.

## Đầu vào P26

CLI/readiness và replay contracts ở [PR #12](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/12), chưa có trên main trước khi PR merge:

```powershell
python -X utf8 -m eval.person3_handoff --output data/person4-readiness.json
# Khi có ZIP thực, thêm --bundle với đường dẫn thật
```

CLI chỉ kiểm provenance/count/split/review/bundle; exit 2 khi còn blocker, không tạo gold hay metric chuyên môn. Lượt kiểm tra hiện có 20 claim proposal (5 development/15 heldout), gold 0 dòng, reviewer A/B 0/20 hoàn thành, manifest `draft_not_frozen_not_gold`, ZIP không có trong worktree. Không kết luận ZIP không tồn tại ở máy/người khác.

Để benchmark thật cần:

1. Bundle `mvp-candidates-50-2026-10-02.zip`, SHA-256 `6fbcfd1970318cb0562e6b260be1da6cfe783c8b9961ddb923a59d0195ad66f7`, nguồn/quyền lưu và corpus/index freeze.
2. Hai reviewer độc lập, adjudication, frozen gold và protocol tiếp xúc heldout/cutoff/versions. Proposal hay nhãn hệ thống không thay gold.
3. [Eval contract](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/tree/codex/pr-person4-evaluation/eval/README.md): units từ corpus độc lập với gold, map spans/field/pair vào units; cùng dictionary/parser/policy, tách source identity xuyên versions giữa splits.
4. Model recordings gắn request hash, agent hook dùng cùng BM25/replay adapter, protocol trước human review, usage/trace. CandidateQuoteProvider và demo adapter không thay benchmark retrieval/RAG công bằng.
5. Chạy browser xanh và nhận session/ownership/cancel/typed APIs; sau đó mới nghiệm thu UI, reviewer effort và demo cuối.

Hướng dẫn backend hiện tại: [Person 3](person3/README.md), [runbook](runbook.md). [Test report](../vigilens/TEST_REPORT.md) phân biệt main, các PR và lượt kiểm tra lịch sử.
