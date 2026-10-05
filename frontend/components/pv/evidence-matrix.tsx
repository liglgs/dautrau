"use client";

import * as React from "react";
import { ArrowUpDown, Filter } from "lucide-react";
import { Button, Card, Chip, EmptyState, Select } from "@/components/ui";
import { CitationChip, ScopeChip, SourceChip, StanceBadge } from "@/components/pv/badges";
import { useInspector } from "@/lib/store/inspector";
import type { EvidenceItem, Stance } from "@/lib/types";
import { cn } from "@/lib/utils";

const TABS: { key: "all" | Stance; label: string }[] = [
  { key: "all", label: "Tất cả" },
  { key: "supporting", label: "Ủng hộ" },
  { key: "contradicting", label: "Phản bác" },
  { key: "uncertain", label: "Chưa chắc chắn" },
  { key: "background", label: "Thông tin nền" },
];

export function EvidenceMatrix({
  investigationId,
  items,
  density = "comfortable",
  onRequestMore,
  canRequestMore,
}: {
  investigationId: string;
  items: EvidenceItem[];
  density?: "comfortable" | "compact";
  onRequestMore?: (item: EvidenceItem) => void;
  canRequestMore?: boolean;
}) {
  const [tab, setTab] = React.useState<"all" | Stance>("all");
  const [sort, setSort] = React.useState<"step" | "source">("step");
  const [selected, setSelected] = React.useState<string[]>([]);
  const [source, setSource] = React.useState("all");
  const [scope, setScope] = React.useState("all");
  const [comparing, setComparing] = React.useState(false);
  const openInspector = useInspector((state) => state.open);

  const filtered = React.useMemo(() => {
    const list = items.filter((item) => (tab === "all" || item.stance === tab) && (source === "all" || item.source === source) && (scope === "all" || (scope === "unknown" ? !item.scope : item.scope === scope)));
    if (sort === "source") return [...list].sort((a, b) => a.source.localeCompare(b.source));
    // Thiếu bước (backend chưa trả) thì xếp cuối thay vì coi tất cả là bước 0.
    return [...list].sort((a, b) => (a.foundAtStep ?? Number.MAX_SAFE_INTEGER) - (b.foundAtStep ?? Number.MAX_SAFE_INTEGER));
  }, [items, tab, sort, source, scope]);
  const compared = items.filter((item) => selected.includes(item.id));

  const rowHeight = density === "compact" ? "h-9" : "h-11";

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex flex-wrap items-center gap-1">
          {TABS.map((item) => {
            const count = item.key === "all" ? items.length : items.filter((evidence) => evidence.stance === item.key).length;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => setTab(item.key)}
                className={cn(
                  "rounded-[var(--radius-control)] px-2.5 py-1 text-[13px] font-medium transition-colors",
                  tab === item.key ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/60",
                )}
                aria-pressed={tab === item.key}
              >
                {item.label}
                <span className="tabular ml-1.5 text-[11px] text-muted-foreground">{count}</span>
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setSort(sort === "step" ? "source" : "step")}>
            <ArrowUpDown className="h-3.5 w-3.5" aria-hidden />
            {sort === "step" ? "Theo bước" : "Theo nguồn"}
          </Button>
          <Filter className="h-3.5 w-3.5" aria-hidden />
          <Select aria-label="Lọc nguồn" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="all">Mọi nguồn</option><option value="pubmed">PubMed</option><option value="dailymed">DailyMed</option><option value="faers">FAERS</option>
          </Select>
          <Select aria-label="Lọc phạm vi" value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="all">Mọi phạm vi</option><option value="matched">Khớp</option><option value="partial">Một phần</option><option value="mismatched">Lệch</option><option value="unknown">Chưa đánh giá</option>
          </Select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="p-4">
          <EmptyState title="Không có mục bằng chứng nào ở nhóm này" description="Chọn nhóm khác hoặc chạy thêm bước điều tra." />
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] border-collapse text-left">
            <thead>
              <tr className="border-b border-border text-[12px] text-muted-foreground">
                <th className="w-10 px-3 py-2 font-medium">
                  <input
                    type="checkbox"
                    aria-label="Chọn tất cả"
                    checked={selected.length === filtered.length && filtered.length > 0}
                    onChange={(event) => setSelected(event.target.checked ? filtered.map((item) => item.id) : [])}
                  />
                </th>
                <th className="px-2 py-2 font-medium">Mã</th>
                <th className="px-2 py-2 font-medium">Nguồn</th>
                <th className="px-2 py-2 font-medium">Tài liệu</th>
                <th className="px-2 py-2 font-medium">Lập trường</th>
                <th className="px-2 py-2 font-medium">Phạm vi</th>
                <th className="px-2 py-2 font-medium">Bước</th>
                <th className="px-3 py-2 font-medium">Trích dẫn</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} className={cn("border-b border-border/60 last:border-0", rowHeight, "hover:bg-muted/40")}>
                  <td className="px-3">
                    <input
                      type="checkbox"
                      aria-label={`Chọn ${item.label}`}
                      checked={selected.includes(item.id)}
                      onChange={(event) =>
                        setSelected((current) =>
                          event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id),
                        )
                      }
                    />
                  </td>
                  <td className="mono px-2 text-[12px] text-foreground">{item.label}</td>
                  <td className="px-2">
                    <SourceChip source={item.source} />
                  </td>
                  <td className="max-w-[280px] truncate px-2 text-[13px] text-foreground">
                    {item.title}
                    {item.excluded ? <Chip tone="caution" className="ml-2">đã loại</Chip> : null}
                    {item.coverageNote ? <Chip tone="neutral" className="ml-2">{item.coverageNote}</Chip> : null}
                    {item.editedByReviewer ? <Chip tone="caution" className="ml-2">đã sửa</Chip> : null}
                  </td>
                  <td className="px-2">
                    <StanceBadge stance={item.stance} />
                  </td>
                  <td className="px-2">
                    <ScopeChip scope={item.scope} diffs={item.scopeDiffs} />
                  </td>
                  <td className="tabular px-2 text-[12px] text-muted-foreground">{item.foundAtStep ?? "—"}</td>
                  <td className="px-3">
                    <div className="flex items-center gap-1.5">
                      <CitationChip
                        label={item.label}
                        onClick={() => openInspector({ investigationId, evidence: item })}
                        title={item.quotes[0]?.text.slice(0, 120)}
                      />
                      {canRequestMore && onRequestMore ? (
                        <Button variant="ghost" size="sm" onClick={() => onRequestMore(item)}>
                          Yêu cầu tìm thêm
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected.length > 0 ? (
        <div className="flex items-center justify-between gap-3 border-t border-border bg-muted/40 px-4 py-2 text-[13px]">
          <span>Đã chọn {selected.length} mục</span>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => setSelected([])}>
              Bỏ chọn
            </Button>
            <Button variant="secondary" size="sm" disabled={compared.length !== 2} onClick={() => setComparing(!comparing)}>
              So sánh mâu thuẫn (chọn 2 mục)
            </Button>
          </div>
        </div>
      ) : null}
      {comparing && compared.length === 2 ? <section className="border-t border-border p-4" aria-label="So sánh bằng chứng">
        <p className="mb-3 text-[13px] text-muted-foreground">Đối chiếu phạm vi hai bằng chứng; kết quả đối lập cần chuyên viên phân xử. Bảng này không tự xác nhận mâu thuẫn.</p>
        <div className="grid gap-4 sm:grid-cols-2">{compared.map((item) => <div key={item.id} className="space-y-2 rounded border border-border p-3">
          <h3>{item.label} · {item.title}</h3><StanceBadge stance={item.stance} />
          <blockquote className="font-serif">{item.quotes[0]?.text}</blockquote>
          {(["population", "dose", "route", "time_window"] as const).map((field) => <p key={field} className="text-[13px]">{({population: "Quần thể", dose: "Liều", route: "Đường dùng", time_window: "Thời gian"})[field]}: {item.scopeValues?.[field] ?? (field === "population" ? item.studyPopulation : field === "dose" ? item.dose : undefined) ?? "Chưa rõ"}</p>)}
          <CitationChip label={item.label} onClick={() => openInspector({ investigationId, evidence: item })} />
        </div>)}</div>
      </section> : null}
    </Card>
  );
}
