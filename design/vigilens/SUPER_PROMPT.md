# SUPER PROMPT — THIẾT KẾ & DỰNG GIAO DIỆN WEB "VigiLens" (Đề tài P-066)

> **Cách dùng:** Dán toàn bộ nội dung từ "PHẦN A" đến hết vào công cụ tạo giao diện (v0, Lovable, Bolt, Cursor, Claude Code...). Nếu công cụ giới hạn độ dài, dán PHẦN A–H làm nền, rồi gửi lần lượt các "prompt kích hoạt" ở PHẦN S (mỗi giai đoạn một lần).
> Tên thương hiệu **VigiLens** chỉ là tên tạm (vigilance + lens). Toàn bộ tên/slogan phải đọc từ một biến cấu hình `BRAND` để đổi một chỗ là đổi cả site.

---

## PHẦN A. VAI TRÒ, MỤC TIÊU, SẢN PHẨM BÀN GIAO

### A1. Vai trò của bạn
Bạn là **Principal Product Designer kiêm Senior Frontend Engineer**, chuyên về nền tảng dữ liệu y sinh và công cụ hỗ trợ quyết định lâm sàng. Bạn thiết kế như một studio được thuê vì có quan điểm thẩm mỹ riêng: mọi lựa chọn về màu, chữ, bố cục phải xuất phát từ chủ đề **cảnh giác dược (pharmacovigilance)**, không phải từ template SaaS mặc định.

### A2. Mục tiêu
Dựng giao diện frontend của **một website hoàn chỉnh như website sản phẩm thật**, không chỉ 3 màn hình MVP. Website gồm 4 khu vực:
1. **Website công khai** (marketing + nội dung): Trang chủ, Cách hoạt động, Nguồn dữ liệu, Ca điều tra mẫu, Blog, Tài liệu, Giới hạn & an toàn AI, Về dự án, Liên hệ.
2. **Khu vực làm việc có đăng nhập** (`/app`): Dashboard, Danh sách + tạo cuộc điều tra, Timeline & Ma trận bằng chứng, Phê duyệt & Hồ sơ, Hàng chờ duyệt, Thư viện hồ sơ, Thư viện tài liệu, **Trợ lý chatbot**, Cài đặt.
3. **Khu quản trị** (`/admin`): Người dùng & vai trò, Nguồn dữ liệu, **Nhập dữ liệu (ingestion)**, Kho tài liệu, Từ điển thuật ngữ, Cấu hình agent & guardrail, Đánh giá chất lượng (evaluation), Audit log, Quản lý nội dung (blog/FAQ), Sức khỏe hệ thống.
4. **Chatbot** hiện diện ở 3 vị trí (xem PHẦN J).

Giao diện chạy được hoàn toàn bằng **dữ liệu giả (mock)** nhưng cấu trúc sẵn sàng thay bằng API thật.

### A3. Quy trình bắt buộc (làm đúng thứ tự)
1. **Lập design plan ngắn** trước khi viết code: bảng màu 4–6 màu có tên, vai trò các typeface, concept bố cục (kèm ASCII wireframe), 3–5 nguyên tắc riêng của dự án này.
2. **Tự rà soát plan với brief**: phần nào giống thứ bạn sẽ làm cho *bất kỳ* dự án SaaS nào thì sửa lại và ghi một dòng đã đổi gì, vì sao.
3. **Build theo giai đoạn** (PHẦN S). Mỗi giai đoạn phải chạy được trước khi sang giai đoạn kế.
4. **Tự phê bình** ở cuối mỗi giai đoạn: kiểm tra responsive, focus bàn phím, `prefers-reduced-motion`, tương phản, trạng thái rỗng/lỗi/loading. Cắt bớt một thứ trang trí thừa.

### A4. Sản phẩm bàn giao
- Dự án Next.js chạy được bằng `pnpm dev`, có đủ mọi route ở PHẦN F.
- Trang `/dev/design-system`: bày toàn bộ token và component (mọi biến thể badge, alert, trạng thái) để kiểm tra bằng mắt.
- Lớp mock data + **mock agent stream** (phát lại chuỗi sự kiện có độ trễ để Timeline "chạy thật").
- Công cụ **demo role switcher** (nút nổi góc dưới trái, chỉ hiện ở chế độ demo) để chuyển nhanh Visitor / Investigator / Reviewer / Admin.
- `README.md` ngắn: cấu trúc thư mục, cách đổi brand, cách thay mock bằng API.

### A5. Điều KHÔNG làm
- Không dựng backend, không gọi API thật (mock + interface rõ ràng là đủ).
- Không bịa PMID/DOI/Set ID thật. Mọi định danh trong dữ liệu mẫu phải rõ là giả (ví dụ `PMID: DEMO-0001`) và mọi màn có dữ liệu mẫu phải có banner "Dữ liệu minh họa — không dùng cho quyết định lâm sàng".
- Không dùng ảnh stock, ảnh bác sĩ đeo ống nghe, ảnh viên thuốc 3D. Hình ảnh là **chính các thành phần giao diện** (timeline, ma trận, quote highlight) hoặc SVG tự vẽ.
- Không tạo nút/luồng "Agent tự duyệt".

---

## PHẦN B. BỐI CẢNH ĐỀ TÀI (đọc kỹ, đây là "bộ não" của sản phẩm)

**Tên đề tài:** AI Agent chủ động điều tra và kiểm chứng nhận định an toàn thuốc bằng chiến lược truy xuất bằng chứng thích ứng (*Adaptive Evidence Investigation Agent for Pharmacovigilance Safety Claims*) — mã P-066.

**Lĩnh vực:** Cảnh giác dược (PV), đánh giá an toàn thuốc, hỗ trợ quyết định lâm sàng.

**Bài toán thực tế**
- Chuyên viên an toàn thuốc phải tra hàng nghìn báo cáo ca (**openFDA FAERS**), nhãn thuốc (**DailyMed**) và y văn (**PubMed**) để xác minh một *nhận định* như "Thuốc X gây biến cố Y ở bệnh nhân Z".
- Bằng chứng nằm phân tán, rất mất thời gian, và hay bị **lệch phạm vi (Scope Mismatch)**: thuốc chỉ gây biến cố ở người cao tuổi hoặc liều cao, nhưng nhận định lại khái quát cho mọi bệnh nhân.
- LLM/RAG thông thường chỉ tìm một lần rồi tóm tắt: dễ ảo giác, không tự đổi chiến lược, không phân biệt được mâu thuẫn y khoa.

**Giá trị của AI Agent**
- Là **"Điều tra viên thích ứng"**: phân rã claim thành phần kiểm chứng được (hoạt chất, biến cố, quần thể, liều, đường dùng, cửa sổ thời gian) → xác định **khoảng trống bằng chứng (Evidence Gaps)** → tự đổi từ khóa/nguồn khi thiếu dữ liệu (ví dụ biệt dược → tên hoạt chất quốc tế) → chủ động tìm **bằng chứng phản bác** → **từ chối kết luận (Abstain)** khi không đủ căn cứ.
- **Human-in-the-loop:** Agent chỉ là trợ lý đưa khuyến nghị và hồ sơ dẫn chứng. **Reviewer (dược sĩ lâm sàng) là người quyết định cuối cùng.**

**Luồng nghiệp vụ tổng thể**
Khởi tạo (nhập claim + phạm vi, chọn nguồn, đặt ngân sách) → Theo dõi trực tiếp (timeline suy luận, bộ đếm ngân sách) → Phân tích bằng chứng (ma trận Ủng hộ/Phản bác/Chưa chắc chắn/Nền, cảnh báo Scope Mismatch, so sánh mâu thuẫn, xem trích dẫn gốc) → Reviewer Gate (Duyệt / Từ chối / Sửa / Yêu cầu tìm thêm) → Xuất hồ sơ Markdown có provenance + audit trail.

**Từ vựng nghiệp vụ chuẩn (dùng đúng trong toàn bộ UI)**
| Khái niệm | Giá trị kỹ thuật | Nhãn tiếng Việt |
|---|---|---|
| Trạng thái chạy | `queued`, `running`, `waiting_for_review`, `completed` (+ `failed`, `cancelled` để xử lý lỗi) | Đang xếp hàng · Đang chạy · Chờ duyệt · Hoàn tất · Lỗi · Đã hủy |
| Kết luận phân loại | `supported_for_scope` | Có bằng chứng ủng hộ trong phạm vi |
| | `contradicted_for_scope` | Có bằng chứng phản bác trong phạm vi |
| | `insufficient_evidence` | Thiếu bằng chứng — Agent từ chối kết luận |
| | `scope_mismatch` | Lệch phạm vi |
| | `out_of_scope` | Ngoài phạm vi |
| | `requires_human_review` | Bắt buộc chuyên viên can thiệp |
| Lập trường bằng chứng | `supporting`, `contradicting`, `uncertain`, `background` | Ủng hộ · Phản bác · Chưa chắc chắn · Thông tin nền |
| Khớp phạm vi | `matched`, `mismatched` (+ `partial` khi tài liệu không nêu rõ quần thể/liều) | Khớp · Lệch · Khớp một phần |
| Trạng thái duyệt | `not_reviewed`, `approved`, `rejected`, `needs_rereview` | Chưa duyệt · Đã duyệt · Đã từ chối · Cần duyệt lại do có chỉnh sửa mới |

---

## PHẦN C. NGUYÊN TẮC SẢN PHẨM BẤT BIẾN (guardrails — vi phạm là lỗi nghiêm trọng)

1. **Không bao giờ kết luận nhân quả.** Cấm mọi câu như "thuốc chắc chắn gây…", "đã chứng minh gây…", "thuốc an toàn tuyệt đối", "không có nguy cơ". Chỉ dùng ngôn ngữ phạm vi: "được ủng hộ trong phạm vi…", "chưa đủ bằng chứng…". Đặt danh sách cụm cấm trong `lib/guardrails.ts` và một hàm `assertNoCausalClaim(text)` dùng cho dữ liệu mock, đầu ra chatbot và dossier preview.
2. **Màu ≠ an toàn.** Xanh = *nhận định được bằng chứng ủng hộ*. Đỏ = *nhận định bị bằng chứng phản bác*. Không có nghĩa "thuốc an toàn / nguy hiểm". Mọi nơi dùng màu này phải có chú giải ngắn (legend hoặc tooltip) nói rõ điều đó.
3. **Mọi câu bằng chứng đều bấm được.** Mọi mệnh đề dựa trên bằng chứng trong UI, dossier và chatbot có **citation chip** (`[E3]`) mở thẳng *Quote Inspector* tại đúng đoạn trích.
4. **Abstain là trạng thái hạng nhất.** "Thiếu bằng chứng — Agent từ chối kết luận" được trình bày trang trọng, có lý do và danh sách khoảng trống, không giống một thông báo lỗi.
5. **Con người quyết định cuối cùng.** Không có nút Agent tự duyệt. Mọi nội dung do AI sinh ra mang nhãn **"AI đề xuất"** (icon Sparkles, sắc indigo) để phân biệt với hành động của người.
6. **Invalidation tức thì.** Reviewer chỉnh sửa bất kỳ bằng chứng/scope nào sau khi đã duyệt → huy hiệu "Đã duyệt" chuyển ngay thành "Cần duyệt lại do có chỉnh sửa mới", khóa nút tải báo cáo, ghi audit.
7. **Minh bạch giới hạn của AI.** Mọi màn có kết quả đều có liên kết "Giới hạn & cách đọc kết quả". Hồ sơ luôn có mục Giới hạn (Limitations) và Khoảng trống (Gaps).
8. **Khóa có lý do, không ẩn.** Nút bị phân quyền chặn vẫn hiển thị ở trạng thái disabled kèm tooltip nêu rõ lý do ("Chỉ Reviewer được duyệt", "Cần Reviewer duyệt trước khi tải").
9. **Audit append-only.** Mọi thao tác quan trọng (tạo, sửa, duyệt, từ chối, yêu cầu tìm thêm, xuất) tạo một dòng audit hiển thị được, không có nút xóa.
10. **Không chỉ dựa vào màu.** Mọi trạng thái = màu + icon + chữ. Đạt tương phản WCAG AA.
11. **Không dữ liệu định danh bệnh nhân.** Không có trường nhập tên/CMND/ngày sinh bệnh nhân. Ô chat và form claim có gợi ý "Không nhập thông tin định danh bệnh nhân" và hiển thị cảnh báo mềm nếu phát hiện mẫu giống số điện thoại/email/CCCD.
12. **Dữ liệu minh họa luôn được gắn nhãn** (xem A5).

---

## PHẦN D. VAI TRÒ NGƯỜI DÙNG & PHÂN QUYỀN

Bốn vai trò: **Visitor** (chưa đăng nhập), **Investigator** (nhập claim, theo dõi, xem trước kết quả), **Reviewer** (dược sĩ lâm sàng/chuyên viên PV: toàn quyền chuyên môn), **Admin** (quản trị hệ thống; **không** có quyền duyệt lâm sàng, để tách bạch trách nhiệm — có thể cấu hình).

| Chức năng | Visitor | Investigator | Reviewer | Admin |
|---|:-:|:-:|:-:|:-:|
| Xem website công khai, ca mẫu (chỉ đọc) | ✓ | ✓ | ✓ | ✓ |
| Dùng chatbot công khai (hỏi về sản phẩm) | ✓ | ✓ | ✓ | ✓ |
| Tạo cuộc điều tra, chọn nguồn, đặt ngân sách | — | ✓ | ✓ | — |
| Theo dõi timeline realtime, xem ma trận, Quote Inspector | — | ✓ | ✓ | chỉ đọc |
| Chatbot trong ngữ cảnh điều tra | — | ✓ | ✓ | chỉ đọc |
| Xem Dossier Preview | — | ✓ (chỉ đọc) | ✓ | chỉ đọc |
| Duyệt / Từ chối / Sửa bằng chứng-scope / Yêu cầu tìm thêm | — | — | ✓ | — |
| Tải báo cáo Markdown (khi đã duyệt) | — | ✓ | ✓ | — |
| Hàng chờ duyệt | — | — | ✓ | — |
| Quản lý người dùng & vai trò | — | — | — | ✓ |
| Nguồn dữ liệu, nhập dữ liệu, kho tài liệu, từ điển | — | — | từ điển: ✓ | ✓ |
| Cấu hình agent & guardrail | — | — | — | ✓ |
| Đánh giá chất lượng (evaluation) | — | — | xem | ✓ |
| Audit log toàn hệ thống | — | của mình | của hồ sơ | ✓ |

Điều hướng, sidebar và nút hành động phải **đổi theo vai trò** (đọc `useRole()`).

---

## PHẦN E. CÔNG NGHỆ & CẤU TRÚC DỰ ÁN

**Stack:** Next.js (App Router) + TypeScript strict + Tailwind CSS + shadcn/ui (Radix) + lucide-react + framer-motion + TanStack Query + Zustand + react-hook-form + zod + react-markdown (+ remark-gfm, rehype-sanitize) + recharts + date-fns (locale `vi`) + next-themes + next-intl (mặc định `vi`, có sẵn `en`).

**Font:** nạp bằng `next/font/google` với subset **`latin`, `latin-ext`, `vietnamese`** (bắt buộc để dấu tiếng Việt không bị rớt font).

**Route groups & thư mục gợi ý**
```
app/
  (public)/            # layout công khai: Navbar + Footer + chatbot nổi
    page.tsx           # Trang chủ
    how-it-works/ data-sources/ examples/[slug]/ blog/[slug]/
    docs/[...slug]/ glossary/ limitations/ about/ contact/ faq/ privacy/ terms/
  (auth)/login/ register/ forgot-password/
  app/                 # layout làm việc: Sidebar + Topbar
    page.tsx           # Dashboard
    investigations/ new/ [id]/ [id]/review/ [id]/audit/
    reviews/ dossiers/ library/ assistant/[[...threadId]]/ settings/ notifications/
  admin/               # layout quản trị
    page.tsx users/ sources/ ingestion/ ingestion/new/ corpus/ terminology/
    agent-config/ guardrails/ evaluation/ audit/ content/ system/
  dev/design-system/
components/
  ui/            # shadcn gốc
  pv/            # component nghiệp vụ: StatusBadge, EvidenceMatrix, AgentTimeline, QuoteInspector...
  chat/          # ChatLauncher, ChatPanel, MessageList, ClaimCard...
  layout/        # PublicNavbar, AppSidebar, AdminSidebar, Footer
lib/
  mock/          # dữ liệu giả + agent event script
  guardrails.ts  # cụm cấm, assertNoCausalClaim
  api/           # interface client (mock hiện tại, thay bằng fetch sau)
  types.ts
```
**Quy ước:** trang công khai dùng Server Component; trang theo dõi realtime dùng Client Component + hook `useAgentStream(investigationId)` (mock bằng `ReadableStream`/EventSource giả lập). Mọi component nghiệp vụ nhận dữ liệu qua props kiểu `types.ts`, không tự gọi mock bên trong.

---

## PHẦN F. SITEMAP TỔNG THỂ

### F1. Website công khai (`(public)`) — thanh điều hướng trên cùng
| Route | Tên menu | Mục đích |
|---|---|---|
| `/` | Trang chủ | Giới thiệu giá trị, demo sống, dẫn vào đăng nhập/điều tra |
| `/how-it-works` | Cách hoạt động | Giải thích vòng lặp điều tra thích ứng, 6 trạng thái kết luận, vai trò con người |
| `/data-sources` | Nguồn dữ liệu | PubMed, DailyMed, openFDA FAERS: cho biết gì, *không* cho biết gì, độ trễ cập nhật |
| `/examples`, `/examples/[slug]` | Ca điều tra mẫu | Thư viện hồ sơ mẫu chỉ đọc (đủ 6 trạng thái), có Timeline và Ma trận phát lại được |
| `/blog`, `/blog/[slug]` | Blog | Kiến thức cảnh giác dược, ghi chú phát hành |
| `/docs/[...slug]`, `/glossary` | Tài liệu (dropdown) | Hướng dẫn sử dụng, Thuật ngữ, API/định dạng hồ sơ |
| `/limitations` | Giới hạn & an toàn AI (trong dropdown Tài liệu) | Cam kết minh bạch: AI làm được/không làm được gì |
| `/faq` | FAQ (trong dropdown Tài liệu) | Câu hỏi thường gặp |
| `/about` | Về dự án | Đề tài P-066, nhóm thực hiện, phương pháp, tài liệu tham khảo |
| `/contact` | Liên hệ | Form liên hệ/xin quyền truy cập, báo lỗi dữ liệu |
| `/privacy`, `/terms` | (chân trang) | Chính sách, điều khoản, tuyên bố miễn trừ |

### F2. Xác thực (`(auth)`)
`/login` (email + mật khẩu, SSO tổ chức), `/register` (gửi yêu cầu cấp quyền, chọn vai trò đề nghị), `/forgot-password`.

### F3. Khu vực làm việc (`/app`)
| Route | Màn hình | Vai trò |
|---|---|---|
| `/app` | Dashboard | Tất cả |
| `/app/investigations` | **MÀN HÌNH 1** — Danh sách + lịch sử điều tra | Inv, Rev |
| `/app/investigations/new` | **MÀN HÌNH 1** — Form tạo cuộc điều tra (claim + cấu hình) | Inv, Rev |
| `/app/investigations/[id]` | **MÀN HÌNH 2** — Timeline thời gian thực + Ma trận bằng chứng | Inv, Rev |
| `/app/investigations/[id]/review` | **MÀN HÌNH 3** — Phê duyệt & Hồ sơ | Inv (chỉ đọc), Rev |
| `/app/investigations/[id]/audit` | Dấu vết kiểm toán của hồ sơ | Inv, Rev |
| `/app/reviews` | Hàng chờ duyệt | Rev |
| `/app/dossiers` | Thư viện hồ sơ đã duyệt/đã xuất | Inv, Rev |
| `/app/library` | Thư viện tài liệu đã thu thập (PubMed/DailyMed/FAERS) | Inv, Rev |
| `/app/assistant/[[...threadId]]` | Trợ lý chatbot toàn trang | Inv, Rev |
| `/app/settings`, `/app/notifications` | Cài đặt, thông báo | Tất cả |

### F4. Khu quản trị (`/admin`)
`/admin` (tổng quan), `/admin/users`, `/admin/sources`, `/admin/ingestion` + `/new`, `/admin/corpus`, `/admin/terminology`, `/admin/agent-config`, `/admin/guardrails`, `/admin/evaluation`, `/admin/audit`, `/admin/content`, `/admin/system`.

### F5. Trang hệ thống
404, 403 ("Bạn không có quyền với mục này" kèm vai trò hiện tại và cách xin quyền), 500, bảo trì, hết phiên đăng nhập.

---

## PHẦN G. DESIGN SYSTEM

### G1. Hướng thẩm mỹ: "Hồ sơ dẫn chứng" (Evidence file)
Cảm giác của một **nền tảng dữ liệu lâm sàng cao cấp** (gần Linear / Vercel / Retool): tĩnh, chính xác, đáng tin. Nền giấy-hồ-sơ, chữ mực đậm, màu chỉ xuất hiện khi mang **ý nghĩa nghiệp vụ**.

**Dồn sự táo bạo vào đúng 2 chỗ, mọi thứ còn lại giữ yên lặng và kỷ luật:**
1. **Sợi dẫn chứng (provenance thread):** đường nối mảnh (1.5px) nối một câu kết luận → citation chip → vệt highlight trong văn bản gốc. Xuất hiện ở hero trang chủ, ở rail của Timeline, và khi hover/bấm citation chip trong dossier.
2. **Vệt highlight kiểu bút dạ:** đoạn trích làm bằng chứng luôn được tô bằng màu marker vàng nhạt, đây là "chữ ký thị giác" của sản phẩm.

**Cấm các dấu hiệu "AI làm ra"**: nhãn eyebrow IN HOA rải rác trên mọi tiêu đề; tô màu riêng một từ trong headline; đánh số 01/02/03 cho nội dung *không phải* trình tự; chuỗi meta nối bằng dấu chấm giữa "A · B · C" (chỉ dùng khi thật sự là metadata của bảng); nền gradient/glow/glassmorphism làm trang trí; mọi thứ cắt thành thẻ bo tròn giống hệt nhau với bóng xám giống hệt nhau; thêm "→" vào mọi nút; entrance fade-slide-up cho từng section; hover nảy cho mọi card. **Độ bo góc và độ nổi phải phân cấp** theo vai trò (xem G4).

### G2. Token màu (HSL, định nghĩa trong `globals.css`, map vào `tailwind.config`)
Màu thương hiệu = **mực (ink)** gần đen; **không** dùng emerald làm màu thương hiệu vì emerald đã mang nghĩa nghiệp vụ "ủng hộ/hợp lệ/đã duyệt".

```css
:root {
  --background: 210 25% 98%;      /* Giấy hồ sơ */
  --foreground: 222 32% 10%;      /* Mực */
  --card: 0 0% 100%;  --card-foreground: 222 32% 10%;
  --popover: 0 0% 100%;
  --muted: 214 22% 95%;  --muted-foreground: 215 14% 38%;
  --border: 214 20% 89%; --input: 214 20% 86%;
  --primary: 222 32% 10%; --primary-foreground: 210 25% 98%;  /* CTA = mực */
  --ring: 239 84% 60%;
  --radius: 0.625rem;

  /* AI suy luận thích ứng — Indigo */
  --ai: 239 84% 60%;  --ai-soft: 238 100% 97%;  --ai-border: 238 80% 88%;  --ai-fg: 243 55% 38%;
  /* Ủng hộ / hợp lệ / đã duyệt — Emerald */
  --support: 160 84% 32%; --support-soft: 152 70% 95%; --support-border: 152 50% 78%; --support-fg: 162 88% 19%;
  /* Phản bác / lỗi nguồn / từ chối — Rose */
  --contradict: 350 75% 48%; --contradict-soft: 350 100% 97%; --contradict-border: 350 78% 88%; --contradict-fg: 350 70% 31%;
  /* Thận trọng: chờ duyệt, thiếu bằng chứng, chưa chắc chắn — Amber */
  --caution: 38 92% 46%; --caution-soft: 45 100% 94%; --caution-border: 42 90% 76%; --caution-fg: 28 85% 25%;
  /* Lệch phạm vi — Cam (tách khỏi Amber để không nhầm) */
  --scope: 24 90% 48%; --scope-soft: 28 100% 95%; --scope-border: 26 90% 82%; --scope-fg: 20 80% 28%;
  /* Nền / ngoài phạm vi / trung tính — Slate */
  --neutral: 215 16% 47%; --neutral-soft: 214 22% 95%; --neutral-border: 214 18% 84%; --neutral-fg: 217 24% 26%;
  /* Vệt highlight trích dẫn */
  --marker: 50 100% 72%; --marker-ink: 30 80% 18%;
}
.dark {
  --background: 224 25% 7%;  --foreground: 210 20% 94%;
  --card: 224 22% 10%;  --card-foreground: 210 20% 94%;
  --popover: 224 22% 11%;
  --muted: 222 18% 14%; --muted-foreground: 215 14% 66%;
  --border: 222 15% 20%; --input: 222 15% 24%;
  --primary: 210 20% 96%; --primary-foreground: 224 25% 8%;
  --ring: 239 90% 74%;

  --ai: 239 90% 74%;  --ai-soft: 239 40% 16%;  --ai-border: 239 35% 30%;  --ai-fg: 238 100% 88%;
  --support: 158 64% 52%; --support-soft: 160 40% 12%; --support-border: 160 35% 26%; --support-fg: 152 70% 82%;
  --contradict: 350 90% 66%; --contradict-soft: 350 40% 14%; --contradict-border: 350 35% 28%; --contradict-fg: 350 100% 88%;
  --caution: 40 95% 58%; --caution-soft: 38 50% 13%; --caution-border: 38 45% 28%; --caution-fg: 45 100% 82%;
  --scope: 24 95% 62%; --scope-soft: 24 45% 14%; --scope-border: 24 40% 30%; --scope-fg: 28 100% 84%;
  --neutral: 215 14% 62%; --neutral-soft: 222 18% 14%; --neutral-border: 222 15% 26%; --neutral-fg: 214 20% 84%;
  --marker: 48 90% 40%; --marker-ink: 48 100% 92%;
}
```
Giao diện **hỗ trợ cả Light (mặc định, "Clean Medical") và Dark** qua `next-themes`, theo `prefers-color-scheme`, có nút chuyển ở Navbar/Topbar. Mỗi màu ngữ nghĩa có 4 lớp: solid (icon, viền nhấn), soft (nền), border, fg (chữ trên nền soft).

**Ánh xạ trạng thái → màu → icon (Lucide, gợi ý)**
| Trạng thái | Màu | Icon | Ghi chú kiểu dáng |
|---|---|---|---|
| `supported_for_scope` | support | `CircleCheck` | nền soft, viền border |
| `contradicted_for_scope` | contradict | `CircleX` | nền soft |
| `insufficient_evidence` | caution | `CircleHelp` | **viền nét đứt**, nền trong suốt (thể hiện "chưa đủ") |
| `scope_mismatch` | scope | `TriangleAlert` | nền soft + sọc chéo mảnh |
| `out_of_scope` | neutral | `CircleSlash` | nền muted |
| `requires_human_review` | caution | `UserCheck` | nền soft đậm hơn + chấm nhịp thở |
| stance `supporting/contradicting/uncertain/background` | support/contradict/caution (nét đứt)/neutral | `Plus` / `Minus` / `CircleHelp` / `BookOpen` | không dùng biểu tượng "like/dislike" vì dễ hiểu thành đánh giá thuốc |
| run `running` | ai | `LoaderCircle` quay | chấm indigo nhịp thở |
| run `waiting_for_review` | caution | `UserCheck` | |
| run `completed` | support | `CircleCheck` | |
| run `failed` | contradict | `CircleAlert` | |
| AI đề xuất | ai | `Sparkles` | nhãn nhỏ "AI đề xuất" |

### G3. Typography
| Vai trò | Font | Dùng cho |
|---|---|---|
| Display/Heading | **Outfit** (500–600) | H1–H3, số lớn, tiêu đề trang |
| UI/Body | **Inter** (400/500/600), bật `font-feature-settings: "cv11","ss01"` | nhãn, bảng, form, nút, đoạn văn |
| Văn bản bằng chứng | **Source Serif 4** | Quote Inspector, trích dẫn, Dossier Preview, blog (tạo cảm giác tài liệu) |
| Mã/định danh | **JetBrains Mono** | ID điều tra, hash, PMID/Set ID, câu truy vấn |

Thang cỡ chữ: Display 56/60 · H1 40/46 · H2 30/38 · H3 22/30 · H4 18/26 · Body 15/24 (app) hoặc 17/28 (marketing) · Small 13/20 · Caption 12/16. Serif: line-height 1.7, độ rộng dòng ≤ 72 ký tự; sans ≤ 80. Dùng **sentence case** cho mọi nhãn. Không dùng chữ IN HOA cho nhãn. Số liệu trong bảng dùng `tabular-nums`.

### G4. Hình khối, khoảng cách, độ nổi
- Lưới cơ sở **4px**. Khoảng cách chuẩn: 4/8/12/16/24/32/48/64/96.
- **Bo góc phân cấp:** pill đầy đủ cho badge/chip trạng thái · 6px cho input, nút, ô bảng · 10px cho card · 14px cho drawer/modal/chatbot panel.
- **Viền thay cho bóng.** Chỉ phần tử nổi (popover, drawer, modal, launcher chatbot) mới có bóng; bóng nhỏ và lạnh.
- Container marketing 1200px; nội dung đọc (blog, docs) 720px; app dùng bố cục fluid theo lưới 12 cột. Sidebar 264px (thu gọn 64px). Panel phải 320–360px. Drawer Quote Inspector 640px (mobile: full-screen sheet).
- Breakpoint: sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536. Bảng có tùy chọn mật độ **Thoải mái (44px) / Gọn (36px)**.

### G5. Chuyển động
Token: `fast 120ms`, `base 200ms`, `slow 320ms`, easing `cubic-bezier(0.2, 0, 0, 1)`. Chuyển động chỉ để **cho thấy cái gì vừa thay đổi** (bước mới xuất hiện, trạng thái đổi, drawer mở). Không animation tự chạy trang trí, ngoại trừ **một khoảnh khắc có chủ đích**: demo hero trên trang chủ. Tôn trọng `prefers-reduced-motion` (chỉ còn đổi màu/độ mờ, không dịch chuyển/quay).

### G6. Danh mục component nghiệp vụ (`components/pv/`)
| Component | Biến thể / ghi chú |
|---|---|
| `AssessmentBadge` | 6 trạng thái · size `sm`/`md`/`lg`; `lg` hiển thị thêm một câu giải thích và nút "Cách đọc kết quả" |
| `RunStatusPill` | 6 trạng thái; `running` có chấm nhịp thở |
| `ReviewStateBadge` | `not_reviewed`/`approved`/`rejected`/`needs_rereview`; có animation chuyển trạng thái (xem PHẦN M) |
| `StanceBadge` | 4 lập trường; icon + chữ |
| `ScopeChip` | `matched`/`partial`/`mismatched`; tooltip chỉ rõ **chiều nào lệch** (quần thể, liều, đường dùng, thời gian) |
| `SourceChip` | PubMed / DailyMed / openFDA FAERS; dùng monogram SVG tự vẽ, **không** dùng logo thương hiệu |
| `ClaimChips` | drug, adverse event, population, dose, route, time window; mỗi chip có icon riêng; chip chưa điền hiển thị "Chưa giới hạn" nét đứt |
| `CitationChip` | `[E3]`; hover → popover xem nhanh đoạn trích + nguồn; click → Quote Inspector; vẽ sợi dẫn chứng khi hover |
| `HashChip` | SHA-256 rút gọn, nút sao chép, trạng thái `verified` / `mismatch` / `unchecked` |
| `BudgetMeter` | bản gọn (thanh ngang trên header) và bản đầy đủ (card): bước, tài liệu, token |
| `AgentStepCard` | loại bước: `search`, `replan`, `source_switch`, `read`, `contradiction_found`, `gap_identified`, `conclude`, `abstain`; luôn có *Rationale*, nguồn, số tài liệu |
| `ClaimDecomposition` | danh sách thành phần claim + trạng thái kiểm chứng của từng thành phần |
| `EvidenceGapList` | khoảng trống dữ liệu, mỗi dòng có nút "Yêu cầu tìm thêm" (Reviewer) |
| `EvidenceMatrix` | tab + bảng + lọc + sắp xếp + chọn nhiều dòng |
| `ScopeMismatchAlert` | alert card màu cam, nêu rõ chênh lệch (ví dụ 100mg vs 20mg) |
| `ContradictionCompare` | hai cột đối chiếu, đồng bộ cuộn, tô nhấn điểm khác biệt |
| `QuoteInspector` | Drawer: văn bản gốc, highlight, metadata, hash, provenance |
| `ReviewerActionPanel` | 4 hành động + trạng thái duyệt + khóa theo vai trò |
| `InvalidationBanner` | banner amber "Cần duyệt lại do có chỉnh sửa mới" kèm danh sách thay đổi từ lần duyệt trước |
| `DossierPreview` | render Markdown, mục lục dính, citation chip trong dòng |
| `AuditTimeline` | danh sách append-only, lọc theo người/hành động |
| `AiLabel` | nhãn "AI đề xuất" |
| `DemoBanner` | "Dữ liệu minh họa — không dùng cho quyết định lâm sàng" |
| `EmptyState` / `ErrorState` / `Skeleton*` | mỗi cái có biến thể theo ngữ cảnh (xem PHẦN K) |

**Alert card:** 6 biến thể (`ai`, `support`, `contradict`, `caution`, `scope`, `neutral`). Cấu trúc: sọc trái 3px màu solid · icon · tiêu đề (1 dòng) · nội dung · hành động tùy chọn (tối đa 2) · nút đóng tùy chọn. Không dùng nền đặc.

---

## PHẦN H. KHUNG BỐ CỤC (LAYOUT SHELLS)

### H1. PublicLayout — thanh điều hướng trên cùng
```
┌───────────────────────────────────────────────────────────────────────────────┐
│ [logo VigiLens]  Trang chủ  Cách hoạt động  Nguồn dữ liệu  Ca mẫu  Blog        │
│                  Tài liệu ▾            [VI|EN] [☾]  Đăng nhập  [Bắt đầu điều tra]│
└───────────────────────────────────────────────────────────────────────────────┘
```
- Cố định khi cuộn (sticky), nền `background/80` + `backdrop-blur-sm`, hiện viền dưới khi cuộn khỏi đỉnh.
- Dropdown **Tài liệu**: Hướng dẫn sử dụng, Thuật ngữ, Giới hạn & an toàn AI, FAQ, Về dự án.
- Mục đang chọn: gạch chân bằng "sợi" mảnh trượt giữa các mục (framer-motion `layoutId`).
- Nếu đã đăng nhập: thay "Đăng nhập" bằng avatar + menu (Không gian làm việc, Cài đặt, Đăng xuất); CTA đổi thành "Vào không gian làm việc". Admin có thêm mục "Quản trị".
- Mobile (<1024px): logo + nút CTA rút gọn + hamburger → sheet toàn chiều cao, nhóm mục, ô chọn ngôn ngữ/giao diện ở cuối.
- Trên cùng (tùy chọn, mảnh 32px, đóng được): "Đề tài P-066 · bản trình diễn với dữ liệu minh họa" — dùng `DemoBanner`.

### H2. PublicFooter
4 cột: **Sản phẩm** (Cách hoạt động, Nguồn dữ liệu, Ca mẫu, Đăng nhập) · **Tài nguyên** (Blog, Tài liệu, Thuật ngữ, FAQ) · **Minh bạch** (Giới hạn & an toàn AI, Chính sách, Điều khoản) · **Dự án** (Về P-066, Liên hệ). Dưới cùng: tuyên bố miễn trừ: *"VigiLens là công cụ hỗ trợ nghiên cứu cảnh giác dược. Kết quả không thay thế phán đoán chuyên môn của dược sĩ lâm sàng/chuyên viên an toàn thuốc và không phải khuyến cáo điều trị."* + trạng thái hệ thống + bản quyền.

### H3. AppLayout (`/app`)
```
┌──────────┬──────────────────────────────────────────────────────────────┐
│ Sidebar  │ Topbar: breadcrumb · [⌘K Tìm kiếm / lệnh] · [+ Điều tra mới]  │
│ 264px    │         🔔 · role pill · avatar · [Dữ liệu minh họa]          │
│          ├──────────────────────────────────────────────────────────────┤
│          │                                                              │
│          │                    Nội dung trang                            │
│          │                                                              │
└──────────┴──────────────────────────────────────────────────────────────┘
```
**Sidebar (đổi theo vai trò)**
- *Làm việc:* Dashboard · Cuộc điều tra (badge số ca đang chạy) · **Hàng chờ duyệt** (chỉ Reviewer, badge số ca chờ)
- *Kho:* Hồ sơ đã xuất · Thư viện tài liệu
- *Trợ lý:* **Trợ lý VigiLens** (icon Sparkles)
- *Hỗ trợ:* Hướng dẫn · Giới hạn & cách đọc kết quả
- *Cuối:* Thông báo · Cài đặt · thẻ người dùng (tên, vai trò) · nút thu gọn
- Thu gọn → rail 64px chỉ icon + tooltip. Mobile: sidebar thành sheet trượt từ trái, topbar có hamburger.
- **Command palette (⌘K / Ctrl+K):** tìm cuộc điều tra theo mã/thuốc/biến cố, nhảy tới trang, chạy lệnh ("Điều tra mới", "Mở hàng chờ duyệt", "Hỏi trợ lý…").

### H4. AdminLayout (`/admin`)
Cùng khung với AppLayout nhưng sidebar có nhãn "Quản trị" và một dải màu nhận diện riêng (viền trái 2px slate đậm) để người dùng luôn biết mình đang ở khu quản trị. Nhóm: *Tổng quan* · *Dữ liệu* (Nguồn, Nhập dữ liệu, Kho tài liệu, Từ điển) · *Agent* (Cấu hình, Guardrail, Đánh giá) · *Hệ thống* (Người dùng, Audit log, Nội dung, Sức khỏe hệ thống) · liên kết "← Về không gian làm việc".

---

## PHẦN I. WEBSITE CÔNG KHAI — ĐẶC TẢ TỪNG TRANG

> Mọi tiêu đề dùng sentence case. Văn bản mẫu bên dưới là **nội dung thật để dùng**, không thay bằng lorem ipsum.

### I1. Trang chủ `/`

**Hero (khoảnh khắc táo bạo duy nhất của trang)** — mở bằng *chính sản phẩm*, không phải ảnh minh họa:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Nhận định này đúng với ai,            ┌─ Nhận định ────────────────────────┐ │
│ ở liều nào, trong nguồn nào?          │ [Metformin] gây [nhiễm toan lactic]│ │
│                                       │ ở [suy thận 3b], liều [≥2.000mg/ng]│ │
│ VigiLens điều tra nhận định về an     ├─ Agent đang điều tra  ✦ AI đề xuất ┤ │
│ toàn thuốc trên PubMed, DailyMed và   │ ● PubMed        3 tài liệu        │ │
│ openFDA FAERS. Khi thiếu dữ liệu,     │ ↻ Đổi biệt dược → tên hoạt chất   │ │
│ agent tự đổi cách tìm; khi chưa đủ    │ ● DailyMed      nhãn thuốc, mục 5 │ │
│ căn cứ, agent dừng lại. Dược sĩ lâm   │ ⚠ Lệch phạm vi: liều 100 mg ≠ 20  │ │
│ sàng luôn là người duyệt cuối.        │ ◐ Chờ Reviewer duyệt              │ │
│                                       └────────────────────────────────────┘ │
│ [Bắt đầu điều tra] [Xem một ca mẫu]     sợi dẫn chứng nối dòng cuối → vệt     │
│ ✓ Mỗi câu dẫn về nguồn                   highlight trong đoạn trích gốc        │
│ ✓ Agent biết từ chối kết luận                                                │
│ ✓ Con người duyệt cuối                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```
- Khối bên phải là **demo sống**: các chip trong câu nhận định bấm được (đổi thuốc/biến cố từ vài lựa chọn mẫu → timeline chạy lại). Timeline **phát một lần** khi tải trang, các bước lần lượt hiện (mỗi bước ~900ms), bước cuối vẽ sợi dẫn chứng đến vệt highlight. Có nút "Phát lại" và "Tạm dừng". `prefers-reduced-motion` → hiện sẵn trạng thái cuối.
- Dòng cam kết dưới nút CTA: ba ý ngắn, mỗi ý một icon, **không** dùng dấu chấm giữa; hiển thị thành ba cụm riêng.
- Nền hero: lưới chấm cực mờ, chỉ riêng hero. Không gradient.

**Các section tiếp theo** (mỗi section một bố cục khác nhau, tránh lặp "hàng ba thẻ giống nhau"):
1. **"Bằng chứng có thật, nhưng không dành cho mọi bệnh nhân"** — bên trái: ba nỗi đau (bằng chứng phân tán; mất hàng giờ tra FAERS/DailyMed/PubMed; lệch phạm vi) viết thành danh sách câu ngắn, không thẻ. Bên phải: **sơ đồ lệch phạm vi**: một thanh rộng "Nhận định: mọi bệnh nhân, liều 20 mg" và một thanh hẹp nằm trong "Nghiên cứu: ≥65 tuổi, liều 100 mg", phần lệch tô cam, chú thích rõ. Đây là minh họa cốt lõi của đề tài.
2. **"Từ một nhận định đến một hồ sơ dẫn chứng"** — chuỗi **5 bước** (đây là trình tự thật nên được đánh số): Nhập nhận định → Agent điều tra thích ứng → Ma trận bằng chứng → Reviewer duyệt → Xuất hồ sơ. Mỗi bước kèm một mảnh UI thật thu nhỏ (không ảnh chụp), nối nhau bằng sợi dẫn chứng.
3. **"Khác với tìm một lần rồi tóm tắt"** — bảng so sánh hai cột: *RAG thông thường* vs *Điều tra viên thích ứng*; hàng: số lần tìm · khi thiếu dữ liệu · bằng chứng phản bác · kiểm tra phạm vi (quần thể/liều) · khi không đủ căn cứ · vai trò con người · khả năng truy vết.
4. **"Xem ma trận bằng chứng hoạt động"** — Evidence Matrix chỉ đọc có tab Ủng hộ/Phản bác/Chưa chắc chắn/Nền; bấm một dòng mở Quote Inspector mẫu. Dưới bảng là `ScopeMismatchAlert` mẫu.
5. **"Sáu kết luận, không có kết luận nhân quả"** — danh sách dọc sáu `AssessmentBadge` cỡ `md` kèm một câu nghĩa; đoạn chú giải "Xanh nghĩa là nhận định được ủng hộ, không phải thuốc an toàn".
6. **"Ba nguồn, ba giới hạn khác nhau"** — bố cục không đối xứng: PubMed, DailyMed, FAERS, mỗi nguồn hai dòng *Cho biết* / *Không cho biết*, link sang `/data-sources`.
7. **"Agent điều tra. Reviewer quyết định."** — bố cục chia đôi: Investigator làm gì / Reviewer làm gì, kèm ảnh chụp thu nhỏ `ReviewerActionPanel` và cơ chế Invalidation.
8. **"Những điều VigiLens sẽ không làm"** — accordion 5 mục: không kết luận nhân quả · không đưa khuyến cáo điều trị cho bệnh nhân cụ thể · không tự duyệt · không dùng nguồn ngoài danh sách đã chọn · không giấu khoảng trống dữ liệu.
9. **Blog mới nhất** — 1 bài nổi bật (lớn) + 2 bài nhỏ.
10. **FAQ ngắn** (5 câu) + liên kết tới `/faq`.
11. **CTA cuối: "Thử với một nhận định của bạn"** — ô nhập một câu + nút "Soạn nhận định". Nếu chưa đăng nhập → mở trợ lý công khai (xem PHẦN J) để cấu trúc hóa claim, rồi dẫn đăng nhập.

### I2. `/how-it-works` — Cách hoạt động
- Hero ngắn + **sơ đồ SVG vòng lặp điều tra** (có mũi tên quay lại cho replanning): *Phân rã claim → Lập kế hoạch truy xuất → Truy xuất → Đánh giá đủ/thiếu (tìm khoảng trống) → [thiếu] Đổi chiến lược (từ khóa/nguồn) → Tìm bằng chứng phản bác → Kiểm tra phạm vi → Kết luận hoặc Abstain → Reviewer.* Bấm từng nút sơ đồ → panel bên cạnh giải thích kèm ví dụ.
- Mục **"Một ví dụ về replanning"**: biệt dược → tên hoạt chất quốc tế → đổi sang DailyMed (hiển thị đúng 4 bước như timeline thật).
- Mục **Sáu kết luận** (bảng đầy đủ: điều kiện đạt trạng thái, ví dụ, điều Reviewer nên làm).
- Mục **Vai trò con người & Invalidation**.
- Mục **Ngân sách điều tra** (số bước/số tài liệu, trần cứng 20 bước/100 tài liệu và vì sao có trần).

### I3. `/data-sources` — Nguồn dữ liệu
Với mỗi nguồn một phần dài: **PubMed** (tóm tắt y văn; hữu ích cho nghiên cứu quan sát/thử nghiệm; hạn chế: thường chỉ có abstract, thiên lệch công bố), **DailyMed** (nhãn thuốc do nhà sản xuất nộp; hữu ích cho cảnh báo/chống chỉ định/liều; hạn chế: phản ánh thời điểm phiên bản nhãn, không phải bằng chứng độc lập), **openFDA FAERS** (báo cáo tự nguyện; hữu ích để phát hiện tín hiệu; hạn chế: không có mẫu số, có thể trùng lặp, thiếu thông tin liều/quần thể, **không chứng minh nhân quả**). Mỗi nguồn có: *Cho biết / Không cho biết / Độ trễ cập nhật / Agent dùng nguồn này khi nào*. Cuối trang: bảng so sánh ba nguồn và biểu đồ trạng thái cập nhật (mock).

### I4. `/examples` & `/examples/[slug]` — Ca điều tra mẫu
- Danh sách: bộ lọc chip theo 6 trạng thái; thẻ gồm câu nhận định, `AssessmentBadge`, số bằng chứng theo lập trường, nguồn đã dùng. Có đủ **6 ca mẫu, mỗi ca một trạng thái** (PHẦN O).
- Chi tiết: bản **phát lại chỉ đọc** của Màn hình 2 + 3 (Timeline phát lại được với thanh tua, Ma trận, Dossier Preview), watermark `DemoBanner`, CTA "Tự điều tra một nhận định" ở thanh dính phía trên.

### I5. `/blog` & `/blog/[slug]`
- Danh sách: bài nổi bật cỡ lớn + lưới bài; lọc theo chủ đề (Cảnh giác dược cơ bản · Đọc nguồn dữ liệu · Phương pháp Agent · Ghi chú phát hành), ô tìm kiếm, thời gian đọc.
- Chi tiết: cột đọc 720px chữ serif, mục lục dính bên phải, chú thích trích dẫn cuối bài, tác giả/ngày cập nhật, "Bài liên quan", hộp tuyên bố miễn trừ.
- Chủ đề mẫu: "Lệch phạm vi là gì và vì sao nó hay bị bỏ sót" · "FAERS cho biết gì, và không cho biết gì" · "Vì sao một AI agent nên biết từ chối kết luận" · "Đọc nhãn DailyMed để tìm cảnh báo liều" · "Tín hiệu không phải là nhân quả" · "Ghi chú phát hành v0.1".

### I6. `/docs` & `/glossary`
- Docs 3 khung: cây điều hướng trái · nội dung giữa · "Trên trang này" phải; tìm kiếm (⌘K). Mục mẫu: Bắt đầu nhanh · Viết một nhận định tốt · Đọc ma trận bằng chứng · Xử lý lệch phạm vi · Quy trình duyệt · Cấu trúc hồ sơ Markdown · Phím tắt.
- Glossary: A–Z có tìm kiếm, mỗi thuật ngữ có định nghĩa ngắn + "Xem trong ví dụ" (Pharmacovigilance, Adverse event, Signal, Causality, Disproportionality, Scope mismatch, Provenance, Abstain, SPL, FAERS…).

### I7. `/limitations`, `/about`, `/contact`, `/faq`
- **Limitations:** hai cột "VigiLens làm được" / "VigiLens không làm"; "Cách chúng tôi giảm ảo giác" (mọi câu có nguồn, hash toàn vẹn, kiểm tra phạm vi, abstain); "Khi nào nên bỏ qua kết quả của Agent".
- **About:** bối cảnh đề tài P-066, phương pháp, nhóm thực hiện (khung chờ), lộ trình, tài liệu tham khảo.
- **Contact:** form (họ tên, email, tổ chức, loại yêu cầu: xin quyền truy cập / báo lỗi dữ liệu / hợp tác / khác, nội dung) → trạng thái gửi thành công; không có trường dữ liệu bệnh nhân.
- **FAQ:** accordion có tìm kiếm, nhóm theo chủ đề.

### I8. Trang xác thực
Chia đôi: trái là form, phải là khung yên tĩnh minh họa sợi dẫn chứng + một câu cam kết ("Mọi kết luận đều có người duyệt"). Trạng thái: sai mật khẩu, tài khoản bị khóa, **đang chờ Admin cấp quyền** (sau khi đăng ký), phiên hết hạn. Nút "Đăng nhập bằng tài khoản tổ chức (SSO)" ở dưới. Ghi chú: "Quyền Investigator/Reviewer do Admin cấp."

---

## PHẦN J. CHATBOT — VỊ TRÍ, HÌNH DẠNG, HÀNH VI

### J1. Triết lý
Chatbot **không thay thế form**. Nó là cách nói tự nhiên để: **(1) soạn và cấu trúc hóa một nhận định rồi khởi chạy điều tra**, **(2) hỏi đáp trên bằng chứng đã có trong hồ sơ**, **(3) hướng dẫn sử dụng sản phẩm**. Chatbot **không bao giờ** phán quyết thay Reviewer.

### J2. Ba vị trí hiện diện

**① Launcher nổi trên website công khai** — "Trợ lý sản phẩm"
- Nút nổi góc dưới phải, dạng pill **"Hỏi VigiLens"** + icon Sparkles (56px). Mở thành panel **380×600px** (bo 14px, có bóng); trên mobile thành **bottom sheet cao 92%**.
- Chức năng: trả lời về sản phẩm/cách hoạt động/nguồn dữ liệu, gợi ý ca mẫu, và **soạn nhận định** → hiển thị `ClaimCard`. Chưa đăng nhập thì nút "Bắt đầu điều tra" dẫn tới `/login` và **giữ nguyên bản nháp claim** để điền sẵn sau đăng nhập.
- Ẩn ở `/login`, `/register` và khi đang ở `/app/assistant`. Nhớ trạng thái đóng/mở trong phiên.

**② Trang Trợ lý toàn trang** `/app/assistant`
```
┌──────────────┬──────────────────────────────────────────┬─────────────────┐
│ Hội thoại    │  Tiêu đề hội thoại      [Chế độ ▾]        │ Ngữ cảnh       │
│ (280px)      │  ───────────────────────────────────────  │ (340px)        │
│ + Mới        │   tin nhắn…                                │ ClaimCard hiện │
│ Hôm nay      │                                            │ tại / hồ sơ    │
│  · …         │                                            │ đang gắn /     │
│ Tuần trước   │  ┌──────────────────────────────────────┐  │ nguồn đã trích │
│  · …         │  │ Nhập câu hỏi hoặc nhận định…  [Gửi]  │  │                │
│              │  └──────────────────────────────────────┘  │                │
└──────────────┴──────────────────────────────────────────┴─────────────────┘
```
- Ba chế độ chọn ở ô soạn: **Soạn nhận định** · **Hỏi về hồ sơ** (chọn hồ sơ bằng `@INV-…`) · **Hướng dẫn**.
- Lịch sử nhóm theo ngày; đổi tên/lưu trữ (không xóa cứng vì phục vụ kiểm toán).

**③ Ngăn "Hỏi về hồ sơ này"** trong `/app/investigations/[id]` và `/review`
- Drawer phải rộng 400px, mở bằng nút **"Hỏi về hồ sơ này"** (và phím `Ctrl/⌘ + J`). Ngữ cảnh **khóa vào hồ sơ**: chỉ trả lời dựa trên bằng chứng của hồ sơ đó.
- Citation chip trong câu trả lời **cuộn và nháy highlight** đúng dòng trong Ma trận và mở Quote Inspector.
- Có thể thu nhỏ thành tab; có nút "Mở trong trang Trợ lý".

Ngoài ra command palette có lệnh "Hỏi trợ lý…".

### J3. Giải phẫu tin nhắn
- **Người dùng:** căn phải, nền `muted`, không avatar.
- **Trợ lý:** căn trái, không khung bong bóng (giống tài liệu), icon Sparkles + `AiLabel`. Trích dẫn nguyên văn dùng chữ serif có vệt highlight.
- **Các loại thông điệp:**
  | Loại | Mô tả |
  |---|---|
  | `text` | văn bản có `CitationChip` trong dòng |
  | `claim_card` | cấu trúc hóa nhận định thành 6 ô (drug, adverse event, population, dose, route, time window), **sửa tại chỗ**; ô thiếu hiển thị nét đứt + cảnh báo "Agent sẽ coi là không giới hạn và ghi nhận khoảng trống"; nút [Bắt đầu điều tra] [Chỉnh trong form] |
  | `evidence_list` | 3–5 thẻ bằng chứng thu nhỏ (StanceBadge + ScopeChip + CitationChip) |
  | `step_stream` | khi chatbot khởi chạy điều tra, nhúng timeline thu nhỏ chạy trực tiếp, thu gọn được, có nút "Mở toàn màn hình" |
  | `action_proposal` | đề xuất hành động ("Tìm thêm nghiên cứu liều ≤ 20 mg ở người trưởng thành"). **Reviewer** thấy [Yêu cầu Agent tìm thêm]; **Investigator** thấy [Gửi đề xuất tới Reviewer] |
  | `refusal` | thẻ trung tính (viền slate) nêu lý do từ chối + cách đặt lại câu hỏi |
  | `abstain` | "Hồ sơ này không có thông tin về…" + gợi ý yêu cầu tìm thêm |
  | `error` | mất kết nối/quá tải: nêu rõ chuyện gì xảy ra, nút "Thử lại" (không xin lỗi dài dòng) |
- **Đang trả lời:** ba chấm indigo → văn bản stream từng đoạn. Nút "Dừng".
- **Hành động mỗi tin:** Sao chép · Hữu ích/Không hữu ích · **"Báo cáo sai hoặc ảo giác"** (mở form nhỏ chọn lý do: sai nguồn, sai phạm vi, kết luận nhân quả, khác) · Xem nguồn.
- **Gợi ý nhanh (quick replies):** chip dưới tin nhắn cuối ("Giới hạn ≥ 65 tuổi", "Thêm liều 2.000 mg/ngày", "Vì sao lệch phạm vi?").
- **Ô soạn:** textarea tự giãn, Enter gửi, Shift+Enter xuống dòng, nút chế độ, gợi ý `@hồ-sơ`. Dòng nhỏ dưới ô soạn: *"VigiLens có thể sai. Kiểm tra trích dẫn trước khi dùng. Không nhập thông tin định danh bệnh nhân."* Cảnh báo mềm khi phát hiện email/số điện thoại/số định danh.
- **Trạng thái rỗng:** 4 gợi ý theo vai trò (Investigator: "Soạn một nhận định", "Giải thích một ca mẫu"; Reviewer: "Tóm tắt khoảng trống của hồ sơ chờ duyệt", "So sánh hai bằng chứng mâu thuẫn").

### J4. Ranh giới hành vi (hiển thị ở trang `/limitations` và trong UI)
1. Chỉ trả lời từ **bằng chứng trong hồ sơ** hoặc **tài liệu sản phẩm**; không có nguồn thì nói không biết.
2. **Từ chối:** kết luận nhân quả, chẩn đoán, khuyến cáo điều trị hoặc liều dùng cho bệnh nhân cụ thể, thay Reviewer duyệt/từ chối.
3. Mọi câu khẳng định có chip `[E#]`.
4. Chatbot **không đổi trạng thái hồ sơ**; chỉ *đề xuất hành động* và con người xác nhận.
5. Mọi tin nhắn chatbot đều đi qua `assertNoCausalClaim`; nếu vi phạm, thay bằng thẻ `refusal`.

### J5. Ba hội thoại mẫu (dùng làm dữ liệu mock)
**(a) Soạn nhận định**
> **Người dùng:** Metformin có gây nhiễm toan lactic ở người suy thận không, liều cao thì sao?
> **Trợ lý:** Tôi đã tách câu hỏi thành một nhận định có thể kiểm chứng. Bạn kiểm tra giúp trước khi chạy.
> `ClaimCard`: Hoạt chất **metformin** · Biến cố **nhiễm toan lactic** · Quần thể **bệnh nhân suy thận (chưa rõ mức độ)** · Liều **"liều cao" (chưa cụ thể)** · Đường dùng *—* · Thời gian *—*
> Cảnh báo (caution): "'Suy thận' và 'liều cao' chưa cụ thể. Nếu giữ nguyên, Agent sẽ ghi nhận khoảng trống này và kết luận có thể là Lệch phạm vi hoặc Thiếu bằng chứng."
> [Bắt đầu điều tra] [Chỉnh trong form] · chip: *Giới hạn mức lọc cầu thận* · *Thêm liều 2.000 mg/ngày*

**(b) Hỏi về hồ sơ (ngữ cảnh khóa vào INV-0007)**
> **Người dùng:** Vì sao không kết luận "ủng hộ" khi có 3 bài ủng hộ?
> **Trợ lý:** Cả 3 bài ủng hộ [E1][E2][E4] nghiên cứu nhóm ≥ 65 tuổi dùng ≥ 100 mg, trong khi nhận định nêu liều 20 mg ở người trưởng thành. Vì vậy trạng thái là **Lệch phạm vi**. Bài [E3] khớp phạm vi nhưng kết quả không có ý nghĩa thống kê.
> `action_proposal`: "Tìm thêm nghiên cứu ở liều ≤ 20 mg, người trưởng thành" — [Gửi đề xuất tới Reviewer]

**(c) Bị hỏi ngoài ranh giới**
> **Người dùng:** Bệnh nhân 72 tuổi của tôi nên giảm xuống bao nhiêu mg?
> `refusal`: "Tôi không đưa khuyến cáo điều trị hay liều dùng cho một bệnh nhân cụ thể. VigiLens chỉ kiểm chứng một nhận định an toàn dựa trên bằng chứng đã thu thập. Bạn có thể đặt lại thành nhận định kiểm chứng được, ví dụ: *'…ở bệnh nhân ≥ 65 tuổi, liều …'*, hoặc xem mục Giới hạn trong hồ sơ."

---

## PHẦN K. KHU VỰC LÀM VIỆC (`/app`) — ĐẶC TẢ CHI TIẾT

### K0. Quy tắc chung cho mọi trang `/app`
- **Loading:** skeleton đúng hình dạng nội dung (không spinner toàn trang). **Empty:** nói rõ vì sao trống và có đúng một hành động tiếp theo. **Error:** nói chuyện gì xảy ra + cách khắc phục + nút "Thử lại" + mã lỗi (mono, sao chép được); **không xin lỗi dài dòng**. Mọi dữ liệu giả lập phải có công tắc **"Mô phỏng lỗi/rỗng/chậm"** trong menu dev để kiểm tra các trạng thái.
- Tên hành động nhất quán xuyên suốt: nút "Duyệt hồ sơ" → toast "Đã duyệt hồ sơ" → dòng audit "Duyệt hồ sơ".
- Thời gian hiển thị tương đối ("12 phút trước"), tooltip hiện giờ tuyệt đối (múi giờ `Asia/Ho_Chi_Minh`).

### K1. Dashboard `/app`
- **Investigator:** (1) *Đang chạy* — các cuộc điều tra `running` với thanh tiến trình bước/ngân sách và bước hiện tại, cập nhật trực tiếp; (2) *Vừa hoàn tất*; (3) **Bắt đầu nhanh** — một ô nhập câu nhận định + nút "Soạn nhận định" (mở trợ lý) hoặc "Dùng form đầy đủ".
- **Reviewer:** (1) *Chờ bạn duyệt* (kèm thời gian chờ, chip SLA >24h amber, >72h rose); (2) *Cần duyệt lại do có chỉnh sửa mới*; (3) *Đã duyệt gần đây*. KPI nhỏ: số ca chờ, số ca cần duyệt lại, thời gian duyệt trung bình.
- Biểu đồ cột (recharts) **phân bố 6 kết luận** trong 30 ngày, dùng đúng màu ngữ nghĩa; chú thích "Màu thể hiện kết luận về nhận định, không phải mức an toàn của thuốc". Không dùng chỉ số phù phiếm.

### K2. MÀN HÌNH 1 — Tạo & quản lý cuộc điều tra

**K2a. Danh sách `/app/investigations`**
- Header: tiêu đề + nút **[Điều tra mới]**. Thanh lọc: ô tìm (mã/thuốc/biến cố) · lọc *trạng thái chạy* · *kết luận* · *trạng thái duyệt* · *nguồn* · khoảng thời gian · "Của tôi". Chuyển **Bảng ⇄ Thẻ**.
- Cột bảng: **Mã ID** (mono, `INV-0007`) · **Nhận định** (câu chuẩn hóa + `ClaimChips` thu gọn) · **Trạng thái chạy** (`RunStatusPill`; đang chạy có mini-progress "bước 5/8") · **Kết luận** (`AssessmentBadge` hoặc "Chưa có") · **Trạng thái duyệt** · **Nguồn** (SourceChip) · **Người tạo** · **Thời gian tạo**.
- Hành động dòng (menu ⋯): Mở · **Chạy lại với nhận định này** (nhân bản vào form) · Xem audit · Lưu trữ. Bấm dòng → `/app/investigations/[id]`. Mobile: chuyển sang thẻ.
- Trạng thái: *loading* (8 skeleton row) · *empty lần đầu* ("Chưa có cuộc điều tra nào. Bắt đầu bằng một nhận định." + [Điều tra mới] + [Xem ca mẫu]) · *empty do lọc* ("Không có cuộc điều tra khớp bộ lọc" + [Xóa bộ lọc]) · *error*. Tự làm mới dòng `running` mỗi 5 giây.

**K2b. Form tạo mới `/app/investigations/new`**
```
┌───────────────────────────────────────────────┬──────────────────────────────┐
│ Điều tra mới                                  │ Nhận định chuẩn hóa  ✦ xem trước│
│                                               │ "Metformin gây nhiễm toan     │
│ ▸ Nhận định (bắt buộc)                        │  lactic ở …"  [chips]         │
│   Thuốc / Hoạt chất *   [__________]  ↳ gợi ý │ ───────────────────────────── │
│   Biến cố có hại *      [__________]          │ Độ phủ phạm vi: 2/6 trường    │
│                                               │ ◐ thêm quần thể và liều để    │
│ ▸ Giới hạn phạm vi (khuyến nghị) [2/4 đã nhập]│   kết quả sát nhận định hơn   │
│   Quần thể · Liều · Đường dùng · Cửa sổ t.gian │ ───────────────────────────── │
│                                               │ Kế hoạch dự kiến              │
│ ▸ Cấu hình điều tra                           │ Nguồn: PubMed, DailyMed       │
│   ☑ PubMed  ☑ DailyMed  ☐ openFDA FAERS       │ Tối đa 8 bước · 50 tài liệu   │
│   Số bước tối đa ──●──────── 8   (trần 20)     │                              │
│   Số tài liệu tối đa ──●───── 50  (trần 100)   │ [Bắt đầu điều tra]            │
│                                               │ [Lưu nháp]                    │
└───────────────────────────────────────────────┴──────────────────────────────┘
```
- **Trường bắt buộc:** `drug`, `adverse event` (dấu * và thông báo lỗi tại chỗ). Ô thuốc/biến cố có **autocomplete từ Từ điển thuật ngữ**: gõ biệt dược hiện gợi ý "Glucophage → **metformin** (tên hoạt chất)", chọn là điền tên chuẩn và hiển thị chip "đã chuẩn hóa" (đây là gốc của replanning ở Màn hình 2).
- **Accordion "Giới hạn phạm vi"** (đóng mặc định, tiêu đề hiển thị số trường đã nhập): `population` (chọn nhanh: Người cao tuổi ≥65, Trẻ em, Phụ nữ mang thai, Suy thận, Suy gan + nhập tự do), `dose` (giá trị + đơn vị + toán tử `=`/`≥`/`≤`/khoảng), `route` (select), `time window` (từ–đến hoặc "trong vòng N ngày sau khi dùng").
- **Cấu hình:** checkbox nguồn kèm mô tả một dòng, bắt buộc chọn ≥1. **Slider ngân sách:** số bước (mặc định **8**, trần **20**), số tài liệu (mặc định **50**, trần **100**); có vạch đánh dấu mặc định và trần, hiển thị giá trị số bên cạnh, tooltip giải thích đánh đổi ("nhiều bước hơn → thám hiểm sâu hơn nhưng lâu và tốn token hơn"). Có ước tính thời gian/token (mock).
- Nút phụ **"Cấu trúc hóa từ câu văn"**: dán một câu tự do → AI điền các ô (nhãn `AiLabel`, mọi ô vẫn sửa được). Cùng cơ chế với `claim_card` của chatbot.
- **Cột phải dính:** câu nhận định chuẩn hóa dựng trực tiếp theo từng phím gõ; "Độ phủ phạm vi" (định tính, không % giả chính xác); tóm tắt cấu hình.
- Gửi: nút chuyển trạng thái "Đang tạo…", chuyển sang `/app/investigations/[id]` ở trạng thái `queued`. Lỗi mạng: giữ nguyên dữ liệu form, hiện alert tại nút gửi.

### K3. MÀN HÌNH 2 — Timeline thời gian thực & Ma trận bằng chứng (màn hình quan trọng nhất)

**Bố cục desktop ≥1280px** (1024–1279: panel phải thành tab; <1024: ba tab "Tiến trình · Bằng chứng · Tổng quan")
```
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Cuộc điều tra / INV-0007            [Hỏi về hồ sơ này] [Tạm dừng] [Chuyển sang duyệt]│
│ Metformin gây nhiễm toan lactic ở suy thận 3b, liều ≥2.000 mg/ngày                 │
│ [chips] [● Đang chạy] [Kết luận: chưa có] [Chưa duyệt]                             │
│ Bước 5/8 ▓▓▓▓▓░░░ · Tài liệu 31/50 ▓▓▓░░ · Token 48,2k                              │
├────────────────────┬──────────────────────────────────────────┬──────────────────┤
│ TIMELINE SUY LUẬN  │ BẰNG CHỨNG                               │ PANEL PHẢI       │
│ (360px)            │ [Tất cả 14][Ủng hộ 5][Phản bác 3]        │ Ngân sách        │
│ ● B1 Tìm PubMed    │ [Chưa chắc chắn 4][Nền 2]  ⇄ So sánh     │ Phân rã nhận định│
│ │  "Lý do: …"      │ ⚠ 2 cảnh báo lệch phạm vi ▾              │ Khoảng trống     │
│ ↻ B2 Đổi chiến lược│ ┌────────────────────────────────────┐   │ Nguồn đã dùng    │
│ ● B3 Chuyển DailyMed│ │ bảng ma trận                       │   │ Trợ lý (tab)     │
│ ⚠ B4 Phát hiện … │ └────────────────────────────────────┘   │                  │
│ ◌ B5 Đang đọc…     │                                          │                  │
└────────────────────┴──────────────────────────────────────────┴──────────────────┘
```

**Header dính (sticky):** breadcrumb; hành động (**Tạm dừng/Dừng** khi `running`; **Chuyển sang phê duyệt** khi `waiting_for_review`/`completed`; **Hỏi về hồ sơ này**); câu nhận định (H2 Outfit) + `ClaimChips`; `RunStatusPill`, `AssessmentBadge` (khi có), `ReviewStateBadge`; `BudgetMeter` bản gọn.

**1) Timeline suy luận thích ứng (cột trái)**
- Rail dọc, mỗi nút là một `AgentStepCard`: số bước (đây là trình tự thật nên đánh số) · icon loại bước · tiêu đề ("Tìm trên PubMed") · **truy vấn** (mono, sao chép được) · **Rationale** (khung indigo-soft, nhãn `AiLabel`, 1–3 câu: *vì sao Agent làm bước này*) · **kết quả** ("3 tài liệu, 1 mới") · `SourceChip` · thời lượng + token. Bấm mở rộng: danh sách tài liệu tìm được, và với `replan` có **khối đối chiếu truy vấn trước → sau** (diff tô nhấn).
- Loại bước có hình dáng riêng: `search`/`read` (nút tròn indigo) · **`replan`/`source_switch`** (nút indigo đặc, icon rẽ nhánh, nhãn "Đổi chiến lược", hiện *"Vì sao: ít kết quả (2) → thử tên hoạt chất quốc tế"*) · `contradiction_found` (nút rose) · `scope_mismatch` (nút cam) · `gap_identified` (nút amber nét đứt) · `conclude`/`abstain` (nút cuối; abstain trình bày trang trọng).
- Ví dụ chuỗi hiển thị chuẩn: **B1** Tìm PubMed → ít kết quả → **B2** Tự động đổi tên biệt dược sang tên hoạt chất quốc tế (Replanning) → **B3** Đổi nguồn sang DailyMed → **B4** Tìm thấy mâu thuẫn → **B5** Kiểm tra lệch phạm vi → **B6** Kết luận/Abstain.
- **Trực tiếp:** bước đang chạy có chấm nhịp thở + dòng "Đang tìm…" với skeleton kết quả; tự cuộn theo bước mới, **dừng cuộn khi người dùng tự cuộn lên** và hiện pill "Về bước mới nhất". Bộ lọc nhanh: Tất cả · Chỉ đổi chiến lược · Chỉ phát hiện (mâu thuẫn/lệch phạm vi/khoảng trống). Có chú giải ngắn các loại nút.

**2) Ma trận bằng chứng (cột giữa)**
- **Tab/Badge có đếm:** Tất cả · 🟢 **Ủng hộ** · 🔴 **Phản bác** · 🟡 **Chưa chắc chắn / không có ý nghĩa thống kê** · ⚪ **Thông tin nền**. Nút chuyển **Bảng ⇄ So sánh mâu thuẫn**. Có chú giải một dòng "Xanh = nhận định được ủng hộ, không phải thuốc an toàn".
- **Bộ lọc/sắp xếp:** nguồn (đa chọn), khớp phạm vi, tìm trong tiêu đề, sắp theo mới nhất/nguồn/khớp phạm vi. Chọn mật độ dòng.
- **Cột:** `SourceChip` · **Tiêu đề** (kèm năm + ID mono, 2 dòng) · **Quần thể nghiên cứu** · **Liều lượng** · **Scope** (`ScopeChip`) · `StanceBadge` (ẩn khi đang ở tab theo lập trường) · nút **[Xem trích dẫn]**. Viền trái 3px theo màu lập trường. Reviewer có menu ⋯ mỗi dòng: Đổi lập trường · Sửa scope · Loại bỏ (đều mở `EditEvidenceDialog` yêu cầu nhập lý do).
- **Phía trên bảng:** các `ScopeMismatchAlert` (thu gọn được, "2 cảnh báo lệch phạm vi") và alert "Phát hiện mâu thuẫn" có nút **[So sánh song song]**. Ví dụ nội dung cảnh báo: *"Nghiên cứu của Smith et al. có kết quả đối lập nhưng được thực hiện trên liều 100 mg (cao hơn liều 20 mg trong nhận định)."* Bấm cảnh báo → cuộn/nháy dòng liên quan.
- **So sánh mâu thuẫn song song (`ContradictionCompare`):** hai cột "Tài liệu A: Ủng hộ" | "Tài liệu B: Phản bác" gồm tiêu đề, nguồn, thiết kế nghiên cứu, quần thể, liều, đường dùng, kết quả tóm tắt, **đoạn trích serif có highlight**, `ScopeChip`. Giữa hai cột là **thanh khác biệt** liệt kê các thuộc tính lệch (Quần thể: ≥65 tuổi ≠ người trưởng thành · Liều: 100 mg ≠ 20 mg) tô amber. Dưới cùng: nhận định của Agent (`AiLabel`) *"Mâu thuẫn biểu kiến do khác phạm vi"* + (Reviewer) nút **[Đánh dấu đã giải quyết]** kèm ghi chú. Điều hướng ◀ ▶ nếu có nhiều cặp.
- **Trạng thái:** *rỗng theo tab* (đang chạy: "Chưa có bằng chứng ủng hộ. Agent vẫn đang tìm."; đã xong: "Không tìm thấy bằng chứng ủng hộ trong các nguồn đã chọn." + (Reviewer) [Yêu cầu tìm thêm]) · *loading* skeleton dòng · *lỗi nguồn* (alert rose: "DailyMed không phản hồi, đã thử lại 2 lần" + [Thử lại bước này]).
- **Bằng chứng mới đến (live):** dòng trượt vào đầu bảng, nháy viền indigo 1,2 giây rồi lặng; số đếm trên tab tăng bằng hiệu ứng tick. Nếu người dùng đang cuộn xuống, hiện pill "+2 bằng chứng mới" thay vì giật nội dung.

**3) Panel phải (340px, thu gọn được)**
1. **Bộ đếm ngân sách & tài nguyên (đầy đủ):** Bước *5/8* (vạch trần *20*) · Tài liệu *31/50* (vạch trần *100*) · Token LLM *48,2k* (sparkline theo bước) · thời gian chạy. Màu: <70% indigo → ≥80% amber "Sắp hết ngân sách" → 100% hiện "Đã dùng hết ngân sách — Agent dừng với dữ liệu hiện có" (kèm gợi ý Reviewer có thể cấp thêm trong trần).
2. **Phân rã nhận định (`ClaimDecomposition`):** từng thành phần (hoạt chất, biến cố, quần thể, liều, đường dùng, thời gian) với trạng thái *Đã kiểm chứng ✓ / Một phần ◐ / Chưa có bằng chứng ○*.
3. **Khoảng trống bằng chứng (`EvidenceGapList`):** mỗi dòng nêu thiếu gì, Agent đã thử gì, và (Reviewer) nút **[Yêu cầu tìm thêm]**.
4. **Nguồn đã dùng:** số tài liệu và tình trạng từng nguồn.
5. **Tab "Trợ lý":** chatbot ngữ cảnh khóa vào hồ sơ (PHẦN J, vị trí ③).

**Banner trạng thái ở đầu thân trang**
`queued` (xám: "Đang xếp hàng…") · `running` (indigo mảnh: "Agent đang điều tra…") · `waiting_for_review` (amber: "Agent đã hoàn tất. Hồ sơ đang chờ Reviewer." + nút) · `completed`+đã duyệt (emerald) · `needs_rereview` (`InvalidationBanner`) · `failed` (rose, giữ lại kết quả một phần, nút "Thử lại từ bước N") · **mất kết nối trực tiếp** (xám: "Mất kết nối trực tiếp, đang kết nối lại (lần 2/5)…" + [Tải lại]).

**4) Trình soi trích dẫn gốc (`QuoteInspector`)** — Drawer phải 640px (mobile: sheet toàn màn)
- **Đầu drawer:** `SourceChip`, tiêu đề, ID (mono), liên kết "Mở nguồn gốc" (ngoài), `StanceBadge`, `ScopeChip`, nút ◀ ▶ chuyển bằng chứng liền kề.
- **Tab "Trích dẫn":** văn bản đầy đủ chữ serif, có mục (Abstract/Methods/Results hoặc mục nhãn thuốc), **tô highlight marker đúng câu làm bằng chứng** + thanh trái; nút **"Nhảy tới trích dẫn"** (khi mở tự cuộn đến và nháy một lần); nếu nhiều đoạn có điều hướng 1/3. Nút sao chép trích dẫn kèm tham chiếu. Khung **"Vì sao đây là bằng chứng [Ủng hộ]?"** (`AiLabel`): 2–3 thuộc tính trích ra (quần thể, liều, kết quả), mỗi thuộc tính bấm để nhảy tới đoạn tương ứng. Reviewer có [Đổi lập trường] [Sửa scope] [Loại bỏ].
- **Bản ghi FAERS:** hiển thị dạng khóa–giá trị có đánh dấu trường làm bằng chứng (mã báo cáo, nhóm tuổi/giới, thuốc, biến cố, kết cục); **không** có trường định danh cá nhân.
- **Tab "Siêu dữ liệu":** tác giả/năm/tạp chí, thiết kế nghiên cứu, cỡ mẫu, PMID/Set ID/Mã báo cáo, ngày truy xuất.
- **Tab "Nguồn gốc (provenance)":** câu truy vấn đã dùng, **bước nào tìm ra** (link nhảy về Timeline), thời điểm truy xuất, URL nguồn, **mã hash SHA-256 của văn bản đã lưu** (`HashChip`) và nút **[Xác minh toàn vẹn]** → trạng thái *đang tính → ✓ Khớp hash* hoặc *⚠ Không khớp* (alert rose: "Văn bản đã lưu khác hash ghi nhận. Không dùng làm bằng chứng cho đến khi tải lại.").
- Phím tắt: `Esc` đóng, `←/→` chuyển bằng chứng, giữ focus trong drawer, trả focus về dòng đã mở.

### K4. MÀN HÌNH 3 — Trung tâm phê duyệt & Hồ sơ bằng chứng (`/review`)

**Bố cục**
```
┌───────────────────────────────────────────────────────────────────────────────┐
│ INV-0007 / Phê duyệt                                                          │
│ Metformin gây nhiễm toan lactic ở suy thận 3b, liều ≥2.000 mg/ngày            │
│ ┌ [⚠ Lệch phạm vi]  (AssessmentBadge lg)  ✦ Agent đề xuất · Reviewer chưa xác nhận┐│
│ │ "Có bằng chứng, nhưng ở nhóm ≥65 tuổi, liều 100 mg; chưa khớp liều trong nhận định"││
│ └───────────────────────────────────────────────────────────────────────────┘│
│ Độ phủ bằng chứng theo phạm vi: Thuốc ✓  Biến cố ✓  Quần thể ◐  Liều ✗  Đường ○ │
├─────────────────────────────────────────────────┬─────────────────────────────┤
│ [Xem trước] [Markdown nguồn] [Thay đổi từ lần duyệt] │ BẢNG ĐIỀU KHIỂN REVIEWER   │
│ ┌──────────────┬─────────────────────────────┐ │ Trạng thái duyệt            │
│ │ Mục lục dính │ Dossier (serif, citation chip)│ │ [ Duyệt kết quả ]           │
│ └──────────────┴─────────────────────────────┘ │ [ Từ chối ]                 │
│ Nhật ký kiểm toán (Audit Trail)                  │ [ Chỉnh sửa bằng chứng/Scope]│
│                                                 │ [ Yêu cầu Agent tìm thêm ]  │
│                                                 │ ─────────────────────────── │
│                                                 │ [ Tải báo cáo Markdown ] 🔒 │
└─────────────────────────────────────────────────┴─────────────────────────────┘
```

**Huy hiệu kết luận (`AssessmentBadge` cỡ lg):** hiển thị **một trong 6 trạng thái chuẩn** kèm một câu giải thích và nút "Cách đọc kết quả". Luôn có nhãn **"Agent đề xuất"** và chip trạng thái người duyệt riêng ("Reviewer chưa xác nhận" / "Reviewer đã xác nhận"). **Tuyệt đối không** hiển thị "Thuốc chắc chắn gây bệnh" hay "Thuốc an toàn tuyệt đối". Dưới badge là **độ phủ bằng chứng theo phạm vi** (định tính ✓ ◐ ✗ ○).

**Bản xem trước hồ sơ (`DossierPreview`)** — render Markdown y khoa chỉn chu (serif, line-height 1.7, ≤72ch), mục lục dính, **citation chip trong dòng** mở Quote Inspector. 3 tab: *Xem trước* · *Markdown nguồn* (đúng nội dung sẽ tải) · *Thay đổi từ lần duyệt* (diff khi đã có chỉnh sửa). Cấu trúc bắt buộc (xem mẫu ở PHẦN O): Nhận định chuẩn hóa → Kết luận phân loại → Chiến lược tìm kiếm → Danh sách bằng chứng có trích dẫn → Mâu thuẫn & lệch phạm vi → **Khoảng trống dữ liệu (Gaps)** → **Giới hạn (Limitations)** → **Nhật ký kiểm toán (Audit Trail)** → Phụ lục hash.

**Bảng điều khiển Reviewer (`ReviewerActionPanel`, cột phải dính)**
- *Khối trạng thái duyệt:* `ReviewStateBadge` + dòng "Duyệt bởi … lúc …" hoặc "Chưa ai duyệt".
- *Bốn hành động:*
  - **[ Duyệt kết quả ]** (nút emerald đặc) → hộp thoại: tóm tắt (badge, số bằng chứng theo lập trường), **3 ô xác nhận bắt buộc** ("Tôi đã xem các bằng chứng phản bác", "Tôi đã xem cảnh báo lệch phạm vi và khoảng trống", "Tôi xác nhận hồ sơ không chứa kết luận nhân quả"), ô ghi chú tùy chọn → [Hủy] [Duyệt hồ sơ].
  - **[ Từ chối ]** (viền rose) → chọn lý do có sẵn + nhập tự do **≥15 ký tự** → [Từ chối hồ sơ].
  - **[ Chỉnh sửa bằng chứng / Scope ]** → chọn đối tượng (bằng chứng cụ thể hoặc scope của nhận định) và loại thay đổi (đổi lập trường, loại bỏ, sửa quần thể/liều/đường dùng, đổi trạng thái scope) → **bắt buộc nhập lý do (≥15 ký tự)** → hiển thị cảnh báo tác động ("Hồ sơ sẽ được đánh dấu cần duyệt lại") → [Lưu chỉnh sửa].
  - **[ Yêu cầu Agent tìm thêm ]** → chọn các khoảng trống cần bổ sung (hoặc nhập chỉ dẫn tự do), **cấp thêm ngân sách** (stepper bước/tài liệu, không vượt trần còn lại), chọn nguồn → [Gửi cho Agent]. Sau khi gửi, hồ sơ quay về `running`; Timeline thêm nút mốc "Reviewer yêu cầu tìm thêm"; nếu trước đó đã duyệt thì chuyển `needs_rereview`.
- **Cơ chế Invalidation (bắt buộc làm nổi bật):** khi Reviewer lưu *bất kỳ* chỉnh sửa nào sau khi đã duyệt → huy hiệu "Đã duyệt" **chuyển ngay** sang **"Cần duyệt lại do có chỉnh sửa mới"** (animation ở PHẦN M), hiện `InvalidationBanner` liệt kê thay đổi từ lần duyệt trước, **khóa nút tải báo cáo**, thêm dòng audit.
- *Khối xuất:* **[ Tải báo cáo Markdown ]** chỉ active khi `approved`; ngược lại disabled kèm tooltip lý do (chưa duyệt / cần duyệt lại / bị từ chối). Sau khi tải: toast + dòng audit + "Đã xuất lúc …". Tên tệp: `VigiLens_INV-0007_v3_2026-10-02.md`.
- **Người không phải Reviewer** (Investigator/Admin): cả 4 nút disabled, hiện ngay đầu panel dòng "Bạn đang xem ở chế độ chỉ đọc. Chỉ Reviewer được duyệt." Investigator vẫn được tải khi hồ sơ đã duyệt.
- **Trạng thái trang:** *loading* · *Agent chưa hoàn tất* (panel khóa: "Agent đang chạy. Có thể xem bản nháp." + link về Màn hình 2) · `waiting_for_review` · `approved` (viền emerald, nút xuất sáng) · `rejected` (rose, hiển thị lý do) · `needs_rereview` · `failed` · *chỉ đọc*.
- **Nhật ký kiểm toán (`AuditTimeline`):** append-only, mỗi dòng gồm người/AI, hành động, thời điểm, lý do (nếu có), liên kết tới đối tượng; lọc theo người/loại hành động.

### K5. Hàng chờ duyệt `/app/reviews` (Reviewer)
Tab **Chờ duyệt · Cần duyệt lại · Đã xử lý**. Bảng: mã, nhận định, kết luận Agent đề xuất, số mâu thuẫn, số cảnh báo lệch phạm vi, số khoảng trống, **thời gian chờ** (chip SLA), người nhận duyệt. Hành động: **Nhận duyệt** (gán cho mình), mở `/review`. Điều hướng bàn phím (`J/K` lên xuống, `Enter` mở). Empty: "Không có hồ sơ nào đang chờ. Mọi hồ sơ đã được xử lý."

### K6. Thư viện hồ sơ `/app/dossiers`
Danh sách hồ sơ **đã duyệt** (thẻ/bảng): tiêu đề, `AssessmentBadge`, phiên bản (v1, v2…), người/thời điểm duyệt, nút **Xem** và **Tải Markdown**. Chi tiết phiên bản: xem các lần duyệt trước và diff. Empty: "Chưa có hồ sơ nào được duyệt."

### K7. Thư viện tài liệu `/app/library`
Mọi tài liệu đã thu thập từ các cuộc điều tra: tìm kiếm, lọc nguồn/loại/trạng thái hash, cột "Dùng trong N cuộc điều tra"; bấm mở `QuoteInspector` ở chế độ tài liệu. Có huy hiệu hash `verified/mismatch`.

### K8. Cài đặt & Thông báo
- **Cài đặt:** hồ sơ cá nhân; giao diện (Sáng/Tối/Theo hệ thống); ngôn ngữ (VI/EN); mật độ bảng; thông báo (in-app/email) theo sự kiện; phím tắt; phiên đăng nhập.
- **Thông báo:** "Agent đã hoàn tất INV-0007", "INV-0003 cần duyệt lại do có chỉnh sửa mới", "Reviewer yêu cầu tìm thêm", "Nguồn DailyMed lỗi". Đánh dấu đã đọc, lọc theo loại.
- **Audit riêng của hồ sơ** `/app/investigations/[id]/audit`: `AuditTimeline` toàn trang, lọc, nút sao chép.

---

## PHẦN L. KHU QUẢN TRỊ (`/admin`) & NHẬP DỮ LIỆU

**Quy tắc chung:** bảng quản trị dùng lại mẫu bảng của `/app` (lọc, sắp xếp, mật độ). Hành động phá hủy/đổi cấu hình hệ thống luôn có hộp thoại xác nhận nêu rõ hậu quả. **Mọi thay đổi cấu hình ghi một dòng audit** (ai, đổi gì, trước/sau, lý do).

### L1. Tổng quan `/admin`
KPI nhỏ: người dùng hoạt động · cuộc điều tra 7 ngày · tỷ lệ Abstain · số lỗi nguồn 24 giờ. Trạng thái 3 nguồn (Hoạt động/Suy giảm/Ngừng) · hàng đợi nhập dữ liệu · biểu đồ token theo ngày · danh sách cảnh báo hệ thống cần xử lý.

### L2. Người dùng & vai trò `/admin/users`
- Tab **Người dùng** (tên, email, vai trò, trạng thái *hoạt động/chờ cấp quyền/đã khóa*, đăng nhập gần nhất, số cuộc điều tra) và tab **Yêu cầu cấp quyền** (từ `/register`, có nút Duyệt/Từ chối kèm lý do).
- Hành động: Mời qua email (hộp thoại chọn vai trò) · Đổi vai trò · Tạm khóa · Đặt lại MFA. Cấp vai trò **Reviewer** yêu cầu ô xác nhận chuyên môn (ví dụ "Dược sĩ lâm sàng đã xác minh"). Không cho hạ quyền Admin cuối cùng.
- Có khung **Ma trận quyền** chỉ đọc (bảng ở PHẦN D).

### L3. Nguồn dữ liệu `/admin/sources`
Ba khối nguồn (không đối xứng cứng nhắc): **PubMed**, **DailyMed**, **openFDA FAERS**. Mỗi khối: trạng thái (chấm màu + chữ), API key (che, nút Xoay khóa), giới hạn tốc độ và mức dùng hôm nay, timeout/số lần thử lại, TTL bộ nhớ đệm, độ trễ (sparkline), lần gọi thành công gần nhất, nút **[Kiểm tra kết nối]**, công tắc bật/tắt. Tắt nguồn → cảnh báo "Form tạo điều tra sẽ ẩn nguồn này; N cuộc điều tra đang chạy sẽ bỏ qua nguồn." Có nhật ký lỗi gần đây.

### L4. Nhập dữ liệu `/admin/ingestion`
**Danh sách công việc:** mã, loại (*tải tệp / theo định danh / nhập thủ công / CSV hàng loạt*), nguồn, số bản ghi, **tiến trình dạng stepper** (Đã tải lên → Phân tích cú pháp → Chuẩn hóa → Tính hash → Lập chỉ mục → Hoàn tất), trạng thái (`queued`/`running`/`completed`/`partial`/`failed`), người tạo, thời gian. Bấm vào xem **chi tiết**: nhật ký, bảng lỗi theo bản ghi, nút **[Thử lại bản ghi lỗi]**.

**Trình hướng dẫn nhập mới `/admin/ingestion/new`** (4 bước, đây là trình tự thật nên có đánh số):
1. **Chọn phương thức**
   - *Tải tệp:* PDF, XML (nhãn thuốc DailyMed/SPL), JSON/CSV (trích xuất FAERS), TXT; kéo-thả nhiều tệp, hiển thị giới hạn dung lượng.
   - *Theo định danh:* dán nhiều dòng **PMID / DOI / DailyMed Set ID / mã báo cáo FAERS** → hệ thống truy xuất.
   - *Nhập thủ công một tài liệu:* nguồn, tiêu đề, định danh, năm, đoạn văn bản, thiết kế nghiên cứu, quần thể, liều, đường dùng.
   - *CSV hàng loạt:* cho **từ điển thuật ngữ** hoặc **bộ claim vàng** của evaluation.
2. **Ánh xạ & xem trước:** ghép cột ↔ trường, xem trước 10 dòng, lỗi hiện ngay tại ô (thiếu trường, trùng ID, sai định dạng).
3. **Xác nhận & chính sách:** xử lý trùng (*bỏ qua / ghi đè / giữ cả hai*), gắn nhãn nguồn, **quét tự động dấu hiệu thông tin định danh** (cảnh báo nếu có), ghi chú.
4. **Chạy & theo dõi:** tiến trình, kết quả "n thành công, m lỗi", liên kết sang Kho tài liệu.
- **Quy tắc minh bạch:** tài liệu nhập thủ công mang nhãn **"Nhập nội bộ"**, hiển thị khác tài liệu truy xuất tự động trong provenance và Quote Inspector, để Reviewer biết nguồn gốc.

### L5. Kho tài liệu `/admin/corpus`
Bảng mọi tài liệu: ID, nguồn, tiêu đề, định danh, ngày truy xuất/nhập, `HashChip` + trạng thái hash, loại (*tự động / nhập nội bộ*), "dùng trong N hồ sơ". Chi tiết: xem văn bản, **lịch sử phiên bản** (khi nguồn cập nhật sinh hash mới). Nút **[Xác minh lại hash hàng loạt]**. **[Vô hiệu hóa tài liệu]** (không xóa) → hộp thoại liệt kê các hồ sơ bị ảnh hưởng và cho biết chúng sẽ tự chuyển `needs_rereview`.

### L6. Từ điển thuật ngữ `/admin/terminology`
Tab **Thuốc** (biệt dược ↔ hoạt chất, từ đồng nghĩa), **Biến cố** (cách gọi thường ↔ thuật ngữ chuẩn), **Quần thể** (ví dụ "người già" → "≥65 tuổi"), **Đơn vị liều**. Bảng sửa tại chỗ, thêm/nhập CSV, cột "Đã dùng trong replanning N lần" và "Nguồn của ánh xạ". Reviewer được *đề xuất* mục mới, Admin duyệt.

### L7. Cấu hình agent `/admin/agent-config`
- **Ngân sách mặc định & trần cứng** (bước mặc định 8/trần 20; tài liệu mặc định 50/trần 100). Sửa **trần** cần nhập lý do, ghi audit.
- **Mô hình & phiên bản prompt** (danh sách phiên bản, xem diff, quay lui).
- **Chiến lược thích ứng:** công tắc cho từng loại replanning (đổi từ khóa · biệt dược→hoạt chất · đổi nguồn · chủ động tìm bằng chứng phản bác · kiểm tra phạm vi).
- **Mức thận trọng khi kết luận** (3 mức *Thận trọng / Cân bằng / Linh hoạt* kèm mô tả tác động lên tỷ lệ Abstain; **không** dùng con số phần trăm giả chính xác).
- Timeout, số lần thử lại. Khung **[Chạy thử với nhận định mẫu]** (sandbox) hiển thị Timeline thu nhỏ.
- Quy trình **Nháp → Xuất bản** có nhập lý do.

### L8. Guardrail `/admin/guardrails`
- Danh sách **cụm cấm kết luận nhân quả** (thêm/sửa/xóa) + **ô kiểm thử**: dán văn bản → tô đỏ nhạt các cụm vi phạm.
- Chính sách bật/tắt có cảnh báo: bắt buộc citation chip · bắt buộc mục Giới hạn · quét thông tin định danh · **chỉ cho xuất khi đã duyệt** (khóa, không tắt được).
- Nhật ký **đầu ra bị chặn** (thời điểm, nơi phát sinh: chatbot/dossier, đoạn trích, hành động đã thực hiện).

### L9. Đánh giá chất lượng `/admin/evaluation` (phục vụ chứng minh đề tài)
- **Bộ claim vàng:** bảng claim + kết luận chuẩn do chuyên gia gán + nguồn; nhập bằng CSV.
- **Chạy đánh giá:** chọn bộ claim + phiên bản agent + *baseline (RAG tìm một lần)* → chạy, có tiến trình.
- **Kết quả:** thẻ chỉ số — *độ chính xác trạng thái*, *phát hiện lệch phạm vi (precision/recall)*, *Abstain đúng chỗ*, *độ trung thực trích dẫn*, *tỷ lệ tìm được bằng chứng phản bác*, *số bước và token trung bình*. **Biểu đồ cột nhóm Agent vs Baseline**; **ma trận nhầm lẫn 6×6** (dùng thang indigo/trung tính, **không** dùng màu ngữ nghĩa để tránh hiểu nhầm); bảng ca sai (claim, kết luận của Agent, kết luận chuẩn, link xem hồ sơ). Lịch sử các lần chạy, so sánh hai lần. Toàn bộ số liệu là mock và có `DemoBanner`.

### L10. Audit log hệ thống `/admin/audit`
Bảng append-only: thời điểm, người/AI, hành động, đối tượng, địa chỉ phiên; lọc theo người/hành động/đối tượng/thời gian; mở chi tiết xem **diff trước/sau**. Biểu tượng khóa + dòng "Nhật ký không thể sửa hoặc xóa" và chỉ báo **"Chuỗi nhật ký toàn vẹn ✓"**.

### L11. Quản lý nội dung `/admin/content`
Tab **Blog** (danh sách, trình soạn Markdown có xem trước, thẻ chủ đề, trạng thái nháp/đã đăng/hẹn giờ) · **FAQ** (kéo thả sắp xếp) · **Ca mẫu** (chọn một hồ sơ đã hoàn tất → [Xuất bản làm ca mẫu], có bước kiểm tra ẩn danh) · **Thông báo hệ thống** (banner toàn site).

### L12. Sức khỏe hệ thống `/admin/system`
Uptime, độ sâu hàng đợi, số kết nối trực tiếp (SSE), tỷ lệ lỗi, token theo ngày + ước tính chi phí, mức dùng theo người dùng, nhật ký sự cố.

---

## PHẦN M. KỊCH BẢN VI TƯƠNG TÁC (MICRO-INTERACTIONS)

> Mỗi kịch bản phải hỗ trợ `prefers-reduced-motion` (chỉ còn đổi màu/độ mờ, không dịch chuyển/quay) và có thông báo `aria-live` tương ứng.

| # | Tình huống | Phản hồi thị giác | Chi tiết kỹ thuật |
|---|---|---|---|
| M1 | **Agent đang replanning** | Nút bước mới trượt vào rail (240ms), nút **indigo đặc** có biểu tượng rẽ nhánh; một **sợi indigo mảnh vẽ vòng** từ bước trước sang bước mới (stroke-dashoffset 400ms) thể hiện "quay lại lập kế hoạch"; thẻ mở sẵn, khối **truy vấn cũ → mới** hiện diff (từ cũ gạch mờ, từ mới nền indigo-soft), hiện dòng *"Vì sao: ít kết quả (2) → thử tên hoạt chất quốc tế"* | `aria-live="polite"`: "Bước 2: Agent đổi chiến lược" |
| M2 | **Bằng chứng mới đến** | Dòng trượt vào đầu bảng + viền indigo nháy 1,2s rồi lặng; số trên tab tăng kiểu tick; nếu người dùng đã cuộn xuống → pill "+2 bằng chứng mới" (bấm để cuộn lên) thay vì giật nội dung | không nhảy layout |
| M3 | **Phát hiện mâu thuẫn** | Nút bước rose xuất hiện; alert rose trượt xuống phía trên Ma trận; hai dòng mâu thuẫn được nối bằng đường nét đứt rose khi hover alert | focus không bị cướp |
| M4 | **Cảnh báo lệch phạm vi** | Alert cam; **hover**: các chip thuộc tính lệch (liều/quần thể) trong dòng bảng được viền cam; **click**: cuộn tới dòng và mở nhanh popover "100 mg ≠ 20 mg" | |
| M5 | **Xem trích dẫn gốc** | Drawer trượt từ phải (200ms); văn bản **tự cuộn tới đoạn trích** (300ms), vệt marker **"vẽ" từ trái sang phải** (500ms) rồi giữ nguyên; thanh trái 3px sáng một nhịp | trả focus về dòng khi đóng |
| M6 | **Hover citation chip `[E3]`** | Popover xem nhanh (nguồn, câu trích 1–2 dòng) + **sợi dẫn chứng** vẽ từ chip tới dòng tương ứng trong Ma trận (nếu cùng màn hình) | trễ 150ms để tránh nháy |
| M7 | **Ngân sách sắp cạn / cạn** | ≥80%: thanh chuyển amber + chip "Sắp hết ngân sách"; 100%: thanh đầy, chip "Đã dùng hết ngân sách", Timeline thêm nút mốc "Agent dừng với dữ liệu hiện có" | `role="status"` |
| M8 | **Reviewer sửa bằng chứng → Invalidation** | Sau khi lưu: huy hiệu **"Đã duyệt" (emerald) chuyển mượt sang "Cần duyệt lại do có chỉnh sửa mới" (amber)** (màu cross-fade 300ms + icon đổi từ tích sang cảnh báo); `InvalidationBanner` trượt xuống, liệt kê thay đổi; nút tải báo cáo chuyển disabled kèm tooltip; dòng audit mới nháy một lần ở Audit Trail | `role="alert"` |
| M9 | **Duyệt thành công** | Nút Duyệt → trạng thái "Đang duyệt…" → vòng tích emerald **tự vẽ** (400ms) trong huy hiệu; nút Tải báo cáo **mở khóa** (đổi từ disabled sang active với một nhịp sáng viền); toast "Đã duyệt hồ sơ. Có thể tải báo cáo." Không dùng pháo giấy/confetti | |
| M10 | **Tải báo cáo** | Nút hiện tiến trình ngắn → toast "Đã tải VigiLens_INV-0007_v3.md" kèm nút Mở thư mục tải về; dòng audit "Xuất hồ sơ" | |
| M11 | **Abstain** | Bước cuối là nút trung tính-amber nét đứt; badge "Thiếu bằng chứng — Agent từ chối kết luận" **hiện chậm, trang trọng** (fade 400ms, không rung/lắc), kèm danh sách khoảng trống và nút "Yêu cầu tìm thêm" | tránh mọi gợi ý "thất bại" |
| M12 | **Xác minh hash** | Bấm → chip chuyển "Đang tính…" (xoay nhẹ) → **✓ Khớp** (emerald, tích vẽ) hoặc **⚠ Không khớp** (rose + rung ngang nhẹ 1 lần ≤200ms, không lặp) kèm alert giải thích | |
| M13 | **Mất kết nối trực tiếp** | Banner xám xuất hiện sau 3 giây mất tín hiệu: "Mất kết nối trực tiếp, đang kết nối lại (lần 2/5)…"; khi nối lại tự đồng bộ các bước bị lỡ và hiện toast "Đã đồng bộ lại" | không xóa dữ liệu đang hiển thị |
| M14 | **Chatbot** | Stream văn bản theo đoạn; `claim_card` điền dần từng ô (stagger 60ms); xác nhận `action_proposal` đổi nút thành "Đã gửi tới Reviewer ✓"; bấm chip `[E#]` trong chat → Ma trận cuộn + nháy đúng dòng | |
| M15 | **Nút bị khóa theo vai trò** | Hover/focus hiện tooltip lý do ngay (không trễ), icon khóa nhỏ; không tạo cảm giác lỗi | tooltip nhận focus bàn phím |
| M16 | **Hero trang chủ** (khoảnh khắc chuyển động duy nhất tự chạy) | Timeline demo phát **một lần**, mỗi bước ~900ms, bước cuối vẽ sợi dẫn chứng tới vệt highlight; kết thúc dừng ở trạng thái cuối, có nút Phát lại/Tạm dừng | reduced-motion: hiện sẵn trạng thái cuối |
| M17 | **Tạm dừng/Dừng agent** | Dừng: hộp thoại xác nhận ("Giữ kết quả hiện có và dừng điều tra?"); sau khi dừng, Timeline thêm nút "Đã dừng bởi [tên]"; trạng thái chuyển `waiting_for_review` | |
| M18 | **Đổi tab lập trường** | Chỉ gạch chân tab trượt (160ms) và bảng cross-fade 120ms; số đếm không đổi chỗ | |

**Phím tắt:** `⌘/Ctrl+K` palette · `⌘/Ctrl+J` trợ lý · `J/K` lên-xuống danh sách · `Enter` mở · `Esc` đóng drawer/modal · `←/→` chuyển bằng chứng trong Quote Inspector · `G` rồi `I` đến Cuộc điều tra · `G` rồi `R` đến Hàng chờ duyệt · `?` xem danh sách phím tắt.

---

## PHẦN N. MÔ HÌNH DỮ LIỆU & HỢP ĐỒNG API (để giao diện sẵn sàng gắn backend)

```ts
// lib/types.ts
type Role = 'visitor' | 'investigator' | 'reviewer' | 'admin';
type RunStatus = 'queued' | 'running' | 'waiting_for_review' | 'completed' | 'failed' | 'cancelled';
type AssessmentStatus = 'supported_for_scope' | 'contradicted_for_scope' | 'insufficient_evidence'
  | 'scope_mismatch' | 'out_of_scope' | 'requires_human_review';
type ReviewState = 'not_reviewed' | 'approved' | 'rejected' | 'needs_rereview';
type Stance = 'supporting' | 'contradicting' | 'uncertain' | 'background';
type ScopeMatch = 'matched' | 'partial' | 'mismatched';
type SourceId = 'pubmed' | 'dailymed' | 'faers';

interface Claim {
  drug: string; adverseEvent: string;
  population?: string; dose?: { op: '=' | '>=' | '<=' | 'range'; value: number; value2?: number; unit: string };
  route?: string; timeWindow?: string; rawText?: string;
}
interface Budget { maxSteps: number; maxDocs: number; ceilingSteps: 20; ceilingDocs: 100 }
interface BudgetUsage { steps: number; docs: number; tokens: number; elapsedMs: number }

interface Investigation {
  id: string;                       // INV-0007
  claim: Claim; sources: SourceId[]; budget: Budget; usage: BudgetUsage;
  runStatus: RunStatus; assessment?: { status: AssessmentStatus; rationale: string; coverage: Coverage };
  reviewState: ReviewState; reviewedBy?: string; reviewedAt?: string; version: number;
  createdBy: string; createdAt: string; invalidatedReason?: string;
}
interface Coverage { drug: Cov; adverseEvent: Cov; population: Cov; dose: Cov; route: Cov; timeWindow: Cov }
type Cov = 'verified' | 'partial' | 'missing' | 'not_specified';

type StepType = 'search' | 'read' | 'replan' | 'source_switch' | 'contradiction_found'
  | 'scope_mismatch' | 'gap_identified' | 'reviewer_request' | 'conclude' | 'abstain';
interface AgentStep {
  index: number; type: StepType; source?: SourceId; query?: string; prevQuery?: string;
  rationale: string; resultSummary?: string; docsFound?: number; newDocs?: number;
  tokens: number; durationMs: number; startedAt: string; docIds?: string[]; status: 'running' | 'done' | 'error';
}
interface EvidenceItem {
  id: string; label: string;        // E1, E2…
  docId: string; source: SourceId; title: string; year?: number; externalId: string; // ID giả: DEMO-0001
  stance: Stance; scope: ScopeMatch; scopeDiffs?: { field: 'population'|'dose'|'route'|'timeWindow'; claim: string; evidence: string }[];
  studyPopulation?: string; dose?: string; designNote?: string;
  quotes: { start: number; end: number; text: string }[]; foundAtStep: number;
  editedByReviewer?: { by: string; at: string; reason: string };
}
interface DocumentRecord {
  id: string; source: SourceId; origin: 'auto' | 'internal'; text?: string; record?: Record<string,string>;
  sha256: string; hashStatus: 'verified' | 'mismatch' | 'unchecked'; retrievedAt: string; url?: string; meta: Record<string,string>;
}
interface Contradiction { id: string; aId: string; bId: string; diffs: string[]; agentNote: string; resolved?: { by: string; note: string } }
interface Gap { id: string; description: string; tried: string[]; relatedField: keyof Coverage }
interface AuditEntry { id: string; at: string; actor: { name: string; kind: 'human'|'ai'|'system' }; action: string; target?: string; reason?: string; before?: unknown; after?: unknown }
interface IngestionJob { id: string; kind: 'file'|'identifier'|'manual'|'csv'; source?: SourceId; total: number; ok: number; failed: number;
  stage: 'uploaded'|'parsing'|'normalizing'|'hashing'|'indexing'|'done'; status: 'queued'|'running'|'completed'|'partial'|'failed'; createdBy: string; createdAt: string }
interface ChatMessage { id: string; role: 'user'|'assistant'; kind: 'text'|'claim_card'|'evidence_list'|'step_stream'|'action_proposal'|'refusal'|'abstain'|'error';
  content: string; payload?: unknown; citations?: string[]; createdAt: string }
interface EvalRun { id: string; goldSet: string; agentVersion: string; baseline: boolean; metrics: Record<string, number>; confusion: number[][]; createdAt: string }
```

**Sự kiện agent (SSE mock) — hook `useAgentStream`:** `run.started` · `step.started` · `step.completed` · `replan` · `evidence.added` · `contradiction.detected` · `scope_mismatch.detected` · `gap.identified` · `budget.update` · `run.waiting_for_review` · `run.completed` · `run.failed` · `heartbeat`. Kịch bản phát lại nằm trong `lib/mock/agent-script.ts` (mảng sự kiện có `delayMs`), có điều khiển **"Tua nhanh ×4"** ở chế độ demo.

**Endpoint giả lập (`lib/api/`, trả Promise có độ trễ 200–600ms):** `GET/POST /investigations` · `GET /investigations/:id` · `GET /investigations/:id/stream` (SSE) · `GET /investigations/:id/evidence` · `GET /documents/:id` · `POST /documents/:id/verify-hash` · `POST /investigations/:id/review` (`approve|reject`) · `POST /investigations/:id/edit` (bắt buộc `reason`) · `POST /investigations/:id/request-more` · `GET /investigations/:id/dossier.md` · `GET /investigations/:id/audit` · `POST /chat` (stream) · `GET/POST /admin/...`. Chặn ở lớp client: `edit`/`reject` thiếu lý do <15 ký tự → lỗi xác thực; `dossier.md` chỉ trả khi `reviewState === 'approved'`.

---

## PHẦN O. DỮ LIỆU MẪU (SEED) — dùng để UI trông thật và kiểm thử đủ trạng thái

> Toàn bộ là **dữ liệu minh họa tổng hợp**. Định danh dạng `DEMO-xxxx`. Không trích kết quả nghiên cứu thật.

### O1. Cuộc điều tra mẫu (≥10, phủ mọi trạng thái)
| ID | Nhận định (rút gọn) | Chạy | Kết luận | Duyệt |
|---|---|---|---|---|
| INV-0001 | Metformin → nhiễm toan lactic, suy thận 3b, ≥2.000 mg/ngày | completed | supported_for_scope | approved |
| INV-0002 | Thuốc A → viêm gan, người trưởng thành, 50 mg | completed | contradicted_for_scope | approved |
| INV-0003 | Thuốc B → kéo dài QT, ≥65 tuổi, đường uống | completed | supported_for_scope | **needs_rereview** (Reviewer đã sửa 1 bằng chứng) |
| INV-0004 | Thuốc C → hạ đường huyết, trẻ em | waiting_for_review | insufficient_evidence | not_reviewed |
| INV-0005 | Thuốc D → xuất huyết tiêu hóa, mọi bệnh nhân, 20 mg | waiting_for_review | **scope_mismatch** (nghiên cứu ở 100 mg, ≥65 tuổi) | not_reviewed |
| INV-0006 | Thuốc E → rụng tóc (biến cố ngoài chỉ định nhãn) | completed | out_of_scope | approved |
| INV-0007 | Glucophage → nhiễm toan lactic, suy thận 3b (ca dùng cho Timeline replanning) | **running** (bước 5/8) | — | not_reviewed |
| INV-0008 | Thuốc F → đau cơ, phụ nữ mang thai | completed | requires_human_review | not_reviewed |
| INV-0009 | Thuốc G → phát ban | queued | — | not_reviewed |
| INV-0010 | Thuốc H → ho khan | failed (DailyMed timeout) | — | not_reviewed |
| INV-0011 | Thuốc I → chóng mặt, ≥75 tuổi | completed | contradicted_for_scope | rejected (lý do hiển thị) |

### O2. Kịch bản Timeline cho INV-0007 (phát lại bằng mock stream)
1. **B1 Tìm PubMed** — truy vấn `Glucophage lactic acidosis renal impairment` — *Lý do:* bắt đầu từ cách gọi trong nhận định — kết quả **2 tài liệu** (ít).
2. **B2 Đổi chiến lược (replan)** — *Vì sao:* ít kết quả, "Glucophage" là biệt dược → thử tên hoạt chất quốc tế — truy vấn mới `metformin AND lactic acidosis AND "renal insufficiency"` — **14 tài liệu**.
3. **B3 Chuyển nguồn sang DailyMed** — *Vì sao:* cần thông tin cảnh báo/chống chỉ định và liều theo mức lọc cầu thận — 1 nhãn, mục *Warnings* — +3 bằng chứng ủng hộ.
4. **B4 Phát hiện mâu thuẫn** — một nghiên cứu (Smith et al., minh họa) cho kết quả đối lập nhưng ở **liều 100 mg**; nhận định nêu **20 mg**.
5. **B5 Kiểm tra lệch phạm vi** — gắn `scope_mismatch`, tạo cảnh báo cam; xác định **khoảng trống**: *"Chưa có nghiên cứu ở liều ≤20 mg ở người trưởng thành."*
6. *(đang chạy)* **B6 Tìm FAERS** — "Đang tìm…" → (sau tua) **Kết luận đề xuất:** `scope_mismatch` → trạng thái `waiting_for_review`.

### O3. Ma trận bằng chứng mẫu (14 mục cho INV-0007; rút gọn)
- **Ủng hộ (5):** E1 nhãn thuốc (mục cảnh báo) · E2 báo cáo ca · E4 nghiên cứu quan sát ≥65 tuổi, 100 mg · … (một số *Scope: Lệch*).
- **Phản bác (3):** E5 nghiên cứu "Smith et al." (liều 100 mg, quần thể khác → mâu thuẫn biểu kiến) · …
- **Chưa chắc chắn (4):** E3 khớp phạm vi nhưng *không có ý nghĩa thống kê* · …
- **Nền (2):** tổng quan về cơ chế/dược động học.
Văn bản mẫu cho Quote Inspector (viết giả, 3–6 câu, có một câu được highlight) tạo cho ít nhất **6 tài liệu** (2 PubMed, 2 DailyMed, 2 FAERS).

### O4. Mẫu hồ sơ Markdown sẽ tải xuống (hiển thị trong `DossierPreview` và tab "Markdown nguồn")
```markdown
---
dossier_id: INV-0007
version: 3
status: scope_mismatch
review_state: approved
approved_by: DS. Nguyễn Minh Anh (minh họa)
approved_at: 2026-10-02T09:41:00+07:00
data_notice: Dữ liệu minh họa, không dùng cho quyết định lâm sàng
---
# Hồ sơ bằng chứng INV-0007

## 1. Nhận định chuẩn hóa
| Trường | Giá trị |
|---|---|
| Hoạt chất | metformin (đã chuẩn hóa từ "Glucophage") |
| Biến cố | nhiễm toan lactic |
| Quần thể | bệnh nhân suy thận độ 3b |
| Liều | ≥ 2.000 mg/ngày |

## 2. Kết luận phân loại (Agent đề xuất, Reviewer đã xác nhận)
**Lệch phạm vi.** Bằng chứng ủng hộ tồn tại nhưng thuộc nhóm/liều khác với nhận định. Kết luận này **không phải** kết luận nhân quả.

## 3. Chiến lược tìm kiếm
B1 PubMed → ít kết quả → B2 đổi sang tên hoạt chất → B3 DailyMed → B4 phát hiện mâu thuẫn → B5 kiểm tra phạm vi.

## 4. Bằng chứng
### Ủng hộ
- [E1] …(nguồn, phạm vi, trích dẫn nguyên văn, sha256)
### Phản bác
- [E5] …
### Chưa chắc chắn / Nền
- …

## 5. Mâu thuẫn và lệch phạm vi
## 6. Khoảng trống dữ liệu
## 7. Giới hạn
## 8. Nhật ký kiểm toán
## Phụ lục. Danh mục hash
```

### O5. Dữ liệu cho phần công khai
6 ca mẫu (mỗi trạng thái kết luận một ca) · 6 bài blog (chủ đề ở I5) · 12 mục FAQ · 20 thuật ngữ · 3 người dùng mẫu theo vai trò · 12 mục từ điển thuốc/biến cố (gồm "Glucophage → metformin") · 5 công việc nhập dữ liệu (đủ trạng thái) · 3 lần chạy evaluation (Agent vs Baseline) · 40 dòng audit.

---

## PHẦN P. VĂN PHONG & VI MÔ-COPY

**Giọng điệu:** điềm tĩnh, chính xác, tôn trọng chuyên môn; câu ngắn, động từ rõ ràng, sentence case, không sáo rỗng, không hứa hẹn quá mức, không khoa trương về AI. Nói cho người dùng biết **điều gì sẽ xảy ra** khi bấm. Lỗi và trạng thái rỗng chỉ dẫn hành động, không an ủi, không xin lỗi dài dòng.

| Chỗ | Dùng | Không dùng |
|---|---|---|
| Nút tạo | "Bắt đầu điều tra" | "Gửi", "Submit" |
| Nút duyệt | "Duyệt hồ sơ" (toast: "Đã duyệt hồ sơ") | "OK", "Xác nhận" chung chung |
| Abstain | "Thiếu bằng chứng — Agent từ chối kết luận" | "Không tìm thấy gì", "Thất bại" |
| Màu xanh | "Nhận định được ủng hộ trong phạm vi" | "An toàn", "Hợp lệ" (khi nói về thuốc) |
| Lệch phạm vi | "Bằng chứng này thuộc quần thể/liều khác với nhận định" | "Sai phạm vi" |
| AI | "AI đề xuất", "Agent đã thử…" | "AI biết rằng…", "Chắc chắn" |
| Khóa quyền | "Chỉ Reviewer được duyệt hồ sơ" | "Bạn không có quyền" trống trải |
| Lỗi nguồn | "DailyMed không phản hồi. Đã thử lại 2 lần. [Thử lại bước này]" | "Đã xảy ra lỗi" |
| Trống | "Chưa có cuộc điều tra nào. Bắt đầu bằng một nhận định." | "Oops! Không có gì ở đây" |
| Invalidation | "Cần duyệt lại do có chỉnh sửa mới" | "Hồ sơ không hợp lệ" |

**Cụm cấm (kiểm tra bằng `assertNoCausalClaim`):** "chắc chắn gây", "đã chứng minh gây", "nguyên nhân là", "an toàn tuyệt đối", "không có nguy cơ", "hoàn toàn an toàn", "thuốc này an toàn", "gây ra bởi" (khi nêu như kết luận). **Cụm nên dùng:** "được ủng hộ trong phạm vi", "chưa đủ bằng chứng", "có liên quan trong dữ liệu báo cáo (không khẳng định nhân quả)".

**Đa ngôn ngữ:** toàn bộ chuỗi giao diện đặt trong `messages/vi.json` và `messages/en.json`; giá trị enum kỹ thuật (`supported_for_scope`…) giữ nguyên tiếng Anh và hiển thị kèm nhãn tiếng Việt qua một bảng ánh xạ duy nhất `lib/labels.ts`.

---

## PHẦN Q. RESPONSIVE, TRUY CẬP, HIỆU NĂNG

- **Responsive:** thiết kế cho 360px tới 1536px. Bảng nhiều cột chuyển thành thẻ ở <768px (Ma trận bằng chứng ở mobile hiển thị thẻ có `StanceBadge`, `ScopeChip`, nút "Xem trích dẫn"). Drawer thành sheet toàn màn hình. Header dính của Màn hình 2 thu gọn thành một dòng (mã + trạng thái + budget) khi cuộn.
- **Truy cập (WCAG 2.2 AA):** tương phản ≥4.5:1 với chữ thường; focus ring 2px `--ring` luôn nhìn thấy; mọi trạng thái = màu + icon + chữ; điều hướng bàn phím đầy đủ (tab order hợp lý, focus trap trong modal/drawer, trả focus khi đóng); `aria-live` cho bước/bằng chứng mới; `role="alert"` cho Invalidation và lỗi; vùng bấm ≥44px trên mobile; bảng có `scope`, tiêu đề cột rõ; vệt highlight có thêm viền dưới (không chỉ màu nền); hỗ trợ `prefers-reduced-motion` và `prefers-contrast`.
- **Hiệu năng:** trang công khai render server, ảnh/hình là SVG/CSS; bảng dài dùng ảo hóa; `useAgentStream` gộp cập nhật theo khung hình (không re-render từng token); code-split khu `/admin` và `QuoteInspector`; mục tiêu LCP <2,5s trên trang chủ.
- **Chất lượng mã:** TypeScript strict, không `any`; component nghiệp vụ thuần theo props; mọi chuỗi qua i18n; Storybook-like ở `/dev/design-system`.

---

## PHẦN R. TIÊU CHÍ NGHIỆM THU (tự kiểm tra trước khi báo hoàn thành)

**Nội dung & điều hướng**
- [ ] Thanh điều hướng trên cùng đủ: Trang chủ, Cách hoạt động, Nguồn dữ liệu, Ca mẫu, Blog, Tài liệu ▾, Đăng nhập, CTA; mobile có menu sheet.
- [ ] Trang chủ có hero demo sống và đủ 11 section ở I1; mọi trang ở PHẦN F đều tồn tại và không 404.
- [ ] Chatbot xuất hiện đủ **3 vị trí** (nút nổi công khai, trang `/app/assistant`, ngăn "Hỏi về hồ sơ này") và có đủ 8 loại tin nhắn.
- [ ] Sidebar `/app` và `/admin` đổi đúng theo vai trò; công cụ demo role switcher hoạt động.

**3 màn hình MVP**
- [ ] Màn hình 1: form có trường bắt buộc, accordion phạm vi, nguồn, slider (mặc định 8/trần 20 và 50/trần 100), danh sách lịch sử có đủ 4 trạng thái chạy.
- [ ] Màn hình 2: Timeline chạy trực tiếp với replanning, bộ đếm ngân sách, Ma trận 4 tab, Scope Mismatch Alert, so sánh mâu thuẫn song song, Quote Inspector có highlight + hash + xác minh.
- [ ] Màn hình 3: đủ **6 huy hiệu**, 4 nút hành động có phân quyền, **Invalidation hoạt động**, Dossier Preview đủ mục, nút tải Markdown **chỉ active khi đã duyệt**.

**An toàn & minh bạch**
- [ ] Không có chỗ nào hiển thị kết luận nhân quả hoặc "an toàn tuyệt đối"; có chú giải "Xanh ≠ an toàn".
- [ ] Mọi câu bằng chứng có citation chip; Abstain được trình bày trang trọng; mọi thao tác ghi audit.
- [ ] Mọi màn dữ liệu mẫu có `DemoBanner`; không có PMID/DOI giả trông như thật.

**Chất lượng**
- [ ] Đủ các trạng thái loading/empty/error/waiting_review/approved/needs_rereview; công tắc "mô phỏng lỗi/rỗng/chậm" hoạt động.
- [ ] Light + Dark đều đạt tương phản; tiếng Việt hiển thị đúng dấu ở mọi font; responsive 360px không vỡ; focus bàn phím thấy rõ; reduced-motion được tôn trọng.
- [ ] Rà soát "dấu hiệu AI làm ra" ở G1: không eyebrow IN HOA tràn lan, không gradient trang trí, không lưới thẻ giống hệt, không nhấn một từ trong headline.

---

## PHẦN S. PROMPT KÍCH HOẠT THEO GIAI ĐOẠN (gửi lần lượt sau khi đã dán PHẦN A–R)

> Dùng khi công cụ không dựng được cả dự án trong một lượt. Mỗi giai đoạn chạy được trước khi sang giai đoạn kế.

**Giai đoạn 1 — Nền tảng**
"Thực hiện Giai đoạn 1 theo PHẦN A–H, N. Trước hết viết design plan (4–6 màu, vai trò font, concept bố cục, nguyên tắc) và tự rà soát theo A3. Sau đó dựng: dự án Next.js + Tailwind + shadcn, token màu Light/Dark, font có subset `vietnamese`, `lib/types.ts`, `lib/labels.ts`, `lib/guardrails.ts`, ba layout (Public/App/Admin), demo role switcher, toàn bộ component trong `components/pv/` (G6) và trang `/dev/design-system` bày mọi biến thể."

**Giai đoạn 2 — Website công khai**
"Thực hiện Giai đoạn 2 theo PHẦN I: trang chủ với hero demo sống và đủ section, Cách hoạt động, Nguồn dữ liệu, Ca mẫu (đủ 6 trạng thái, có phát lại), Blog, Tài liệu + Thuật ngữ, Giới hạn & an toàn AI, Về dự án, Liên hệ, FAQ, trang xác thực và trang hệ thống. Dùng nội dung thật ở PHẦN I và O5, không lorem ipsum."

**Giai đoạn 3 — Khu làm việc & 3 màn hình MVP**
"Thực hiện Giai đoạn 3 theo PHẦN K, M, O: Dashboard, Màn hình 1, **Màn hình 2** (mock agent stream cho INV-0007, Ma trận, so sánh mâu thuẫn, Quote Inspector), **Màn hình 3** (hành động Reviewer, Invalidation, Dossier Preview, xuất Markdown), Hàng chờ duyệt, Thư viện hồ sơ/tài liệu, Cài đặt/Thông báo. Cài đủ trạng thái loading/empty/error/waiting_review/approved/needs_rereview và công tắc mô phỏng."

**Giai đoạn 4 — Chatbot**
"Thực hiện Giai đoạn 4 theo PHẦN J: nút nổi trên site công khai, trang `/app/assistant`, ngăn 'Hỏi về hồ sơ này', 8 loại tin nhắn, ba hội thoại mẫu J5, lọc `assertNoCausalClaim`, liên kết citation chip với Ma trận và Quote Inspector."

**Giai đoạn 5 — Quản trị & nhập dữ liệu**
"Thực hiện Giai đoạn 5 theo PHẦN L: Tổng quan, Người dùng, Nguồn dữ liệu, **Nhập dữ liệu (wizard 4 bước + danh sách job)**, Kho tài liệu, Từ điển thuật ngữ, Cấu hình agent, Guardrail, Evaluation (Agent vs Baseline), Audit log, Quản lý nội dung, Sức khỏe hệ thống."

**Giai đoạn 6 — Hoàn thiện**
"Thực hiện Giai đoạn 6: áp dụng toàn bộ PHẦN M (vi tương tác), PHẦN Q (responsive/a11y/hiệu năng), chạy PHẦN R từng mục và báo cáo mục nào đạt/chưa đạt. Rà soát 'dấu hiệu AI làm ra' ở G1 và cắt bớt một thứ trang trí thừa."

---
*Hết super prompt. Phiên bản 1.0 — soạn cho đề tài P-066.*
