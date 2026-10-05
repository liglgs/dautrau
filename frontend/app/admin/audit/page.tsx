"use client";

import * as React from "react";
import { Bot, User } from "lucide-react";
import { Button, Card, CardBody, CardHeader, CardTitle, Chip, Input } from "@/components/ui";
import { DEMO_AUDIT } from "@/lib/mock/seed";
import { formatDateTime } from "@/lib/utils";
import type { AuditEntry } from "@/lib/types";

export default function AdminAuditPage() {
  const [query, setQuery] = React.useState("");
  const [onlyHuman, setOnlyHuman] = React.useState(false);

  const entries: (AuditEntry & { investigationId: string })[] = Object.entries(DEMO_AUDIT).flatMap(([investigationId, list]) =>
    list.map((entry) => ({ ...entry, investigationId })),
  );

  const filtered = entries
    .filter((entry) => (onlyHuman ? entry.actor.kind === "human" : true))
    .filter((entry) => (query ? `${entry.action} ${entry.target ?? ""} ${entry.actor.name}`.toLowerCase().includes(query.toLowerCase()) : true))
    .sort((a, b) => (a.at < b.at ? 1 : -1));

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Audit log toàn hệ thống</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Nhật ký chỉ ghi thêm. Mỗi bản ghi có người thực hiện, hành động, đối tượng và lý do.
        </p>
      </header>

      <Card>
        <CardBody className="flex flex-wrap items-center gap-2 py-3">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Tìm theo hành động, đối tượng hoặc người thực hiện…"
            aria-label="Tìm trong audit log"
          />
          <Button variant="ghost" size="sm" onClick={() => setOnlyHuman((value) => !value)}>
            {onlyHuman ? "Hiện tất cả" : "Chỉ thao tác người"}
          </Button>
          <Button variant="outline" size="sm" disabled>
            Kết xuất JSONL
          </Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{filtered.length} bản ghi</CardTitle>
          <Chip tone="caution">Dữ liệu minh họa</Chip>
        </CardHeader>
        <CardBody>
          <ol className="space-y-2">
            {filtered.map((entry) => (
              <li key={entry.id} className="flex items-start gap-3 rounded-[var(--radius-control)] border border-border px-3 py-2.5">
                <span className="mt-0.5 text-muted-foreground">
                  {entry.actor.kind === "ai" ? <Bot className="h-4 w-4 text-ai" aria-hidden /> : <User className="h-4 w-4" aria-hidden />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="mono text-[11px] text-muted-foreground">{entry.investigationId}</span>
                    <span className="text-[13px] font-medium text-foreground">{entry.action}</span>
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
        </CardBody>
      </Card>
    </div>
  );
}
