"use client";

import Link from "next/link";
import { Chip, EmptyState, Skeleton } from "@/components/ui";
import { StatusSet } from "@/components/casework/work-item-shell";
import { useWorkItems } from "@/lib/hooks/use-casework";

export default function WorkItemsPage() {
  const { data, isLoading, error } = useWorkItems();
  return <div className="space-y-4"><header className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="font-display text-[26px] text-foreground">Công việc</h1><p className="mt-1 text-[14px] text-muted-foreground">Tiếp nhận, bằng chứng, phản hồi và duyệt độc lập theo cùng một hồ sơ.</p></div><Link href="/app/work-items/new" className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-primary px-4 text-sm font-medium text-primary-foreground">Tiếp nhận mới</Link></header>{error ? <p role="alert" className="text-contradict-fg">Không tải được danh sách: {error.message}</p> : null}{isLoading ? <div className="space-y-2"><Skeleton className="h-24 w-full" /><Skeleton className="h-24 w-full" /></div> : !(data?.items.length) ? <EmptyState title="Chưa có hồ sơ công việc" description="Tạo yêu cầu thông tin thuốc hoặc tiếp nhận nghi ngờ ADR từ câu mô tả nguyên văn." action={<Link href="/app/work-items/new" className="text-sm underline">Tiếp nhận mới</Link>} /> : <ul className="space-y-2">{data.items.map((item) => <li key={item.id}><Link href={`/app/work-items/${encodeURIComponent(item.id)}`} className="block rounded-[var(--radius-card)] border border-border bg-card p-4 hover:bg-muted"><div className="flex flex-wrap items-center gap-2"><span className="mono text-[12px] text-muted-foreground">{item.id}</span><Chip tone={item.kind === "adr" ? "caution" : "ai"}>{item.kind === "adr" ? "ADR" : "Thông tin thuốc"}</Chip><span className="ml-auto text-[12px] text-muted-foreground">{item.next_action ?? "Mở để xem việc tiếp theo"}</span></div><p className="mt-2 line-clamp-2 text-[14px] text-foreground">{item.raw_text}</p><div className="mt-3"><StatusSet work={item.work_status} run={item.run_status} review={item.review_status} /></div></Link></li>)}</ul>}</div>;
}
