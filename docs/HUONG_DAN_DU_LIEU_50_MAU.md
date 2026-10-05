# Hướng Dẫn Tải & Quản Lý Dữ Liệu 50 Mẫu Ứng Viên (Candidate Corpus)

Tài liệu này hướng dẫn cách tải, cấu hình và sử dụng gói dữ liệu 50 tài liệu nguồn thực tế (`mvp-candidates-50-2026-10-02`) phục vụ thử nghiệm và đánh giá hệ thống P-066.

---

## 1. THÔNG TIN GÓI DỮ LIỆU & LINK TẢI

- **Link Google Drive chia sẻ nội bộ:**  
  👉 **[Thư mục Google Drive tải dữ liệu P-066](https://drive.google.com/drive/folders/1G4Xd-Nve_Zs0IN3Eu5Xngrb56uSA1hu-)**
- **Đường dẫn chuẩn trong dự án:**
  ```text
  data/mvp-candidates-50-2026-10-02/
  ```
  *(Hoặc file nén `data/mvp-candidates-50-2026-10-02.zip`)*
- **Quy tắc Git:** Thư mục và file `.zip` này đã được cấu hình trong `.gitignore`. **Tuyệt đối không sử dụng `git add -f` để đẩy dữ liệu lớn lên repository.**

---

## 2. TỔNG QUAN 50 TÀI LIỆU NGUỒN

Gói dữ liệu gồm **50 tài liệu được thu thập từ 3 nguồn y văn và nhãn thuốc chính thức**:

| Cặp thuốc – biến cố bất lợi | PubMed | DailyMed | FAERS | Tổng tài liệu |
|---|:---:|:---:|:---:|:---:|
| **1. Ibuprofen – Gastrointestinal haemorrhage** | 5 | 2 | 3 | 10 |
| **2. Metformin – Diarrhoea** | 5 | 2 | 3 | 10 |
| **3. Lisinopril – Cough** | 5 | 2 | 3 | 10 |
| **4. Atorvastatin – Myalgia** | 5 | 2 | 3 | 10 |
| **5. Amoxicillin – Rash** | 5 | 2 | 3 | 10 |
| **TỔNG CỘNG** | **25** | **10** | **15** | **50** |

### Cấu trúc thư mục chi tiết:
```text
data/mvp-candidates-50-2026-10-02/
├── amoxicillin/              # pubmed.json, dailymed.json, faers.json
├── atorvastatin/             # pubmed.json, dailymed.json, faers.json
├── ibuprofen/                # pubmed.json, dailymed.json, faers.json
├── lisinopril/               # pubmed.json, dailymed.json, faers.json
├── metformin/                # pubmed.json, dailymed.json, faers.json
├── raw/                      # Snapshot XML/JSON/Text thô nguyên bản
├── collection.json           # Metadata toàn bộ 50 tài liệu
├── files.sha256.json         # Checksum đối chiếu toàn vẹn
├── INDEX.md                  # Danh mục tra cứu nhanh
├── README.md                 # Thuyết minh thu thập từ Người 1
└── review.jsonl              # Ghi nhận đánh giá sơ bộ
```

---

## 3. HƯỚNG DẪN CHI TIẾT CHO TỪNG VAI TRÒ

### 📌 Người 1 (Connectors & Data Pipeline)
1. **Kiểm tra toàn vẹn**: Chạy script đối chiếu checksum:
   ```powershell
   python scripts/prepare_person3_corpus.py --bundle data/mvp-candidates-50-2026-10-02
   ```
2. **Nhập PubMed Local**: Nhập dữ liệu từ thư mục `raw/` vào kho PubMed cục bộ để ứng dụng có thể chạy mà không cần gọi mạng ngoài:
   ```powershell
   python -m scripts.import_pubmed --input data/mvp-candidates-50-2026-10-02/raw/pubmed/
   ```
3. **Cung cấp Snapshot**: Đảm bảo các file XML DailyMed và JSON FAERS được lưu vào `data/snapshots/` sẵn sàng cho kịch bản chạy offline của Agent Runner.

### 📌 Người 2 (Core Backend & Agent Orchestration)
1. **Chạy Runner với dữ liệu thật**: Cấu hình biến môi trường trong `.env` hoặc terminal:
   ```powershell
   $env:MVP_SOURCE_MODE="live"
   $env:MVP_PUBMED_MODE="local"
   $env:MVP_EVIDENCE_MODE="person3"
   ```
2. **Kiểm tra chuỗi truy xuất nguồn gốc (Provenance Chain)**:
   - Đảm bảo khi tạo cuộc điều tra với 1 trong 5 cặp thuốc trên, Agent Runner truy xuất đúng tài liệu từ gói dữ liệu này, trích xuất bằng chứng có `doc_id` và `quote` khớp 100% với văn bản gốc.
3. **Kiểm tra trần ngân sách**: Xác nhận các giới hạn `max_steps` và `max_documents` trong `InvestigationConfig` hoạt động chính xác khi duyệt qua tập tài liệu này.

### 📌 Người 3 (Extraction, Scope & Contradiction)
1. **Từ điển chuẩn hóa**: Đã tích hợp 5 cặp thuốc vào `data/dictionaries/mvp_candidates_2026_10_02.json`.
2. **Kiểm thử trích xuất**: Chạy bộ test trích xuất trên tập dữ liệu này:
   ```powershell
   python -m pytest tests/test_evidence/test_person3_evaluation.py -v
   ```

### 📌 Người 4 (Frontend, UI & Evaluation)
1. **Chạy Benchmark Đánh giá**: Sử dụng bộ dữ liệu này kết hợp với hook của Người 2 để chạy đánh giá so sánh:
   ```powershell
   python -m eval.run_evaluation --system all --agent-hook src.services.eval_hook:replay_agent_prediction --manifest data/benchmark/corpus_manifest.json --claims data/benchmark/claims.jsonl --annotations data/benchmark/annotations.jsonl
   ```
2. **Hiển thị giao diện**: Đảm bảo các trích dẫn (`quote`) và tài liệu gốc (`documents/{doc_id}`) hiển thị mượt mà trên giao diện VigiLens khi người dùng tra cứu các ca trong tập 5 cặp thuốc mẫu.
