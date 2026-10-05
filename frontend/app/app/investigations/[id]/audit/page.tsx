"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Bot, Download, User } from "lucide-react";
import { Button, Card, CardBody, Chip, EmptyState, Skeleton } from "@/components/ui";
import { useAudit } from "@/lib/hooks/use-data";
import { formatDateTime } from "@/lib/utils";

const ACTOR_LABEL = { human: "Người", ai: "AI", system: "Hệ thống" } as const;

export default function AuditTabPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id ?? "");
  const { data, isLoading } = useAudit(id);
  const [onlyHuman, setOnlyHuman] = React.useState(false);

  const entries = (data ?? []).filter((entry) => (onlyHuman ? entry.actor.kind === "human" : true));

  /** Kết xuất JSONL phía máy khách: mỗi dòng một bản ghi của nhật ký đang hiển thị. */
  const exportJsonl = () => {
    if (!entries.length) return;
    const jsonl = `${entries.map((entry) => JSON.stringify(entry)).join("\n")}\n`;
    const blob = new Blob([jsonl], { type: "application/x-ndjson;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${id}-audit.jsonl`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-[15px] font-semibold text-foreground">Nhật ký kiểm toán</h2>
            <p className="mt-1 text-[12px] text-muted-foreground">Chỉ ghi thêm, không sửa. Mọi thao tác của người và AI đều ở đây.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setOnlyHuman((value) => !value)}>
              {onlyHuman ? "Hiện tất cả" : "Chỉ thao tác người"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={exportJsonl}
              disabled={entries.length === 0}
              title="Tải nhật ký đang hiển thị dưới dạng JSONL"
            >
              <Download className="h-3.5 w-3.5" aria-hidden /> Kết xuất JSONL
            </Button>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : entries.length === 0 ? (
          <EmptyState title="Chưa có bản ghi nào" description="Nhật ký sẽ đầy lên khi agent chạy và khi người duyệt ra quyết định." />
        ) : (
          <ol className="space-y-2">
            {entries.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 rounded-[var(--radius-control)] border border-border px-3 py-2.5">
                <span className="mt-0.5 text-muted-foreground">
                  {entry.actor.kind === "ai" ? <Bot className="h-4 w-4 text-ai" aria-hidden /> : <User className="h-4 w-4" aria-hidden />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13px] font-medium text-foreground">{entry.action}</span>
                    <Chip tone={entry.actor.kind === "ai" ? "ai" : "neutral"}>{ACTOR_LABEL[entry.actor.kind]}</Chip>
                    {entry.target ? <span className="mono text-[11px] text-muted-foreground">{entry.target}</span> : null}
                    <span className="ml-auto text-[11px] text-muted-foreground">{formatDateTime(entry.at)}</span>
                  </div>
                  <p className="mt-1 text-[12px] text-muted-foreground">
                    {entry.actor.name}
                    {entry.reason ? ` — ${entry.reason}` : ""}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  );
}
