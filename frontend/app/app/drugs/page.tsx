"use client";

import * as React from "react";
import { BookOpen, Info, Library, Search } from "lucide-react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Chip, EmptyState, Input, Skeleton, Textarea } from "@/components/ui";
import { WarehouseSourceChip } from "@/components/pv/badges";
import { WarehouseQualityFlagChips } from "@/components/pv/warehouse";
import { WarehouseDocumentBody, WarehouseUnavailableAlert, isWarehouseUnavailable } from "@/components/pv/warehouse";
import { useDrugLookup, useRagSearch, useWarehouseDocument } from "@/lib/hooks/use-data";
import { formatDateTime } from "@/lib/utils";

function ScoreChip({ score }: { score: number }) {
  const tone = score >= 0.75 ? "support" : score >= 0.5 ? "ai" : "neutral";
  return (
    <Chip tone={tone} className="tabular">
      {score.toFixed(3)}
    </Chip>
  );
}

function DocumentDetailPanel({ docId, onClose }: { docId: string; onClose: () => void }) {
  const detail = useWarehouseDocument(docId, 1200);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="mono text-[14px]">{docId}</CardTitle>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Đóng
        </Button>
      </CardHeader>
      <CardBody className="space-y-3 text-[13px]">
        {detail.isLoading ? <Skeleton className="h-24 w-full" /> : null}
        {detail.error ? (
          isWarehouseUnavailable(detail.error) ? (
            <WarehouseUnavailableAlert error={detail.error} />
          ) : (
            <p className="text-contradict-fg">Không tải được tài liệu: {(detail.error as Error).message}</p>
          )
        ) : null}
        {detail.data ? <WarehouseDocumentBody detail={detail.data} /> : null}
      </CardBody>
    </Card>
  );
}

export default function DrugLookupPage() {
  const [drugInput, setDrugInput] = React.useState("");
  const [drugQuery, setDrugQuery] = React.useState("");
  const [ragInput, setRagInput] = React.useState("");
  const [ragPairId, setRagPairId] = React.useState<string | undefined>(undefined);
  const [openDocId, setOpenDocId] = React.useState("");

  const lookup = useDrugLookup(drugQuery, drugQuery.length >= 2);
  const rag = useRagSearch();
  const result = lookup.data;

  const runLookup = (event: React.FormEvent) => {
    event.preventDefault();
    const query = drugInput.trim();
    if (query.length < 2) return;
    setOpenDocId("");
    setDrugQuery(query);
  };

  const runRag = (event: React.FormEvent) => {
    event.preventDefault();
    const query = ragInput.trim();
    if (query.length < 3) return;
    rag.mutate({ query, k: 6, ...(ragPairId ? { pairId: ragPairId } : {}) });
  };

  const askAboutPair = (pairId: string, drugName: string, eventTerm: string) => {
    const query = `${drugName} ${eventTerm}`.trim();
    setRagInput(query);
    setRagPairId(pairId);
    rag.mutate({ query, k: 6, pairId });
  };

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Tra cứu thuốc</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Tìm hoạt chất trong kho bằng chứng và hỏi kho bằng tìm kiếm ngữ nghĩa (RAG). Kho là tập ứng viên, không phải
          kết luận lâm sàng.
        </p>
      </header>

      <Alert tone="neutral" title="Kho ứng viên, chưa phải gold lâm sàng" icon={<Info className="h-4 w-4" aria-hidden />}>
        Cặp thuốc–biến cố trong kho có trạng thái <code className="mono">candidate_not_gold</code> (ứng viên, chưa qua
        duyệt gold). Mọi kết luận vẫn cần người duyệt đọc bằng chứng gốc.
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Tra cứu theo tên thuốc</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <form onSubmit={runLookup} className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[240px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input
                value={drugInput}
                onChange={(event) => setDrugInput(event.target.value)}
                placeholder="Ví dụ: ibuprofen"
                className="pl-9"
                aria-label="Tên thuốc cần tra cứu"
              />
            </div>
            <Button type="submit" disabled={drugInput.trim().length < 2 || lookup.isFetching}>
              {lookup.isFetching ? "Đang tra…" : "Tra cứu"}
            </Button>
          </form>

          {lookup.isLoading ? <Skeleton className="h-20 w-full" /> : null}
          {lookup.error && !result ? (
            isWarehouseUnavailable(lookup.error) ? (
              <WarehouseUnavailableAlert error={lookup.error} />
            ) : (
              <p className="text-[13px] text-contradict-fg">Không tra được kho: {(lookup.error as Error).message}</p>
            )
          ) : null}

          {result && !result.matched ? (
            <EmptyState
              title="Không tìm thấy thuốc trong kho"
              description={`Không có hoạt chất nào khớp với “${result.query}”. Kiểm tra chính tả hoặc thử tên gốc (INN).`}
            />
          ) : null}

          {result?.matched ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {result.drugs.map((drug) => (
                  <span key={drug.drug_id} className="inline-flex items-center gap-2 rounded-[var(--radius-chip)] border border-border px-2.5 py-1 text-[13px]">
                    <span className="font-medium text-foreground">{drug.name}</span>
                    <span className="text-muted-foreground">{drug.ingredient}</span>
                    <Chip tone={drug.verified ? "support" : "caution"}>{drug.verified ? "đã xác minh" : "chưa xác minh"}</Chip>
                    {drug.aliases.length ? <span className="text-[12px] text-muted-foreground">({drug.aliases.join(", ")})</span> : null}
                  </span>
                ))}
                <Chip tone="neutral">nguồn tra: {result.origin === "warehouse" ? "kho đã nạp" : "từ điển"}</Chip>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-[13px]">
                  <thead className="text-[12px] uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="py-2 pr-4">Cặp thuốc – biến cố</th>
                      <th className="py-2 pr-4">Trạng thái</th>
                      <th className="py-2 pr-4">Nguồn cặp</th>
                      <th className="py-2">Hỏi kho</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.pairs.map((pair) => (
                      <tr key={pair.pair_id} className="border-t border-border">
                        <td className="py-2 pr-4 text-foreground">
                          {pair.drug_name} → {pair.event_term}
                        </td>
                        <td className="py-2 pr-4">
                          <Chip tone="caution">
                            {pair.status === "candidate_not_gold" ? "ứng viên — NOT gold" : pair.status}
                          </Chip>
                        </td>
                        <td className="py-2 pr-4 text-muted-foreground">{pair.source}</td>
                        <td className="py-2">
                          <Button variant="ghost" size="sm" onClick={() => askAboutPair(pair.pair_id, pair.drug_name, pair.event_term)}>
                            <Library className="h-3.5 w-3.5" aria-hidden /> Tìm trong kho
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {result.pairs.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-2 text-muted-foreground">
                          Chưa có cặp thuốc–biến cố nào trong kho cho hoạt chất này.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-[13px] text-muted-foreground">
                <span>Tài liệu liên quan trong kho:</span>
                {Object.entries(result.documents).length ? (
                  Object.entries(result.documents).map(([source, count]) => (
                    <span key={source} className="inline-flex items-center gap-1.5">
                      <WarehouseSourceChip source={source} />
                      <span className="tabular">{count}</span>
                    </span>
                  ))
                ) : (
                  <span>chưa có tài liệu nào cho các cặp trên.</span>
                )}
              </div>
            </div>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Hỏi kho bằng chứng</CardTitle>
          <Chip tone="ai">RAG</Chip>
        </CardHeader>
        <CardBody className="space-y-3">
          <form onSubmit={runRag} className="space-y-2">
            <Textarea
              rows={2}
              value={ragInput}
              onChange={(event) => setRagInput(event.target.value)}
              placeholder="Ví dụ: ibuprofen có làm tăng nguy cơ xuất huyết tiêu hoá không?"
              aria-label="Câu hỏi cho kho bằng chứng"
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button type="submit" disabled={ragInput.trim().length < 3 || rag.isPending}>
                <BookOpen className="h-3.5 w-3.5" aria-hidden /> {rag.isPending ? "Đang tìm…" : "Tìm trong kho"}
              </Button>
              {ragPairId ? (
                <Chip tone="scope" className="gap-2">
                  lọc theo cặp {ragPairId}
                  <button type="button" className="underline" onClick={() => setRagPairId(undefined)}>
                    bỏ lọc
                  </button>
                </Chip>
              ) : null}
              <span className="text-[12px] text-muted-foreground">
                Nạp tài liệu mới cần vai trò dược sĩ duyệt (Quản trị → Nạp tài liệu).
              </span>
            </div>
          </form>

          {rag.isPending ? <Skeleton className="h-24 w-full" /> : null}
          {rag.error ? (
            isWarehouseUnavailable(rag.error) ? (
              <WarehouseUnavailableAlert error={rag.error} />
            ) : (
              <p className="text-[13px] text-contradict-fg">Không tìm được trong kho: {(rag.error as Error).message}</p>
            )
          ) : null}
          {rag.data && !rag.isPending ? (
            rag.data.hits.length === 0 ? (
              <EmptyState title="Không có đoạn nào phù hợp" description="Thử từ khoá khác hoặc bỏ lọc theo cặp thuốc–biến cố." />
            ) : (
              <ul className="space-y-2">
                {rag.data.hits.map((hit) => (
                  <li key={hit.chunk_id} className="min-w-0 rounded-[var(--radius-card)] border border-border px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <ScoreChip score={hit.score} />
                      <WarehouseSourceChip source={hit.document.source} />
                      <Chip tone={hit.document.quality_status === "keep" ? "support" : "caution"}>{hit.document.quality_status}</Chip>
                      <WarehouseQualityFlagChips flags={hit.document.quality_flags} />
                      <span className="mono break-all text-[11px] text-muted-foreground">{hit.chunk_id}</span>
                      {!hit.in_postgres ? <Chip tone="caution">chỉ có trong Chroma</Chip> : null}
                      {hit.document.retrieved_at ? (
                        <span className="ml-auto text-[11px] text-muted-foreground">{formatDateTime(hit.document.retrieved_at)}</span>
                      ) : null}
                    </div>
                    <p className="mt-1.5 text-[13px] font-medium text-foreground">{hit.document.title}</p>
                    <p className="mt-1 min-w-0 break-words text-[13px] text-muted-foreground [overflow-wrap:anywhere]">
                      {hit.text.slice(0, 280)}{hit.text.length > 280 ? "…" : ""}
                    </p>
                    <div className="mt-2">
                      <Button variant="outline" size="sm" onClick={() => setOpenDocId(hit.document.doc_id)} aria-expanded={openDocId === hit.document.doc_id}>
                        Mở tài liệu
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )
          ) : null}
          {rag.data ? (
            <p className="text-[12px] text-muted-foreground">
              Mô hình nhúng: <span className="mono">{rag.data.embedding_model}</span> · {rag.data.hits.length} đoạn gần nhất
            </p>
          ) : null}
        </CardBody>
      </Card>

      {openDocId ? <DocumentDetailPanel docId={openDocId} onClose={() => setOpenDocId("")} /> : null}
    </div>
  );
}
