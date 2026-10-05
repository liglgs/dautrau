"use client";

import * as React from "react";
import Link from "next/link";
import { Bell, CheckCheck } from "lucide-react";
import { Button, Card, CardBody, CardHeader, CardTitle, Chip, EmptyState } from "@/components/ui";
import { useInvestigations } from "@/lib/hooks/use-data";
import { formatRelative } from "@/lib/utils";

export default function NotificationsPage() {
  const { data } = useInvestigations();
  const [read, setRead] = React.useState<string[]>([]);
  const items = data?.items ?? [];

  const notifications = [
    ...items
      .filter((item) => item.runStatus === "waiting_for_review")
      .map((item) => ({
        id: `wait-${item.id}`,
        title: `${item.id} đang chờ duyệt`,
        body: `${item.claim.drug} → ${item.claim.adverseEvent}`,
        at: item.createdAt,
        href: `/app/investigations/${item.id}/review`,
        tone: "caution" as const,
      })),
    ...items
      .filter((item) => item.reviewState === "needs_rereview")
      .map((item) => ({
        id: `rereview-${item.id}`,
        title: `${item.id} cần duyệt lại`,
        body: item.invalidatedReason ?? "Bằng chứng đã thay đổi sau khi duyệt.",
        at: item.createdAt,
        href: `/app/investigations/${item.id}`,
        tone: "contradict" as const,
      })),
    ...items
      .filter((item) => item.assessment?.status === "insufficient_evidence")
      .map((item) => ({
        id: `insufficient-${item.id}`,
        title: `${item.id} thiếu bằng chứng`,
        body: "Agent từ chối kết luận và đã ghi lại các khoảng trống.",
        at: item.createdAt,
        href: `/app/investigations/${item.id}`,
        tone: "neutral" as const,
      })),
  ];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-[26px] text-foreground">Thông báo</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">Việc cần bạn chú ý, không phải luồng tin gây nhiễu.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setRead(notifications.map((item) => item.id))}>
          <CheckCheck className="h-3.5 w-3.5" aria-hidden /> Đánh dấu đã đọc
        </Button>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Đang chờ xử lý ({notifications.filter((item) => !read.includes(item.id)).length})</CardTitle>
          <Bell className="h-4 w-4 text-muted-foreground" aria-hidden />
        </CardHeader>
        <CardBody className="space-y-2">
          {notifications.length === 0 ? (
            <EmptyState title="Không có thông báo nào" description="Khi có ca chờ duyệt hoặc hồ sơ cần duyệt lại, thông báo sẽ xuất hiện ở đây." />
          ) : (
            notifications.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                onClick={() => setRead((current) => [...current, item.id])}
                className="flex items-start gap-3 rounded-[var(--radius-control)] border border-border px-4 py-3 hover:bg-muted"
              >
                <Chip tone={item.tone}>{read.includes(item.id) ? "đã đọc" : "mới"}</Chip>
                <span className="min-w-0 flex-1">
                  <span className="block text-[14px] text-foreground">{item.title}</span>
                  <span className="block text-[12px] text-muted-foreground">{item.body}</span>
                </span>
                <span className="text-[12px] text-muted-foreground">{formatRelative(item.at)}</span>
              </Link>
            ))
          )}
        </CardBody>
      </Card>
    </div>
  );
}
