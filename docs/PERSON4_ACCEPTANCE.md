# Đối chiếu nghiệm thu Người 4 — mục 17–18

Cập nhật 03/10/2026 trên main `fa1c1d1` và các PR đề xuất. Đây là bằng chứng kiểm tra kỹ thuật, chưa phải nghiệm thu toàn nhóm hoặc chuyên môn. [Plan](planthegioifinal.md), [status](PERSON4_STATUS.md), [test report](../vigilens/TEST_REPORT.md).

## Definition of Done

| Điều kiện | Trạng thái | Bằng chứng / còn cần làm |
|---|---|---|
| Contract/API và ví dụ | Một phần | Main có OpenAPI; frontend Draft giữ contract hiện có, chưa có session/cancel/contradiction APIs đầy đủ |
| Tests không cần key/mạng thật | Một phần | P26 xanh Windows/Linux; frontend 29 unit tests xanh nhưng Chromium E2E/integration đỏ |
| Ghép và review | Một phần | PR P26 đã qua review hai lỗi integrity; frontend Draft còn lỗi Important evidence refresh/conflict và browser đỏ |
| Docs và giới hạn | Có bản cập nhật | PR handoff phân biệt main với đề xuất, giữ lịch sử hashes riêng |
| Clone sạch bởi người độc lập | Chưa có | Cần ghi commit, OS/runtime, lệnh và lỗi thực tế |

## Ma trận yêu cầu

| Mã | Bằng chứng kỹ thuật hiện có | Điều kiện còn thiếu |
|---|---|---|
| R01 Input | Main schema; Draft có validation/Unicode tests | Model normalization và xử lý mơ hồ bằng gold thật |
| R02 Ba nguồn | Main connectors; DailyMed/FAERS live smoke; PubMed HTTP fixture/local corpus | PubMed API live trên mạng phù hợp, nghiệm thu nguồn/quyền lưu |
| R03 Version/cutoff | Main provenance; P26 snapshot/hash/locator/cutoff và split theo source xuyên versions | Corpus benchmark thật được freeze |
| R04 Extraction | Main Person 3 demo; Draft quote/citation contract | Recordings/gold spans, rubric và chuyên viên |
| R05 Scope | P26 kiểm field keys; Draft evidence comparison | Quality trên heldout độc lập và browser regression |
| R06 Contradictions | P26 canonical direct/apparent pairs và reference checks | Typed API/labels và quality chuyên môn |
| R07 Duplicates | Chưa đủ API UI | Candidates, metadata và giải thích match |
| R08 Replanning | Main graph/demo, P26 replay adapter | Agent hook/trace/query/source change trên corpus chung |
| R09 Budget/abstention | Main budget/run state; eval ceilings/N/A | Crash/resume và rubric toàn luồng |
| R10 Review/permissions | Main version/checkpoints/role token; Draft 409 form | Browser regression; session/CSRF/ownership, direct bypass nghiệm thu |
| R11 Dossier/export | Main approved-only export; Draft quote/HTML guard tests | Browser và chuyên viên xác minh dossier |
| R12 Audit/replay | Main state/snapshots; P26 input/code/prompt/model hashes | Full agent replay và audit nghiệp vụ |
| R13 Security | Existing local-demo limits; Draft URL/HTML unit tests | Server sessions, ownership và prompt injection nghiệm thu |
| R14 UI | 29 unit tests, lint/typecheck/API build xanh trong Draft | Chromium E2E/integration hiện đỏ; chưa ready |
| R15 Benchmark | [P26 PR #12](https://github.com/AI20K-Build-Phase-Cohort-4/P-066/pull/12), 74 eval tests, synthetic baselines | Gold/recordings/agent/reviewer study thật |
| R16 Ops | Main Docker fresh build/healthy/smoke và backup/restore đã kiểm tra | GitHub jobs bị billing; môi trường deploy và recovery mục tiêu |
| R17 Handoff/demo | Runbook/main docs và gói handoff này | Peer clone sạch, media/deck cuối, narration/live URL và nghiệm thu |

K10/P22–P24 còn Draft; K11/P25–P26 có hạ tầng nhưng thiếu dữ liệu thật; K12 chưa có so sánh agent; K13 có gói Docker local, chưa có deployment/demo cuối. Không gộp “unit/build xanh” thành “luồng browser đạt”.

## Quy trình reviewer clone sạch

1. Clone commit cần review. Dùng Python 3.11+ và Node 24, cài `requirements.lock.txt`/`npm ci`; làm theo runbook và tạo token local.
2. Checkout đúng PR: eval ở #12; browser commands chỉ có trên nhánh frontend hoặc sau khi merge. Chạy lint/types/unit/build tuần tự, Chromium fixture và integration. Không bỏ assertions hoặc nới timeout để nghiệm thu.
3. Chạy seed/replay development/heldout; `all` phải báo lỗi nếu thiếu agent hook. Fixture authored không phải output model thật.
4. Kiểm tra create/poll/review/409/quote/approval invalidation/export; ghi role demo, fixture hay live. Chạy smoke/backup/restore theo runbook cho target.
5. Ghi tên/ngày/commit/OS/runtime, logs đã bỏ secrets và bước còn thiếu. Review kỹ thuật không thay gold adjudication hoặc nghiên cứu reviewer.

Media/deck từ VinhDang chưa nhập trong ba PR; không gắn link tới file chưa có trên main. Chưa có bản live/narration/PPTX được nghiệm thu.
