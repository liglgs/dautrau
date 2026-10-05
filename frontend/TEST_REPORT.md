# Báo cáo kiểm tra Người 4 — cập nhật 03/10/2026

Phân biệt main `fa1c1d1`, các PR đề xuất và lịch sử VinhDang `0965747`. Không coi kiểm tra fixture/build là nghiệm thu nguồn/model live, session thật hoặc chất lượng chuyên môn.

## Kiểm tra mới nhất khi tách PR

| Phạm vi | Kết quả | Môi trường / giới hạn |
|---|---|---|
| P26 Python toàn bộ | 509 passed, 1 skipped, 28 subtests | Windows/Python 3.14 sau sửa integrity |
| P26 Python Docker toàn bộ | 510 passed, 28 subtests | Linux/Python 3.11; pip check/Ruff/OpenAPI đạt, network disabled |
| Eval suite | 74 tests | Gồm 20 regression detection/provenance/source-version split |
| Keyword/recorded RAG fixture | 4/4/2/2 rows, 0 errors | Development/heldout; authored synthetic recordings |
| Frontend nhánh riêng | ESLint/check:api/typecheck đạt | Node 24.21, API types khớp main |
| Frontend Vitest | 29 tests, 5 files đạt | Unit tests, không chứng minh browser luồng |
| Frontend API production build | Đạt, 46 routes | Build tuần tự sau unit/types |
| Candidate main + frontend E2E lần đầu | 5 pass, 5 fail | Chromium; có `clientReferenceManifest`/HTTP 500 |
| Candidate E2E cache mới | 4 pass, 6 fail | Navigation/create/polling/reload/review/export/citation; chưa xác định nguyên nhân |
| Candidate full-stack integration | 1 fail | POST create 202 hợp lệ, RSC investigation pending trước timeout 15 giây |
| GitHub Actions | Jobs chưa khởi chạy | Billing/spending limit; [run main](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/actions/runs/37096221686) |

Frontend source giữ cùng nội dung đã kiểm tra trên candidate; trên nhánh riêng đã chạy lại lint/API types/typecheck/unit/build, chưa chạy lại browser sau tách PR. Không thay assertions/timeout để làm xanh. [Draft source](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/tree/codex/pr-person4-frontend); cần chạy lại cả hai browser suite sau sửa trước khi ready.

Code review frontend `c595ab5`: không có Critical/credential exposure mới; một Important còn mở ở `review/page.tsx:47`. Refresh evidence thất bại vẫn làm viewed version tiến lên và xóa conflict, có thể submit version mới với evidence cũ. Cần kiểm kết quả refetch và giữ conflict/version cũ khi lỗi, kèm regression. Minor: refresh ghi đè drug/event đang sửa. Đây là điều kiện cần xử lý trước merge, bên cạnh browser regression.

P26 sửa hai findings Important từ review: measured detection phải là list keys hợp lệ/canonical, gold visible và predictions retrieved; split ownership theo `(source, source_id)` xuyên versions, kể cả detection-only gold. Regression trước sửa 18 fail; sau sửa toàn suite xanh. Review lại exact commit `ce53216` không còn Critical/Important. [PR #12](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/12).

Main trước tách PR đã được kiểm tra Docker fresh build/healthy, smoke end-to-end và backup/restore; backend Linux 436 tests, Windows 435+1 skip, frontend 10 unit tests/typecheck/build. Không yêu cầu nhập lại backend Người 3 hoặc làm lại Docker Người 1. Main không chứa eval/frontend tests mới trước khi PR merge.

## Phạm vi browser

E2E intercept API contract fixture để kiểm double-submit, cache/cursor, review 409, viewer UI, evidence scope/Unicode quote, unsafe URL/HTML, approved-only export, approval invalidation và citation. Full-stack integration dùng Next proxy → HTTP FastAPI → SQLite → graph thật, nhưng source/model synthetic. Vai trò browser không chứng minh session/server ownership; UI disable không thay bypass tests. Browser failures hiện tại chặn nghiệm thu toàn luồng.

## Lịch sử VinhDang

Ngày 02/10 tác giả ghi 295 Python (31 eval), 26 Vitest và 10 Chromium E2E đạt trên Windows/Python 3.11.16. Sau nhập tiendat: 402 Python+25 subtests, 29 Vitest, 10 E2E và 1 full-stack synthetic đạt. Sau sync main `e48d5ce`: 432 Python+28 subtests (54 eval), Ruff/API check đạt; không chạy browser trong lượt sync đó.

Đây là kết quả lịch sử trên commit/môi trường cũ; browser hồi quy mới đỏ thay thế chúng cho quyết định merge. Manifest nhập/sync vẫn giữ hashes lịch sử ở [handoff](../docs/PERSON4_MAIN_SYNC.md), không giả định chúng khớp main hiện tại. Media/demo reports không nhập trong gói này.

## Giới hạn còn lại

Chưa có gold độc lập, model recordings thật, agent hook/reviewer study; readiness có 20 proposal (5/15), gold 0, reviewer A/B 0/20 và ZIP thiếu trong worktree. Chưa nghiệm thu session/CSRF/ownership/cancel/typed contradictions/duplicates, deployment mục tiêu hay clone sạch bởi thành viên độc lập. [Status](../docs/PERSON4_STATUS.md), [integration handoff](../docs/PERSON4_TIENDAT_INTEGRATION.md).
