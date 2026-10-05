# Bàn giao Người 4 — P22–P24, P26, P29

Cập nhật 03/10/2026, đối chiếu main `fa1c1d1`. Nguồn chọn lọc: VinhDang `0965747`. Phạm vi theo [plan](planthegioifinal.md); frontend MVP là `vigilens/`.

## Main và các PR đang đề xuất

Main đã có backend evidence/dossier Người 3 và phần Người 1: connectors, PubMed local chủ động, lockfile, Docker MVP, CI, smoke và backup/restore. Xem [bàn giao Người 1](mvp-person1-status.md), [runbook](runbook.md), [architecture](../ARCHITECTURE.md). MVP dùng SQLite, một Uvicorn worker và runner trong tiến trình; PostgreSQL/worker của VMEC cũ không phải điều kiện triển khai MVP hiện tại. PubMed API live chưa nghiệm thu trên mạng kiểm tra; nguồn/model live hoàn chỉnh và session server vẫn chưa hoàn tất.

| Hạng mục | Phần đề xuất từ Người 4 | Trạng thái / phần còn thiếu |
|---|---|---|
| P22 | Tooling ESLint/API types, client xử lý lỗi | [PR frontend #13](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/13) là Draft; session/login/CSRF/ownership chưa có |
| P23 | Validate claim, double-submit/idempotency, cursor/polling/cache | Browser navigation/polling/reload đang lỗi; cancel và tùy chỉnh nguồn/budget còn phụ thuộc API |
| P24 | Review theo version, giữ form khi 409, quote Unicode, evidence comparison, export guard | Browser review/dossier chưa đạt; typed contradictions/duplicate/coverage và quyền server chưa đầy đủ |
| P26 | Corpus replay, BM25/recorded RAG, metrics N/A, raw/manifests, readiness và integrity checks | [PR #12](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/12) chỉ là hạ tầng; thiếu gold độc lập, recordings thật, agent hook và nghiên cứu reviewer |
| P29 | Handoff, test report, quy trình chạy và demo scenarios | Tài liệu phân biệt main/PR; media/deck, deploy URL và nghiệm thu toàn nhóm chưa thuộc gói PR này |

Các dòng trên là phạm vi đề xuất, không khẳng định frontend/eval đã merge vào main. [Test report](../vigilens/TEST_REPORT.md) ghi các lượt kiểm tra hiện tại; kết quả browser cũ trên VinhDang không thay thế hồi quy trên main mới.

## Bàn giao tiếp theo

- Người 2: session/login/me/logout, CSRF/expiry/ownership; cancel/config và typed response models; agent replay hook, usage/trace và protocol trước human review. Backend hiện dùng `/continue`.
- Người 3: corpus snapshot/index được freeze, quyền lưu, claims/family/split, gold span/field/pair và hai reviewer độc lập/adjudication; recordings có request hash, statement citation review và coverage/duplicates. [Handoff](PERSON4_TIENDAT_INTEGRATION.md) ghi đầu vào cụ thể.
- Người 1/nhóm: giữ cấu hình MVP theo runbook; hỗ trợ kiểm tra PubMed API live trên mạng phù hợp và nghiệm thu môi trường triển khai. Lockfile/container/backup đã có, không yêu cầu làm lại hoặc thay bằng stack PostgreSQL cũ.
- Người 4: sửa lỗi review refresh tiến version/xóa conflict khi evidence refetch thất bại; xử lý giữ dirty claim fields khi refresh. Sửa/kiểm chứng browser failures trong Draft; chạy lại Chromium fixture và full-stack integration, nhận review rồi mới chuyển ready. Benchmark thật chỉ chạy sau khi đủ đầu vào; media/demo/deck tiếp tục sau phần chức năng.

Chưa có đo thời gian làm/reviewer effort hoặc ký nghiệm thu chuyên môn. Không nhập lại 75 file backend Người 3 đã có trên main; không sửa `docs/guide/`, hooks hoặc tài liệu MedReview cũ trong gói này.
