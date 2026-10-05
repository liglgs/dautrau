# Tách Người 4 từ VinhDang trên main

Cập nhật 03/10/2026. Main: `fa1c1d1a1e79e708ccc56cb96e51fa21a17a2392`; nguồn VinhDang: `096574754984b587dc8bfccf84c61cd67105efa9`. Ba PR độc lập đều target main, không target lẫn nhau.

| Gói | Phạm vi | Trạng thái |
|---|---|---|
| [P26 #12](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/12) | 28 file eval/seed/tests từ VinhDang, workflow và sửa integrity | Regular PR; backend regression/replay xanh, thiếu benchmark thật được ghi rõ |
| [P22–P24 frontend #13](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/13) | 39 file UI/client/tests/launcher, ignore và workflow riêng | Draft; browser regression và lỗi evidence refresh/conflict chưa đạt |
| P29 | 11 file handoff/README/test report/journal/worklog | Docs riêng; dùng PR links cho code chưa merge |

Main đã có backend Người 3, config nguồn Người 1, PubMed local, lockfile và Docker MVP. Không nhập lại commit 75 file tiendat; giữ nguyên README/ARCHITECTURE/.env/config/backend của main. Media/screenshots/deck từ VinhDang, bản plan ở gốc bị trùng, legacy docs và chỉnh imports `submit_log.py` không nằm trong gói PR.

## P26 được review và sửa thêm

Detection keys từng nhận string và evidence ngoài context; kiểm tra split từng chỉ dùng doc_id, nên hai version cùng source có thể lọt qua. Đã thêm 20 tests hồi quy (18 thất bại trước sửa), strict list/format/canonical-pair validation, gold cutoff/prediction retrieved refs, detection-only split checks và ownership `(source, source_id)` xuyên versions. Hai findings Important đã được review lại trên `ce53216`, không còn Critical/Important.

Windows/Python 3.14: 509 passed, 1 skipped, 28 subtests. Docker Linux/Python 3.11: 510 passed, 28 subtests; pip check/Ruff/OpenAPI đạt. Keyword/recorded RAG development/heldout: 4/4/2/2 rows, 0 errors, authored synthetic. Raw ngày 02/10 được giữ lịch sử trong PR, không sửa thành số đo mới.

Frontend nhánh riêng: lint/check:api/typecheck, 29 Vitest và API production build 46 routes đạt. Candidate ghép main: E2E 5 pass/5 fail, cache mới 4 pass/6 fail; integration 1 fail sau create. POST 202 hợp lệ nhưng RSC navigation pending trước timeout; chưa xác định nguyên nhân. Không coi browser xanh dựa vào kết quả cũ của VinhDang.

GitHub CI chưa chạy jobs vì billing/spending limit; [run main xác nhận](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/actions/runs/37096221686). Docker/local xanh không thay thế GitHub CI. Main Docker build/smoke/backup/restore đã được kiểm tra ở lượt trước.

## Lịch sử provenance

[person4_main_sync.json](person4_main_sync.json) mô tả lượt lấy sáu file từ main `e48d5ce` vào VinhDang, không phải manifest main hiện tại. [person4_tiendat_import.json](person4_tiendat_import.json) ghi lượt nhập `8c369c8` vào VinhDang. Giữ nguyên hashes/strategy lịch sử; chúng không yêu cầu nhập lại file hoặc chứng minh hash hiện tại.

## Phụ thuộc chưa hoàn tất

Session/CSRF/ownership, cancel/config và contradiction/duplicate/coverage APIs; ZIP corpus/frozen gold/hai reviewer/model recordings/agent hook. Readiness: 20 claims 5/15, gold 0, reviewer A/B 0/20, ZIP thiếu trong worktree kiểm tra. Media/deck tiếp tục sau chức năng; xem [status](PERSON4_STATUS.md).
