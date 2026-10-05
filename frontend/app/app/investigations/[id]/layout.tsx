"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { ArrowLeft, CircleAlert, Download, LoaderCircle, Play, RotateCcw } from "lucide-react";
import { Button, Card, CardBody, Chip, Skeleton } from "@/components/ui";
import { AssessmentBadge, ClaimChips, CoverageGrid, LastReviewNote, ReviewStateBadge, RunStatusPill, assessmentNote } from "@/components/pv/badges";
import { BudgetMeter } from "@/components/pv/agent-timeline";
import { useContinueRun, useExportDossier, useInvestigation } from "@/lib/hooks/use-data";
import { useAppStore } from "@/lib/store/app-store";
import { cn, downloadMarkdown, formatDateTime } from "@/lib/utils";
import { canContinueRun } from "@/lib/investigation-rules";

const TABS = [
  { href: "", label: "Tổng quan" },
  { href: "/evidence", label: "Ma trận bằng chứng" },
  { href: "/dossier", label: "Hồ sơ" },
  { href: "/review", label: "Duyệt" },
  { href: "/audit", label: "Nhật ký" },
];

export default function InvestigationLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const id = decodeURIComponent(params.id ?? "");
  const { data, isLoading, error } = useInvestigation(id);
  const continueRun = useContinueRun(id);
  const exportDossier = useExportDossier(id);
  const role = useAppStore((state) => state.role);
  const [exportError, setExportError] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  const base = `/app/investigations/${encodeURIComponent(id)}`;

  const handleExport = () => {
    if (error || data?.reviewState !== "approved" || exportDossier.isPending) return;
    setExportError(null);
    exportDossier.mutate(undefined, {
      onSuccess: (result) => {
        if (!result.ok || !result.markdown) {
          setExportError(result.message ?? "Chưa xuất được hồ sơ.");
          return;
        }
        downloadMarkdown(result.markdown, `${id}-dossier.md`);
      },
      onError: (mutationError) => setExportError((mutationError as Error).message),
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardBody className="space-y-2">
          <p className="flex items-center gap-2 text-[15px] text-contradict-fg">
            <CircleAlert className="h-4 w-4" aria-hidden /> Không tìm thấy cuộc điều tra {id}
          </p>
          <p className="text-[13px] text-muted-foreground">{(error as Error | null)?.message ?? "Cuộc điều tra có thể đã bị xóa hoặc mã không đúng."}</p>
          <Link href="/app/investigations" className="text-[13px] underline">
            Quay lại danh sách
          </Link>
        </CardBody>
      </Card>
    );
  }

  const canContinue = canContinueRun(data, role);

  return (
    <div className="space-y-4">
      {error ? <p role="alert" className="text-[13px] text-caution-fg">Không làm mới được trạng thái: {error.message} Nội dung đã tải được giữ lại.</p> : null}
      {continueRun.data && !continueRun.data.ok ? <p role="alert" className="text-[13px] text-contradict-fg">{continueRun.data.message}</p> : null}
      <div className="flex items-center gap-3">
        <Link href="/app/investigations" className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Danh sách
        </Link>
        <span className="mono text-[12px] text-muted-foreground">{id}</span>
        <Chip tone="neutral">v{data.version}</Chip>
      </div>

      <Card>
        <CardBody className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <RunStatusPill status={data.runStatus} />
                {data.assessment ? <AssessmentBadge status={data.assessment.status} size="md" /> : null}
                <ReviewStateBadge state={data.reviewState} />
                {data.reviewedBy ? (
                  <span className="text-[12px] text-muted-foreground">
                    {data.reviewedBy} · {data.reviewedAt ? formatDateTime(data.reviewedAt) : ""}
                  </span>
                ) : null}
              </div>
              <p className="mt-2 font-display text-[20px] leading-snug text-foreground">
                {data.claim.drug} → {data.claim.adverseEvent}
              </p>
              {data.claim.rawText ? <p className="mt-1 max-w-[80ch] text-[13px] text-muted-foreground">“{data.claim.rawText}”</p> : null}
              {data.invalidatedReason ? (
                <p className="mt-2 flex items-start gap-2 text-[13px] text-caution-fg">
                  <RotateCcw className="mt-0.5 h-3.5 w-3.5" aria-hidden /> {data.invalidatedReason}
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {canContinue ? (
                <Button variant="secondary" onClick={() => continueRun.mutate()} disabled={continueRun.isPending}>
                  {continueRun.isPending ? <LoaderCircle className="h-4 w-4 animate-spin-slow" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
                  Tiếp tục chạy
                </Button>
              ) : null}
              <Button variant="outline" onClick={handleExport} disabled={Boolean(error) || exportDossier.isPending || data.reviewState !== "approved"}>
                <Download className="h-4 w-4" aria-hidden /> Xuất Markdown
              </Button>
              <Button
                variant="ghost"
                onClick={async () => {
                  await navigator.clipboard.writeText(window.location.href);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
              >
                {copied ? "Đã sao chép" : "Chia sẻ liên kết"}
              </Button>
            </div>
          </div>

          <div className="border-t border-border pt-3">
            <ClaimChips claim={data.claim} />
          </div>

          {data.assessment ? (
            <div className="space-y-2 border-t border-border pt-3">
              <p className="max-w-[92ch] text-[14px] leading-relaxed text-foreground">{data.assessment.rationale}</p>
              <p className="text-[12px] text-muted-foreground">{assessmentNote(data.assessment.status)}</p>
              {data.reviewState === "not_reviewed" ? <LastReviewNote lastReview={data.lastReview} /> : null}
              <CoverageGrid coverage={data.assessment.coverage} />
              <p className="text-[12px] text-muted-foreground">
                Mức phủ được suy ra từ nhận định đã chuẩn hoá và các trường còn `unknown`; không phải kết luận về chất
                lượng bằng chứng.
              </p>
            </div>
          ) : null}

          <div className="grid gap-3 border-t border-border pt-3 sm:grid-cols-2">
            <BudgetMeter steps={data.usage.steps} maxSteps={data.budget.maxSteps} docs={data.usage.docs} maxDocs={data.budget.maxDocs} tokens={data.usage.tokens} />
            <div className="text-[12px] text-muted-foreground">
              <p>
                {data.createdBy ? `Tạo bởi ${data.createdBy} · ` : "Tạo lúc "}
                {formatDateTime(data.createdAt)}
              </p>
              <p className="mt-1">
                {data.sources.length ? `Nguồn đã tìm: ${data.sources.join(", ")}` : "Chưa tìm nguồn nào"}
                {` · ${data.usage.tokens.toLocaleString("vi-VN")} token`}
              </p>
            </div>
          </div>

          {exportError ? <p className="text-[13px] text-contradict-fg">{exportError}</p> : null}
          {continueRun.isError ? <p className="text-[13px] text-contradict-fg">{(continueRun.error as Error).message}</p> : null}
        </CardBody>
      </Card>

      <nav className="flex flex-wrap gap-1 border-b border-border" aria-label="Các phần của cuộc điều tra">
        {TABS.map((tab) => {
          const href = `${base}${tab.href}`;
          const active = tab.href === "" ? pathname === base : pathname.startsWith(href);
          return (
            <Link
              key={tab.label}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "-mb-px border-b-2 px-3 py-2 text-[14px]",
                active ? "border-foreground font-medium text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}
