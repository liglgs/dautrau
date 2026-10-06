"use client";

import * as React from "react";
import { ShieldAlert } from "lucide-react";
import { Alert, Chip } from "@/components/ui";
import { HashChip, WarehouseSourceChip } from "@/components/pv/badges";
import { WAREHOUSE_FLAG_LABEL, warehouseFlagLabel } from "@/lib/warehouse-flags";
import type { BackendError } from "@/lib/api/errors";
import type { WarehouseDocumentDetail } from "@/lib/api/types";
import { safeSourceUrl } from "@/lib/evidence-view";

/** Lệnh dựng kho ELT khi backend trả 503 WAREHOUSE_UNAVAILABLE. */
export const WAREHOUSE_DOCKER_COMMAND = "docker compose -f docker-compose.elt.yml up -d --wait";

export function isWarehouseUnavailable(error: unknown) {
  const err = error as Partial<BackendError> | null | undefined;
  return err?.status === 503 || err?.code === "WAREHOUSE_UNAVAILABLE";
}

/**
 * Chip cảnh báo cho các cờ chất lượng của tài liệu. Dùng ở mọi nơi hiển thị nhãn
 * nguồn, để tài liệu nạp tay không trông giống bằng chứng gốc.
 */
export function WarehouseQualityFlagChips({
  flags,
  max = 2,
  className,
}: {
  flags?: string[] | null;
  max?: number;
  className?: string;
}) {
  if (!flags?.length) return null;
  const shown = flags.slice(0, max);
  const rest = flags.length - shown.length;
  return (
    <>
      {shown.map((flag) => (
        <Chip key={flag} tone="caution" className={className}>
          {warehouseFlagLabel(flag)}
        </Chip>
      ))}
      {rest > 0 ? <Chip tone="neutral" className={className}>+{rest} cờ khác</Chip> : null}
    </>
  );
}

/** Cảnh báo dùng chung khi kho chưa sẵn sàng (backend 503). */
export function WarehouseUnavailableAlert({ error }: { error: unknown }) {
  return (
    <Alert tone="caution" title="Kho bằng chứng chưa sẵn sàng" icon={<ShieldAlert className="h-4 w-4" aria-hidden />}>
      <p>{(error as Error | null)?.message}</p>
      <p className="mt-1">
        Khởi động kho rồi thử lại:{" "}
        <code className="mono rounded bg-muted px-1.5 py-0.5 text-[12px]">{WAREHOUSE_DOCKER_COMMAND}</code>
      </p>
    </Alert>
  );
}

/**
 * Phần thân chi tiết một tài liệu kho: nhãn nguồn, trạng thái chất lượng, băm,
 * mục nội dung, trích đoạn và liên kết nguồn gốc.
 */
export function WarehouseDocumentBody({
  detail,
  previewClassName = "max-h-64",
}: {
  detail: WarehouseDocumentDetail;
  previewClassName?: string;
}) {
  const sourceUrl = safeSourceUrl(detail.source_url);
  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <WarehouseSourceChip source={detail.source} />
        <Chip tone={detail.quality_status === "keep" ? "support" : detail.quality_status === "reject" ? "neutral" : "caution"}>
          {detail.quality_status}
        </Chip>
        <Chip tone="neutral">v{detail.version}</Chip>
        {detail.pair_id ? <Chip tone="scope">{detail.pair_id}</Chip> : null}
      </div>
      <p className="text-[14px] font-medium text-foreground">{detail.title}</p>
      <p className="flex items-center gap-2">
        <HashChip hash={detail.text_sha256} />
      </p>
      {detail.quality_flags.length ? (
        <p className="text-[12px] text-muted-foreground">
          Cờ chất lượng:{" "}
          {detail.quality_flags.map((flag) => {
            const label = WAREHOUSE_FLAG_LABEL[flag];
            return label ? `${label} (${flag})` : flag;
          }).join(", ")}
        </p>
      ) : null}
      {detail.sections.length ? (
        <div>
          <p className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">Mục nội dung</p>
          <ul className="mt-1 space-y-0.5">
            {detail.sections.map((section) => (
              <li key={`${section.title}-${section.start}`} className="text-[12px] text-muted-foreground">
                {section.title} <span className="mono">[{section.start}..{section.end}]</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div>
        <p className="text-[12px] font-medium uppercase tracking-wide text-muted-foreground">Trích đoạn văn bản</p>
        <pre
          className={`mono mt-1 overflow-y-auto whitespace-pre-wrap rounded-[var(--radius-card)] border border-border bg-muted px-3 py-2 text-[12px] leading-relaxed text-foreground ${previewClassName}`}
        >
          {detail.text_preview || "Tài liệu không có phần xem trước."}
        </pre>
      </div>
      {sourceUrl ? (
        <a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-block underline">
          Mở nguồn gốc
        </a>
      ) : null}
    </>
  );
}
