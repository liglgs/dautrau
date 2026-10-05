"use client";

import Link from "next/link";
import { Inbox } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle, EmptyState, Skeleton } from "@/components/ui";
import { AssessmentBadge, CoverageGrid, ReviewStateBadge, RunStatusPill } from "@/components/pv/badges";
import { useInvestigations } from "@/lib/hooks/use-data";
import { formatRelative } from "@/lib/utils";

export default function ReviewsPage() {
  const { data, isLoading } = useInvestigations();
  const items = data?.items ?? [];
  const waiting = items.filter((item) => item.runStatus === "waiting_for_review");
  const decided = items.filter((item) => item.reviewState === "approved" || item.reviewState === "rejected" || item.reviewState === "needs_rereview");

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Hàng đợi duyệt</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Agent đã dừng và đang chờ quyết định của dược sĩ lâm sàng. Không có mục nào tự động chuyển tiếp.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Chờ duyệt ({waiting.length})</CardTitle>
          <Inbox className="h-4 w-4 text-muted-foreground" aria-hidden />
        </CardHeader>
        <CardBody className="space-y-2">
          {isLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : waiting.length === 0 ? (
            <EmptyState title="Hàng đợi trống" description="Khi agent dừng ở checkpoint, ca sẽ xuất hiện ở đây kèm lý do dừng." />
          ) : (
            waiting.map((item) => (
              <Link
                key={item.id}
                href={`/app/investigations/${item.id}/review`}
                className="block rounded-[var(--radius-card)] border border-border px-4 py-3 hover:bg-muted"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[12px] text-muted-foreground">{item.id}</span>
                  <RunStatusPill status={item.runStatus} />
                  {item.assessment ? <AssessmentBadge status={item.assessment.status} /> : null}
                  <span className="ml-auto text-[12px] text-muted-foreground">{formatRelative(item.createdAt)}</span>
                </div>
                <p className="mt-2 text-[14px] text-foreground">
                  {item.claim.drug} → {item.claim.adverseEvent}
                </p>
                {item.assessment ? <CoverageGrid coverage={item.assessment.coverage} /> : null}
              </Link>
            ))
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Đã có quyết định ({decided.length})</CardTitle>
        </CardHeader>
        <CardBody className="space-y-2">
          {decided.map((item) => (
            <Link
              key={item.id}
              href={`/app/investigations/${item.id}/audit`}
              className="flex flex-wrap items-center gap-3 rounded-[var(--radius-control)] px-2 py-2 hover:bg-muted"
            >
              <span className="mono w-[104px] text-[12px] text-muted-foreground">{item.id}</span>
              <span className="min-w-0 flex-1 truncate text-[14px] text-foreground">
                {item.claim.drug} → {item.claim.adverseEvent}
              </span>
              <ReviewStateBadge state={item.reviewState} />
              <span className="text-[12px] text-muted-foreground">{item.reviewedBy ?? ""}</span>
            </Link>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
