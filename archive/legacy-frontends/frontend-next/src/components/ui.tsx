"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { labels } from "../types";
import { Icon, type IconName } from "./icons";

export const cx = (...parts: Array<string | false | null | undefined>) =>
  parts.filter(Boolean).join(" ");

/* ------------------------------------------------------------------ *
 * Trạng thái → tông màu. Nhãn chữ luôn hiển thị (không chỉ dựa màu).
 * ------------------------------------------------------------------ */
export type Tone = "neutral" | "brand" | "ok" | "warn" | "danger" | "info";

const okStates = new Set([
  "approved",
  "closed",
  "completed",
  "confirmed_information_resolved",
  "confirmed_no_difference",
  "confirmed_intentional",
  "documented_explanation",
  "online",
  "answered",
  "acknowledged",
]);

const warnStates = new Set([
  "changes_pending",
  "waiting_event",
  "waiting_response",
  "budget_exhausted",
  "high",
  "handed_off",
  "escalated",
]);

const dangerStates = new Set([
  "failed",
  "urgent",
  "error",
  "confirmed_unintentional",
]);

const infoStates = new Set([
  "draft",
  "reviewing",
  "queued",
  "running",
  "new",
  "investigating",
  "ready_for_review",
  "assigned",
  "unassigned",
  "in_progress",
  "open",
]);

const brandStates = new Set([
  "prior_prescription",
  "medication_history",
  "admission_order",
  "clinical_note",
  "verification_response",
]);

export function toneFor(value: string): Tone {
  if (okStates.has(value)) return "ok";
  if (dangerStates.has(value)) return "danger";
  if (warnStates.has(value)) return "warn";
  if (infoStates.has(value)) return "info";
  if (brandStates.has(value)) return "brand";
  return "neutral";
}

const tonePill: Record<Tone, string> = {
  neutral: "border-line bg-surface-2 text-ink-soft",
  brand: "border-brand/30 bg-brand-soft text-brand-ink",
  ok: "border-ok/30 bg-ok-soft text-ok",
  warn: "border-warn/30 bg-warn-soft text-warn",
  danger: "border-danger/30 bg-danger-soft text-danger",
  info: "border-info/30 bg-info-soft text-info",
};

const toneDot: Record<Tone, string> = {
  neutral: "bg-muted",
  brand: "bg-brand",
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
  info: "bg-info",
};

export function Badge({ value }: { value: string }) {
  const tone = toneFor(value);
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] text-[11px] font-semibold whitespace-nowrap",
        tonePill[tone],
      )}
    >
      <span className={cx("size-1.5 rounded-full", toneDot[tone])} aria-hidden="true" />
      {labels[value] ?? value}
    </span>
  );
}

export function StatusPill({
  tone = "neutral",
  children,
  icon,
}: {
  tone?: Tone;
  children: ReactNode;
  icon?: IconName;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11.5px] font-semibold",
        tonePill[tone],
      )}
    >
      {icon && <Icon name={icon} className="size-3.5" />}
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Button — một nguồn duy nhất cho nút và liên kết dạng nút.
 * ------------------------------------------------------------------ */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "subtle";
export type ButtonSize = "sm" | "md" | "lg";

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-teal-600 to-emerald-600 text-white font-bold border border-teal-500/30 hover:from-teal-500 hover:to-emerald-500 shadow-md shadow-teal-500/20 active:scale-[0.98] transition-all duration-150",
  secondary:
    "bg-surface text-ink-soft border border-line hover:border-line-strong hover:bg-surface-2 active:scale-[0.98] transition-all duration-150 shadow-sm",
  ghost: "bg-transparent text-ink-soft border border-transparent hover:bg-surface-2 active:scale-[0.98] transition-all",
  danger:
    "bg-gradient-to-r from-rose-600 to-red-600 text-white font-bold border border-rose-500/30 hover:from-rose-500 hover:to-red-500 shadow-md shadow-rose-500/20 active:scale-[0.98] transition-all duration-150",
  subtle:
    "bg-brand-soft text-brand-ink border border-brand/20 hover:bg-brand-soft/80 active:scale-[0.98] transition-all duration-150 font-bold",
};

const sizeClass: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-[12px] rounded-[9px] gap-1.5",
  md: "h-9.5 px-4 text-[13px] rounded-xl gap-2",
  lg: "h-11 px-5 text-[14px] rounded-xl gap-2.5",
};

export function buttonClass(
  variant: ButtonVariant = "secondary",
  size: ButtonSize = "md",
  className?: string,
) {
  return cx(
    "inline-flex items-center justify-center font-semibold transition-colors duration-150 no-underline disabled:cursor-not-allowed disabled:opacity-50",
    variantClass[variant],
    sizeClass[size],
    className,
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  busy,
  icon,
  iconRight,
  className,
  children,
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  busy?: boolean;
  icon?: IconName;
  iconRight?: IconName;
}) {
  return (
    <button
      type={type}
      className={buttonClass(variant, size, className)}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? (
        <Icon name="spinner" className="size-3.5 animate-spin" />
      ) : (
        icon && <Icon name={icon} className="size-4" />
      )}
      {children}
      {iconRight && <Icon name={iconRight} className="size-4" />}
    </button>
  );
}

export function IconButton({
  name,
  label,
  className,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { name: IconName; label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cx(
        "inline-grid size-9 place-items-center rounded-[10px] border border-line bg-surface text-ink-soft transition-colors hover:border-line-strong hover:bg-surface-2",
        className,
      )}
      {...rest}
    >
      <Icon name={name} className="size-4" />
    </button>
  );
}

/* ------------------------------------------------------------------ *
 * Khung nội dung
 * ------------------------------------------------------------------ */
export function Panel({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={cx(
        "rounded-[var(--radius-card)] border border-line bg-surface shadow-[var(--shadow-card)] transition-shadow duration-200 hover:shadow-[var(--shadow-card-hover)]",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function PanelHead({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cx(
        "flex flex-wrap items-start justify-between gap-3 border-b border-line/80 px-6 py-4.5 bg-surface-2/40",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-1 text-[10.5px] font-bold tracking-[0.14em] text-brand-ink uppercase">
            {eyebrow}
          </p>
        )}
        <h2 className="text-ink font-heading text-[16px]">{title}</h2>
        {description && <p className="mt-1 text-[12px] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function PanelBody({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return <div className={cx("px-6 py-5", className)}>{children}</div>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-line/50 pb-5">
      <div className="min-w-0">
        <div className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand-soft px-3 py-1 text-[10.5px] font-bold tracking-[0.12em] text-brand-ink uppercase">
          <span className="size-1.5 rounded-full bg-brand" />
          {eyebrow}
        </div>
        <h1 className="mt-2.5 font-heading tracking-tight text-ink">{title}</h1>
        {description && (
          <p className="mt-2 max-w-3xl text-[13.5px] text-muted leading-relaxed">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5">{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  sub,
  tone = "brand",
  icon,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  tone?: Tone;
  icon?: IconName;
}) {
  return (
    <div className="card-lift relative overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-bold tracking-[0.12em] text-muted uppercase">
          {label}
        </p>
        {icon && (
          <span
            className={cx(
              "grid size-9 place-items-center rounded-xl border shadow-sm transition-transform group-hover:scale-105",
              tonePill[tone],
            )}
          >
            <Icon name={icon} className="size-4.5" />
          </span>
        )}
      </div>
      <p
        className={cx(
          "mt-3.5 text-[32px] font-heading leading-none font-extrabold tracking-tight",
          tone === "ok" && "text-ok",
          tone === "warn" && "text-warn",
          tone === "danger" && "text-danger",
          tone === "brand" && "text-brand",
          tone === "info" && "text-info",
          tone === "neutral" && "text-ink",
        )}
      >
        {value}
      </p>
      {sub && <div className="mt-2.5 text-[12px] text-muted flex items-center gap-1.5">{sub}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Trạng thái tải / rỗng / lỗi (gate-1: có skeleton, không ô trống)
 * ------------------------------------------------------------------ */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("skeleton h-4 w-full", className)} aria-hidden="true" />;
}

export function LoadingPanel({ rows = 3, label }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite">
      <span className="sr-only">{label ?? "Đang tải…"}</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center gap-3">
          <Skeleton className="size-9 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function Empty({ children, icon = "inbox" }: { children: ReactNode; icon?: IconName }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-[var(--radius-control)] border border-dashed border-line-strong bg-surface-2 px-6 py-8 text-center text-[13px] text-muted">
      <span className="grid size-10 place-items-center rounded-full border border-line bg-surface text-muted">
        <Icon name={icon} className="size-5" />
      </span>
      <div>{children}</div>
    </div>
  );
}

export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-[var(--radius-control)] border border-danger/35 bg-danger-soft px-4 py-3 text-[13px] font-medium text-danger"
    >
      <Icon name="alert" className="size-4 shrink-0" />
      <span className="flex-1">{message}</span>
      {retry && (
        <Button size="sm" variant="secondary" icon="refresh" onClick={retry}>
          Thử lại
        </Button>
      )}
    </div>
  );
}

export function Notice({
  children,
  tone = "info",
  role,
}: {
  children: ReactNode;
  tone?: Tone;
  role?: "status" | "alert";
}) {
  return (
    <div
      role={role}
      className={cx(
        "flex items-start gap-2.5 rounded-[var(--radius-control)] border px-4 py-3 text-[12.5px] leading-relaxed",
        tonePill[tone],
      )}
    >
      <Icon name="info" className="mt-0.5 size-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Modal / Drawer — giữ <dialog> + showModal() để Esc, focus trap và
 * trả focus hoạt động như bản cũ; nút đóng luôn có nhãn "Đóng panel".
 * ------------------------------------------------------------------ */
export function Modal({
  title,
  children,
  onClose,
  variant,
  footer,
  wide,
}: {
  title: ReactNode;
  children: ReactNode;
  onClose: () => void;
  variant?: "drawer";
  footer?: ReactNode;
  wide?: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const previous = useRef<HTMLElement | null>(null);
  const titleId = useId();

  useEffect(() => {
    previous.current = document.activeElement as HTMLElement;
    const node = dialog.current!;
    if (!node.open) node.showModal();
    return () => {
      node.close();
      queueMicrotask(() => {
        if (previous.current?.isConnected) previous.current.focus();
      });
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className={cx(
        "m-auto border border-line bg-surface p-0 text-ink shadow-[var(--shadow-pop)] backdrop:bg-[rgba(9,24,36,0.55)] backdrop:backdrop-blur-[2px]",
        variant === "drawer"
          ? "fixed inset-y-0 right-0 left-auto m-0 h-dvh max-h-none w-[min(640px,100vw)] rounded-none border-y-0 border-r-0"
          : cx(
              "max-h-[92dvh] rounded-[18px]",
              wide ? "w-[min(940px,94vw)]" : "w-[min(680px,92vw)]",
            ),
      )}
    >
      <div className="flex h-full flex-col">
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <h2 id={titleId} className="text-ink">
            {title}
          </h2>
          <IconButton
            name="close"
            label="Đóng panel"
            onClick={onClose}
            className="border-transparent bg-transparent hover:bg-surface-2"
          />
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <footer className="border-t border-line bg-surface-2 px-5 py-3">{footer}</footer>
        )}
      </div>
    </dialog>
  );
}

/* ------------------------------------------------------------------ *
 * Thanh chuyển mục trong màn (giữ role button để không đổi cách
 * truy vấn hiện có của kiểm thử).
 * ------------------------------------------------------------------ */
export function TabBar<K extends string>({
  tabs,
  active,
  onChange,
  label,
}: {
  tabs: { key: K; label: string; icon?: IconName }[];
  active: K;
  onChange: (key: K) => void;
  label: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="flex flex-wrap items-center gap-1.5 rounded-[12px] border border-line bg-surface-2 p-1.5"
    >
      {tabs.map((tab) => {
        const selected = tab.key === active;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.key)}
            className={cx(
              "inline-flex items-center gap-2 rounded-[9px] px-3.5 py-2 text-[12.5px] font-semibold transition-colors",
              selected
                ? "bg-surface text-brand shadow-[0_1px_2px_rgba(16,42,60,0.08)]"
                : "text-muted hover:text-ink-soft",
            )}
          >
            {tab.icon && <Icon name={tab.icon} className="size-4" />}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function ProgressRing({
  value,
  size = 118,
  label,
}: {
  value: number;
  size?: number;
  label: string;
}) {
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--line)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--brand)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (clamped / 100) * circumference}
        />
      </svg>
      <div className="absolute text-center">
        <p className="text-[22px] font-bold text-ink">{clamped}%</p>
        <p className="text-[10px] font-semibold tracking-wide text-muted uppercase">{label}</p>
      </div>
    </div>
  );
}

export function Avatar({
  name,
  tone = "brand",
  size = "md",
  className,
}: {
  name: string;
  tone?: Tone;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  return (
    <span
      title={name}
      className={cx(
        "inline-grid shrink-0 place-items-center rounded-full border font-bold",
        tonePill[tone],
        size === "sm" && "size-7 text-[10px]",
        size === "md" && "size-9 text-[12px]",
        size === "lg" && "size-11 text-[14px]",
        className,
      )}
    >
      {name
        .split(/[\s·]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase() ?? "")
        .join("")}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Thông báo dùng vùng trạng thái (gate-1: không tự chuyển màn).
 * ------------------------------------------------------------------ */
type ToastItem = { id: string; message: string; tone: Tone };
const ToastContext = createContext<(message: string, tone?: Tone) => void>(() => {});

export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const notify = useCallback((message: string, tone: Tone = "ok") => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    setItems((prev) => [...prev, { id, message, tone }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id));
    }, 4200);
  }, []);
  const value = useMemo(() => notify, [notify]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      {items.length > 0 && (
        <div
          aria-live="polite"
          className="pointer-events-none fixed bottom-5 left-1/2 z-50 flex w-[min(520px,92vw)] -translate-x-1/2 flex-col gap-2"
        >
        {items.map((item) => (
          <div
            key={item.id}
            className={cx(
              "pointer-events-auto flex items-start gap-2.5 rounded-[12px] border px-4 py-3 text-[12.5px] font-semibold shadow-[var(--shadow-pop)]",
              tonePill[item.tone],
            )}
          >
            <Icon
              name={item.tone === "danger" ? "alert" : "checkCircle"}
              className="mt-px size-4 shrink-0"
            />
            <span>{item.message}</span>
          </div>
        ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}




