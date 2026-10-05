"use client";

import * as React from "react";
import { Search, ShieldAlert } from "lucide-react";
import { Alert, Card, CardBody, CardHeader, CardTitle, Chip, EmptyState, Input, Select, Skeleton } from "@/components/ui";
import { WarehouseSourceChip } from "@/components/pv/badges";
import { WAREHOUSE_FLAG_LABEL, warehouseFlagLabel } from "@/lib/warehouse-flags";
import { WarehouseDocumentBody, WarehouseUnavailableAlert, isWarehouseUnavailable } from "@/components/pv/warehouse";
import { useWarehouseDocument, useWarehouseDocuments, useWarehouseOverview } from "@/lib/hooks/use-data";
import { ROLE_LABEL, useAppStore } from "@/lib/store/app-store";
import { formatDateTime, formatNumber } from "@/lib/utils";

function QualityChip({ status }: { status: string }) {
  return <Chip tone={status === "keep" ? "support" : status === "quarantine" ? "caution" : "neutral"}>{status}</Chip>;
}

export default function AdminCorpusPage() {
  const role = useAppStore((state) => state.role);
  // Backend cho mọi vai trò đã đăng nhập đọc kho; chỉ người chưa đăng nhập mới bị chặn ở đây.
  const canView = role !== "visitor";
  const [source, setSource] = React.useState("all");
  const [quality, setQuality] = React.useState("all");
  const [query, setQuery] = React.useState("");
  const [selectedDocId, setSelectedDocId] = React.useState("");

  const overview = useWarehouseOverview(canView);
  const documents = useWarehouseDocuments(
    { source: source === "all" ? undefined : source, qualityStatus: quality === "all" ? undefined : quality, limit: 200 },
    canView,
  );
  const detail = useWarehouseDocument(selectedDocId, 1200);

  const filtered = (documents.data?.documents ?? []).filter((doc) => {
    if (!query.trim()) return true;
    return `${doc.doc_id} ${doc.title} ${doc.source_id}`.toLowerCase().includes(query.trim().toLowerCase());
  });

  const tableCounts = Object.entries(overview.data?.table_counts ?? {}).sort((a, b) => b[1] - a[1]);
  const qualityFindings = [...(overview.data?.quality_findings ?? [])].sort((a, b) => b.count - a.count).slice(0, 6);
  const rag = overview.data?.rag;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Kho tài liệu</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Kho bằng chứng thật từ backend: nguồn dữ liệu, trạng thái chất lượng, phát hiện chất lượng, chỉ mục RAG và danh
          sách tài liệu kèm chi tiết.
        </p>
      </header>

      {!canView ? (
        <Alert tone="caution" title="Không có quyền xem kho tài liệu" icon={<ShieldAlert className="h-4 w-4" aria-hidden />}>
          Vai trò hiện tại ({ROLE_LABEL[role]}) chưa đăng nhập nên không đọc được kho tài liệu. Hãy đăng nhập bằng token điều tra viên hoặc dược sĩ duyệt.
        </Alert>
      ) : (
        <>
          {overview.isLoading ? (
            <Card>
              <CardBody className="space-y-2">
                <Skeleton className="h-20 w-full" />
              </CardBody>
            </Card>
          ) : null}
          {overview.error ? (
            isWarehouseUnavailable(overview.error) ? (
              <WarehouseUnavailableAlert error={overview.error} />
            ) : (
              <Alert tone="contradict" title="Không tải được tổng quan kho">{(overview.error as Error).message}</Alert>
            )
          ) : null}

          {overview.data ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Tài liệu theo nguồn</CardTitle>
                </CardHeader>
                <CardBody className="space-y-2 text-[13px]">
                  {overview.data.documents_by_source.map((item) => (
                    <div key={item.source} className="flex flex-wrap items-center gap-2 border-b border-border/60 pb-2 last:border-0 last:pb-0">
                      <WarehouseSourceChip source={item.source} />
                      <span className="tabular font-medium text-foreground">{formatNumber(item.documents)}</span>
                      <span className="text-[12px] text-muted-foreground">
                        {Object.entries(item.by_content_level)
                          .map(([level, count]) => `${level}: ${count}`)
                          .join(" · ")}
                      </span>
                      <span className="ml-auto text-[11px] text-muted-foreground">
                        {item.latest_retrieved_at ? `mới nhất ${formatDateTime(item.latest_retrieved_at)}` : "chưa có mốc lấy"}
                      </span>
                    </div>
                  ))}
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Chất lượng & chỉ mục RAG</CardTitle>
                </CardHeader>
                <CardBody className="space-y-3 text-[13px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-muted-foreground">Trạng thái chất lượng:</span>
                    {Object.entries(overview.data.documents_by_quality_status).map(([status, count]) => (
                      <span key={status} className="inline-flex items-center gap-1.5">
                        <QualityChip status={status} />
                        <span className="tabular">{formatNumber(count)}</span>
                      </span>
                    ))}
                  </div>
                  <div>
                    <p className="text-[12px] uppercase tracking-wide text-muted-foreground">Phát hiện chất lượng (theo số lượng)</p>
                    <ul className="mt-1 space-y-1">
                      {qualityFindings.map((finding) => (
                        <li key={finding.check_name} className="flex items-center gap-2">
                          <span className="text-[12px] text-foreground">
                            {WAREHOUSE_FLAG_LABEL[finding.check_name] ? (
                              <>
                                {WAREHOUSE_FLAG_LABEL[finding.check_name]}{" "}
                                <span className="mono text-[11px] text-muted-foreground">({finding.check_name})</span>
                              </>
                            ) : (
                              <span className="mono">{finding.check_name}</span>
                            )}
                          </span>
                          <Chip tone={finding.severity === "warn" ? "caution" : "neutral"}>{finding.severity}</Chip>
                          <span className="tabular ml-auto text-muted-foreground">{formatNumber(finding.count)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {rag ? (
                    <div className="border-t border-border pt-2">
                      <p className="text-[12px] uppercase tracking-wide text-muted-foreground">Chỉ mục RAG (Chroma vs Postgres)</p>
                      <p className="mt-1">
                        Chroma: <span className="tabular font-medium">{formatNumber(rag.chroma_chunks)}</span> đoạn · Postgres:{" "}
                        <span className="tabular font-medium">{formatNumber(rag.postgres_chunks)}</span> đoạn ·{" "}
                        <Chip tone={rag.chroma_chunks === rag.postgres_chunks ? "support" : "contradict"}>
                          {rag.chroma_chunks === rag.postgres_chunks ? "khớp" : "lệch"}
                        </Chip>
                      </p>
                      <p className="mt-1 text-[12px] text-muted-foreground">
                        <span className="mono">{rag.collection}</span> · {rag.embedding_provider}/{rag.embedding_model} · {rag.persist_dir}
                      </p>
                    </div>
                  ) : null}
                </CardBody>
              </Card>

              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Số dòng theo bảng</CardTitle>
                </CardHeader>
                <CardBody>
                  <dl className="grid grid-cols-2 gap-2 text-[13px] sm:grid-cols-3 lg:grid-cols-4">
                    {tableCounts.map(([table, count]) => (
                      <div key={table} className="rounded-[var(--radius-control)] border border-border px-3 py-2">
                        <dt className="mono truncate text-[11px] text-muted-foreground">{table}</dt>
                        <dd className="tabular mt-0.5 font-medium text-foreground">{formatNumber(count)}</dd>
                      </div>
                    ))}
                  </dl>
                </CardBody>
              </Card>
            </div>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Danh sách tài liệu</CardTitle>
              <Chip tone="neutral">{formatNumber(documents.data?.count ?? 0)} tài liệu</Chip>
            </CardHeader>
            <CardBody className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Select aria-label="Lọc theo nguồn" value={source} onChange={(event) => setSource(event.target.value)} className="max-w-[200px]">
                  <option value="all">Mọi nguồn</option>
                  <option value="pubmed">PubMed</option>
                  <option value="dailymed">DailyMed</option>
                  <option value="faers">openFDA FAERS</option>
                  <option value="reference">Tài liệu tham chiếu</option>
                  <option value="manual">Tài liệu nạp tay</option>
                </Select>
                <Select aria-label="Lọc theo chất lượng" value={quality} onChange={(event) => setQuality(event.target.value)} className="max-w-[200px]">
                  <option value="all">Mọi trạng thái chất lượng</option>
                  <option value="keep">keep</option>
                  <option value="quarantine">quarantine</option>
                </Select>
                <div className="relative min-w-[220px] flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                  <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm theo tiêu đề, mã tài liệu hoặc mã nguồn…" className="pl-9" aria-label="Tìm tài liệu trong kho" />
                </div>
              </div>

              {documents.isLoading ? <Skeleton className="h-32 w-full" /> : null}
              {documents.error ? (
                isWarehouseUnavailable(documents.error) ? (
                  <WarehouseUnavailableAlert error={documents.error} />
                ) : (
                  <Alert tone="contradict" title="Không tải được danh sách tài liệu">{(documents.error as Error).message}</Alert>
                )
              ) : null}
              {!documents.isLoading && !documents.error && filtered.length === 0 ? (
                <EmptyState title="Không có tài liệu nào khớp bộ lọc" description="Đổi bộ lọc nguồn/chất lượng hoặc xoá từ khoá tìm kiếm." />
              ) : null}
              {filtered.length ? (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[860px] text-left text-[13px]">
                    <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-2 pr-4">Mã</th>
                        <th className="py-2 pr-4">Nguồn</th>
                        <th className="py-2 pr-4">Tiêu đề</th>
                        <th className="py-2 pr-4">Chất lượng</th>
                        <th className="py-2 pr-4">Phiên bản</th>
                        <th className="py-2">Lấy lúc</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((doc) => (
                        <tr
                          key={doc.doc_id}
                          className="cursor-pointer border-t border-border hover:bg-muted/40"
                          onClick={() => setSelectedDocId(doc.doc_id)}
                          aria-selected={selectedDocId === doc.doc_id}
                        >
                          <td className="mono py-2 pr-4 text-muted-foreground">{doc.doc_id}</td>
                          <td className="py-2 pr-4">
                            <WarehouseSourceChip source={doc.source} />
                          </td>
                          <td className="max-w-[360px] truncate py-2 pr-4 text-foreground">{doc.title}</td>
                          <td className="py-2 pr-4">
                            <QualityChip status={doc.quality_status} />
                            {doc.quality_flags.length ? (
                              <span className="ml-2 text-[11px] text-muted-foreground">
                                {doc.quality_flags.map((flag) => warehouseFlagLabel(flag)).join(", ")}
                              </span>
                            ) : null}
                          </td>
                          <td className="tabular py-2 pr-4 text-muted-foreground">v{doc.version}</td>
                          <td className="py-2 text-muted-foreground">{formatDateTime(doc.retrieved_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </CardBody>
          </Card>

          {selectedDocId ? (
            <Card>
              <CardHeader>
                <CardTitle className="mono text-[14px]">{selectedDocId}</CardTitle>
                <button type="button" className="text-[13px] text-muted-foreground underline" onClick={() => setSelectedDocId("")}>
                  Đóng chi tiết
                </button>
              </CardHeader>
              <CardBody className="space-y-3 text-[13px]">
                {detail.isLoading ? <Skeleton className="h-24 w-full" /> : null}
                {detail.error ? (
                  isWarehouseUnavailable(detail.error) ? (
                    <WarehouseUnavailableAlert error={detail.error} />
                  ) : (
                    <p className="text-contradict-fg">Không tải được chi tiết: {(detail.error as Error).message}</p>
                  )
                ) : null}
                {detail.data ? <WarehouseDocumentBody detail={detail.data} previewClassName="max-h-72" /> : null}
              </CardBody>
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}
