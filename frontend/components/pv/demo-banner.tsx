"use client";

import * as React from "react";
import { X } from "lucide-react";
import { DATA_MODE } from "@/lib/api";
import { BRAND } from "@/lib/brand";
import { cn } from "@/lib/utils";

/**
 * Banner bắt buộc: mọi màn có dữ liệu phải nói rõ nguồn dữ liệu.
 * Chế độ `api` chỉ xác nhận kết nối; backend vẫn có thể dùng nguồn fixture.
 */
export function DemoBanner({ className, compact = false }: { className?: string; compact?: boolean }) {
  const [hidden, setHidden] = React.useState(false);
  if (hidden) return null;
  const live = DATA_MODE === "api";
  const notice = live
    ? compact
      ? BRAND.liveNotice
      : `${BRAND.liveProjectNotice} — ${BRAND.liveNotice}`
    : compact
      ? BRAND.demoNotice
      : `${BRAND.projectNotice} — ${BRAND.demoNotice}`;
  return (
    <div
      className={cn(
        "flex items-center justify-center gap-2 border-b border-caution-border bg-caution-soft px-4 py-1 text-center text-[12px] text-caution-fg",
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-caution" aria-hidden />
      <span>{notice}</span>
      <button type="button" onClick={() => setHidden(true)} aria-label={live ? "Ẩn thông báo nguồn dữ liệu" : "Ẩn thông báo dữ liệu minh họa"} className="ml-1 opacity-70 hover:opacity-100">
        <X className="h-3 w-3" aria-hidden />
      </button>
    </div>
  );
}
