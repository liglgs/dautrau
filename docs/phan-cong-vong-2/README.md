# Phân công vòng hai — bốn người

Bản kế hoạch chính: [nghiên cứu E2E đầy đủ và phân công](NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md). Mục 1–14 có nghiên cứu nghiệp vụ, pain, data, feature, giao diện, E2E và thẩm định bản agent; mục 15–19 có task, phụ thuộc, thứ tự bàn giao và nghiệm thu. Đây là phân công đề xuất, chưa phải tiến độ được xác nhận. Các phiếu dưới đây trích cùng nội dung từ mục 15 để thuận tiện nhận việc.

```text
phan-cong-vong-2/
├── README.md
├── NGHIEN_CUU_CHUYEN_SAU_VA_GIAI_PHAP_E2E_CANH_GIAC_DUOC.md
├── nguoi-1/
│   └── README.md  # Dữ liệu, hạ tầng, deploy
├── nguoi-2/
│   └── README.md  # Agent, workflow, API
├── nguoi-3/
│   └── README.md  # Bằng chứng, hồ sơ chuyên môn
└── nguoi-4/
    └── README.md  # UI, evaluation, demo
```

| Người | Phiếu chi tiết | Số task | Bắt đầu ngay | Đầu vào cần nhận để tích hợp |
|---|---|---|---|---|
| 1 | [Dữ liệu, hạ tầng, deploy](nguoi-1/README.md) | 8 | Manifest, nguồn, data inventory, staging/backup khung | Contract nhỏ từ 2; quy tắc mapping/coverage từ 3; build/UI từ 4 cho release |
| 2 — bạn | [Agent, workflow, API](nguoi-2/README.md) | 9 | Contract A, interface/harness, permission matrix | Provenance/storage từ 1; fields/rubric/template từ 3; flow/feedback từ 4 |
| 3 | [Bằng chứng, hồ sơ chuyên môn](nguoi-3/README.md) | 8 | Rubric, mapping, extraction trên snapshot, template, annotation guide | Snapshot/metadata từ 1; interface/context từ 2; feedback giao diện từ 4; reviewer thật cho clinical labels |
| 4 | [UI, evaluation, demo](nguoi-4/README.md) | 8 | Prototype, field map, protocol/baseline; sau H1 làm UI theo examples | Contract/API từ 2; evidence/template/rubric từ 3; staging/dữ liệu từ 1 |

Thứ tự: **H0 đầu vào nghiệp vụ → H1 contract nhỏ → tiếp nhận/làm rõ → bằng chứng → phiếu trả lời/theo dõi → release/pilot**. H1 giúp ba người còn lại bắt đầu phát triển mà không phải chờ toàn bộ agent. Nguồn/storage/rubric/UI cũng là phụ thuộc của Người 2.

Tiến độ thực thi từng task (mẫu 18.3, kèm artifact và bằng chứng) ghi tại [`TIEN_DO_THUC_THI.md`](TIEN_DO_THUC_THI.md). Tài liệu mô tả dữ liệu thật nằm trong [`docs/data/`](../data/README.md).

Phân biệt `DEV_DONE` (xong phần riêng), `INTEGRATED` (nối các bên thật) và `PILOT_ACCEPTED` (người dùng/chuyên viên nghiệm thu). Khi chờ, ghi task/đầu vào thiếu/ai giao/việc có thể tiếp tục; không dùng một trạng thái “xong” chung cho cả ba mức.

Đọc mục 16 báo cáo chính để xem các gói bàn giao H0–H6, thứ tự từng đợt và cách tiếp tục khi thiếu bên khác. ADR đầy đủ/cập nhật an toàn là lát cắt B/C; dữ liệu, SOP và reviewer của bệnh viện là phụ thuộc bên ngoài, không giải quyết bằng mock.
