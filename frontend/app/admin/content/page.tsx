"use client";

import { Card, CardBody, CardHeader, CardTitle, Chip } from "@/components/ui";
import { BRAND } from "@/lib/brand";

const PAGES = [
  { path: "/", state: "đã có", note: "Trang chủ với demo sống." },
  { path: "/how-it-works", state: "đã có", note: "Vòng lặp điều tra 6 bước." },
  { path: "/data-sources", state: "đã có", note: "Ba nguồn và giới hạn từng nguồn." },
  { path: "/limitations", state: "đã có", note: "Cam kết minh bạch." },
  { path: "/examples", state: "đã có", note: "Ca mẫu công khai." },
  { path: "/glossary", state: "đã có", note: "Thuật ngữ dùng trong sản phẩm." },
  { path: "/faq", state: "đã có", note: "Câu hỏi thường gặp." },
  { path: "/blog", state: "khung", note: "Chưa có bài viết thật." },
  { path: "/docs", state: "khung", note: "Tài liệu kỹ thuật cho nhà phát triển." },
];

export default function AdminContentPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Nội dung công khai</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Trang công khai dùng để giải thích giới hạn của hệ thống trước khi người dùng đăng nhập.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Bản sắc</CardTitle>
          <Chip tone="ai">{BRAND.name}</Chip>
        </CardHeader>
        <CardBody className="space-y-1 text-[13px] text-muted-foreground">
          <p>{BRAND.tagline}</p>
          <p>{BRAND.demoNotice}</p>
          <p>Ngôn ngữ: {BRAND.locales.join(", ")}</p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trang</CardTitle>
        </CardHeader>
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-[13px]">
            <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 pr-4">Đường dẫn</th>
                <th className="py-2 pr-4">Trạng thái</th>
                <th className="py-2">Ghi chú</th>
              </tr>
            </thead>
            <tbody>
              {PAGES.map((page) => (
                <tr key={page.path} className="border-t border-border">
                  <td className="mono py-2 pr-4 text-foreground">{page.path}</td>
                  <td className="py-2 pr-4">
                    <Chip tone={page.state === "đã có" ? "support" : "neutral"}>{page.state}</Chip>
                  </td>
                  <td className="py-2 text-muted-foreground">{page.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
