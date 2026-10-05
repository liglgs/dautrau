import * as React from "react";
import { cn } from "@/lib/utils";

/* ---------------------------------------------------------------------------------------
   Primitive giao diện tối giản, không phụ thuộc thư viện ngoài.
   Quy ước hình khối (PHẦN G4): chip = pill · input/nút = 6px · card = 10px · overlay = 14px.
   --------------------------------------------------------------------------------------- */

type ButtonVariant = "primary" | "secondary" | "ghost" | "outline" | "danger";
type ButtonSize = "sm" | "md" | "lg" | "icon";

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-foreground hover:bg-primary/90",
  secondary: "bg-muted text-foreground hover:bg-muted/70 border border-border",
  ghost: "text-foreground hover:bg-muted",
  outline: "border border-input bg-card text-foreground hover:bg-muted",
  danger: "bg-contradict text-white hover:bg-contradict/90",
};

const BUTTON_SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-[13px]",
  md: "h-9 px-4 text-sm",
  lg: "h-11 px-6 text-[15px]",
  icon: "h-9 w-9",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  // Mặc định `type="button"`: nút nằm trong <form> mà không ghi rõ type sẽ thành nút gửi,
  // khiến một cú nhấp (ví dụ nút "Tạo phiên bản mới" trong cảnh báo 409) gửi biểu mẫu thật.
  { className, variant = "primary", size = "md", type = "button", ...props },
  ref,
) {
  return (
    <button
      type={type}
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)] font-medium transition-colors duration-150",
        "disabled:cursor-not-allowed disabled:opacity-50",
        BUTTON_VARIANTS[variant],
        BUTTON_SIZES[size],
        className,
      )}
      {...props}
    />
  );
});

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-[var(--radius-card)] border border-border bg-card", className)} {...props} />;
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-start justify-between gap-4 border-b border-border px-5 py-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-[15px] font-semibold text-foreground", className)} {...props} />;
}

export function CardBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}

export function Chip({
  className,
  tone = "neutral",
  children,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: "neutral" | "ai" | "support" | "contradict" | "caution" | "scope" }) {
  const tones: Record<string, string> = {
    neutral: "bg-neutral-soft text-neutral-fg border-neutral-border",
    ai: "bg-ai-soft text-ai-fg border-ai-border",
    support: "bg-support-soft text-support-fg border-support-border",
    contradict: "bg-contradict-soft text-contradict-fg border-contradict-border",
    caution: "bg-caution-soft text-caution-fg border-caution-border",
    scope: "bg-scope-soft text-scope-fg border-scope-border",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[var(--radius-chip)] border px-2 py-0.5 text-[12px] font-medium",
        tones[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-[var(--radius-control)] border border-input bg-card px-3 text-sm text-foreground",
        "placeholder:text-muted-foreground focus:border-ring",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-[var(--radius-control)] border border-input bg-card px-3 py-2 text-sm text-foreground",
        "placeholder:text-muted-foreground focus:border-ring",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-9 w-full rounded-[var(--radius-control)] border border-input bg-card px-2 text-sm text-foreground",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-[13px] font-medium text-muted-foreground", className)} {...props} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-[var(--radius-control)] bg-muted", className)} />;
}

export function Separator({ className }: { className?: string }) {
  return <div className={cn("h-px w-full bg-border", className)} />;
}

export function Alert({
  tone = "neutral",
  title,
  children,
  action,
  icon,
  className,
}: {
  tone?: "ai" | "support" | "contradict" | "caution" | "scope" | "neutral";
  title?: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  const bar: Record<string, string> = {
    ai: "bg-ai",
    support: "bg-support",
    contradict: "bg-contradict",
    caution: "bg-caution",
    scope: "bg-scope",
    neutral: "bg-neutral",
  };
  const iconTone: Record<string, string> = {
    ai: "text-ai",
    support: "text-support",
    contradict: "text-contradict",
    caution: "text-caution",
    scope: "text-scope",
    neutral: "text-neutral",
  };
  return (
    <div className={cn("relative flex gap-3 overflow-hidden rounded-[var(--radius-card)] border border-border bg-card px-4 py-3", className)}>
      <span className={cn("absolute left-0 top-0 h-full w-[3px]", bar[tone])} aria-hidden />
      {icon ? <span className={cn("mt-0.5 shrink-0", iconTone[tone])}>{icon}</span> : null}
      <div className="min-w-0 flex-1">
        {title ? <p className="text-[14px] font-semibold text-foreground">{title}</p> : null}
        {children ? <div className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{children}</div> : null}
      </div>
      {action ? <div className="shrink-0 self-start">{action}</div> : null}
    </div>
  );
}

export function Progress({ value, tone = "ai", className }: { value: number; tone?: string; className?: string }) {
  const colors: Record<string, string> = {
    ai: "bg-ai",
    support: "bg-support",
    caution: "bg-caution",
    contradict: "bg-contradict",
  };
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={cn("h-full rounded-full transition-all duration-200", colors[tone] ?? "bg-ai")} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-[var(--radius-card)] border border-dashed border-border bg-card/50 px-6 py-12 text-center">
      {icon ? <div className="text-muted-foreground">{icon}</div> : null}
      <div>
        <p className="text-[15px] font-semibold text-foreground">{title}</p>
        {description ? <p className="mx-auto mt-1 max-w-md text-[13px] text-muted-foreground">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="group/tt relative inline-flex">
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-2 hidden w-max max-w-xs -translate-x-1/2 rounded-[var(--radius-control)] border border-border bg-popover px-2.5 py-1.5 text-[12px] text-popover-foreground hairline-shadow group-hover/tt:block"
      >
        {label}
      </span>
    </span>
  );
}

