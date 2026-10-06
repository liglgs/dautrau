"use client";

import * as React from "react";
import { ChevronUp, UserCog } from "lucide-react";
import { ROLE_LABEL, useAppStore } from "@/lib/store/app-store";
import type { Role } from "@/lib/types";
import { DATA_MODE } from "@/lib/api";
import { cn } from "@/lib/utils";

const ROLES: Role[] = ["visitor", "investigator", "reviewer", "admin"];

/** Nút nổi giữa mép dưới — chỉ hiện ở chế độ demo (mặc định bật), không che thanh bên. */
export function RoleSwitcher() {
  const { role, setRole, demoMode } = useAppStore();
  const [open, setOpen] = React.useState(false);
  if (!demoMode || DATA_MODE === "api") return null;
  return (
    <div className="fixed bottom-4 left-1/2 z-40 -translate-x-1/2 print:hidden">
      {open ? (
        <div className="absolute bottom-full left-1/2 mb-2 w-64 -translate-x-1/2 rounded-[var(--radius-overlay)] border border-border bg-popover p-2 hairline-shadow">
          <p className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">Chế độ demo · đổi vai trò</p>
          {ROLES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setRole(item);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-[var(--radius-control)] px-2 py-1.5 text-left text-[13px] transition-colors",
                role === item ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/60",
              )}
            >
              {ROLE_LABEL[item]}
              {role === item ? <span className="text-[11px] text-ai-fg">đang dùng</span> : null}
            </button>
          ))}
        </div>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex items-center gap-2 rounded-[var(--radius-chip)] border border-border bg-popover px-3 py-2 text-[12px] font-medium text-foreground hairline-shadow"
        aria-expanded={open}
      >
        <UserCog className="h-4 w-4 text-ai" aria-hidden />
        {ROLE_LABEL[role]}
        <ChevronUp className={cn("h-3 w-3 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
    </div>
  );
}
