"use client";

import Link from "next/link";
import { ArrowUpRight, CircleAlert, LoaderCircle, Sparkles, UserCheck } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle, EmptyState, Progress, Skeleton } from "@/components/ui";
import { AssessmentBadge, CoverageGrid, LastReviewNote, ReviewStateBadge, RunStatusPill } from "@/components/pv/badges";
import { useInvestigations } from "@/lib/hooks/use-data";
import { useAppStore } from "@/lib/store/app-store";
import { formatRelative } from "@/lib/utils";

export default function DashboardPage() {
  const { data, isLoading, error } = useInvestigations();
  const role = useAppStore((state) => state.role);

  const items = data?.items ?? [];
  const waiting = items.filter((item) => item.runStatus === "waiting_for_review");
  const running = items.filter((item) => item.runStatus === "running" || item.runStatus === "queued");
  const abstained = items.filter((item) => item.assessment?.status === "insufficient_evidence");
  const approved = items.filter((item) => item.reviewState === "approved");

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-[26px] text-foreground">Bảng điều khiển</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">
            {role === "reviewer"
              ? "Các ca đang chờ bạn duyệt và tình trạng bằng chứng."
              : "Tình trạng các cuộc điều tra bạn đang theo dõi."}
          </p>
        </div>
        <Link
          href="/app/investigations/new"
          className="inline-flex h-10 items-center gap-2 rounded-[var(--radius-control)] bg-primary px-4 text-[14px] font-medium text-primary-foreground hover:bg-primary/90"
        >
          <Sparkles className="h-4 w-4" aria-hidden /> Điều tra mới
        </Link>
      </header>

      {data?.warning ? (
        <div className="flex items-start gap-2 rounded-[var(--radius-card)] border border-caution-border bg-caution-soft px-4 py-3 text-[13px] text-caution-fg">
          <CircleAlert className="mt-0.5 h-4 w-4" aria-hidden />
          <p>{data.warning}</p>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Chờ duyệt", value: waiting.length, icon: <UserCheck className="h-4 w-4 text-caution" aria-hidden />, hint: "Cần người quyết định" },
          { label: "Đang chạy", value: running.length, icon: <LoaderCircle className="h-4 w-4 text-ai" aria-hidden />, hint: "Agent đang tìm bằng chứng" },
          { label: "Từ chối kết luận", value: abstained.length, icon: <CircleAlert className="h-4 w-4 text-caution" aria-hidden />, hint: "Kết quả hợp lệ" },
          { label: "Đã duyệt", value: approved.length, icon: <Sparkles className="h-4 w-4 text-support" aria-hidden />, hint: "Có hồ sơ xuất được" },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <CardBody className="py-4">
              <div className="flex items-center justify-between">
                <p className="text-[13px] text-muted-foreground">{kpi.label}</p>
                {kpi.icon}
              </div>
              <div className="mt-2 font-display text-[28px] leading-none text-foreground">
                {isLoading ? <Skeleton className="h-7 w-10" /> : kpi.value}
              </div>
              <p className="mt-1.5 text-[12px] text-muted-foreground">{kpi.hint}</p>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ưu tiên hôm nay</CardTitle>
          <Link href="/app/reviews" className="text-[13px] text-muted-foreground hover:text-foreground">
            Xem hàng đợi duyệt
          </Link>
        </CardHeader>
        <CardBody className="space-y-3">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : error ? (
            <p className="text-[14px] text-contradict-fg">Không tải được danh sách: {(error as Error).message}</p>
          ) : waiting.length === 0 ? (
            <EmptyState
              title="Không có ca nào chờ duyệt"
              description="Khi agent dừng ở checkpoint, ca sẽ xuất hiện ở đây kèm lý do dừng và các khoảng trống còn lại."
            />
          ) : (
            waiting.map((item) => (
              <Link
                key={item.id}
                href={`/app/investigations/${item.id}`}
                className="block rounded-[var(--radius-card)] border border-border px-4 py-3 hover:bg-muted"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[12px] text-muted-foreground">{item.id}</span>
                  <RunStatusPill status={item.runStatus} />
                  {item.assessment ? <AssessmentBadge status={item.assessment.status} /> : null}
                  <span className="ml-auto text-[12px] text-muted-foreground">{formatRelative(item.createdAt)}</span>
                </div>
                <p className="mt-2 text-[14px] text-foreground">
                  <strong>{item.claim.drug}</strong> → {item.claim.adverseEvent}
                  {item.claim.population ? ` · ${item.claim.population}` : ""}
                </p>
                {item.assessment ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <CoverageGrid coverage={item.assessment.coverage} />
                    <ReviewStateBadge state={item.reviewState} />
                    <LastReviewNote lastReview={item.lastReview} />
                  </div>
                ) : null}
                {!item.summaryOnly ? <Progress className="mt-2" value={(item.usage.steps / item.budget.maxSteps) * 100} /> : null}
              </Link>
            ))
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Hoạt động gần đây</CardTitle>
          <Link href="/app/investigations" className="text-[13px] text-muted-foreground hover:text-foreground">
            Tất cả cuộc điều tra
          </Link>
        </CardHeader>
        <CardBody className="space-y-2">
          {items.slice(0, 6).map((item) => (
            <Link
              key={item.id}
              href={`/app/investigations/${item.id}`}
              className="flex items-center gap-3 rounded-[var(--radius-control)] px-2 py-2 hover:bg-muted"
            >
              <span className="mono w-[104px] shrink-0 text-[12px] text-muted-foreground">{item.id}</span>
              <span className="min-w-0 flex-1 truncate text-[14px] text-foreground">
                {item.claim.drug} → {item.claim.adverseEvent}
              </span>
              <ReviewStateBadge state={item.reviewState} />
              <RunStatusPill status={item.runStatus} />
              <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            </Link>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}
