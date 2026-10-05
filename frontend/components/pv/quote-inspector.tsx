"use client";

import * as React from "react";
import Link from "next/link";
import { ExternalLink, Quote, X } from "lucide-react";
import { Button, Chip, Separator } from "@/components/ui";
import { HashChip, ScopeChip, SourceChip, StanceBadge } from "@/components/pv/badges";
import { useInspector } from "@/lib/store/inspector";
import type { DocumentRecord } from "@/lib/types";
import { getDataSource } from "@/lib/api";
import { quoteSegments, safeSourceUrl } from "@/lib/evidence-view";

/**
 * Quote Inspector — drawer 640px (mobile: toàn màn hình).
 * Nguyên tắc: mọi câu bằng chứng đều bấm được và mở đúng đoạn trích trong văn bản gốc.
 */
export function QuoteInspector() {
  const { target, close } = useInspector();
  const [document, setDocument] = React.useState<DocumentRecord | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!target) return;
    let cancelled = false;
    setLoading(true);
    setDocument(null);
    setError(null);
    getDataSource()
      .getDocument(target.investigationId, target.evidence.docId)
      .then((value) => { if (!cancelled) setDocument(value); })
      .catch((cause) => { if (!cancelled) setError((cause as Error).message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [target]);

  React.useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  if (!target) return null;
  const { evidence } = target;
  const quote = evidence.quotes[target.quoteIndex ?? 0] ?? evidence.quotes[0];
  const text = document?.text ?? "";
  const segments = quote ? quoteSegments(text, quote) : null;
  const sourceUrl = safeSourceUrl(document?.url);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Trình xem trích dẫn">
      <button className="absolute inset-0 bg-foreground/20 backdrop-blur-[1px]" onClick={close} aria-label="Đóng trình xem trích dẫn" />
      <div className="relative flex h-full w-full max-w-[640px] flex-col border-l border-border bg-card hairline-shadow">
        <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Trích dẫn {evidence.label}</p>
            <h2 className="mt-1 truncate text-[16px] font-semibold text-foreground">{evidence.title}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <SourceChip source={evidence.source} />
              <StanceBadge stance={evidence.stance} />
              <ScopeChip scope={evidence.scope} diffs={evidence.scopeDiffs} />
              <Chip tone="neutral">{evidence.externalId}</Chip>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={close} aria-label="Đóng">
            <X className="h-4 w-4" aria-hidden />
          </Button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {evidence.editedByReviewer ? (
            <div className="mb-4 rounded-[var(--radius-card)] border border-caution-border bg-caution-soft px-3 py-2 text-[12px] text-caution-fg">
              Reviewer {evidence.editedByReviewer.by} đã sửa trích dẫn này lúc {new Date(evidence.editedByReviewer.at).toLocaleString("vi-VN")} — lý do: {evidence.editedByReviewer.reason}
            </div>
          ) : null}

          <section>
            <h3 className="flex items-center gap-2 text-[13px] font-semibold text-foreground">
              <Quote className="h-3.5 w-3.5 text-ai" aria-hidden /> Đoạn trích làm bằng chứng
            </h3>
            <blockquote className="mt-2 rounded-[var(--radius-card)] border border-border bg-muted/40 px-4 py-3 font-serif text-[15px] leading-[1.7] text-foreground">
              “{quote?.text}”
            </blockquote>
          </section>

          <section className="mt-6">
            <h3 className="text-[13px] font-semibold text-foreground">Văn bản gốc</h3>
            {loading ? (
              <p className="mt-2 text-[13px] text-muted-foreground">Đang tải tài liệu…</p>
            ) : (
              <div className="mt-2 max-h-[320px] overflow-y-auto rounded-[var(--radius-card)] border border-border bg-card px-4 py-3 font-serif text-[15px] leading-[1.75] text-foreground">
                {segments && (evidence.version == null || document?.version === evidence.version) ? (
                  <>
                    {segments.before}
                    <mark className="evidence-mark">{segments.marked}</mark>
                    {segments.after}
                  </>
                ) : (
                  <>
                    {error ?? (text || "Không tải được nội dung tài liệu.")}
                    <p className="mt-2 font-sans text-[12px] text-contradict-fg">
                      Không tìm thấy nguyên văn đoạn trích trong tài liệu hiện tại — trích dẫn có thể đã bị chỉnh sửa.
                    </p>
                  </>
                )}
              </div>
            )}
          </section>

          <section className="mt-6 grid gap-3 sm:grid-cols-2">
            <div className="rounded-[var(--radius-card)] border border-border px-3 py-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Quần thể nghiên cứu</p>
              <p className="mt-0.5 text-[13px] text-foreground">{evidence.studyPopulation ?? "Không nêu"}</p>
            </div>
            <div className="rounded-[var(--radius-card)] border border-border px-3 py-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Liều trong nghiên cứu</p>
              <p className="mt-0.5 text-[13px] text-foreground">{evidence.dose ?? "Không nêu"}</p>
            </div>
          </section>

          {evidence.designNote ? (
            <section className="mt-4">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Ghi chú thiết kế nghiên cứu</p>
              <p className="mt-0.5 text-[13px] text-muted-foreground">{evidence.designNote}</p>
            </section>
          ) : null}

          {evidence.scopeDiffs?.length ? (
            <section className="mt-6">
              <h3 className="text-[13px] font-semibold text-foreground">Khác biệt phạm vi so với nhận định</h3>
              <ul className="mt-2 space-y-1.5">
                {evidence.scopeDiffs.map((diff) => (
                  <li key={diff.field} className="rounded-[var(--radius-control)] border border-scope-border bg-scope-soft px-3 py-2 text-[13px] text-scope-fg">
                    <span className="font-medium">{diff.field}</span>: nhận định “{diff.claim}” — bằng chứng “{diff.evidence}”
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <Separator className="my-6" />

          <section className="space-y-2">
            <h3 className="text-[13px] font-semibold text-foreground">Truy vết nguồn (provenance)</h3>
            <div className="flex flex-wrap items-center gap-2">
              <HashChip hash={document?.sha256 ?? "không có"} status={document?.hashStatus ?? "unchecked"} />
              <Chip tone="neutral">Thu thập lúc {document ? new Date(document.retrievedAt).toLocaleString("vi-VN") : "—"}</Chip>
              <Chip tone="neutral">Phiên bản nguồn {document?.version ?? "chưa có"}</Chip>
              {document?.meta.coverage ? <Chip tone="caution">{document.meta.coverage}</Chip> : null}
              {sourceUrl ? (
                <Link href={sourceUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[12px] text-ai-fg underline">
                  <ExternalLink className="h-3 w-3" aria-hidden /> Trang nguồn
                </Link>
              ) : null}
            </div>
            <p className="text-[12px] text-muted-foreground">
              Hash do nguồn dữ liệu cung cấp; trạng thái “chưa kiểm tra” không xác nhận nội dung đã được kiểm chứng.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
