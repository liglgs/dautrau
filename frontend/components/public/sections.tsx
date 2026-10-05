import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: { href: string; label: string }[];
}) {
  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto w-full max-w-[1200px] px-5 py-10 sm:py-14">
        {breadcrumb?.length ? (
          <nav aria-label="Breadcrumb" className="mb-3 text-[12px] text-muted-foreground">
            <ol className="flex flex-wrap items-center gap-2">
              {breadcrumb.map((crumb) => (
                <li key={crumb.href} className="flex items-center gap-2">
                  <Link href={crumb.href} className="hover:text-foreground">
                    {crumb.label}
                  </Link>
                  <span aria-hidden>/</span>
                </li>
              ))}
            </ol>
          </nav>
        ) : null}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="max-w-[62ch]">
            <h1 className="font-display text-[32px] leading-[1.15] text-foreground sm:text-[40px]">{title}</h1>
            {description ? <p className="mt-3 text-[16px] leading-relaxed text-muted-foreground">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
        </div>
      </div>
    </header>
  );
}

export function Section({
  title,
  description,
  children,
  className,
}: {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("mx-auto w-full max-w-[1200px] px-5 py-12", className)}>
      {title ? (
        <div className="mb-6 max-w-[62ch]">
          <h2 className="font-display text-[24px] text-foreground sm:text-[30px]">{title}</h2>
          {description ? <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">{description}</p> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Prose({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("max-w-[72ch] space-y-4 text-[16px] leading-[1.75] text-foreground", className)}>{children}</div>;
}

export function FeatureGrid({ items }: { items: { icon?: React.ReactNode; title: string; body: string }[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <div key={item.title} className="rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
          {item.icon ? <div className="mb-2 text-ai">{item.icon}</div> : null}
          <h3 className="text-[15px] font-semibold text-foreground">{item.title}</h3>
          <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{item.body}</p>
        </div>
      ))}
    </div>
  );
}

export function NumberedSteps({ steps }: { steps: { title: string; body: string }[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((step, index) => (
        <li key={step.title} className="flex gap-4 rounded-[var(--radius-card)] border border-border bg-card px-5 py-4">
          <span className="mono mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-[12px] text-muted-foreground">
            {index + 1}
          </span>
          <div>
            <h3 className="text-[15px] font-semibold text-foreground">{step.title}</h3>
            <p className="mt-1 text-[14px] leading-relaxed text-muted-foreground">{step.body}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
