# Người 3 — chạy với gói nguồn thật ngày 02/10/2026

> **AUTH-01 (2026-10-06):** cầu nối giao diện không còn nhận vai do trình duyệt khai
> (`X-Vigilens-Role`) và không còn token vai trò phía máy chủ. Đăng nhập bằng email + mật khẩu;
> tạo tài khoản bằng `scripts/auth_cli.py create-user`.

## Trạng thái

Đã tiếp nhận `data/mvp-candidates-50-2026-10-02.zip` từ Người 1. Gói có **50 tài liệu**: PubMed 25, DailyMed 10, FAERS 15, thuộc 5 cặp thuốc–biến cố. Đã kiểm tra schema 50 tài liệu, checksum 44 tệp, hash văn bản/raw, ID, hàng review và giới hạn section. Đây là kiểm tra tính toàn vẹn của gói được giao; chưa xác minh độc lập nội dung với website nguồn.

Dictionary có provenance cho 5 hoạt chất/5 biến cố; `diarrhea`/`diarrhoea` có attestation. Một số tên muối được ánh xạ **chỉ khi SPL XML có quan hệ active ingredient → active moiety rõ ràng**, có raw hash/URL. Không suy tên biệt dược, không gán mã ontology và không coi tên nhóm bệnh gần nhau là đồng nghĩa.

### Hai chế độ cần phân biệt

| Chế độ | Nguồn | Bộ trích xuất | Kết quả dùng cho |
|---|---|---|---|
| `offline` mặc định | Tài liệu thật trong ZIP | Gợi ý trích đoạn bằng từ khóa; luôn uncertain, scope thiếu giữ null | Kiểm tra nạp nguồn, quote/offset/hash, API, checkpoint và hồ sơ |
| `transport` | Cùng tài liệu thật | Model cấu hình trong `.env`, qua gateway/budget | Thử extraction thật sau khi có model/key; vẫn cần chuyên gia duyệt |

Ở lượt chuẩn bị ban đầu chưa có key. Sau đó người dùng cấu hình `.env` và **đã chạy model thật trên 10 tài liệu metformin**: 20 phản hồi, 13 quote hợp lệ, 3 quote bị loại do không nguyên văn, không có lỗi extraction. Hai tài liệu có quote bị loại đều có quote hợp lệ khác. Xem `eval/person3/corpus/live-source-check.json`; đây là kiểm tra kỹ thuật nguồn/citation, chưa phải metric clinical hay entailment. Chế độ offline vẫn chỉ là provider gợi ý từ khóa, với bộ đếm mô phỏng.

## Chạy thử ngay

Từ thư mục gốc dự án:

```powershell
python scripts/prepare_person3_corpus.py
python scripts/check_person3_corpus.py
python scripts/test_person3_corpus_flow.py
python scripts/check_person3_annotations.py
```

`prepare` không ghi đè các file nhận định/annotation đã có. Dictionary và audit được tái tạo từ gói có checksum. Corpus văn bản nằm ở `data/person3/corpus/documents.jsonl` và không được Git theo dõi.

Kết quả đã chạy:

- 50 tài liệu nguồn qua kiểm tra tính toàn vẹn.
- Extraction offline trên **10 tài liệu development của metformin**: **14 trích đoạn hợp lệ**, không có lỗi citation/dossier. Có tài liệu không tạo trích đoạn từ khóa; đây không phải nhãn irrelevant.
- **5/5 nhận định development** qua HTTP: 4 ca abstain đi qua review assessment → continue → dossier → review dossier → export; ca brand chưa xác định dừng ở normalization.
- Hồi quy backend hiện tại: **320 tests passed, 25 subtests passed**. Snapshot main trước các sửa locator/report: **183 tests passed, 25 subtests passed**, tám kịch bản synthetic đều PASS.
- Quyết định duyệt trong script kiểm thử dùng **DB tạm và reviewer kiểm thử**; không tạo gold hoặc duyệt cuộc điều tra đang dùng của bạn.
- 20 nhận định vẫn chờ hai người duyệt chuyên môn. File gold đang rỗng.

Các báo cáo: `eval/person3/corpus/audit.json`, `offline/report-metformin.json`, `development-api-flow.json`, `annotation-status.json`. JSON/Markdown từng tài liệu chứa trích đoạn nguồn chỉ lưu cục bộ, có tiêu đề chưa duyệt.

## Xem trên UI có sẵn

**Terminal backend:** Nếu backend cũ còn chạy cổng 8000, nhấn `Ctrl+C` ở terminal đó rồi chạy:

```powershell
$env:INVESTIGATOR_TOKEN = "person3-investigator-demo"
$env:REVIEWER_TOKEN = "person3-reviewer-demo"
python scripts/run_person3_corpus.py --family metformin
```

**Terminal UI:** dùng VigiLens hiện có. Nếu UI đã chạy đúng biến môi trường thì giữ terminal đó; nếu cần khởi động lại:

```powershell
$env:NEXT_PUBLIC_VIGILENS_DATA_MODE = "api"
$env:VIGILENS_API_BASE = "http://127.0.0.1:8000"
cd frontend
npm.cmd run dev -- --hostname 127.0.0.1
```

Mở `http://127.0.0.1:3100/app/investigations`, chọn **Điều tra mới**:

| Ô | Nhập |
|---|---|
| Nhận định | Kiểm tra bằng chứng về metformin và tiêu chảy |
| Hoạt chất | `metformin` |
| Biến cố | `diarrhoea` hoặc `diarrhea` |
| Quần thể, liều, đường dùng, thời gian | Để trống cho lượt thử đầu |

Xem Ma trận bằng chứng → mở trích dẫn → đối chiếu văn bản gốc. Trong chế độ offline, **“Chưa đủ bằng chứng” là kết quả được thiết kế**, vì chương trình không tự gán stance/scope từ việc có từ khóa. Các ca synthetic cũ vẫn chạy bằng `run_person3_demo.py` và dùng DB khác.

Nếu duyệt để thử quy trình, lý do cần nói rõ đây là kiểm thử hồ sơ abstain, chưa xác nhận chuyên môn. Duyệt assessment, trở về Điều tra viên để Tiếp tục chạy, rồi duyệt dossier mới có thể xuất Markdown. Người dùng đã thử UI corpus với model thật và gửi ảnh cùng file Markdown; bằng chứng kỹ thuật của ca development tại [manual-ui/README.md](../../eval/person3/corpus/manual-ui/README.md). Không dùng tự động hóa trình duyệt.

## Khi Người 1 cấu hình model

Không đưa API key vào Git hoặc chat. Người 1 cấu hình `.env` theo `.env.example` và model mà nhóm chọn. Khi đã có key/model:

```powershell
python scripts/check_person3_corpus.py --family metformin --provider transport
python scripts/run_person3_corpus.py --family metformin --provider transport
```

Các lệnh này có gọi dịch vụ model. Chạy development trước, đọc report và các trích dẫn bị excluded. Không chuyển sang heldout để sửa prompt. Runtime giới hạn ở cặp đã chọn; đổi `--family` cần dùng nhận định tương ứng. Nguồn vẫn là snapshot, không phải connector tìm kiếm live.

## Tài liệu dài và phạm vi

Extractor dùng cửa sổ 10.000 ký tự, overlap 2.000, tối đa 3 cửa sổ/tài liệu. Giữ cửa sổ đầu và ưu tiên cửa sổ chứa tên biến cố; không kết luận relevance chỉ từ bước chọn này. Model có thể bỏ locator: code tìm vị trí **câu nguyên văn xuất hiện duy nhất trong đúng cửa sổ đã gửi**. Locator đúng được giữ; locator sai chỉ được sửa khi quote khớp duy nhất, có alignment event và issue `realigned_exact_unique`. Không tìm trong phần chưa đọc, không sửa/paraphrase quote. Quote mơ hồ hoặc khác whitespace vẫn bị loại. Sau đó code đổi về **offset Unicode của văn bản đầy đủ** và kiểm tra hash/version.

Lượt model thật đầu tiên do người dùng chạy nhận 23 phản hồi nhưng offset model không đáng tin cậy: 0 quote hợp lệ, 7 tài liệu có lỗi. Đã sửa resolver và prompt `person3.3`. Lượt người dùng chạy sau sửa đạt **13 quote hợp lệ, 3 quote bị loại, 0 lỗi extraction**. Công cụ chat không gọi được model nhưng đọc được báo cáo live của người dùng. Có thể kiểm tra riêng một tài liệu trước:

```powershell
python scripts/check_person3_corpus.py --family metformin --provider transport --doc-id pubmed:27987248:1
```

Các báo cáo mới có `exclusion_reasons`; JSON từng tài liệu lưu `alignment_events` và `raw_model_outputs` cục bộ để chẩn đoán. Báo cáo trước sửa được giữ ở `eval/person3/corpus/transport/before-alignment-fix/`.

Console ban đầu gộp quote bị loại vào `failures`; đã sửa report để **processing failures** chỉ gồm lỗi gọi model/format hoặc citation/dossier đang hoạt động không hợp lệ. Quote bị loại được giữ trong `excluded_quotes` và `documents_with_excluded_quotes` để review; không biến thành quote được chấp nhận và không bỏ dấu vết. Một tài liệu trả findings rỗng không được tự gán irrelevant. Xem lại report cũ bằng lệnh sau, không gọi model và không sửa dữ liệu raw:

```powershell
python scripts/check_person3_corpus.py --family metformin --provider transport --summary
```

Phần chưa đọc được ghi gap theo số ký tự/coverage. Tất cả calls/repair tính ngân sách; nếu hết ngân sách giữa các cửa sổ, node lưu các trích đoạn đã kiểm chứng và dừng với insufficient. Cache tránh tính lại cửa sổ không đổi trong cùng run. Không coi các cửa sổ là các tài liệu độc lập.

PubMed là abstract-only, version là local collection, chưa xác nhận revision trên PubMed. DailyMed có thể lặp nội dung giữa SETID. FAERS có báo cáo nhiều thuốc, chỉ là background; không dùng để suy nhân quả/tỷ lệ mắc. Population/dose/time mô tả khác nhau còn giữ unknown nếu chưa có chuyển đổi đã kiểm chứng.

## Bàn giao

**Người 1:** Bộ nguồn đã nạp/kiểm tra, model đã được người dùng cấu hình và gọi thành công. Khi đưa connectors live vào runner, giữ nguyên SourceDocument text/hash/version/metadata. Nguồn snapshot không chứng minh các connectors app đã hoàn tất.

**Người 2:** Review phần chunk extraction/node/gateway. Schema API không đổi; runtime corpus được bật bằng launcher riêng, không đổi runtime mặc định. Patch 12 tệp chung vẫn dùng cho nền tích hợp trước đó.

**Người 4:** Có 20 nhận định **đề xuất kỹ thuật**, split theo family và hai form review độc lập trong `data/benchmark/`. Cần xác nhận/điều chỉnh nhận định bằng chuyên gia, đóng băng split trước tuning và kiểm tra đủ các nhóm kết luận. Không chạy metric clinical trên file gold rỗng. Hướng dẫn cụ thể tại `data/benchmark/README.md`.

### Còn cần người của nhóm để nghiệm thu

1. Một ca development đã chạy toàn runner/UI với model thật đến export: 10 tài liệu, 14 quote hoạt động, 2 bị loại, 26 calls trong trần 80, 5 bước trong trần 8. Lượt đầu lỗi format đã được phục hồi qua reviewer request_more. File xuất khớp renderer và content hash, kiểm tra dossier không có lỗi. Ca này vẫn insufficient_evidence; chưa chứng minh độ ổn định của model hay chất lượng lâm sàng.
2. Hai reviewer chuyên môn gán nhãn độc lập, giải quyết bất đồng và chốt gold/split. Bộ 50 nguồn chưa đảm bảo có precise contrary/direct contradiction; cần bổ sung nguồn nếu thiếu.
3. Entailment chuyên môn cho các statement tổng hợp. Dossier tự sinh hiện giữ quote có provenance; fact/inference/hypothesis chưa được tự phê duyệt bằng kiểm tra chuỗi.
4. Người 4 ghép baseline/evaluation và kiểm tra UI cho các ca còn lại; một ca development của Người 3 đã có ảnh thao tác và bản xuất được đối chiếu với backend.

Phần triển khai và chuẩn bị dữ liệu Người 3 có thể bàn giao; chưa đánh dấu toàn M04/M06/M09 đạt nghiệm thu chuyên môn.
