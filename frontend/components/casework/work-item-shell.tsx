"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { Alert, Card, CardBody, Chip, Skeleton } from "@/components/ui";
import { cn } from "@/lib/utils";
import { useWorkflow } from "@/lib/hooks/use-casework";
import type { ReviewStatus, RunStatus, WorkStatus } from "@/lib/api/casework-types";

const tabs = [
  ["", "Tổng quan"], ["/intake", "Tiếp nhận"], ["/evidence", "Bằng chứng"], ["/response", "Phản hồi"],
  ["/review", "Duyệt"], ["/follow-ups", "Theo dõi"], ["/audit", "Nhật ký"],
] as const;

const labels: Record<string, string> = {
  draft: "Bản nháp", accepted: "Đã tiếp nhận", in_progress: "Đang xử lý", awaiting_information: "Chờ bổ sung", awaiting_review: "Chờ duyệt", completed: "Hoàn tất", cancelled: "Đã hủy",
  not_started: "Chưa chạy", queued: "Đang xếp hàng", running: "Đang chạy", waiting_for_review: "Chờ checkpoint", failed: "Lỗi", interrupted: "Gián đoạn",
  not_required: "Chưa cần duyệt", pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Đã từ chối", changes_requested: "Cần duyệt lại",
  not_assessed: "Chưa đánh giá", needs_information: "Cần thêm thông tin", reportable: "Có thể báo cáo", not_reportable: "Không báo cáo", preliminary_retrieval: "Tìm sơ bộ", scoped_analysis: "Phân tích theo phạm vi",
};

export const statusLabel = (value: WorkStatus | RunStatus | ReviewStatus | string) => labels[value] ?? value;

export function StatusSet({ work, run, review }: { work: WorkStatus; run: RunStatus; review: ReviewStatus }) {
  return <div className="flex flex-wrap gap-2" aria-label="Ba trạng thái độc lập"><Chip tone="neutral">Công việc: {statusLabel(work)}</Chip><Chip tone="ai">Lần chạy: {statusLabel(run)}</Chip><Chip tone={review === "approved" ? "support" : review === "changes_requested" || review === "rejected" ? "caution" : "neutral"}>Duyệt: {statusLabel(review)}</Chip></div>;
}

export function WorkItemShell({ children }: { children: React.ReactNode }) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname();
  const id = decodeURIComponent(params.id ?? "");
  const workflow = useWorkflow(id);
  const base = `/app/work-items/${encodeURIComponent(id)}`;
  if (workflow.isLoading) return <div className="space-y-3"><Skeleton className="h-12 w-full" /><Skeleton className="h-56 w-full" /></div>;
  if (!workflow.data) return <Card><CardBody><p role="alert">{workflow.error instanceof Error ? workflow.error.message : "Không tải được yêu cầu. Kiểm tra quyền hoặc kết nối rồi thử lại."}</p><div className="mt-3 flex gap-3"><button className="text-sm underline" onClick={() => void workflow.refetch()}>Thử lại</button><Link className="text-sm underline" href="/app/work-items">Quay lại danh sách</Link></div></CardBody></Card>;
  const item = workflow.data.work_item;
  return <div className="space-y-4">
    {workflow.error ? <Alert tone="caution" title="Không làm mới được dữ liệu">Nội dung đã tải có thể đã cũ. Tải lại trước khi duyệt hoặc xuất phản hồi. <button className="underline" onClick={() => void workflow.refetch()}>Tải lại</button></Alert> : null}
    <Link href="/app/work-items" className="text-[13px] text-muted-foreground hover:text-foreground">← Danh sách công việc</Link>
    <Card><CardBody className="space-y-3"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="mono text-[12px] text-muted-foreground">{item.id} · v{item.version} · input v{item.input_revision}</p><h1 className="mt-1 font-display text-[22px] text-foreground">{item.kind === "adr" ? "Tiếp nhận nghi ngờ ADR" : "Yêu cầu thông tin thuốc"}</h1><p className="mt-1 max-w-[85ch] text-[14px] text-muted-foreground">{item.raw_text}</p></div><StatusSet work={item.work_status} run={item.run_status} review={item.review_status} /></div><p className="text-[13px] text-muted-foreground"><strong className="text-foreground">Việc tiếp theo:</strong> {item.next_action ?? workflow.data.readiness.blockers[0] ?? "Theo dõi trạng thái yêu cầu."}</p></CardBody></Card>
    <nav className="flex overflow-x-auto border-b border-border" aria-label="Các phần của yêu cầu">{tabs.map(([suffix, label]) => { const href = `${base}${suffix}`; const active = suffix ? pathname.startsWith(href) : pathname === base; return <Link key={label} href={href} aria-current={active ? "page" : undefined} className={cn("-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-[13px]", active ? "border-foreground font-medium text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}>{label}</Link>; })}</nav>
    {children}
  </div>;
}
