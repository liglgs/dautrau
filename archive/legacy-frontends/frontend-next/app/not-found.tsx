"use client";

import Link from "next/link";
import { buttonClass } from "@/src/components/ui";
import { Icon } from "@/src/components/icons";

export default function NotFound() {
  return (
    <div className="grid min-h-dvh place-items-center bg-canvas px-6">
      <div className="w-full max-w-[520px] rounded-[var(--radius-card)] border border-line bg-surface p-7 text-center shadow-[var(--shadow-card)]">
        <span className="mx-auto grid size-12 place-items-center rounded-[14px] border border-line bg-surface-2 text-muted">
          <Icon name="search" className="size-5" />
        </span>
        <h1 className="mt-4 text-[22px] font-bold tracking-tight text-ink">
          Không tìm thấy trang
        </h1>
        <p className="mt-2 text-[13px] text-muted">
          Đường dẫn không tồn tại hoặc bạn không có quyền truy cập ca này.
        </p>
        <div className="mt-5 flex justify-center">
          <Link href="/" className={buttonClass("primary", "md")}>
            Về trang chính
          </Link>
        </div>
      </div>
    </div>
  );
}
