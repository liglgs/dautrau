"use client";

import Link from "next/link";
import { Download, FileText } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle, EmptyState, Skeleton } from "@/components/ui";
import { ReviewStateBadge, RunStatusPill } from "@/components/pv/badges";
import { useInvestigations } from "@/lib/hooks/use-data";
import { formatRelative } from "@/lib/utils";

export default function DossiersPage() {
  const { data, isLoading } = useInvestigations();
  const items = (data?.items ?? []).filter((item) => item.runStatus === "completed" || item.runStatus === "waiting_for_review");

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Hồ sơ</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Hồ sơ chỉ xuất được khi đã duyệt và mọi trích dẫn còn khớp nguyên văn tài liệu nguồn.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Hồ sơ khả dụng ({items.length})</CardTitle>
          <FileText className="h-4 w-4 text-muted-foreground" aria-hidden />
        </CardHeader>
        <CardBody className="space-y-2">
          {isLoading ? (
            <Skeleton className="h-16 w-full" />
          ) : items.length === 0 ? (
            <EmptyState title="Chưa có hồ sơ nào" description="Hoàn tất một cuộc điều tra để tạo hồ sơ đầu tiên." />
          ) : (
            items.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center gap-3 rounded-[var(--radius-card)] border border-border px-4 py-3">
                <span className="mono w-[104px] text-[12px] text-muted-foreground">{item.id}</span>
                <span className="min-w-0 flex-1 truncate text-[14px] text-foreground">
                  {item.claim.drug} → {item.claim.adverseEvent}
                </span>
                <RunStatusPill status={item.runStatus} />
                <ReviewStateBadge state={item.reviewState} />
                <span className="text-[12px] text-muted-foreground">{formatRelative(item.createdAt)}</span>
                <Link
                  href={`/app/investigations/${item.id}/dossier`}
                  className="inline-flex items-center gap-1.5 rounded-[var(--radius-control)] border border-input px-2.5 py-1 text-[12px] hover:bg-muted"
                >
                  <Download className="h-3 w-3" aria-hidden /> Mở hồ sơ
                </Link>
              </div>
            ))
          )}
        </CardBody>
      </Card>
    </div>
  );
}
