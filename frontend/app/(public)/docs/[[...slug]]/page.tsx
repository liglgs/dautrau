import Link from "next/link";
import { PageHeader, Prose, Section } from "@/components/public/sections";

export const metadata = { title: "Tài liệu kỹ thuật" };

const SECTIONS = [
  { href: "/docs", label: "Tổng quan" },
  { href: "/docs/api", label: "API điều tra" },
  { href: "/docs/review", label: "Luồng duyệt" },
  { href: "/docs/dossier", label: "Định dạng hồ sơ" },
  { href: "/docs/limits", label: "Giới hạn & ngân sách" },
];

const CONTENT: Record<string, { title: string; paragraphs: string[]; code?: string }> = {
  "": {
    title: "Tổng quan",
    paragraphs: [
      "Backend FastAPI cung cấp các endpoint điều tra, bằng chứng, hồ sơ và duyệt. Giao diện này gọi các endpoint đó khi chạy ở chế độ backend thật.",
      "Đặt NEXT_PUBLIC_VIGILENS_DATA_MODE=api và VIGILENS_API_BASE trỏ tới máy chủ. Token vai trò chỉ nằm ở biến môi trường phía máy chủ; trình duyệt gọi cùng gốc /api/backend/*.",
    ],
    code: "curl -H 'X-API-Token: <token>' http://127.0.0.1:8000/api/v1/investigations",
  },
  api: {
    title: "API điều tra",
    paragraphs: [
      "Tạo cuộc điều tra trả về 202 kèm mã ca. Chạy lại một cuộc điều tra đang bận trả về 429; gửi cùng Idempotency-Key chỉ tạo một job.",
      "Danh sách, chi tiết, sự kiện, bằng chứng và tài liệu đều nằm dưới /api/v1/investigations.",
    ],
    code: "POST /api/v1/investigations\nGET  /api/v1/investigations/{id}/events?after_id=0",
  },
  review: {
    title: "Luồng duyệt",
    paragraphs: [
      "Agent dừng ở checkpoint. Người duyệt gửi quyết định qua POST /api/v1/investigations/{id}/reviews với lý do bắt buộc.",
      "Chỉ token vai trò reviewer gọi được endpoint này; token khác trả về 403.",
    ],
    code: 'POST /api/v1/investigations/{id}/reviews\n{ "action": "approve", "reason": "..." }',
  },
  dossier: {
    title: "Định dạng hồ sơ",
    paragraphs: [
      "Hồ sơ là Markdown: tóm tắt nhận định, phạm vi, bằng chứng kèm trích dẫn nguyên văn, mâu thuẫn, khoảng trống và phần duyệt.",
      "GET /export chỉ trả về khi hồ sơ đã duyệt và còn hợp lệ; nếu trích dẫn không còn khớp nguồn, máy chủ trả về 409 dossier_invalid kèm danh sách lỗi.",
    ],
    code: "GET /api/v1/investigations/{id}/export",
  },
  limits: {
    title: "Giới hạn & ngân sách",
    paragraphs: [
      "Ngân sách bước, tài liệu, lượt gọi model và token đều bị chặn ở phía máy chủ. Hết ngân sách thì hệ thống không gọi model nữa.",
      "Bản MVP chưa có endpoint hủy cuộc điều tra và chưa có xác thực theo tài khoản.",
    ],
  },
};

export default async function DocsPage({ params }: { params: Promise<{ slug?: string[] }> }) {
  const { slug } = await params;
  const key = slug?.[0] ?? "";
  const page = CONTENT[key] ?? CONTENT[""];

  return (
    <>
      <PageHeader
        breadcrumb={[{ href: "/", label: "Trang chủ" }, { href: "/docs", label: "Tài liệu" }]}
        title={page.title}
        description="Tài liệu kỹ thuật cho người tích hợp và vận hành."
      />
      <Section>
        <div className="grid gap-8 lg:grid-cols-[200px_1fr]">
          <nav aria-label="Mục tài liệu" className="space-y-1">
            {SECTIONS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={
                  "block rounded-[var(--radius-control)] px-3 py-1.5 text-[13px] " +
                  (item.href === `/docs${key ? `/${key}` : ""}` ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted")
                }
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <Prose>
            {page.paragraphs.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            {page.code ? (
              <pre className="mono overflow-x-auto rounded-[var(--radius-card)] border border-border bg-muted px-4 py-3 text-[12px] leading-relaxed text-foreground">
                {page.code}
              </pre>
            ) : null}
          </Prose>
        </div>
      </Section>
    </>
  );
}
