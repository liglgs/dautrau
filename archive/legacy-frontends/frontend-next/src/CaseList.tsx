"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Case } from "./types";
import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  LoadingPanel,
  PageHeader,
  Panel,
  PanelBody,
  PanelHead,
  StatCard,
  buttonClass,
  cx,
} from "./components/ui";
import { Icon } from "./components/icons";
import { ImportForm } from "./forms";
import { useSession } from "../app/providers";

const lifecycleOrder: Record<string, number> = {
  changes_pending: 0,
  reviewing: 1,
  draft: 2,
  approved: 3,
};

export default function CaseList() {
  const router = useRouter();
  const params = useSearchParams();
  const { user } = useSession();
  const [importing, setImporting] = useState(false);
  const q = params.get("q") ?? "";
  const status = params.get("status") ?? "";
  const [cases, setCases] = useState<Case[]>();
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setError("");
    api<Case[]>("/cases")
      .then(setCases)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(load, [load]);

  const setParams = (next: { q?: string; status?: string }) => {
    const search = new URLSearchParams();
    const nextQ = next.q ?? "";
    const nextStatus = next.status ?? "";
    if (nextQ) search.set("q", nextQ);
    if (nextStatus) search.set("status", nextStatus);
    const query = search.toString();
    router.replace(query ? `/cases?${query}` : "/cases", { scroll: false });
  };

  const filtered = cases
    ?.filter(
      (c) =>
        (c.id.toLowerCase().includes(q.toLowerCase()) ||
          c.patient_id.toLowerCase().includes(q.toLowerCase())) &&
        (!status || c.lifecycle === status),
    )
    .sort(
      (a, b) =>
        lifecycleOrder[a.lifecycle] - lifecycleOrder[b.lifecycle] ||
        a.id.localeCompare(b.id),
    );

  const fromQuery = params.toString();

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Không gian làm việc lâm sàng"
        title="Danh Sách Ca Bệnh Cần Rà Soát"
        description="Quản lý và tiếp nhận hồ sơ nhập viện. Một ca bệnh tương ứng một đợt điều trị nhập viện cần đối chiếu đơn thuốc."
        actions={
          user?.role !== "admin" && (
            <Button variant="primary" icon="plus" onClick={() => setImporting(true)}>
              Nhập hồ sơ mô phỏng mới
            </Button>
          )
        }
      />

      {/* 3 Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Ca được phân công"
          value={cases?.length ?? "—"}
          icon="cases"
          sub="Phạm vi tài khoản đang trực"
          tone="brand"
        />
        <StatCard
          label="Đang rà soát lâm sàng"
          value={cases?.filter((c) => c.lifecycle === "reviewing").length ?? "—"}
          tone="warn"
          icon="activity"
          sub="Hồ sơ đang mở hoặc có việc mở"
        />
        <StatCard
          label="Đã ký duyệt hoàn tất"
          value={cases?.filter((c) => c.lifecycle === "approved").length ?? "—"}
          tone="ok"
          icon="checkCircle"
          sub="Đã có biên bản tổng hợp phê duyệt"
        />
      </div>

      {/* Main Filter & Case List Panel */}
      <Panel className="overflow-hidden border border-line">
        <PanelHead
          eyebrow="Bộ lọc & Hàng đợi ưu tiên"
          title="Hồ Sơ Ca Bệnh Của Tôi"
          description="Các ca bệnh có nguồn tài liệu mới (cần rà lại) được tự động ưu tiên hiển thị lên đầu danh sách."
        />

        {/* Search & Filter Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-2/40 px-6 py-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative">
              <input
                value={q}
                onChange={(e) => setParams({ q: e.target.value, status })}
                placeholder="Tìm theo mã ca (SIM-001) hoặc bệnh nhân…"
                className="h-9.5 w-[260px] rounded-xl border border-line bg-surface px-3.5 text-[13px] text-ink outline-none focus:border-brand shadow-2xs"
              />
            </div>
            <select
              value={status}
              onChange={(e) => setParams({ q, status: e.target.value })}
              className="h-9.5 rounded-xl border border-line bg-surface px-3 text-[13px] font-medium text-ink outline-none focus:border-brand shadow-2xs cursor-pointer"
            >
              <option value="">Tất cả trạng thái</option>
              <option value="draft">Chưa xử lý (Draft)</option>
              <option value="reviewing">Đang rà soát (Reviewing)</option>
              <option value="approved">Đã duyệt (Approved)</option>
              <option value="changes_pending">Cần rà lại (Changes Pending)</option>
            </select>
          </div>

          {(q || status) && (
            <Button variant="ghost" size="sm" icon="close" onClick={() => setParams({})}>
              Xóa bộ lọc
            </Button>
          )}
        </div>

        <PanelBody className="p-0">
          {error ? (
            <div className="p-6">
              <ErrorBox message={error} retry={load} />
            </div>
          ) : !cases ? (
            <div className="p-6">
              <LoadingPanel rows={3} label="Đang tải danh sách ca bệnh…" />
            </div>
          ) : !filtered?.length ? (
            <div className="p-8">
              <Empty icon={cases.length ? "search" : "inbox"}>
                {cases.length
                  ? "Không tìm thấy ca bệnh nào phù hợp với điều kiện lọc."
                  : "Hiện tại bạn chưa được phân công ca bệnh nào."}
              </Empty>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-[13px]">
                <thead>
                  <tr className="bg-surface-2/80 text-left text-[10.5px] font-bold tracking-[0.1em] text-muted uppercase border-b border-line">
                    <th className="px-6 py-3.5 min-w-[220px]">Ca bệnh / Bệnh nhân</th>
                    <th className="px-6 py-3.5 min-w-[150px]">Trạng thái hồ sơ</th>
                    <th className="hidden px-6 py-3.5 sm:table-cell min-w-[150px]">Tiến trình AI</th>
                    <th className="px-6 py-3.5 text-right min-w-[120px]">Hành động</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => {
                    const openWork = c.issues.filter(
                      (i) => !["closed", "handed_off"].includes(i.work_status),
                    ).length;
                    const handed = c.issues.filter((i) => i.work_status === "handed_off").length;
                    const isPending = c.lifecycle === "changes_pending";

                    return (
                      <tr
                        key={c.id}
                        className={cx(
                          "border-t border-line/70 align-top transition-colors hover:bg-surface-2/60",
                          isPending && "bg-amber-500/[0.04] border-l-4 border-l-amber-500",
                        )}
                      >
                        <td className="px-6 py-4.5">
                          <div className="flex items-center gap-2">
                            <span className="font-heading text-[15px] font-bold text-ink">
                              {c.id}
                            </span>
                            {isPending && (
                              <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10.5px] font-bold text-amber-700 dark:text-amber-400 border border-amber-500/20">
                                Nguồn mới
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-[12px] text-muted">
                            Mã BN: <strong>{c.patient_id}</strong> · Đợt: <strong>{c.encounter_id}</strong>
                          </p>
                          <div className="mt-1.5 flex items-center gap-2 text-[11.5px] text-ink-soft">
                            <span className={openWork > 0 ? "font-bold text-amber-600 dark:text-amber-400" : "text-muted"}>
                              {openWork} việc mở
                            </span>
                            <span className="text-muted">·</span>
                            <span className="text-muted">{handed} đã bàn giao</span>
                          </div>
                        </td>
                        <td className="px-6 py-4.5">
                          <Badge value={c.lifecycle} />
                          <small className="mt-1 block text-[11px] text-muted">
                            v{c.revision} ({c.sources.length} văn bản)
                          </small>
                        </td>
                        <td className="hidden px-6 py-4.5 sm:table-cell">
                          {c.run ? (
                            <Badge value={c.run.status} />
                          ) : (
                            <span className="text-[12px] text-muted">Chưa kích hoạt</span>
                          )}
                        </td>
                        <td className="px-6 py-4.5 text-right">
                          <Link
                            href={`/cases/${c.id}${
                              fromQuery ? `?from=${encodeURIComponent(fromQuery)}` : ""
                            }`}
                            className={buttonClass("primary", "sm", "shadow-sm")}
                          >
                            Mở Workspace →
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </PanelBody>
      </Panel>

      {importing && <ImportForm close={() => setImporting(false)} done={load} />}
    </div>
  );
}
