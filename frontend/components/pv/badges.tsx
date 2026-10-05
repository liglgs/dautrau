"use client";

import {
  BookOpen,
  CircleAlert,
  CircleCheck,
  CircleHelp,
  CircleSlash,
  CircleX,
  Clock,
  FlaskConical,
  Hash,
  LoaderCircle,
  Minus,
  PencilLine,
  Pill,
  Plus,
  ShieldQuestion,
  Sparkles,
  TriangleAlert,
  UserCheck,
  Users,
  Utensils,
} from "lucide-react";
import { cn, formatRelative } from "@/lib/utils";
import { Chip, Tooltip } from "@/components/ui";
import type { AssessmentStatus, Claim, Cov, CoverageField, ReviewState, RunStatus, ScopeMatch, SourceId, Stance } from "@/lib/types";
import { COVERAGE_FIELD_LABEL } from "@/lib/investigation-rules";

/* ---------------------------------------------------------------------------------------
   Nhãn nghiệp vụ — mọi trạng thái = màu + icon + chữ (không chỉ dựa vào màu).
   --------------------------------------------------------------------------------------- */

const ASSESSMENT: Record<AssessmentStatus, { label: string; tone: "support" | "contradict" | "caution" | "scope" | "neutral"; icon: React.ReactNode; note: string }> = {
  supported_for_scope: {
    label: "Có bằng chứng ủng hộ trong phạm vi",
    tone: "support",
    icon: <CircleCheck className="h-3.5 w-3.5" aria-hidden />,
    note: "Màu xanh chỉ nghĩa là nhận định được bằng chứng ủng hộ — không có nghĩa thuốc an toàn.",
  },
  contradicted_for_scope: {
    label: "Có bằng chứng phản bác trong phạm vi",
    tone: "contradict",
    icon: <CircleX className="h-3.5 w-3.5" aria-hidden />,
    note: "Màu đỏ chỉ nghĩa là nhận định bị bằng chứng phản bác — không có nghĩa thuốc nguy hiểm.",
  },
  insufficient_evidence: {
    label: "Thiếu bằng chứng — Agent từ chối kết luận",
    tone: "caution",
    icon: <CircleHelp className="h-3.5 w-3.5" aria-hidden />,
    note: "Agent dừng lại vì chưa đủ căn cứ. Đây là kết quả hợp lệ, không phải lỗi.",
  },
  scope_mismatch: {
    label: "Lệch phạm vi",
    tone: "scope",
    icon: <TriangleAlert className="h-3.5 w-3.5" aria-hidden />,
    note: "Bằng chứng tìm được nằm ngoài phạm vi nhận định (quần thể, liều, đường dùng hoặc thời gian).",
  },
  out_of_scope: {
    label: "Ngoài phạm vi hệ thống",
    tone: "neutral",
    icon: <CircleSlash className="h-3.5 w-3.5" aria-hidden />,
    note: "Nhận định không thuộc nhóm được hệ thống hỗ trợ điều tra.",
  },
  requires_human_review: {
    label: "Bắt buộc chuyên viên can thiệp",
    tone: "caution",
    icon: <UserCheck className="h-3.5 w-3.5" aria-hidden />,
    note: "Có tín hiệu nhưng dữ liệu chưa đủ để bất kỳ kết luận tự động nào.",
  },
};

export function AssessmentBadge({
  status,
  size = "sm",
  className,
}: {
  status: AssessmentStatus;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const config = ASSESSMENT[status];
  const dashed = status === "insufficient_evidence";
  return (
    <Tooltip label={config.note}>
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-[var(--radius-chip)] border font-medium",
          dashed ? "border-dashed bg-transparent" : "",
          size === "sm" ? "px-2 py-0.5 text-[12px]" : size === "md" ? "px-2.5 py-1 text-[13px]" : "px-3 py-1.5 text-[14px]",
          config.tone === "support" && "border-support-border bg-support-soft text-support-fg",
          config.tone === "contradict" && "border-contradict-border bg-contradict-soft text-contradict-fg",
          config.tone === "caution" && "border-caution-border bg-caution-soft text-caution-fg",
          config.tone === "scope" && "border-scope-border bg-scope-soft text-scope-fg",
          config.tone === "neutral" && "border-neutral-border bg-neutral-soft text-neutral-fg",
          className,
        )}
      >
        {config.icon}
        {config.label}
      </span>
    </Tooltip>
  );
}

export function assessmentNote(status: AssessmentStatus) {
  return ASSESSMENT[status].note;
}

const RUN: Record<RunStatus, { label: string; tone: "ai" | "caution" | "support" | "contradict" | "neutral"; icon: React.ReactNode }> = {
  queued: { label: "Đang xếp hàng", tone: "neutral", icon: <Clock className="h-3.5 w-3.5" aria-hidden /> },
  running: { label: "Đang chạy", tone: "ai", icon: <LoaderCircle className="h-3.5 w-3.5 animate-spin-slow" aria-hidden /> },
  waiting_for_review: { label: "Chờ duyệt", tone: "caution", icon: <UserCheck className="h-3.5 w-3.5" aria-hidden /> },
  completed: { label: "Hoàn tất", tone: "support", icon: <CircleCheck className="h-3.5 w-3.5" aria-hidden /> },
  failed: { label: "Lỗi", tone: "contradict", icon: <CircleAlert className="h-3.5 w-3.5" aria-hidden /> },
  cancelled: { label: "Đã hủy", tone: "neutral", icon: <CircleAlert className="h-3.5 w-3.5" aria-hidden /> },
  interrupted: { label: "Bị gián đoạn", tone: "caution", icon: <TriangleAlert className="h-3.5 w-3.5" aria-hidden /> },
};

const RUN_FALLBACK = { label: "Không rõ trạng thái", tone: "neutral" as const, icon: null };

export function RunStatusPill({ status, className }: { status: RunStatus; className?: string }) {
  const config = RUN[status] ?? RUN_FALLBACK;
  return (
    <Chip tone={config.tone === "neutral" ? "neutral" : config.tone} className={className}>
      {config.icon}
      {config.label}
      {status === "running" ? <span className="ml-0.5 inline-block h-1.5 w-1.5 animate-breathe rounded-full bg-ai" aria-hidden /> : null}
    </Chip>
  );
}

const REVIEW: Record<ReviewState, { label: string; tone: "support" | "contradict" | "caution" | "neutral"; icon: React.ReactNode }> = {
  not_reviewed: { label: "Chưa duyệt", tone: "neutral", icon: <CircleHelp className="h-3.5 w-3.5" aria-hidden /> },
  approved: { label: "Đã duyệt", tone: "support", icon: <CircleCheck className="h-3.5 w-3.5" aria-hidden /> },
  rejected: { label: "Đã từ chối", tone: "contradict", icon: <CircleX className="h-3.5 w-3.5" aria-hidden /> },
  changes_requested: { label: "Yêu cầu chỉnh sửa", tone: "caution", icon: <PencilLine className="h-3.5 w-3.5" aria-hidden /> },
  needs_rereview: { label: "Cần duyệt lại do có chỉnh sửa mới", tone: "caution", icon: <TriangleAlert className="h-3.5 w-3.5" aria-hidden /> },
};

export function ReviewStateBadge({ state, className }: { state: ReviewState; className?: string }) {
  const config = REVIEW[state] ?? { label: "Chưa duyệt", tone: "neutral" as const, icon: null };
  return (
    <Chip tone={config.tone} className={cn("transition-colors duration-200", className)}>
      {config.icon}
      {config.label}
    </Chip>
  );
}

/** Tên checkpoint của backend, dùng cho dòng dấu vết người duyệt. */
const CHECKPOINT_LABEL: Record<string, string> = {
  normalization: "bước chuẩn hoá",
  assessment: "bước nhận định",
  dossier: "bước hồ sơ",
};

const REVIEW_ACTION_LABEL: Record<string, string> = {
  approve: "đã duyệt",
  reject: "đã từ chối",
  request_more: "đã yêu cầu tìm thêm",
  edit_claim: "đã sửa nhận định",
  edit_evidence: "đã sửa bằng chứng",
  exclude_evidence: "đã loại bằng chứng",
};

/**
 * Dấu vết quyết định của người duyệt ở bất kỳ checkpoint nào.
 *
 * ``reviewState`` chỉ nói về phiên bản hồ sơ, nên một ca bị từ chối ở bước nhận định vẫn hiện
 * "Chưa duyệt" nếu không có dòng này.
 */
export function LastReviewNote({
  lastReview,
  className,
}: {
  lastReview?: { action: string; checkpoint?: string | null; createdAt?: string };
  className?: string;
}) {
  if (!lastReview?.action) return null;
  const action = REVIEW_ACTION_LABEL[lastReview.action] ?? `đã ${lastReview.action}`;
  const checkpoint = lastReview.checkpoint ? CHECKPOINT_LABEL[lastReview.checkpoint] ?? lastReview.checkpoint : null;
  return (
    <span className={cn("text-[12px] text-muted-foreground", className)}>
      Người duyệt {action}
      {checkpoint ? ` ở ${checkpoint}` : ""}
      {lastReview.createdAt ? ` · ${formatRelative(lastReview.createdAt)}` : ""}
    </span>
  );
}

const STANCE: Record<Stance, { label: string; tone: "support" | "contradict" | "caution" | "neutral"; icon: React.ReactNode }> = {
  supporting: { label: "Ủng hộ", tone: "support", icon: <Plus className="h-3.5 w-3.5" aria-hidden /> },
  contradicting: { label: "Phản bác", tone: "contradict", icon: <Minus className="h-3.5 w-3.5" aria-hidden /> },
  uncertain: { label: "Chưa chắc chắn", tone: "caution", icon: <CircleHelp className="h-3.5 w-3.5" aria-hidden /> },
  background: { label: "Thông tin nền", tone: "neutral", icon: <BookOpen className="h-3.5 w-3.5" aria-hidden /> },
};

export function StanceBadge({ stance, className }: { stance: Stance; className?: string }) {
  const config = STANCE[stance] ?? STANCE.uncertain;
  const dashed = stance === "uncertain";
  return (
    <Chip tone={config.tone} className={cn(dashed && "border-dashed bg-transparent", className)}>
      {config.icon}
      {config.label}
    </Chip>
  );
}

const SCOPE: Record<ScopeMatch, { label: string; tone: "support" | "caution" | "scope" }> = {
  matched: { label: "Khớp phạm vi", tone: "support" },
  partial: { label: "Khớp một phần", tone: "caution" },
  mismatched: { label: "Lệch phạm vi", tone: "scope" },
};

export function ScopeChip({ scope, diffs }: { scope?: ScopeMatch; diffs?: { field: string; claim: string; evidence: string }[] }) {
  // Backend chưa trả kết luận so khớp phạm vi: hiện "chưa đối chiếu" thay vì đoán một kết luận.
  const config = scope ? SCOPE[scope] ?? SCOPE.partial : { label: "Chưa đối chiếu", tone: "neutral" as const };
  const tooltip = diffs?.length
    ? diffs.map((diff) => `${diff.field}: nhận định “${diff.claim}” ≠ bằng chứng “${diff.evidence}”`).join(" · ")
    : "Chưa đối chiếu được từng trường phạm vi với bằng chứng.";
  return (
    <Tooltip label={tooltip}>
      <Chip tone={config.tone}>{config.label}</Chip>
    </Tooltip>
  );
}

const SOURCE_META: Record<SourceId, { label: string; monogram: string; note: string }> = {
  pubmed: { label: "PubMed", monogram: "PM", note: "Y văn khoa học (PubMed)" },
  dailymed: { label: "DailyMed", monogram: "DM", note: "Nhãn thuốc do cơ quan quản lý công bố" },
  faers: { label: "openFDA FAERS", monogram: "FA", note: "Báo cáo tự nguyện — không có mẫu số, không suy ra tỷ lệ mắc" },
};

export function SourceChip({ source, className }: { source: SourceId; className?: string }) {
  const meta = SOURCE_META[source];
  return (
    <Tooltip label={meta.note}>
      <span className={cn("inline-flex items-center gap-1.5 rounded-[var(--radius-chip)] border border-border bg-card px-2 py-0.5 text-[12px] font-medium text-foreground", className)}>
        <span className="mono inline-flex h-4 w-4 items-center justify-center rounded-[3px] bg-neutral-soft text-[9px] font-semibold text-neutral-fg" aria-hidden>
          {meta.monogram}
        </span>
        {meta.label}
      </span>
    </Tooltip>
  );
}


const COV_LABEL: Record<Cov, { label: string; tone: "support" | "caution" | "contradict" | "neutral" }> = {
  verified: { label: "Đã xác minh", tone: "support" },
  partial: { label: "Một phần", tone: "caution" },
  missing: { label: "Còn thiếu", tone: "contradict" },
  not_specified: { label: "Chưa nêu", tone: "neutral" },
};

export function CoverageGrid({ coverage }: { coverage: Record<CoverageField, Cov> }) {
  const labels = COVERAGE_FIELD_LABEL;
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {(Object.keys(labels) as CoverageField[]).map((key) => {
        const cov = coverage[key];
        const meta = COV_LABEL[cov];
        return (
          <div key={key} className="rounded-[var(--radius-control)] border border-border bg-card px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{labels[key]}</dt>
            <dd className="mt-0.5">
              <Chip tone={meta.tone}>{meta.label}</Chip>
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

export function ClaimChips({ claim, className }: { claim: Claim; className?: string }) {
  const items: { icon: React.ReactNode; label: string; value?: string; missing: string }[] = [
    { icon: <Pill className="h-3.5 w-3.5" aria-hidden />, label: "Thuốc", value: claim.drug, missing: "chưa rõ thuốc" },
    { icon: <FlaskConical className="h-3.5 w-3.5" aria-hidden />, label: "Biến cố", value: claim.adverseEvent, missing: "chưa rõ biến cố" },
    { icon: <Users className="h-3.5 w-3.5" aria-hidden />, label: "Quần thể", value: claim.population, missing: "Chưa giới hạn" },
    {
      icon: <Utensils className="h-3.5 w-3.5" aria-hidden />,
      label: "Liều",
      value: claim.doseText ?? (claim.dose ? `${claim.dose.op === "=" ? "" : claim.dose.op}${claim.dose.value} ${claim.dose.unit}` : undefined),
      missing: "Chưa giới hạn",
    },
    { icon: <ShieldQuestion className="h-3.5 w-3.5" aria-hidden />, label: "Đường dùng", value: claim.route, missing: "Chưa giới hạn" },
    { icon: <Clock className="h-3.5 w-3.5" aria-hidden />, label: "Thời gian", value: claim.timeWindow, missing: "Chưa giới hạn" },
  ];
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      {items.map((item) => (
        <Tooltip key={item.label} label={item.label}>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-[var(--radius-chip)] border px-2 py-0.5 text-[12px]",
              item.value ? "border-border bg-card text-foreground" : "border-dashed border-neutral-border bg-transparent text-muted-foreground",
            )}
          >
            {item.icon}
            {item.value ?? item.missing}
          </span>
        </Tooltip>
      ))}
    </div>
  );
}

export function CitationChip({
  label,
  onClick,
  title,
}: {
  label: string;
  onClick?: () => void;
  title?: string;
}) {
  return (
    <Tooltip label={title ?? `Mở đoạn trích ${label}`}>
      <button
        type="button"
        onClick={onClick}
        className="mono inline-flex items-center rounded-[var(--radius-control)] border border-ai-border bg-ai-soft px-1.5 py-0.5 text-[11px] font-semibold text-ai-fg transition-colors hover:bg-ai/15"
      >
        [{label}]
      </button>
    </Tooltip>
  );
}

export function HashChip({
  hash,
  status = "verified",
  className,
}: {
  hash: string;
  status?: "verified" | "mismatch" | "unchecked";
  className?: string;
}) {
  const map = {
    verified: { tone: "support" as const, label: "khớp" },
    mismatch: { tone: "contradict" as const, label: "lệch" },
    unchecked: { tone: "neutral" as const, label: "chưa kiểm" },
  };
  return (
    <Tooltip label={`SHA-256 ${status === "verified" ? "khớp với bản ghi" : status === "mismatch" ? "không khớp bản ghi" : "chưa được kiểm tra"}`}>
      <span className={cn("mono inline-flex items-center gap-1 rounded-[var(--radius-chip)] border border-border bg-muted px-2 py-0.5 text-[11px] text-muted-foreground", className)}>
        <Hash className="h-3 w-3" aria-hidden />
        {hash.slice(0, 12)}…
        <span className={cn("font-semibold", map[status].tone === "support" ? "text-support-fg" : map[status].tone === "contradict" ? "text-contradict-fg" : "text-muted-foreground")}>
          {map[status].label}
        </span>
      </span>
    </Tooltip>
  );
}

export function AiSparkles({ label = "AI đề xuất" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-[var(--radius-chip)] bg-ai-soft px-2 py-0.5 text-[11px] font-semibold text-ai-fg">
      <Sparkles className="h-3 w-3" aria-hidden />
      {label}
    </span>
  );
}
