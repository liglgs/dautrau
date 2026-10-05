# P-066 / VigiLens — AI Agent Điều Tra & Kiểm Chứng Bằng Chứng An Toàn Thuốc

> **Dự án:** P-066 (VigiLens) — Hệ thống AI Agent hỗ trợ chuyên viên điều tra, thu thập và đối chiếu đa nguồn bằng chứng an toàn thuốc y khoa (PubMed, DailyMed, FAERS) với cơ chế phân xử mâu thuẫn (Contradiction Handling), kiểm soát ngân sách nghiêm ngặt và quy trình thẩm định chuyên gia có kiểm toán (Human-in-the-loop).

[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Orchestrator-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![API](https://img.shields.io/badge/Backend-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2015-black.svg)](https://nextjs.org/)
[![Tests](https://img.shields.io/badge/Tests-572%20Passed-brightgreen.svg)]()
[![Gate G2](https://img.shields.io/badge/Gate%20G2-Ready-success.svg)]()

---

## 📌 MỤC LỤC

1. [Tổng Quan & Giá Trị Cốt Lõi](#1-tổng-quan--giá-trị-cốt-lõi)
2. [Hồ Sơ Nghiệm Thu Gate G2](#2-hồ-sơ-nghiệm-thu-gate-g2)
3. [Kiến Trúc Hệ Thống & Luồng Dữ Liệu](#3-kiến-trúc-hệ-thống--luồng-dữ-liệu)
4. [Hướng Dẫn Cài Đặt & Khởi Chạy Nhanh](#4-hướng-dẫn-cài-đặt--khởi-chạy-nhanh)
5. [Bảng Cấu Hình Biến Môi Trường (Environment Variables)](#5-bảng-cấu-hình-biến-môi-trường-environment-variables)
6. [Các Câu Truy Vấn Mẫu (Sample Queries)](#6-các-câu-truy-vấn-mẫu-sample-queries)
7. [Kiểm Thử & Nghiệm Thu Hệ Thống](#7-kiểm-thử--nghiệm-thu-hệ-thống)
8. [Tài Liệu Kỹ Thuật Liên Quan](#8-tài-liệu-kỹ-thuật-liên-quan)

---

## 1. Tổng Quan & Giá Trị Cốt Lõi

VigiLens giải quyết bài toán rà soát và đánh giá các báo cáo tín hiệu an toàn thuốc (Adverse Drug Events) từ các cơ quan quản lý và y văn lâm sàng:
- **Truy xuất đa nguồn có nguồn gốc (Multi-source Provenance):** Tích hợp tự động 3 nguồn dữ liệu chuẩn mực: **PubMed** (y văn đối chứng), **DailyMed** (nhãn thuốc FDA chính thức) và **openFDA FAERS** (báo cáo biến cố bất lợi tự nguyện).
- **Chống ảo giác 100% (Strict Non-hallucination):** Toàn bộ câu trích dẫn bằng chứng (`EvidenceUnit.quote`) bắt buộc phải trùng khớp nguyên văn từng ký tự (`exact quote locator`) với văn bản gốc (`document.text`).
- **Điều phối Agent hữu hạn (Deterministic LangGraph StateGraph):** Vòng lặp điều tra có điểm dừng rõ ràng, tự động thay đổi chiến lược truy vấn khi gặp bão hòa/kết quả rỗng, kiểm soát trần ngân sách (`BudgetState`) để loại bỏ hoàn toàn nguy cơ lặp vô tận.
- **Phê duyệt con người (Human-in-the-loop):** Dừng tại 2 checkpoint độc lập: thẩm định kết luận sơ bộ (`assessment`) và phê duyệt xuất bản hồ sơ tổng hợp (`dossier`). Chỉ hồ sơ đã qua phê duyệt mới được xuất bản (`export Markdown`).

---

## 2. Hồ Sơ Nghiệm Thu Gate G2

Dự án đã chuẩn bị đầy đủ 5 tiêu chí nghiệm thu của **Gate G2 (hạn chót: 23:59 ngày 04/10/2026)**:

| # | Yêu Cầu Gate G2 | Chi Tiết Minh Chứng Trong Repo | Đường Dẫn / Trạng Thái |
|:---:|---|---|---|
| **1** | **MVP Demo** | Video demo quay toàn bộ luồng người dùng (user flow end-to-end) từ nhập claim, xem timeline, tra cứu bằng chứng, kiểm tra quote locator đến review & export | [`presentation/person4_ui_fixture_demo.webm`](presentation/person4_ui_fixture_demo.webm)<br>Bộ ảnh: [`docs/demo_assets/`](docs/demo_assets/) |
| **2** | **Architecture Diagram** | Sơ đồ kiến trúc tổng thể, 14 nodes LangGraph StateGraph, data flow và các ranh giới thành phần | [`ARCHITECTURE.md`](ARCHITECTURE.md)<br>Sơ đồ chi tiết: [`docs/architecture_diagram.md`](docs/architecture_diagram.md) |
| **3** | **Repo >= 10 PR Merged** | Kho lưu trữ đã có **17 Pull Requests được sáp nhập (merged)** vào nhánh `main` (PR #1, #4, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15, #16, #17, #18, #19, #20) | **Đạt 17/10 PRs (170%)** |
| **4** | **README.md** | Hướng dẫn cài đặt chi tiết, bảng biến môi trường toàn diện, 5 câu truy vấn mẫu copy-paste | *Chính tài liệu này (Mục 4, 5, 6)* |
| **5** | **Eval Evidences** | Báo cáo chi tiết nghiệm thu **5 test case manual** chạy thực tế trên 5 cặp ứng viên lâm sàng, kèm toàn văn hồ sơ dossier xuất ra | [`docs/GATE2_EVAL_EVIDENCES.md`](docs/GATE2_EVAL_EVIDENCES.md) |

---

## 3. Kiến Trúc Hệ Thống & Luồng Dữ Liệu

```mermaid
flowchart TB
    subgraph UI_Layer ["Tầng Giao Diện Người Dùng (Next.js 15)"]
        UI["VigiLens Frontend (Tailwind, Zustand)"]
        ProxyRoute["Next.js Route Handler (/api/backend/*) - Quản lý Session Cookie"]
    end

    subgraph API_Layer ["Tầng Dịch Vụ API (FastAPI)"]
        AuthMid["Xác thực Quyền (Investigator / Reviewer)"]
        InvRoutes["Investigations API (/api/v1/investigations)"]
        RevRoutes["Reviews & Checkpoints API (/reviews, /continue, /cancel, /export)"]
    end

    subgraph Core_Engine ["Bộ Điều Phối Agent & Vòng Đời (LangGraph)"]
        Runner["InProcessRunner (Khóa Đơn Độc Quyền, Hủy An Toàn)"]
        Store[("SQLite Store (Bất biến State, Events, Documents & Dossiers)")]
        Graph["LangGraph State Machine (14 Nodes & Checkpoints)"]
        Budget["Budget & Stopping Controller (Ngân sách bước, tài liệu, LLM calls)"]
    end

    subgraph Evidence_Layer ["Tầng Trích Xuất & Phân Tích Bằng Chứng"]
        Norm["Claim Normalizer & Dictionary Mapping"]
        Extract["Evidence Extractor (Exact Quote Locators)"]
        Scope["Scope Matcher & Contradiction Detection"]
        Builder["Dossier Builder & Policy Enforcement"]
    end

    subgraph Data_Sources ["Tầng Nguồn Bằng Chứng"]
        PubMed["PubMed Adapter (Corpus Local & API)"]
        DailyMed["DailyMed Adapter (Nhãn thuốc FDA)"]
        FAERS["FAERS Adapter (Báo cáo Biến Cố Bất Lợi)"]
    end

    %% Kết nối
    UI --> ProxyRoute
    ProxyRoute --> AuthMid
    AuthMid --> InvRoutes & RevRoutes
    InvRoutes --> Runner
    RevRoutes --> Store
    Runner --> Graph
    Graph --> Norm
    Graph --> PubMed & DailyMed & FAERS
    Graph --> Extract & Scope
    Graph --> Budget
    Graph --> Builder
    Graph --> Store
```

---

## 4. Hướng Dẫn Cài Đặt & Khởi Chạy Nhanh

### Kho dữ liệu ELT/RAG (một lệnh cho máy mới)

Ngoài hai ứng dụng trên, repo có kho dữ liệu ELT (PostgreSQL + ChromaDB) cho PubMed/DailyMed/FAERS.
Trên một máy mới, chạy duy nhất:

```bash
./scripts/setup_elt.sh          # tạo venv, cài phụ thuộc, dựng PostgreSQL, tải dữ liệu, nạp kho, dựng chỉ mục, kiểm tra
```

Tùy chọn: `--offline` (không dùng mạng), `--live` (tải thêm từ API nguồn), `--no-rag`, `--reset`, `--skip-install`.
Kiểm tra lại bất cứ lúc nào bằng `make elt-check`; mô tả dữ liệu nằm trong `docs/data/`;
tiến độ từng task của vòng hai nằm trong `docs/phan-cong-vong-2/TIEN_DO_THUC_THI.md`.

**Khi hết hạn mức nhúng vector:** bước dựng chỉ mục cần khoá Gemini (8 khoá luân phiên).
Nếu tất cả khoá đều trả HTTP 429, đặt `RAG_EMBEDDING_PROVIDER=hash` trong `.env` rồi chạy lại
`./scripts/setup_elt.sh --skip-install`. Chế độ `hash` chạy cục bộ, không cần mạng — chỉ để kiểm tra
đường ống (kho PostgreSQL, ChromaDB, số đoạn khớp nhau); chất lượng ngữ nghĩa thấp hơn Gemini.
Chỉ mục sinh bằng `hash` nằm ở bộ sưu tập khác, nên muốn quay lại Gemini thì chạy lại với
`--reset` (hoặc `python -m scripts.elt.load_chroma --reset-index`).

Các lệnh tiện dụng: `make db-up`, `make db-down`, `make elt-run`, `make elt-docs`, `make dev-api`, `make dev-web`.

---

### Yêu Cầu Hệ Thống
- **Python:** 3.11 hoặc mới hơn (khuyên dùng môi trường ảo `.venv`).
- **Node.js:** 20.x hoặc 24.x (`npm.cmd` trên Windows).
- **Hệ điều hành:** Hỗ trợ Windows (PowerShell) và Linux/macOS.

---

### Khởi Chạy Backend (FastAPI)

```powershell
# 1. Cài đặt các gói phụ thuộc Python
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt

# 2. Thiết lập biến môi trường và chạy server Uvicorn (cổng 8000)
$env:APP_ENV="development"
$env:INVESTIGATOR_TOKEN="test-investigator-token-12345"
$env:REVIEWER_TOKEN="test-reviewer-token-12345"
$env:MVP_DB_PATH="data/mvp.sqlite3"
$env:MVP_SOURCE_MODE="fixture"  # Dùng 'live' nếu muốn kết nối nguồn thật
$env:MVP_SNAPSHOT_ROOT="data/snapshots"

.\.venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 1
```

*Kiểm tra backend đã sẵn sàng:* Truy cập `http://127.0.0.1:8000/health` (trả về `{"status":"ok"}`).

---

### Khởi Chạy Frontend (VigiLens Next.js)

Trong một cửa sổ dòng lệnh riêng biệt:

```powershell
cd frontend

# 1. Cài đặt các gói npm
npm.cmd ci

# 2. Cấu hình biến môi trường cục bộ (tạo file frontend/.env.local)
# NEXT_PUBLIC_VIGILENS_AUTH_MODE=session
# VIGILENS_BACKEND_URL=http://127.0.0.1:8000
# VIGILENS_INVESTIGATOR_TOKEN=test-investigator-token-12345
# VIGILENS_REVIEWER_TOKEN=test-reviewer-token-12345

# 3. Khởi chạy giao diện (cổng 3100)
npm.cmd run dev -- -p 3100 -H 127.0.0.1
```

Mở trình duyệt tại: **`http://127.0.0.1:3100`**

---

### Chạy Bằng Docker Compose

Nếu sử dụng Docker Desktop:

```powershell
$env:INVESTIGATOR_TOKEN="test-investigator-token-12345"
$env:REVIEWER_TOKEN="test-reviewer-token-12345"
docker compose -f docker-compose.mvp.yml up -d --build
```
Hệ thống sẽ tự động khởi tạo backend tại cổng `8000` và frontend tại cổng `3100`.

---

## 5. Bảng Cấu Hình Biến Môi Trường (Environment Variables)

Hệ thống hỗ trợ cấu hình linh hoạt qua biến môi trường hoặc file `.env`:

### 1. Cấu Hình Backend (`src/`)

| Tên biến | Kiểu giá trị | Mặc định | Ý nghĩa & Mô tả |
|---|:---:|:---:|---|
| `APP_ENV` | `string` | `development` | Môi trường chạy (`development`, `production`, `test`). |
| `PORT` | `int` | `8000` | Cổng dịch vụ FastAPI. |
| `INVESTIGATOR_TOKEN` | `string` | *(Bắt buộc)* | Token bí mật cho vai trò Điều tra viên (`investigator`). |
| `REVIEWER_TOKEN` | `string` | *(Bắt buộc)* | Token bí mật cho vai trò Thẩm định viên (`reviewer`). |
| `MVP_DB_PATH` | `string` | `data/mvp.sqlite3` | Đường dẫn tệp cơ sở dữ liệu SQLite lưu trữ trạng thái. |
| `MVP_SOURCE_MODE` | `string` | `fixture` | Chế độ nguồn dữ liệu: `fixture` (offline demo) hoặc `live` (nguồn thực tế). |
| `MVP_PUBMED_MODE` | `string` | `local` | Chế độ PubMed: `local` (tìm trên corpus đã import) hoặc `api` (gọi NCBI live). |
| `MVP_EVIDENCE_MODE` | `string` | `person3` | Chế độ trích xuất bằng chứng: `person3` (bộ phân tích y khoa chuẩn hóa) hoặc `fixture`. |
| `MVP_PUBMED_CORPUS_ROOT`| `string` | `data/pubmed-local`| Đường dẫn thư mục chứa các bài báo PubMed cục bộ đã nạp. |
| `MVP_SNAPSHOT_ROOT` | `string` | `data/snapshots` | Đường dẫn thư mục lưu cache raw snapshots (DailyMed / FAERS). |
| `MVP_DICTIONARY_PATH` | `string` | `data/dictionaries/mvp_candidates_2026_10_02.json` | Đường dẫn từ điển chuẩn hóa hoạt chất & biến cố y khoa. |
| `CORS_ORIGINS` | `string` | `http://localhost:3000,http://localhost:3100,http://127.0.0.1:3100` | Danh sách URL được phép truy cập CORS. |

### 2. Cấu Hình Frontend (`frontend/.env.local`)

| Tên biến | Kiểu giá trị | Mặc định | Ý nghĩa & Mô tả |
|---|:---:|:---:|---|
| `NEXT_PUBLIC_VIGILENS_DATA_MODE` | `string` | `mock` | Nguồn dữ liệu của giao diện: `mock` (dữ liệu mẫu) hoặc `api` (gọi backend thật). |
| `NEXT_PUBLIC_VIGILENS_AUTH_MODE` | `string` | `session` | Cơ chế xác thực: `session` (cookie HTTP-only an toàn) hoặc `token` (công tắc vai trò, chỉ dùng khi demo local). |
| `NEXT_PUBLIC_VIGILENS_API_PREFIX` | `string` | `/api/backend` | Tiền tố cầu nối server route sang backend FastAPI. |
| `VIGILENS_API_BASE` | `string` | `http://127.0.0.1:8000` | URL gốc của backend FastAPI mà cầu nối `/api/backend/*` gọi tới. |
| `VIGILENS_INVESTIGATOR_TOKEN` | `string` | `test-investigator-token-12345` | Token investigator dùng cho server route proxy (không lọt vào bundle trình duyệt). |
| `VIGILENS_REVIEWER_TOKEN` | `string` | `test-reviewer-token-12345` | Token reviewer dùng cho server route proxy. |
| `NEXT_ALLOWED_DEV_ORIGINS` | `string` | *(trống)* | Danh sách host cho phép khi chạy dev server sau proxy công khai (cách nhau dấu phẩy). |

### 3. Cấu Hình Kho Dữ Liệu ELT/RAG (backend, trong `.env`)

Các biến này do `./scripts/setup_elt.sh` ghi vào `.env` nếu còn thiếu; xem thêm `docs/data/cau-truc-kho.md`.

| Tên biến | Kiểu giá trị | Mặc định | Ý nghĩa & Mô tả |
|---|:---:|:---:|---|
| `ELT_DATABASE_URL` | `string` | `postgresql+psycopg://medreview:medreview@localhost:5433/vigilens_elt` | Chuỗi kết nối kho PostgreSQL của ELT (cổng 5433, tách khỏi kho VMEC cũ). |
| `ELT_DB_PORT` | `int` | `5433` | Cổng host của container `vigilens-elt-db`. |
| `RAG_ENABLED` | `bool` | `true` | Bật/tắt các điểm cuối RAG. |
| `RAG_CHROMA_DIR` | `string` | `./data/chroma` | Thư mục lưu chỉ mục vector ChromaDB. |
| `RAG_COLLECTION` | `string` | `vigilens_docs` | Tên bộ sưu tập (tên thật gắn thêm nhà cung cấp và mô hình nhúng). |
| `RAG_EMBEDDING_PROVIDER` | `string` | `auto` | `auto` / `gemini` / `hash`; dùng `hash` khi hết hạn mức để kiểm tra đường ống ngoại tuyến. |
| `RAG_EMBEDDING_MODEL` | `string` | `gemini-embedding-001` | Mô hình nhúng (3.072 chiều); đổi mô hình phải dựng lại chỉ mục. |
| `RAG_TOP_K` | `int` | `6` | Số đoạn trả về mặc định cho mỗi truy vấn tìm kiếm ngữ nghĩa. |
| `GEMINI_API_KEY` … `GEMINI_API_KEY_8` | `string` | *(trống)* | Các khoá Gemini dùng luân phiên cho nhúng vector và mô hình ngôn ngữ. |
| `NCBI_API_KEY` | `string` | *(trống)* | Khoá NCBI tuỳ chọn, tăng hạn mức khi tải PubMed. |

---

## 6. Các Câu Truy Vấn Mẫu (Sample Queries)

Để người chấm hoặc kiểm thử viên có thể kiểm tra ngay lập tức, dưới đây là **5 câu truy vấn mẫu chuẩn y khoa** từ bộ 50 ca ứng viên thực tế:

| Ca | Hoạt chất (`drug`) | Biến cố y khoa (`event`) | Quần thể (`population`) | Đường dùng (`route`) | Mục đích kiểm tra |
|:---:|---|---|---|---|---|
| **1** | `metformin` | `diarrhoea` | `adults` | `oral` | Kiểm tra xử lý trường hợp biến cố thường gặp, dừng an toàn khi thiếu văn bản đối chứng. |
| **2** | `amoxicillin` | `rash` | *(Tất cả)* | `oral` | Kiểm tra trích xuất 7 câu trích nguyên văn từ PubMed cục bộ, kiểm tra phản ứng dị ứng thuốc. |
| **3** | `atorvastatin` | `myalgia` | `adults` | `oral` | Kiểm tra phát hiện đau cơ do nhóm statin, ghi nhận khoảng trống bằng chứng (`gaps`). |
| **4** | `ibuprofen` | `gastrointestinal haemorrhage` | *(Tất cả)* | `oral` | Kiểm tra tác dụng phụ xuất huyết tiêu hóa do NSAID, kiểm soát ngân sách truy vấn. |
| **5** | `lisinopril` | `cough` | `adults` | `oral` | Kiểm tra trích xuất 15 câu trích nguyên văn dài, tự động cắt gọn hồ sơ an toàn theo schema. |

---

### Mẫu Gọi API Trực Tiếp (cURL / PowerShell)

Bạn có thể gửi yêu cầu tạo cuộc điều tra qua lệnh sau:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/investigations" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: test-investigator-token-12345" \
  -d '{
    "claim_text": "Investigate reported association: lisinopril / cough.",
    "drug": "lisinopril",
    "event": "cough",
    "population": "adults",
    "route": "oral",
    "config": {
      "sources": ["pubmed", "dailymed", "faers"],
      "max_steps": 4,
      "max_documents": 5
    }
  }'
```

*Phản hồi mẫu:* Trả về mã `202 Accepted` kèm `investigation_id` (ví dụ: `INV-94ade23fde3e`) để frontend polling tiến trình qua `GET /api/v1/investigations/{id}`.

---

## 7. Kiểm Thử & Nghiệm Thu Hệ Thống

Hệ thống được bảo vệ bởi bộ kiểm thử tự động toàn diện:

```powershell
# 1. Chạy toàn bộ test suite của dự án (572 tests):
.\.venv\Scripts\python.exe -m pytest tests/ -q

# 2. Chạy bộ kiểm thử tích hợp sống M10 Người 1-2-3 (5 tests):
.\.venv\Scripts\python.exe -m pytest tests/test_agents/test_m10_live_integration.py -v

# 3. Chạy kịch bản tự động hóa kiểm chứng 5 ca lâm sàng thực tế:
.\.venv\Scripts\python.exe scripts/verify_person2_complete.py

# 4. Kiểm tra mã nguồn bằng Ruff linter:
.\.venv\Scripts\python.exe -m ruff check src tests scripts
```

**Kết quả kiểm tra thực tế:**
- **572 passed, 4 skipped, 28 subtests passed** (100% không có lỗi hồi quy).
- **5/5 live integration tests passed** trong 1.02s.
- **5/5 ca ứng viên lâm sàng đạt trạng thái PASS** toàn vẹn qua cả 2 trạm kiểm soát của Reviewer.

---

## 8. Tài Liệu Kỹ Thuật Liên Quan

- [Sơ đồ kiến trúc & LangGraph StateGraph](ARCHITECTURE.md) (`ARCHITECTURE.md`).
- [Báo cáo chi tiết 5 Test Cases thực tế Gate G2](docs/GATE2_EVAL_EVIDENCES.md) (`docs/GATE2_EVAL_EVIDENCES.md`).
- [Chi tiết sơ đồ 14 Nodes LangGraph StateGraph](docs/architecture_diagram.md) (`docs/architecture_diagram.md`).
- [Hợp đồng điểm cắm tích hợp Người 1 - 2 - 3 - 4](docs/INTEGRATION_PLUG_POINTS.md) (`docs/INTEGRATION_PLUG_POINTS.md`).
- [Hướng dẫn tải dữ liệu 50 mẫu ứng viên](docs/HUONG_DAN_DU_LIEU_50_MAU.md) (`docs/HUONG_DAN_DU_LIEU_50_MAU.md`).
- [Runbook vận hành, sao lưu và phục hồi](docs/runbook.md) (`docs/runbook.md`).
- [Bản đặc tả hợp đồng dữ liệu MVP](docs/mvp-contracts.md) (`docs/mvp-contracts.md`).
