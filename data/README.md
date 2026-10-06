# Thư Mục Dữ Liệu Dự Án P-066 (Data Directory)

Thư mục này chứa các từ điển chuẩn hóa, bộ benchmark và các tài liệu snapshot dùng cho hệ thống kiểm chứng an toàn thuốc.

> [!IMPORTANT]
> **Toàn bộ dữ liệu lớn, file `.zip` và các thư mục snapshot thô KHÔNG được commit lên Git.**  
> Git chỉ lưu trữ các template, từ điển cấu hình nhỏ và tài liệu hướng dẫn.

---

## 📦 Link Tải Gói Dữ Liệu 50 Mẫu Ứng Viên (Candidate Corpus)

- **Link Google Drive:** [Tải gói dữ liệu 50 mẫu tại đây](https://drive.google.com/drive/folders/1G4Xd-Nve_Zs0IN3Eu5Xngrb56uSA1hu-)
- **Vị trí giải nén / đặt dữ liệu chuẩn:**
  ```text
  data/mvp-candidates-50-2026-10-02/
  ```
  *(Hoặc đặt file zip nguyên bản tại `data/mvp-candidates-50-2026-10-02.zip`)*

---

## 📂 Cấu Trúc Gói Dữ Liệu Sau Khi Giải Nén

Gói dữ liệu gồm **50 tài liệu thật** thuộc 5 cặp thuốc – biến cố bất lợi:

```text
data/mvp-candidates-50-2026-10-02/
├── amoxicillin/          # 5 PubMed, 2 DailyMed, 3 FAERS
├── atorvastatin/         # 5 PubMed, 2 DailyMed, 3 FAERS
├── ibuprofen/            # 5 PubMed, 2 DailyMed, 3 FAERS
├── lisinopril/           # 5 PubMed, 2 DailyMed, 3 FAERS
├── metformin/            # 5 PubMed, 2 DailyMed, 3 FAERS
├── raw/                  # File thô gốc (SPL XML, PubMed Tagged Text, FAERS JSON)
├── collection.json       # Metadata mô tả bộ sưu tập
├── files.sha256.json     # Checksum SHA-256 đối chiếu toàn vẹn
├── INDEX.md              # Bảng chỉ mục chi tiết 50 tài liệu
├── README.md             # Thuyết minh thu thập từ Người 1
└── review.jsonl          # Bảng gán nhãn sơ bộ cho Người 3
```

---

## 👥 Hướng Dẫn Cho Từng Thành Viên Khi Đã Có Dữ Liệu

1. **Người 1 (Connectors & Data Pipeline):**
   - Sử dụng các file thô trong `raw/` để nạp vào cache / snapshot local.
   - Nhập dữ liệu PubMed vào kho local:
     ```powershell
     python -m scripts.import_pubmed --input data/mvp-candidates-50-2026-10-02/raw/...
     ```
   - Đảm bảo runner đọc được tài liệu PubMed local khi chạy `MVP_SOURCE_MODE=live` + `MVP_PUBMED_MODE=local` mà không cần mạng; DailyMed/FAERS vẫn gọi HTTP nên hai nguồn đó cần mạng.

2. **Người 2 (Core Backend & Agent Orchestration):**
   - Chạy kiểm thử Agent Runner trên dữ liệu thật với `MVP_SOURCE_MODE=live` kết hợp `MVP_EVIDENCE_MODE=person3`.
   - Xác thực chuỗi bảo chứng nguồn gốc (provenance chain) từ claim ➔ query ➔ tài liệu nguồn ➔ evidence ➔ hồ sơ dossier.

3. **Người 3 (Evidence Extraction & Scope):**
   - Đã ánh xạ 5 hoạt chất vào từ điển `data/dictionaries/mvp_candidates_2026_10_02.json`.
   - Tiếp tục hoàn thiện trích xuất và đối chiếu trích dẫn trên 50 tài liệu này.

4. **Người 4 (Frontend & Evaluation):**
   - Dùng gói dữ liệu này để chạy kịch bản benchmark so sánh 3 hệ thống (Agent vs RAG vs Keyword):
     ```powershell
     python -m eval.run_evaluation --system all --agent-hook src.services.eval_hook:replay_agent_prediction ...
     ```
   - Hiển thị bảng ma trận bằng chứng và trích dẫn trên giao diện VigiLens.

Chi tiết xem tại tài liệu: [`docs/HUONG_DAN_DU_LIEU_50_MAU.md`](../docs/HUONG_DAN_DU_LIEU_50_MAU.md).
