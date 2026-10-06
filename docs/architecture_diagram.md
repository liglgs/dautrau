# Sơ đồ Kiến trúc Hệ thống & Điều phối Agent (P-066)

> **Phạm vi:** Trợ lý AI điều tra an toàn thuốc (P-066 / VMEC-03 MVP) — Phụ trách bởi **Kỹ sư trưởng Backend & Điều phối Agent (Người 2)**.  
> **Mục tiêu:** Kiểm soát chu trình suy luận của Agent qua đồ thị trạng thái xác định (Deterministic StateGraph), kiểm soát ngân sách chặt chẽ, hỗ trợ dừng/tiếp tục qua Human-in-the-loop (HITL) và tối ưu hóa hạ tầng LLM với cơ chế xoay vòng 8 Gemini API keys.

---

## 1. Sơ đồ Kiến trúc Điều phối Tổng thể (System & Agent Architecture)

```mermaid
flowchart TB
    subgraph UI_Layer ["Tầng Giao diện (Vigilens Next.js 15)"]
        UI["Web App (App Router, Tailwind v4, Zustand)"]
        ProxyRoute["Route Handler (/api/backend/*) - Gắn Role Token"]
    end

    subgraph API_Layer ["Tầng Dịch vụ API (FastAPI)"]
        AuthMid["Xác thực Token (Role: Investigator / Reviewer)"]
        InvRoutes["Investigations API (/api/v1/investigations)"]
        RevRoutes["Reviews & Checkpoints API (/reviews, /continue, /export)"]
    end

    subgraph Core_Engine ["Bộ điều phối Agent & Vòng đời (Người 2)"]
        Runner["InProcessRunner (Khóa đơn độc quyền, Phục hồi Crash)"]
        Store[("MvpStore (SQLite)\n- investigations (khóa lạc quan)\n- events (timeline append-only)\n- documents (bất biến)\n- evidence & dossier versions")]
        Graph["LangGraph StateGraph Engine (MvpGraphState)"]
    end

    subgraph LLM_Gateway_Layer ["Tầng Cổng Mô hình & Quản lý Ngân sách (P11)"]
        Gateway["LLMGateway (Đặt trước ngân sách, Sửa JSON 1 lần)"]
        Ledger["UsageLedger (Ghi nhận số lượt gọi & Token theo task)"]
        Rotator["Gemini Key Pool Rotator (8 API Keys Round-Robin)"]
        Failover["Tự động Failover khi gặp HTTP 429"]
    end

    subgraph External_Models ["Nhà cung cấp Mô hình Trực tiếp"]
        GeminiFlash["Google Gemini API (gemini-3.5-flash-lite)"]
        OpenAIAPI["OpenAI API (Fallback gpt-4o-mini)"]
    end

    subgraph Data_Adapters ["Tầng Nguồn & Adapter Dữ liệu (Người 1 & 3)"]
        DailyMed["DailyMed Adapter (Nhãn thuốc FDA)"]
        PubMed["PubMed Adapter (Y văn đối chứng)"]
        FAERS["FAERS Adapter (Báo cáo tự nguyện)"]
    end

    %% Luồng kết nối
    UI -->|REST + cookie phiên HttpOnly| ProxyRoute
    ProxyRoute -->|HTTP + Header X-API-Token| AuthMid
    AuthMid --> InvRoutes & RevRoutes
    InvRoutes -->|Tạo ca / Tiếp tục| Runner
    RevRoutes -->|Quyết định duyệt / Reject| Store
    Runner -->|Đọc / Lưu State & Timeline| Store
    Runner -->|Kích hoạt vòng chạy| Graph

    Graph -->|Tra cứu tài liệu nguồn| DailyMed & PubMed & FAERS
    Graph -->|Thực thi Prompt có cấu trúc| Gateway
    Gateway -->|Kiểm tra trần ngân sách| Ledger
    Gateway -->|Gửi request JSON| Rotator
    Rotator --> Failover
    Failover -->|HTTP Headers: x-goog-api-key| GeminiFlash
    Failover -.->|Dự phòng| OpenAIAPI
```

---

## 2. Chu trình LangGraph StateGraph (14 Nodes & Checkpoints)

Đồ thị trạng thái được thiết kế theo nguyên tắc hữu hạn, chống lặp vô tận và có các điểm dừng chờ con người (Human-In-The-Loop):

```mermaid
flowchart TD
    START([Bắt đầu lượt chạy]) --> EntryRouter{Entry Router}

    %% Nhánh khởi tạo
    EntryRouter -->|Chạy mới: Chưa chuẩn hóa| Node_Normalize["1. normalize\n(Chuẩn hóa claim y tế)"]
    EntryRouter -->|Chạy tiếp: Đã có claim| Node_Checklist["2. checklist\n(Khởi tạo 6 gaps mặc định)"]
    EntryRouter -->|Resume sau duyệt: next=build_dossier| Node_BuildDossier["7. build_dossier\n(Dựng hồ sơ tổng hợp)"]

    %% Kiểm tra claim
    Node_Normalize --> Cond_Norm{Claim hợp lệ?}
    Cond_Norm -->|Mơ hồ / Thiếu thông tin cốt lõi| CP_Norm["🛑 Checkpoint: normalization\n(Chờ reviewer làm rõ claim)"]
    Cond_Norm -->|Đạt chuẩn| Node_Checklist

    %% Vòng lặp điều tra chính
    Node_Checklist --> Node_Plan["3. plan\n(Lập chiến lược chọn nguồn & query)"]

    Node_Plan --> Cond_Plan{Quyết định Planner}
    Cond_Plan -->|Chọn nguồn: DailyMed / PubMed / FAERS| Node_Retrieve["4. retrieve\n(Lấy tài liệu nguồn bất biến)"]
    Cond_Plan -->|Hết ngân sách / Không còn nguồn| Node_Stop["6. stop_or_continue\n(Đánh giá điều kiện dừng)"]

    Node_Retrieve --> Node_Extract["5. extract_assess\n(Trích xuất bằng chứng & câu trích)"]
    Node_Extract --> Node_Gaps["Cập nhật khoảng trống (update_gaps)\n& chuỗi không tiến triển"]
    Node_Gaps --> Node_Stop

    %% Rẽ nhánh sau khi đánh giá dừng
    Node_Stop --> Cond_Stop{Có nên dừng?}
    Cond_Stop -->|Chưa: Tiếp tục thu thập| Node_Plan
    Cond_Stop -->|Dừng: Đủ bằng chứng / Hết budget| CP_Assess["🛑 Checkpoint: assessment\n(Chờ reviewer duyệt kết luận sơ bộ)"]

    %% Nhánh tổng hợp hồ sơ
    CP_Assess -.->|Reviewer Approved -> API /continue| EntryRouter
    Node_BuildDossier --> CP_Dossier["🛑 Checkpoint: dossier\n(Chờ reviewer duyệt hồ sơ trước export)"]

    %% Điểm kết thúc
    CP_Norm --> END([Tạm dừng run / Chờ Review])
    CP_Assess --> END
    CP_Dossier --> END
```

---

## 3. Vòng đời Trạng thái Cuộc Điều tra (Run Lifecycle & State Transitions)

```mermaid
stateDiagram-v2
    [*] --> queued: POST /api/v1/investigations
    queued --> running: InProcessRunner cấp khóa thực thi

    running --> waiting_for_review: Đụng Checkpoint (normalization / assessment / dossier)
    running --> failed: Lỗi kỹ thuật ngoại lệ không phục hồi được
    running --> interrupted: Server bị khởi động lại hoặc ngắt tiến trình đột ngột

    waiting_for_review --> running: POST /api/v1/investigations/{id}/continue (sau khi duyệt)
    waiting_for_review --> completed: Reviewer duyệt Dossier cuối cùng
    waiting_for_review --> queued: Reviewer yêu cầu sửa / bổ sung phạm vi

    interrupted --> running: InProcessRunner tự động recover và tiếp tục
    completed --> [*]: Sẵn sàng xuất báo cáo GET /export
```

---

## 4. Các Nguyên tắc Thiết kế Cốt lõi (Design Decisions & Defense-in-Depth)

| Tiêu chuẩn | Cách triển khai trong mã nguồn P-066 | Mục đích đối với tiêu chí BTC |
|------------|--------------------------------------|-------------------------------|
| **Deterministic StateGraph** | Sử dụng LangGraph `StateGraph(MvpGraphState)` với các điều kiện rẽ nhánh rõ ràng | Ngăn chặn vòng lặp vô tận, đảm bảo mọi ca đều đi qua các bước kiểm tra có trật tự (System Design 9/10). |
| **Strict Budget Boundaries** | `BudgetController`: Giới hạn cứng 20 bước suy luận, 100 tài liệu nguồn, 80 lượt truy vấn | Đảm bảo không cạn kiệt tài nguyên, bảo vệ chi phí token (System Design & DevOps). |
| **Human-In-The-Loop (HITL)** | Tách biệt quyền máy và quyền người tại 3 checkpoints: `normalization`, `assessment`, `dossier` | Bác sĩ/Dược sĩ luôn là người quyết định cuối cùng; Agent không tự kết luận quan hệ nhân quả. |
| **Anti-Hallucination & Provenance** | Bằng chứng bắt buộc trích dẫn đúng nguyên văn (`quote`), nguồn (`source_id`) và vị trí (`locator`) | Chống bịa đặt trích dẫn; tự động từ chối xuất hồ sơ nếu câu trích bị sai lệch. |
| **Gemini Multi-Key Rotator** | Pool 8 API keys với cơ chế Round-Robin đa luồng và tự động failover khi chạm HTTP 429 | Đảm bảo hệ thống đạt độ sẵn sàng cao (High Availability), không bị gián đoạn vì giới hạn RPM/TPM của Gemini. |
| **Optimistic Locking & Immutability** | SQLite `version` field kiểm soát ghi đè; tài liệu nguồn là bất biến (hash-addressed) | Đảm bảo tính toàn vẹn dữ liệu khi có nhiều thao tác đồng thời. |
