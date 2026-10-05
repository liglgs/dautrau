"use client";

import * as React from "react";
import {
  BookOpen,
  CircleHelp,
  GitBranch,
  LoaderCircle,
  RefreshCcw,
  Search,
  ShieldAlert,
  Sparkles,
  TriangleAlert,
  UserCheck,
} from "lucide-react";
import { Button, Card, Chip, EmptyState } from "@/components/ui";
import { CitationChip, SourceChip } from "@/components/pv/badges";
import { coverageFieldLabel } from "@/lib/investigation-rules";
import { useInspector } from "@/lib/store/inspector";
import type { AgentStep, EvidenceItem, StepType } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEP_META: Record<StepType, { label: string; icon: React.ReactNode; tone: string }> = {
  search: { label: "Tìm kiếm", icon: <Search className="h-3.5 w-3.5" aria-hidden />, tone: "text-ai" },
  read: { label: "Đọc tài liệu", icon: <BookOpen className="h-3.5 w-3.5" aria-hidden />, tone: "text-neutral-fg" },
  replan: { label: "Đổi truy vấn", icon: <RefreshCcw className="h-3.5 w-3.5" aria-hidden />, tone: "text-ai" },
  source_switch: { label: "Đổi nguồn", icon: <GitBranch className="h-3.5 w-3.5" aria-hidden />, tone: "text-ai" },
  contradiction_found: { label: "Phát hiện mâu thuẫn", icon: <ShieldAlert className="h-3.5 w-3.5" aria-hidden />, tone: "text-contradict" },
  scope_mismatch: { label: "Lệch phạm vi", icon: <TriangleAlert className="h-3.5 w-3.5" aria-hidden />, tone: "text-scope" },
  gap_identified: { label: "Khoảng trống bằng chứng", icon: <CircleHelp className="h-3.5 w-3.5" aria-hidden />, tone: "text-caution" },
  reviewer_request: { label: "Chờ reviewer", icon: <UserCheck className="h-3.5 w-3.5" aria-hidden />, tone: "text-caution" },
  human_review: { label: "Quyết định người duyệt", icon: <UserCheck className="h-3.5 w-3.5" aria-hidden />, tone: "text-support" },
  assess: { label: "Đánh giá tạm thời", icon: <Sparkles className="h-3.5 w-3.5" aria-hidden />, tone: "text-neutral-fg" },
  dossier: { label: "Tạo hồ sơ", icon: <BookOpen className="h-3.5 w-3.5" aria-hidden />, tone: "text-neutral-fg" },
  conclude: { label: "Kết luận trong phạm vi", icon: <Sparkles className="h-3.5 w-3.5" aria-hidden />, tone: "text-support" },
  abstain: { label: "Từ chối kết luận", icon: <CircleHelp className="h-3.5 w-3.5" aria-hidden />, tone: "text-caution" },
};

export function AgentTimeline({
  investigationId,
  steps,
  evidence,
  onReplay,
  playing,
}: {
  investigationId: string;
  steps: AgentStep[];
  evidence: EvidenceItem[];
  onReplay?: () => void;
  playing?: boolean;
}) {
  const openInspector = useInspector((state) => state.open);
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [steps.length]);

  if (steps.length === 0) {
    return <EmptyState title="Chưa có bước nào" description="Agent sẽ hiện từng bước suy luận tại đây khi cuộc điều tra bắt đầu." />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[13px] text-muted-foreground">
          {steps.length} bước · mỗi bước đều có lý do (rationale) và kết quả
        </p>
        {onReplay ? (
          <Button variant="ghost" size="sm" onClick={onReplay} disabled={playing}>
            <RefreshCcw className={cn("h-3.5 w-3.5", playing && "animate-spin-slow")} aria-hidden />
            {playing ? "Đang phát lại" : "Phát lại"}
          </Button>
        ) : null}
      </div>

      <ol className="relative space-y-3 border-l border-border pl-5">
        {steps.map((step) => {
          const meta = STEP_META[step.type];
          const stepEvidence = evidence.filter((item) => item.foundAtStep === step.index);
          // Backend chưa gắn bằng chứng với bước, nên danh sách này thường rỗng ở chế độ API.
          return (
            <li key={step.index} className="relative">
              <span className="absolute -left-[26px] top-3 flex h-4 w-4 items-center justify-center rounded-full border border-border bg-card text-[9px] text-muted-foreground">
                {step.index}
              </span>
              <Card className={cn("px-4 py-3", step.status === "running" && "border-ai-border bg-ai-soft/40")}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn("inline-flex items-center gap-1.5 text-[13px] font-semibold", meta.tone)}>
                    {step.status === "running" ? <LoaderCircle className="h-3.5 w-3.5 animate-spin-slow" aria-hidden /> : meta.icon}
                    {meta.label}
                  </span>
                  {step.source ? <SourceChip source={step.source} /> : null}
                  {step.prevQuery ? (
                    <span className="mono text-[11px] text-muted-foreground line-through">{step.prevQuery}</span>
                  ) : null}
                  {step.query ? <span className="mono text-[12px] text-foreground">{step.query}</span> : null}
                  <span className="tabular ml-auto text-[11px] text-muted-foreground">
                    {step.docsFound ? `${step.docsFound} tài liệu` : ""}
                    {step.newDocs ? ` · ${step.newDocs} mới` : ""}
                    {step.tokens ? ` · ${step.tokens.toLocaleString("vi-VN")} token` : ""}
                  </span>
                </div>
                <p className="mt-2 text-[13px] leading-relaxed text-foreground">
                  <span className="font-medium text-muted-foreground">Lý do: </span>
                  {step.rationale}
                </p>
                {step.resultSummary ? (
                  <p className="mt-1 text-[13px] text-muted-foreground">
                    <span className="font-medium">Kết quả: </span>
                    {step.resultSummary}
                  </p>
                ) : null}
                {stepEvidence.length > 0 ? (
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span className="text-[12px] text-muted-foreground">Bằng chứng:</span>
                    {stepEvidence.map((item) => (
                      <CitationChip
                        key={item.id}
                        label={item.label}
                        title={item.quotes[0]?.text.slice(0, 120)}
                        onClick={() => openInspector({ investigationId, evidence: item })}
                      />
                    ))}
                  </div>
                ) : null}
              </Card>
            </li>
          );
        })}
      </ol>
      <div ref={bottomRef} />
    </div>
  );
}

export function BudgetMeter({
  steps,
  maxSteps,
  docs,
  maxDocs,
  tokens,
  compact = false,
}: {
  steps: number;
  maxSteps: number;
  docs: number;
  maxDocs: number;
  tokens: number;
  compact?: boolean;
}) {
  const items = [
    { label: "Bước", used: steps, max: maxSteps },
    { label: "Tài liệu", used: docs, max: maxDocs },
  ];
  if (compact) {
    return (
      <div className="flex items-center gap-3 text-[12px] text-muted-foreground">
        {items.map((item) => (
          <span key={item.label} className="tabular">
            {item.label} {item.used}/{item.max}
          </span>
        ))}
        <span className="tabular">Token {tokens.toLocaleString("vi-VN")}</span>
      </div>
    );
  }
  return (
    <Card className="px-4 py-3">
      <p className="text-[13px] font-semibold text-foreground">Ngân sách điều tra</p>
      <div className="mt-3 space-y-3">
        {items.map((item) => {
          const pct = Math.round((item.used / item.max) * 100);
          return (
            <div key={item.label}>
              <div className="flex items-center justify-between text-[12px]">
                <span className="text-muted-foreground">{item.label}</span>
                <span className="tabular text-foreground">
                  {item.used}/{item.max}
                </span>
              </div>
              <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div className={cn("h-full rounded-full", pct > 85 ? "bg-caution" : "bg-ai")} style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-muted-foreground">Token đã dùng</span>
          <span className="tabular text-foreground">{tokens.toLocaleString("vi-VN")}</span>
        </div>
      </div>
      <p className="mt-3 text-[11px] text-muted-foreground">
        Agent dừng khi hết ngân sách hoặc khi bằng chứng bão hoà; luôn giữ lại một bước cho hồ sơ.
      </p>
    </Card>
  );
}

export function GapList({
  gaps,
  onRequestMore,
  canRequestMore,
}: {
  gaps: { id: string; kind?: string; description: string; tried: string[]; relatedField: string }[];
  onRequestMore?: (gapId: string) => void;
  canRequestMore?: boolean;
}) {
  if (gaps.length === 0) {
    return <p className="text-[13px] text-muted-foreground">Không có khoảng trống bằng chứng nào được ghi nhận.</p>;
  }
  return (
    <ul className="space-y-2">
      {gaps.map((gap) => (
        <li key={gap.id} className="rounded-[var(--radius-card)] border border-caution-border bg-caution-soft px-3 py-2">
          {gap.kind === "contradiction" ? <p className="text-[12px] font-semibold text-caution-fg">Mâu thuẫn cần người duyệt đối chiếu</p> : null}
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[13px] font-medium text-caution-fg">{gap.description}</p>
              {gap.tried.length > 0 ? (
                <p className="mono mt-1 text-[11px] text-caution-fg/80">Đã thử: {gap.tried.join(" · ")}</p>
              ) : null}
            </div>
            {gap.relatedField ? (
              <Chip tone="caution">{coverageFieldLabel(gap.relatedField)}</Chip>
            ) : null}
          </div>
          {canRequestMore && onRequestMore ? (
            <Button variant="secondary" size="sm" className="mt-2" onClick={() => onRequestMore(gap.id)}>
              Yêu cầu tìm thêm
            </Button>
          ) : null}
          {!canRequestMore ? (
            <p className="mt-2 text-[12px] text-muted-foreground">
              Chỉ dược sĩ duyệt mới gửi được yêu cầu tìm thêm, ở tab Duyệt.
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
