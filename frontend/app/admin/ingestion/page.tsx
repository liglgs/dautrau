"use client";

import * as React from "react";
import { Database, FileUp, RefreshCcw, ShieldAlert } from "lucide-react";
import { Alert, Button, Card, CardBody, CardHeader, CardTitle, Chip, EmptyState, Input, Label, Select, Skeleton, Textarea } from "@/components/ui";
import { WarehouseSourceChip } from "@/components/pv/badges";
import { useIngestDocument, useIngestionEvents } from "@/lib/hooks/use-data";
import type { BackendError } from "@/lib/api/errors";
import { formatDateTime } from "@/lib/utils";
import type { IngestDocumentInput, IngestDocumentResult, WarehouseSourceId } from "@/lib/api/types";

const SOURCES: { value: WarehouseSourceId; label: string }[] = [
  { value: "pubmed", label: "PubMed" },
  { value: "dailymed", label: "DailyMed" },
  { value: "faers", label: "openFDA FAERS" },
  { value: "reference", label: "Tài liệu tham chiếu" },
  { value: "manual", label: "Tài liệu nạp tay" },
];

const STATUS_TONE: Record<string, "support" | "caution" | "contradict" | "ai" | "neutral"> = {
  completed: "support",
  partial: "caution",
  failed: "contradict",
  running: "ai",
  queued: "neutral",
};

const DOCKER_COMMAND = "docker compose -f docker-compose.elt.yml up -d --wait";

/** Lỗi nạp tài liệu theo mã HTTP của backend; giữ thông điệp gốc để người vận hành xử lý. */
function IngestError({ error, onBumpVersion }: { error: unknown; onBumpVersion: () => void }) {
  const err = error as Partial<BackendError> | null | undefined;
  const status = err?.status;
  const message = (error as Error | null)?.message ?? "Không rõ lỗi.";
  if (status === 403) {
    return (
      <Alert tone="caution" title="Cần vai trò dược sĩ duyệt" icon={<ShieldAlert className="h-4 w-4" aria-hidden />}>
        {message} Nạp tài liệu chỉ dành cho vai trò reviewer/admin; token hiện tại bị từ chối.
      </Alert>
    );
  }
  if (status === 409) {
    return (
      <Alert
        tone="caution"
        title="Trùng mã nguồn và phiên bản"
        action={
          <Button variant="outline" size="sm" onClick={onBumpVersion}>
            Tạo phiên bản mới
          </Button>
        }
      >
        {message} Cùng mã nguồn và phiên bản nhưng nội dung khác: backend không ghi đè, hãy tăng số phiên bản rồi gửi lại.
      </Alert>
    );
  }
  if (status === 503 || err?.code === "WAREHOUSE_UNAVAILABLE") {
    return (
      <Alert tone="caution" title="Kho bằng chứng chưa sẵn sàng">
        <p>{message}</p>
        <p className="mt-1">
          Khởi động kho rồi thử lại: <code className="mono rounded bg-muted px-1.5 py-0.5 text-[12px]">{DOCKER_COMMAND}</code>
        </p>
      </Alert>
    );
  }
  return (
    <Alert tone="contradict" title={status === 422 ? "Dữ liệu chưa hợp lệ" : "Chưa nạp được tài liệu"}>
      {message}
    </Alert>
  );
}

function IngestResultCard({ result }: { result: IngestDocumentResult }) {
  return (
    <Alert tone="support" title={result.created ? "Đã nạp tài liệu mới" : "Tài liệu đã tồn tại, không tạo bản sao"}>
      <div className="space-y-1 text-[13px]">
        <p>
          <span className="mono">{result.doc_id}</span> · {result.text_chars.toLocaleString("vi-VN")} ký tự
        </p>
        <p className="mono break-all text-[11px]">sha256: {result.sha256}</p>
        <p>
          Chất lượng: <Chip tone={result.quality_status === "keep" ? "support" : "caution"}>{result.quality_status}</Chip>
          {result.quality_flags.length ? <span className="ml-2">cờ: {result.quality_flags.join(", ")}</span> : null}
        </p>
        <p>
          RAG:{" "}
          {result.rag.indexed
            ? `đã đánh chỉ mục ${result.rag.chunks_written} đoạn vào ${result.rag.collection} (${result.rag.embedding_model})`
            : "chưa đánh chỉ mục"}
        </p>
        <p className="text-muted-foreground">Sự kiện: <span className="mono">{result.event_id}</span></p>
      </div>
    </Alert>
  );
}

export default function AdminIngestionPage() {
  const events = useIngestionEvents(20);
  const ingest = useIngestDocument();
  const [source, setSource] = React.useState<WarehouseSourceId>("manual");
  const [sourceId, setSourceId] = React.useState("");
  const [version, setVersion] = React.useState("1");
  const [title, setTitle] = React.useState("");
  const [text, setText] = React.useState("");
  const [sourceUrl, setSourceUrl] = React.useState("");
  const [localError, setLocalError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<IngestDocumentResult | null>(null);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    const parsedVersion = Number(version);
    if (!sourceId.trim() || !title.trim()) {
      setLocalError("Cần mã nguồn và tiêu đề tài liệu.");
      return;
    }
    if (!Number.isInteger(parsedVersion) || parsedVersion < 1) {
      setLocalError("Phiên bản phải là số nguyên ≥ 1.");
      return;
    }
    if (text.trim().length < 40) {
      setLocalError("Văn bản cần ít nhất 40 ký tự để tách nội dung và băm.");
      return;
    }
    if (text.length > 200_000) {
      setLocalError("Văn bản vượt 200.000 ký tự; hãy tách thành tài liệu nhỏ hơn.");
      return;
    }
    const input: IngestDocumentInput = {
      source,
      source_id: sourceId.trim(),
      version: parsedVersion,
      title: title.trim(),
      text,
      source_url: sourceUrl.trim() || undefined,
    };
    setResult(null);
    ingest.mutate(input, { onSuccess: (payload) => setResult(payload) });
  };

  const bumpVersion = () => {
    const parsed = Number(version);
    setVersion(String(Number.isInteger(parsed) && parsed >= 1 ? parsed + 1 : 1));
  };

  const eventList = events.data?.events ?? [];

  return (
    <div className="space-y-4">
      <header>
        <h1 className="font-display text-[26px] text-foreground">Nạp tài liệu</h1>
        <p className="mt-1 text-[14px] text-muted-foreground">
          Nạp tài liệu công khai hoặc tài liệu nội bộ vào kho bằng chứng, kèm hash và đánh chỉ mục RAG. Nạp tài liệu chỉ
          dành cho vai trò dược sĩ duyệt.
        </p>
      </header>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Nạp tài liệu mới</CardTitle>
            <Chip tone="ai">reviewer</Chip>
          </CardHeader>
          <CardBody>
            <form onSubmit={submit} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <Label htmlFor="ingest-source">Nguồn</Label>
                  <Select id="ingest-source" value={source} onChange={(event) => setSource(event.target.value as WarehouseSourceId)}>
                    {SOURCES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <Label htmlFor="ingest-version">Phiên bản</Label>
                  <Input id="ingest-version" inputMode="numeric" value={version} onChange={(event) => setVersion(event.target.value)} />
                </div>
              </div>
              <div>
                <Label htmlFor="ingest-source-id">Mã nguồn (source_id) *</Label>
                <Input id="ingest-source-id" value={sourceId} onChange={(event) => setSourceId(event.target.value)} placeholder="Ví dụ: pmid-39466269 hoặc ghi-chu-noi-bo-01" />
              </div>
              <div>
                <Label htmlFor="ingest-title">Tiêu đề *</Label>
                <Input id="ingest-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Tiêu đề tài liệu" />
              </div>
              <div>
                <Label htmlFor="ingest-url">URL nguồn (không bắt buộc)</Label>
                <Input id="ingest-url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://…" />
              </div>
              <div>
                <Label htmlFor="ingest-text">Văn bản đầy đủ * (40–200.000 ký tự)</Label>
                <Textarea id="ingest-text" rows={8} value={text} onChange={(event) => setText(event.target.value)} placeholder="Dán toàn văn tài liệu cần nạp…" />
                <p className="mt-1 text-[12px] text-muted-foreground">{text.length.toLocaleString("vi-VN")} ký tự</p>
              </div>
              {localError ? <Alert tone="contradict" title="Chưa gửi được">{localError}</Alert> : null}
              {ingest.error ? <IngestError error={ingest.error} onBumpVersion={bumpVersion} /> : null}
              {result ? <IngestResultCard result={result} /> : null}
              <div className="flex items-center gap-2">
                <Button type="submit" disabled={ingest.isPending}>
                  <FileUp className="h-4 w-4" aria-hidden />
                  {ingest.isPending ? "Đang nạp…" : "Nạp vào kho"}
                </Button>
                {ingest.isSuccess ? (
                  <Button type="button" variant="ghost" size="sm" onClick={() => { setResult(null); ingest.reset(); }}>
                    Xoá kết quả
                  </Button>
                ) : null}
              </div>
            </form>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dòng sự kiện nạp</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => void events.refetch()} disabled={events.isFetching}>
              <RefreshCcw className="h-3.5 w-3.5" aria-hidden /> Làm mới
            </Button>
          </CardHeader>
          <CardBody className="space-y-3">
            {events.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : null}
            {events.error ? (
              (events.error as Partial<BackendError>)?.status === 503 || (events.error as Partial<BackendError>)?.code === "WAREHOUSE_UNAVAILABLE" ? (
                <Alert tone="caution" title="Kho bằng chứng chưa sẵn sàng">
                  <p>{(events.error as Error).message}</p>
                  <p className="mt-1">
                    Khởi động kho rồi thử lại: <code className="mono rounded bg-muted px-1.5 py-0.5 text-[12px]">{DOCKER_COMMAND}</code>
                  </p>
                </Alert>
              ) : (
                <Alert tone="contradict" title="Không tải được dòng sự kiện">{(events.error as Error).message}</Alert>
              )
            ) : null}
            {!events.isLoading && !events.error && eventList.length === 0 ? (
              <EmptyState title="Chưa có sự kiện nạp nào" description="Nạp tài liệu đầu tiên hoặc chạy ELT để dòng sự kiện có dữ liệu." />
            ) : null}
            {eventList.map((item) => (
              <div key={item.event_id} className="rounded-[var(--radius-card)] border border-border px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Database className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                  <span className="mono text-[12px] text-muted-foreground">{item.event_id}</span>
                  <Chip tone={STATUS_TONE[item.status] ?? "neutral"}>{item.status}</Chip>
                  <Chip tone="neutral">{item.kind}</Chip>
                  <span className="ml-auto text-[12px] text-muted-foreground">{formatDateTime(item.created_at)}</span>
                </div>
                <p className="mt-1.5 text-[13px] text-foreground">{item.title}</p>
                {Object.keys(item.detail ?? {}).length ? (
                  <details className="mt-1.5">
                    <summary className="cursor-pointer text-[12px] text-muted-foreground">Chi tiết kỹ thuật</summary>
                    <pre className="mono mt-1 max-h-48 overflow-auto rounded-[var(--radius-control)] border border-border bg-muted px-2 py-1.5 text-[11px] leading-relaxed text-foreground">
                      {JSON.stringify(item.detail, null, 2)}
                    </pre>
                  </details>
                ) : null}
              </div>
            ))}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quy tắc nạp</CardTitle>
        </CardHeader>
        <CardBody className="space-y-1.5 text-[13px] text-muted-foreground">
          <p>Mỗi tài liệu lưu hash SHA-256 tại thời điểm lấy; hash hiện trong trình xem nguồn.</p>
          <p>Tài liệu nội bộ được đánh dấu rõ là “nội bộ”, không trộn với nguồn công khai.</p>
          <p>Nạp lại cùng mã nguồn và phiên bản với nội dung khác bị từ chối (HTTP 409); tạo phiên bản mới để giữ truy vết.</p>
          <p>Nạp tài liệu cần vai trò dược sĩ duyệt (điều tra viên nhận HTTP 403); xem dòng sự kiện chỉ cần đăng nhập.</p>
          <p className="flex flex-wrap items-center gap-2">
            Nguồn hỗ trợ:
            {SOURCES.map((item) => (
              <WarehouseSourceChip key={item.value} source={item.value} />
            ))}
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
