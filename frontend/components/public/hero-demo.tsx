"use client";

import * as React from "react";
import Link from "next/link";
import { LoaderCircle, Pause, Play, RefreshCcw, Sparkles, TriangleAlert, UserCheck } from "lucide-react";
import { Button, Chip } from "@/components/ui";
import { CitationChip, SourceChip } from "@/components/pv/badges";
import { useInspector } from "@/lib/store/inspector";
import { DEMO_EVIDENCE } from "@/lib/mock/seed";
import { cn } from "@/lib/utils";

interface HeroStep {
  label: string;
  detail: string;
  icon: React.ReactNode;
  tone: "ai" | "support" | "caution" | "scope";
}

const SCRIPT: HeroStep[] = [
  { label: "PubMed", detail: "3 tài liệu về metformin và nhiễm toan lactic", icon: <LoaderCircle className="h-3.5 w-3.5 animate-spin-slow" aria-hidden />, tone: "ai" },
  { label: "Đổi truy vấn", detail: "Biệt dược “Glucophage” không có kết quả → dùng tên hoạt chất", icon: <RefreshCcw className="h-3.5 w-3.5" aria-hidden />, tone: "ai" },
  { label: "DailyMed", detail: "Nhãn thuốc, mục 5: giới hạn liều 1.000 mg/ngày khi eGFR 30–44", icon: <LoaderCircle className="h-3.5 w-3.5" aria-hidden />, tone: "ai" },
  { label: "Lệch phạm vi", detail: "Nhận định nói ≥2.000 mg/ngày — bằng chứng nói tối đa 1.000 mg/ngày", icon: <TriangleAlert className="h-3.5 w-3.5" aria-hidden />, tone: "scope" },
  { label: "Chờ reviewer duyệt", detail: "Agent dừng ở checkpoint; dược sĩ lâm sàng quyết định cuối", icon: <UserCheck className="h-3.5 w-3.5" aria-hidden />, tone: "caution" },
];

const CLAIMS = [
  { drug: "Glucophage", event: "nhiễm toan lactic", population: "suy thận giai đoạn 3b", dose: "≥2.000 mg/ngày" },
  { drug: "telmisartan", event: "phù mạch", population: "người lớn", dose: "" },
  { drug: "thuốc D (minh họa)", event: "xuất huyết tiêu hóa", population: "mọi bệnh nhân", dose: "20 mg/ngày" },
];

/** Demo sống ở hero: chạy một lần khi tải trang, có nút phát lại/tạm dừng, tôn trọng prefers-reduced-motion. */
export function HeroDemo() {
  const [index, setIndex] = React.useState(0);
  const [playing, setPlaying] = React.useState(true);
  const [claimIndex, setClaimIndex] = React.useState(0);
  const openInspector = useInspector((state) => state.open);
  const reducedMotion = React.useMemo(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    [],
  );

  React.useEffect(() => {
    if (reducedMotion) {
      setIndex(SCRIPT.length - 1);
      setPlaying(false);
      return;
    }
    if (!playing) return;
    if (index >= SCRIPT.length) return;
    const timer = setTimeout(() => setIndex((value) => value + 1), 900);
    return () => clearTimeout(timer);
  }, [index, playing, reducedMotion]);

  const claim = CLAIMS[claimIndex];
  const evidence = DEMO_EVIDENCE["INV-0007"] ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-[1.05fr_1fr] lg:items-center">
      <div>
        <h1 className="font-display text-[36px] leading-[1.12] text-foreground sm:text-[46px]">
          Nhận định này đúng với ai, ở liều nào, trong nguồn nào?
        </h1>
        <p className="mt-4 max-w-[54ch] text-[17px] leading-[1.7] text-muted-foreground">
          VigiLens điều tra nhận định về an toàn thuốc trên PubMed, DailyMed và openFDA FAERS. Khi thiếu dữ liệu, agent tự đổi
          cách tìm; khi chưa đủ căn cứ, agent dừng lại. Dược sĩ lâm sàng luôn là người duyệt cuối.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link
            href="/app/investigations/new"
            className="inline-flex h-11 items-center rounded-[var(--radius-control)] bg-primary px-5 text-[15px] font-medium text-primary-foreground hover:bg-primary/90"
          >
            Bắt đầu điều tra
          </Link>
          <Link
            href="/examples/inv-0001-metformin"
            className="inline-flex h-11 items-center rounded-[var(--radius-control)] border border-input px-5 text-[15px] font-medium text-foreground hover:bg-muted"
          >
            Xem một ca mẫu
          </Link>
        </div>
        <ul className="mt-6 grid gap-2 text-[13px] text-muted-foreground sm:grid-cols-3">
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ai" aria-hidden /> Mỗi câu dẫn về nguồn
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-caution" aria-hidden /> Agent biết từ chối kết luận
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-support" aria-hidden /> Con người duyệt cuối
          </li>
        </ul>
      </div>

      <div className="hero-grid rounded-[var(--radius-card)] border border-border bg-card p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[12px] uppercase tracking-wide text-muted-foreground">Nhận định</p>
          <Chip tone="ai">
            <Sparkles className="h-3 w-3" aria-hidden /> AI đề xuất
          </Chip>
        </div>
        <p className="mt-2 text-[15px] leading-relaxed text-foreground">
          <span className="rounded-[4px] bg-muted px-1 font-medium">{claim.drug}</span> gây{" "}
          <span className="rounded-[4px] bg-muted px-1 font-medium">{claim.event}</span> ở{" "}
          <span className="rounded-[4px] bg-muted px-1 font-medium">{claim.population}</span>
          {claim.dose ? (
            <>
              , liều <span className="rounded-[4px] bg-muted px-1 font-medium">{claim.dose}</span>
            </>
          ) : null}
          .
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {CLAIMS.map((item, itemIndex) => (
            <button
              key={item.drug}
              type="button"
              onClick={() => {
                setClaimIndex(itemIndex);
                setIndex(0);
                setPlaying(true);
              }}
              className={cn(
                "rounded-[var(--radius-chip)] border px-2 py-0.5 text-[12px]",
                itemIndex === claimIndex ? "border-ai-border bg-ai-soft text-ai-fg" : "border-border text-muted-foreground hover:bg-muted",
              )}
            >
              {item.drug}
            </button>
          ))}
        </div>

        <div className="mt-4 border-t border-border pt-4">
          <div className="flex items-center justify-between">
            <p className="text-[13px] font-semibold text-foreground">Agent đang điều tra</p>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={() => setPlaying((value) => !value)}>
                {playing ? <Pause className="h-3.5 w-3.5" aria-hidden /> : <Play className="h-3.5 w-3.5" aria-hidden />}
                {playing ? "Tạm dừng" : "Tiếp tục"}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setIndex(0);
                  setPlaying(true);
                }}
              >
                <RefreshCcw className="h-3.5 w-3.5" aria-hidden /> Phát lại
              </Button>
            </div>
          </div>

          <ul className="mt-3 space-y-2">
            {SCRIPT.map((step, stepIndex) => {
              const visible = stepIndex < index;
              return (
                <li
                  key={step.label}
                  className={cn(
                    "flex items-start gap-2.5 rounded-[var(--radius-control)] border px-3 py-2 transition-all duration-200",
                    visible ? "border-border bg-card opacity-100" : "border-transparent bg-transparent opacity-0",
                  )}
                  aria-hidden={!visible}
                >
                  <span
                    className={cn(
                      "mt-0.5",
                      step.tone === "ai" && "text-ai",
                      step.tone === "scope" && "text-scope",
                      step.tone === "caution" && "text-caution",
                      step.tone === "support" && "text-support",
                    )}
                  >
                    {step.icon}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[13px] font-medium text-foreground">{step.label}</span>
                    <span className="block text-[12px] text-muted-foreground">{step.detail}</span>
                  </span>
                </li>
              );
            })}
          </ul>

          <div className="mt-4 flex items-center gap-2 border-t border-border pt-3">
            <span className="text-[12px] text-muted-foreground">Trích dẫn:</span>
            {evidence.slice(0, 3).map((item) => (
              <CitationChip
                key={item.id}
                label={item.label}
                onClick={() => openInspector({ investigationId: "INV-0007", evidence: item })}
                title={item.quotes[0]?.text.slice(0, 120)}
              />
            ))}
            <span className="ml-auto flex items-center gap-1.5">
              <SourceChip source="pubmed" />
              <SourceChip source="dailymed" />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
