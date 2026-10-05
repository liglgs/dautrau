# Ví dụ demo đề xuất

Nhóm chưa cung cấp cặp thuốc–biến cố; đây là lựa chọn khởi đầu để thử normalization, chưa phải gold benchmark.

- Thuốc nhập: `aspirin`.
- Biến cố nhập: `stomach bleeding`.
- Dictionary: `data/dictionaries/aspirin_demo.json`.
- Nguồn đối chiếu tên: [DailyMed — Aspirin Regular Strength, Walgreen](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=0b27c0fd-7ea8-4588-9169-5ad4e8df77ef), nhãn cập nhật 25/06/2026, đọc ngày 02/10/2026; mục Active ingredient và Warnings.

Chỉ ghi mapping tên xuất hiện trong nguồn. Không tự thêm brand, không gán mã MedDRA, không gộp `stomach bleeding` với mọi dạng `gastrointestinal bleeding`. Mapping không xác nhận nhân quả hoặc thay việc thu thập đủ nguồn và duyệt claim.

Chưa lưu toàn nhãn hoặc tạo SourceDocument live bằng cách chép trang này. Người 1 lấy tài liệu qua connector/parser, giữ hash/version/locator. Quote và dossier preview vẫn là dữ liệu hư cấu, không lấy nhãn này làm gold.
