"use client";

import * as React from "react";
import Link from "next/link";
import { Search, SlidersHorizontal } from "lucide-react";
import { Button, Card, CardBody, EmptyState, Input, Select, Skeleton } from "@/components/ui";
import { AssessmentBadge, ClaimChips, CoverageGrid, ReviewStateBadge, RunStatusPill } from "@/components/pv/badges";
import { useInvestigations } from "@/lib/hooks/use-data";
import type { AssessmentStatus, RunStatus } from "@/lib/types";
import { formatRelative } from "@/lib/utils";

const RUN_FILTERS: { value: RunStatus | "all"; label: string }[] = [
  { value: "all", label: "Mọi trạng thái chạy" },
  { value: "queued", label: "Đang xếp hàng" },
  { value: "running", label: "Đang chạy" },
  { value: "waiting_for_review", label: "Chờ duyệt" },
  { value: "completed", label: "Hoàn tất" },
  { value: "failed", label: "Lỗi" },
  { value: "cancelled", label: "Đã hủy" },
  { value: "interrupted", label: "Bị gián đoạn" },
];

const ASSESSMENT_FILTERS: { value: AssessmentStatus | "all"; label: string }[] = [
  { value: "all", label: "Mọi kết luận" },
  { value: "supported_for_scope", label: "Có bằng chứng ủng hộ" },
  { value: "contradicted_for_scope", label: "Có bằng chứng phản bác" },
  { value: "insufficient_evidence", label: "Thiếu bằng chứng" },
  { value: "scope_mismatch", label: "Lệch phạm vi" },
  { value: "requires_human_review", label: "Bắt buộc chuyên viên" },
];

export default function InvestigationsPage() {
  const { data, isLoading, error } = useInvestigations();
  const [query, setQuery] = React.useState("");
  const [runFilter, setRunFilter] = React.useState<RunStatus | "all">("all");
  const [assessmentFilter, setAssessmentFilter] = React.useState<AssessmentStatus | "all">("all");

  const items = (data?.items ?? []).filter((item) => {
    const haystack = `${item.id} ${item.claim.drug} ${item.claim.adverseEvent} ${item.claim.population ?? ""}`.toLowerCase();
    if (query && !haystack.includes(query.toLowerCase())) return false;
    if (runFilter !== "all" && item.runStatus !== runFilter) return false;
    if (assessmentFilter !== "all" && item.assessment?.status !== assessmentFilter) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      {error ? <p role="alert" className="text-caution-fg">Không tải được danh sách: {error.message}</p> : null}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-[26px] text-foreground">Cuộc điều tra</h1>
          <p className="mt-1 text-[14px] text-muted-foreground">Mỗi dòng là một nhận định đã hoặc đang được kiểm chứng.</p>
        </div>
        <Link
          href="/app/investigations/new"
          className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-primary px-4 text-[14px] font-medium text-primary-foreground hover:bg-primary/90"
        >
          Điều tra mới
        </Link>
      </header>

      <Card>
        <CardBody className="flex flex-wrap items-center gap-2 py-3">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm theo mã ca, hoạt chất, biến cố…"
              className="pl-9"
              aria-label="Tìm cuộc điều tra"
            />
          </div>
          <Select value={runFilter} onChange={(event) => setRunFilter(event.target.value as RunStatus | "all")} aria-label="Lọc theo trạng thái chạy">
            {RUN_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Select
            value={assessmentFilter}
            onChange={(event) => setAssessmentFilter(event.target.value as AssessmentStatus | "all")}
            aria-label="Lọc theo kết luận"
          >
            {ASSESSMENT_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Button variant="ghost" size="sm" onClick={() => { setQuery(""); setRunFilter("all"); setAssessmentFilter("all"); }}>
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden /> Xóa lọc
          </Button>
        </CardBody>
      </Card>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="Không có cuộc điều tra nào khớp bộ lọc"
          description="Thử xóa bộ lọc, hoặc tạo một cuộc điều tra mới từ một nhận định bạn đang phải kiểm chứng."
        />
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                href={`/app/investigations/${item.id}`}
                className="block rounded-[var(--radius-card)] border border-border bg-card px-5 py-4 hover:bg-muted"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[12px] text-muted-foreground">{item.id}</span>
                  <RunStatusPill status={item.runStatus} />
                  {item.assessment ? <AssessmentBadge status={item.assessment.status} /> : null}
                  <ReviewStateBadge state={item.reviewState} />
                  <span className="ml-auto text-[12px] text-muted-foreground">
                    {item.summaryOnly ? "Mở để xem tiến trình và ngân sách" : `${item.usage.steps}/${item.budget.maxSteps} bước · ${item.usage.docs}/${item.budget.maxDocs} tài liệu`} ·{" "}
                    {formatRelative(item.createdAt)}
                  </span>
                </div>
                <div className="mt-2">
                  <ClaimChips claim={item.claim} />
                </div>
                {item.assessment ? (
                  <div className="mt-2.5 border-t border-border pt-2.5">
                    <CoverageGrid coverage={item.assessment.coverage} />
                  </div>
                ) : null}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
