"use client";

import * as React from "react";
import { FileText, Search } from "lucide-react";
import { Card, CardBody, EmptyState, Input, Select } from "@/components/ui";
import { HashChip, SourceChip } from "@/components/pv/badges";
import { useEvidence, useInvestigations, useTimeline } from "@/lib/hooks/use-data";
import { getDataSource } from "@/lib/api";
import { safeSourceUrl } from "@/lib/evidence-view";
import { useQuery } from "@tanstack/react-query";
import { formatDateTime } from "@/lib/utils";
import type { DocumentRecord, SourceId } from "@/lib/types";

export default function LibraryPage() {
  const { data } = useInvestigations();
  const [selected, setSelected] = React.useState<string>("");
  const [query, setQuery] = React.useState("");
  const [sourceFilter, setSourceFilter] = React.useState<SourceId | "all">("all");

  const first = data?.items?.[0]?.id ?? "";
  const investigationId = selected || first;
  const { data: timeline } = useTimeline(investigationId);
  const { data: evidence } = useEvidence(investigationId);

  // Chế độ minh hoạ gắn tài liệu vào bước; chế độ API lấy từ danh sách bằng chứng.
  const docIds = React.useMemo(() => {
    const ids = new Set<string>();
    (timeline?.steps ?? []).forEach((step) => step.docIds?.forEach((docId) => ids.add(docId)));
    (evidence ?? []).forEach((item) => {
      if (item.docId) ids.add(item.docId);
    });
    return [...ids];
  }, [timeline, evidence]);

  const { data: documents = [] } = useQuery({
    queryKey: ["library-documents", investigationId, docIds.join(",")],
    queryFn: async () => {
      const source = getDataSource();
      const found = await Promise.all(docIds.map((docId) => source.getDocument(investigationId, docId)));
      return found.filter((item): item is DocumentRecord => Boolean(item));
    },
    enabled: Boolean(investigationId) && docIds.length > 0,
  });

  const filtered = documents.filter((document) => {
    if (sourceFilter !== "all" && document.source !== sourceFilter) return false;
    if (query && !`${document.title} ${document.id} ${document.url ?? ""}`.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Thư viện tài liệu</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Tài liệu đã dùng trong các cuộc điều tra, kèm hash và nguồn gốc. Bấm vào tài liệu để xem nguyên văn.
        </p>
      </header>

      <Card>
        <CardBody className="flex flex-wrap items-center gap-2 py-3">
          <Select value={investigationId} onChange={(event) => setSelected(event.target.value)} aria-label="Chọn cuộc điều tra">
            {(data?.items ?? []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.id} · {item.claim.drug}
              </option>
            ))}
          </Select>
          <div className="relative min-w-[200px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm tài liệu…" className="pl-9" aria-label="Tìm tài liệu" />
          </div>
          <Select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value as SourceId | "all")} aria-label="Lọc theo nguồn">
            <option value="all">Mọi nguồn</option>
            <option value="pubmed">PubMed</option>
            <option value="dailymed">DailyMed</option>
            <option value="faers">openFDA FAERS</option>
          </Select>
        </CardBody>
      </Card>

      {filtered.length === 0 ? (
        <EmptyState
          title="Chưa có tài liệu nào"
          description="Chọn một cuộc điều tra đã chạy để xem các tài liệu agent đã đọc."
        />
      ) : (
        <ul className="space-y-2">
          {filtered.map((document) => {
            // Chỉ hiển thị và mở URL nguồn khi vượt qua bộ lọc an toàn (https + tên miền nguồn đã biết).
            const safeUrl = safeSourceUrl(document.url);
            return (
              <li key={document.id} className="rounded-[var(--radius-card)] border border-border bg-card px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <SourceChip source={document.source} />
                  <span className="mono text-[12px] text-muted-foreground">{document.id}</span>
                  <span className="ml-auto text-[12px] text-muted-foreground">{formatDateTime(document.retrievedAt)}</span>
                </div>
                <p className="mt-1.5 flex items-center gap-2 text-[14px] text-foreground">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground" aria-hidden /> {document.title}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px] text-muted-foreground">
                  <span className="mono">{safeUrl ?? document.id}</span>
                  <HashChip hash={document.sha256} status={document.hashStatus} />
                  {safeUrl ? (
                    <a href={safeUrl} target="_blank" rel="noreferrer" className="underline">
                      Mở nguồn gốc
                    </a>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
