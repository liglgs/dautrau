# Thư mục `docs/data` — dữ liệu của VigiLens (P-066)

Thư mục này mô tả **dữ liệu nào được dùng, lấy từ đâu, xử lý thế nào và đạt chuẩn gì**.
Đây là tài liệu kèm theo kho ELT, không thay thế kế hoạch trong `docs/phan-cong-vong-2/`.

## Đọc theo thứ tự

| Tài liệu | Nội dung |
| --- | --- |
| [`nguon-du-lieu.md`](nguon-du-lieu.md) | Danh mục nguồn dữ liệu: 3 nguồn API, gói 50 mẫu, gói tham chiếu; mỗi nguồn trả lời được câu hỏi gì và **không** trả lời được gì |
| [`tien-xu-ly.md`](tien-xu-ly.md) | Quyết định tiền xử lý: tải thô, băm, văn bản chuẩn hoá, cắt đoạn, chống trùng |
| [`cong-chat-luong.md`](cong-chat-luong.md) | Cổng chất lượng: điều kiện `keep` / `quarantine` / `reject` và bằng chứng |
| [`bao-cao-chat-luong.md`](bao-cao-chat-luong.md) | **Tự sinh** từ lần chạy ELT thật (số liệu, không viết tay) |
| [`cau-truc-kho.md`](cau-truc-kho.md) | Cấu trúc PostgreSQL + ChromaDB, cách truy vấn và kiểm tra khớp hai kho |

## Chạy lại từ máy mới (1 lệnh)

```bash
./scripts/setup_elt.sh
```

Lệnh này tạo môi trường ảo, cài phụ thuộc, dựng PostgreSQL bằng Docker, tải dữ liệu,
nạp kho, dựng chỉ mục vector và kiểm tra khớp số liệu. Xem `scripts/setup_elt.sh --help`.

Kiểm tra lại bất cứ lúc nào:

```bash
python -m scripts.elt.check_warehouse      # kho PostgreSQL + chỉ mục ChromaDB
python -m scripts.elt.docs_data            # sinh lại docs/data/bao-cao-chat-luong.md
```

## Nguyên tắc bắt buộc

1. **Không nguỵ tạo dữ liệu.** Mọi con số trong tài liệu này đến từ manifest, báo cáo ELT hoặc truy vấn kho thật.
2. **Phân biệt mục đích nguồn.** PubMed = tra cứu bằng chứng (chỉ tóm tắt), DailyMed = đối chiếu nhãn,
   FAERS = báo cáo nghi ngờ ADR. Không dùng FAERS để suy nhân quả hay tỷ lệ mắc.
3. **Gói 50 mẫu chưa phải chuẩn vàng.** `review.jsonl` vẫn `pending`, `gold_label: null`;
   mọi cặp thuốc–biến cố mang trạng thái `candidate_not_gold`.
4. **Không xoá tài liệu cũ.** Thêm tệp mới thay vì sửa/xoá nội dung đã công bố.
