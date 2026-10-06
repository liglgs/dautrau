"use client";

import Link from "next/link";
import { Activity, CircleAlert, Database, Users } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle, Chip, Progress } from "@/components/ui";
import { useInvestigations } from "@/lib/hooks/use-data";
import { formatNumber } from "@/lib/utils";

export default function AdminOverviewPage() {
  const { data } = useInvestigations();
  const items = data?.items ?? [];
  const tokens = items.reduce((sum, item) => sum + item.usage.tokens, 0);
  const steps = items.reduce((sum, item) => sum + item.usage.steps, 0);
  const abstained = items.filter((item) => item.assessment?.status === "insufficient_evidence").length;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Quản trị hệ thống</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Khu vực quản trị có nền tối hơn và viền trái để bạn luôn biết mình không ở khu vực làm việc thường.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Cuộc điều tra", value: formatNumber(items.length), icon: <Activity className="h-4 w-4 text-ai" aria-hidden />, hint: "Tổng số trong hệ thống" },
          { label: "Bước agent đã chạy", value: formatNumber(steps), icon: <Database className="h-4 w-4 text-ai" aria-hidden />, hint: "Trong ngân sách cho phép" },
          { label: "Token đã dùng", value: formatNumber(tokens), icon: <Activity className="h-4 w-4 text-ai" aria-hidden />, hint: "Tính trên mọi cuộc điều tra" },
          { label: "Ca từ chối kết luận", value: formatNumber(abstained), icon: <CircleAlert className="h-4 w-4 text-caution" aria-hidden />, hint: "Kết quả hợp lệ, không phải lỗi" },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <CardBody className="py-4">
              <div className="flex items-center justify-between">
                <p className="text-[13px] text-muted-foreground">{kpi.label}</p>
                {kpi.icon}
              </div>
              <p className="mt-2 font-display text-[26px] leading-none text-foreground">{kpi.value}</p>
              <p className="mt-1.5 text-[12px] text-muted-foreground">{kpi.hint}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Ngân sách đã dùng</CardTitle>
            <Chip tone="neutral">Trần cứng 20 bước · 100 tài liệu</Chip>
          </CardHeader>
          <CardBody className="space-y-3">
            {items.slice(0, 5).map((item) => (
              <div key={item.id}>
                <div className="flex items-center justify-between text-[12px] text-muted-foreground">
                  <span className="mono">{item.id}</span>
                  <span className="tabular">
                    {item.usage.steps}/{item.budget.maxSteps} bước · {item.usage.docs}/{item.budget.maxDocs} tài liệu
                  </span>
                </div>
                <Progress className="mt-1" value={(item.usage.steps / item.budget.ceilingSteps) * 100} />
              </div>
            ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Lối vào nhanh</CardTitle>
          </CardHeader>
          <CardBody className="grid gap-2 sm:grid-cols-2">
            {[
              { href: "/admin/users", label: "Người dùng & vai trò" },
              { href: "/admin/sources", label: "Nguồn dữ liệu" },
              { href: "/admin/guardrails", label: "Guardrail" },
              { href: "/admin/evaluation", label: "Đánh giá chất lượng" },
              { href: "/admin/audit", label: "Audit log" },
              { href: "/admin/system", label: "Sức khỏe hệ thống" },
            ].map((link) => (
              <Link key={link.href} href={link.href} className="rounded-[var(--radius-control)] border border-border px-3 py-2 text-[13px] hover:bg-muted">
                {link.label}
              </Link>
            ))}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Nhắc về phạm vi MVP</CardTitle>
          <Users className="h-4 w-4 text-muted-foreground" aria-hidden />
        </CardHeader>
        <CardBody className="space-y-1.5 text-[13px] text-muted-foreground">
          <p>Backend xác thực bằng token vai trò (X-API-Token) hoặc phiên đăng nhập qua POST /api/v1/auth/login; vai trò quyết định quyền duyệt hồ sơ và quyền nạp tài liệu.</p>
          <p>Cuộc điều tra đang chạy hủy được bằng POST /api/v1/investigations/&#123;id&#125;/cancel; thao tác được ghi vào nhật ký kiểm toán.</p>
          <p>Màn hình “Nạp tài liệu” và “Kho tài liệu” đã nối backend thật (kho ELT + Postgres + ChromaDB); các màn hình quản trị còn lại trình bày thiết kế cho giai đoạn sau.</p>
        </CardBody>
      </Card>
    </div>
  );
}
