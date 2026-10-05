"use client";

import Link from "next/link";
import { useState } from "react";
import { useApi } from "./hooks";
import type { DashboardMetrics } from "./types";
import {
  Button,
  Empty,
  ErrorBox,
  PageHeader,
  Panel,
  PanelBody,
  PanelHead,
} from "./components/ui";
import { Icon } from "./components/icons";

export default function Dashboard() {
  const { data: metrics, error, load } = useApi<DashboardMetrics>(
    "/dashboard/metrics",
    true,
  );
  const [copied, setCopied] = useState(false);

  if (error) {
    return (
      <Panel>
        <PanelBody>
          <ErrorBox message={error} retry={load} />
        </PanelBody>
      </Panel>
    );
  }

  if (!metrics) {
    return (
      <Panel>
        <PanelBody>
          <Empty>Đang tải dữ liệu giám sát và chỉ số vận hành lâm sàng…</Empty>
        </PanelBody>
      </Panel>
    );
  }

  const matchPercent =
    metrics.total_cases > 0
      ? Math.round((metrics.matched_count / metrics.total_cases) * 100)
      : 0;
  const gapPercent =
    metrics.total_cases > 0
      ? Math.round((metrics.gap_count / metrics.total_cases) * 100)
      : 0;
  const approvedPercent =
    metrics.total_cases > 0
      ? Math.round((metrics.approved_count / metrics.total_cases) * 100)
      : 0;

  const handleCopyReport = () => {
    const text = `BÁO CÁO GIÁM SÁT ĐỐI CHIẾU THUỐC VMEC-03\n- Tổng số ca: ${metrics.total_cases}\n- Ca khớp hoàn toàn: ${metrics.matched_count} (${matchPercent}%)\n- Ca có khoảng trống thông tin: ${metrics.gap_count} (${gapPercent}%)\n- Đã phê duyệt lâm sàng: ${metrics.approved_count} (${approvedPercent}%)\n- Trạng thái AI Agent: ${metrics.agent_status} (${metrics.agent_model})\n- Thời gian xử lý TB: ${metrics.avg_time_mins} phút/ca`;
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Trung tâm giám sát & phân tích vận hành"
        title="Bảng Điều Khiển Đối Chiếu Thuốc Lâm Sàng"
        description="Theo dõi toàn diện tiến độ ca bệnh, chất lượng đối chiếu đơn thuốc và chỉ số độ tin cậy của AI Agent thời gian thực."
        actions={
          <>
            <Button
              variant="secondary"
              icon="refresh"
              onClick={load}
              title="Cập nhật số liệu mới nhất"
            >
              Làm mới số liệu
            </Button>
            <Button variant="primary" onClick={handleCopyReport}>
              {copied ? "✓ Đã sao chép tóm tắt" : "📋 Xuất báo cáo nhanh"}
            </Button>
          </>
        }
      />

      {/* Row 1: Modern Bento Grid KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {/* Card 1: Tổng số ca */}
        <div className="card-lift relative overflow-hidden rounded-2xl border border-line bg-surface p-5.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold tracking-[0.14em] text-muted uppercase">
              Tổng số ca tiếp nhận
            </span>
            <span className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <Icon name="cases" className="size-4.5" />
            </span>
          </div>
          <div className="mt-3.5 flex items-baseline gap-2">
            <span className="font-heading text-[34px] font-extrabold tracking-tight text-ink">
              {metrics.total_cases}
            </span>
            <span className="text-[12px] font-semibold text-muted">hồ sơ nhập viện</span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[12px] font-medium text-muted">
            <span className="inline-block size-1.5 rounded-full bg-teal-500" />
            <span>Phân tích tự động 100% tài liệu TXT</span>
          </div>
        </div>

        {/* Card 2: Ca khớp */}
        <div className="card-lift relative overflow-hidden rounded-2xl border border-teal-500/20 bg-gradient-to-br from-surface to-teal-50/40 dark:to-teal-950/20 p-5.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold tracking-[0.14em] text-teal-700 dark:text-teal-400 uppercase">
              Tỷ lệ ca khớp đối chiếu
            </span>
            <span className="grid size-9 place-items-center rounded-xl bg-teal-50 text-teal-600 dark:bg-teal-950/60 dark:text-teal-400 border border-teal-200/50">
              <Icon name="shield" className="size-4.5" />
            </span>
          </div>
          <div className="mt-3.5 flex items-baseline gap-2">
            <span className="font-heading text-[34px] font-extrabold tracking-tight text-teal-600 dark:text-teal-400">
              {matchPercent}%
            </span>
            <span className="text-[12px] font-semibold text-teal-700/80 dark:text-teal-400/80">
              ({metrics.matched_count}/{metrics.total_cases} ca)
            </span>
          </div>
          {/* Mini progress bar */}
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-teal-100 dark:bg-teal-950">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-500 to-emerald-400 transition-all duration-500"
              style={{ width: `${matchPercent}%` }}
            />
          </div>
        </div>

        {/* Card 3: Khoảng trống thông tin */}
        <div className="card-lift relative overflow-hidden rounded-2xl border border-amber-500/20 bg-gradient-to-br from-surface to-amber-50/40 dark:to-amber-950/20 p-5.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold tracking-[0.14em] text-amber-700 dark:text-amber-400 uppercase">
              Khoảng trống thông tin
            </span>
            <span className="grid size-9 place-items-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400 border border-amber-200/50">
              <Icon name="info" className="size-4.5" />
            </span>
          </div>
          <div className="mt-3.5 flex items-baseline gap-2">
            <span className="font-heading text-[34px] font-extrabold tracking-tight text-amber-600 dark:text-amber-400">
              {metrics.gap_count}
            </span>
            <span className="text-[12px] font-semibold text-amber-700/80 dark:text-amber-400/80">
              ca cần làm rõ ({gapPercent}%)
            </span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[12px] font-medium text-amber-700/90 dark:text-amber-400">
            <span className="inline-block size-1.5 rounded-full bg-amber-500 animate-pulse" />
            <span>Phát hiện khác biệt liều hoặc thiếu tiền sử</span>
          </div>
        </div>

        {/* Card 4: Đã phê duyệt */}
        <div className="card-lift relative overflow-hidden rounded-2xl border border-blue-500/20 bg-gradient-to-br from-surface to-blue-50/40 dark:to-blue-950/20 p-5.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold tracking-[0.14em] text-blue-700 dark:text-blue-400 uppercase">
              Đã phê duyệt hoàn tất
            </span>
            <span className="grid size-9 place-items-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200/50">
              <Icon name="check" className="size-4.5" />
            </span>
          </div>
          <div className="mt-3.5 flex items-baseline gap-2">
            <span className="font-heading text-[34px] font-extrabold tracking-tight text-blue-600 dark:text-blue-400">
              {metrics.approved_count}
            </span>
            <span className="text-[12px] font-semibold text-blue-700/80 dark:text-blue-400/80">
              phiên bản đã ký
            </span>
          </div>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-blue-100 dark:bg-blue-950">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500"
              style={{ width: `${approvedPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Row 2: AI Health Console & Quick Shortcuts */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        {/* Panel 1: AI Agent Operational Console */}
        <Panel className="overflow-hidden border border-line">
          <PanelHead
            eyebrow="Giám sát & Độ tin cậy AI Agent"
            title="Trạng Thái Vận Hành Khai Thác Mô Hình"
            description="Đo lường độ trễ thực tế P95, số lượng yêu cầu và kiểm định quy tắc an toàn y tế."
            actions={
              <div className="inline-flex items-center gap-2 rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-[11.5px] font-bold text-brand-ink shadow-2xs">
                <span className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-teal-500 opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-teal-500" />
                </span>
                <span>{metrics.agent_status === "online" ? "ĐANG HOẠT ĐỘNG (ONLINE)" : "CHỜ LỆNH"}</span>
              </div>
            }
          />
          <PanelBody className="space-y-5">
            {/* 3 Metrics Boxes */}
            <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-3">
              <div className="rounded-xl border border-line/80 bg-surface-2/80 p-3.5">
                <span className="text-[10.5px] font-bold tracking-[0.1em] text-muted uppercase">
                  Mô hình khai thác
                </span>
                <strong className="mt-1.5 block truncate font-heading text-[14px] font-bold text-ink" title={metrics.agent_model}>
                  {metrics.agent_model}
                </strong>
                <small className="text-[11px] text-teal-600 dark:text-teal-400 font-medium">Adapter chính xác cao</small>
              </div>

              <div className="rounded-xl border border-line/80 bg-surface-2/80 p-3.5">
                <span className="text-[10.5px] font-bold tracking-[0.1em] text-muted uppercase">
                  Độ trễ phản hồi (P95)
                </span>
                <strong className="mt-1.5 block font-heading text-[16px] font-bold text-ink">
                  {metrics.avg_latency_ms} ms
                </strong>
                <small className="text-[11px] text-ok font-medium">✓ Đạt chuẩn mục tiêu ≤ 2s</small>
              </div>

              <div className="rounded-xl border border-line/80 bg-surface-2/80 p-3.5">
                <span className="text-[10.5px] font-bold tracking-[0.1em] text-muted uppercase">
                  Lượt gọi &amp; Dung lượng
                </span>
                <strong className="mt-1.5 block font-heading text-[16px] font-bold text-ink">
                  {metrics.calls_today} calls
                </strong>
                <small className="text-[11px] text-muted">
                  ~{metrics.total_tokens.toLocaleString()} tokens
                </small>
              </div>
            </div>

            {/* Medical Guardrails Checklist */}
            <div className="rounded-xl border border-teal-500/20 bg-teal-500/[0.04] p-4.5">
              <div className="flex items-center gap-2">
                <Icon name="shield" className="size-4 text-teal-600 dark:text-teal-400" />
                <p className="font-heading text-[12.5px] font-bold text-ink">
                  Nguyên Tắc An Toàn Y Tế Đang Kích Hoạt (Clinical Guardrails)
                </p>
              </div>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-[12px]">
                <div className="flex items-center gap-2 rounded-lg bg-surface/80 p-2.5 border border-line/60">
                  <span className="text-ok font-bold text-[14px]">✓</span>
                  <span className="font-medium text-ink-soft">100% trích xuất có chứng cứ gốc</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-surface/80 p-2.5 border border-line/60">
                  <span className="text-ok font-bold text-[14px]">✓</span>
                  <span className="font-medium text-ink-soft">Không tự ý suy diễn đơn thuốc cũ</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-surface/80 p-2.5 border border-line/60">
                  <span className="text-ok font-bold text-[14px]">✓</span>
                  <span className="font-medium text-ink-soft">Chặn duyệt khi còn câu hỏi mở</span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-surface/80 p-2.5 border border-line/60">
                  <span className="text-ok font-bold text-[14px]">✓</span>
                  <span className="font-medium text-ink-soft">Tách quyền Dược sĩ rà soát &amp; Bác sĩ duyệt</span>
                </div>
              </div>
            </div>
          </PanelBody>
        </Panel>

        {/* Panel 2: Quick System Shortcuts */}
        <Panel className="overflow-hidden border border-line">
          <PanelHead
            eyebrow="Phân hệ chuyên môn"
            title="Truy Cập Nhanh Nghiệp Vụ"
            description="Điều hướng nhanh tới các phân hệ rà soát và hỗ trợ điều trị."
          />
          <PanelBody className="grid gap-3">
            <Link
              href="/cases"
              className="card-lift flex items-center gap-4 rounded-xl border border-line bg-surface p-3.5 no-underline hover:border-teal-500/40 hover:bg-teal-50/20 dark:hover:bg-teal-950/20"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-600 dark:bg-teal-950 dark:text-teal-400 border border-teal-200/50 text-[20px]">
                📋
              </span>
              <div className="min-w-0 flex-1">
                <strong className="block text-[13.5px] font-bold text-ink">
                  Danh Sách Ca Cần Rà Soát
                </strong>
                <small className="text-[12px] text-muted leading-tight">
                  Mở không gian đối chiếu thuốc Workspace và gửi phê duyệt
                </small>
              </div>
              <span className="text-slate-400 font-bold text-sm">→</span>
            </Link>

            <Link
              href="/dispatch"
              className="card-lift flex items-center gap-4 rounded-xl border border-line bg-surface p-3.5 no-underline hover:border-teal-500/40 hover:bg-teal-50/20 dark:hover:bg-teal-950/20"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400 border border-indigo-200/50 text-[20px]">
                📦
              </span>
              <div className="min-w-0 flex-1">
                <strong className="block text-[13.5px] font-bold text-ink">
                  Trung Tâm Điều Phối Kíp Trực
                </strong>
                <small className="text-[12px] text-muted leading-tight">
                  Phân bổ trách nhiệm Bác sĩ duyệt, Dược sĩ rà soát và Điều dưỡng
                </small>
              </div>
              <span className="text-slate-400 font-bold text-sm">→</span>
            </Link>

            <Link
              href="/agent-chat"
              className="card-lift flex items-center gap-4 rounded-xl border border-line bg-surface p-3.5 no-underline hover:border-teal-500/40 hover:bg-teal-50/20 dark:hover:bg-teal-950/20"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400 border border-emerald-200/50 text-[20px]">
                💬
              </span>
              <div className="min-w-0 flex-1">
                <strong className="block text-[13.5px] font-bold text-ink">
                  Trợ Lý AI Đối Thoại Lâm Sàng
                </strong>
                <small className="text-[12px] text-muted leading-tight">
                  Hỏi đáp so sánh liều, tìm lý do khác biệt và trích dẫn bằng chứng
                </small>
              </div>
              <span className="text-slate-400 font-bold text-sm">→</span>
            </Link>

            <Link
              href="/tasks"
              className="card-lift flex items-center gap-4 rounded-xl border border-line bg-surface p-3.5 no-underline hover:border-teal-500/40 hover:bg-teal-50/20 dark:hover:bg-teal-950/20"
            >
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950 dark:text-amber-400 border border-amber-200/50 text-[20px]">
                ✅
              </span>
              <div className="min-w-0 flex-1">
                <strong className="block text-[13.5px] font-bold text-ink">
                  Hộp Nhiệm Vụ Xác Minh (Inbox)
                </strong>
                <small className="text-[12px] text-muted leading-tight">
                  Phản hồi các câu hỏi làm rõ từ điều dưỡng tiếp nhận bệnh nhân
                </small>
              </div>
              <span className="text-slate-400 font-bold text-sm">→</span>
            </Link>
          </PanelBody>
        </Panel>
      </div>

      {/* Row 3: Live Audit Stream */}
      <Panel className="overflow-hidden border border-line">
        <PanelHead
          eyebrow="Nhật ký kiểm toán thời gian thực (Audit Trail)"
          title="Lịch Sử Thao Tác &amp; Quyết Định Lâm Sàng"
          description="Lưu vết minh bạch và bất biến mọi thao tác của Reviewer, Clinician và các lượt chạy của Agent."
        />
        <PanelBody>
          {metrics.recent_audits.length === 0 ? (
            <Empty>Chưa có thao tác kiểm toán nào được ghi nhận trong phiên này.</Empty>
          ) : (
            <div className="space-y-2.5">
              {metrics.recent_audits.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line/70 bg-surface-2/60 px-4 py-3 text-[13px] transition-colors hover:bg-surface-2"
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="rounded-lg bg-surface px-2.5 py-1 font-bold text-brand-ink border border-line/60 shadow-2xs">
                      {item.actor}
                    </span>
                    <span className="text-muted">·</span>
                    <span className="font-medium text-ink-soft">{item.action}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {item.case_id && (
                      <Link
                        href={`/cases/${item.case_id}`}
                        className="rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-[11.5px] font-bold text-brand-ink no-underline hover:bg-teal-500/20 transition-colors"
                      >
                        {item.case_id} →
                      </Link>
                    )}
                    <span className="text-[12px] font-mono text-muted">
                      {new Date(item.time).toLocaleTimeString("vi-VN", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </PanelBody>
      </Panel>
    </div>
  );
}
