"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import type { Assertion, Case, Evidence, Issue, Source } from "./types";
import { labels } from "./types";
import {
  Badge,
  Button,
  Empty,
  ErrorBox,
  Modal,
  Notice,
  PageHeader,
  Panel,
  PanelBody,
  PanelHead,
  StatusPill,
  TabBar,
  buttonClass,
  cx,
} from "./components/ui";
import { Icon } from "./components/icons";
import { useApi, useMutation } from "./hooks";
import { EditAssertion, ImportForm, IssueForm } from "./forms";
import AgentChat from "./AgentChat";
import { isLive } from "./lib/env";

const TABS = [
  { key: "medications", label: "Bảng đối chiếu thuốc", icon: "pill" },
  { key: "timeline", label: "Dòng thời gian sự kiện", icon: "clock" },
  { key: "audit", label: "Nhật ký kiểm toán", icon: "list" },
  { key: "sources", label: "Tài liệu nguồn", icon: "doc" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function EvidencePanel({ c, id, close }: { c: Case; id: string; close: () => void }) {
  const { data, error, load } = useApi<Evidence>(`/cases/${c.id}/evidence/${id}`);
  const source =
    data &&
    c.sources.find(
      (s) => s.source_id === data.source_id && s.version === data.version,
    );
  return (
    <Modal title="Trích Dẫn & Bằng Chứng Gốc" onClose={close} variant="drawer">
      {error ? (
        <ErrorBox message={error} retry={load} />
      ) : !data ? (
        <Empty>Đang nạp trích dẫn bằng chứng…</Empty>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-line pb-3">
            <span className="rounded-full bg-teal-500/10 px-3 py-1 font-mono text-[11px] font-bold text-teal-700 dark:text-teal-400 border border-teal-500/25">
              {data.source_id} · v{data.version}
            </span>
            <span className="text-[12px] font-medium text-muted">
              {source?.event_time ? new Date(source.event_time).toLocaleDateString("vi-VN") : "Thời điểm chưa rõ"}
            </span>
          </div>

          <div>
            <p className="text-[11px] font-bold tracking-[0.12em] text-muted uppercase">
              Tài liệu phát sinh
            </p>
            <p className="mt-1 font-heading text-[14.5px] font-bold text-ink">
              {source?.filename} · <span className="text-brand-ink">{source?.author_role}</span>
            </p>
          </div>

          <div>
            <p className="text-[11px] font-bold tracking-[0.12em] text-amber-700 dark:text-amber-400 uppercase">
              Đoạn trích chứng cứ trực tiếp
            </p>
            <div className="quote-block mt-2">
              <mark>{data.quote}</mark>
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold tracking-[0.12em] text-muted uppercase">
              Ngữ cảnh tài liệu xung quanh
            </p>
            <div className="quote-block mt-2 font-mono text-[12px] text-ink-soft">
              {data.context}
            </div>
          </div>

          <Notice tone="info">
            Trích dẫn được liên kết bất biến với mã băm sha256 của tài liệu gốc. Mở nguồn để đối chiếu tính xác thực y tế.
          </Notice>
        </div>
      )}
    </Modal>
  );
}

export default function Workspace({ caseId }: { caseId: string }) {
  const params = useSearchParams();
  const { data: c, error, load } = useApi<Case>(`/cases/${caseId}`, true);
  const [tab, setTab] = useState<TabKey>("medications");
  const [medFilter, setMedFilter] = useState<"all" | "history" | "order">("all");
  const [evidenceId, setEvidenceId] = useState<string>();
  const [source, setSource] = useState<Source>();
  const [runReason, setRunReason] = useState("");
  const [importing, setImporting] = useState(false);
  const [editing, setEditing] = useState<Assertion>();
  const [chatDrawerOpen, setChatDrawerOpen] = useState(false);
  const [form, setForm] = useState<{
    issue: Issue;
    kind: "confirm" | "task" | "handoff";
  }>();
  const mutation = useMutation();

  const receipt = params.get("receipt");
  const fromParam = params.get("from");
  const backHref =
    fromParam !== null && fromParam !== undefined
      ? `/cases${fromParam ? `?${fromParam}` : ""}`
      : "/cases";

  if (!c) {
    return (
      <div className="space-y-4">
        <Link href={backHref} className="inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-brand">
          <Icon name="arrowLeft" className="size-4" /> ← Quay lại danh sách ca
        </Link>
        <Panel>
          <PanelBody>
            <Empty>Đang tải không gian đối chiếu hồ sơ ca {caseId}…</Empty>
          </PanelBody>
        </Panel>
      </div>
    );
  }

  const open = c.issues.filter((i) => !["closed", "handed_off"].includes(i.work_status)).length;
  const closed = c.issues.filter((i) => i.work_status === "closed").length;
  const handed = c.issues.filter((i) => i.work_status === "handed_off").length;

  const act = async (path: string, revision: number, body?: unknown) => {
    const payload =
      body && typeof body === "object"
        ? { expected_revision: revision, ...body }
        : { expected_revision: revision };
    const ok = await mutation.run(path, payload);
    if (ok) await load();
  };

  const sourceButtons = (ids: string[]) =>
    ids.map((id) => (
      <button
        key={id}
        type="button"
        onClick={() => setEvidenceId(id)}
        className="inline-flex items-center gap-1 rounded-full border border-teal-500/30 bg-teal-50/60 dark:bg-teal-950/40 px-2.5 py-0.5 text-[11px] font-bold text-teal-700 dark:text-teal-300 hover:bg-teal-100 transition-colors shadow-2xs"
      >
        <span className="text-[10px]">↗</span> {id}
      </button>
    ));

  const filteredAssertions = c.assertions.filter((a) => {
    if (medFilter === "history") return a.side === "history";
    if (medFilter === "order") return a.side === "order";
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb */}
      <div>
        <Link
          href={backHref}
          className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1.5 text-[12px] font-semibold text-ink-soft shadow-xs no-underline hover:border-line-strong hover:bg-surface-2 transition-all"
        >
          <Icon name="arrowLeft" className="size-3.5" /> Quay lại danh sách ca
        </Link>
      </div>

      {/* Case Header Banner */}
      <div className="rounded-2xl border border-line bg-gradient-to-r from-surface via-surface to-teal-50/20 dark:to-teal-950/20 p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="rounded-full bg-teal-500/10 px-3 py-1 text-[11px] font-extrabold tracking-[0.1em] text-brand-ink uppercase border border-teal-500/20">
                Ca bệnh: {c.id}
              </span>
              <Badge value={c.lifecycle} />
              {c.run && <Badge value={c.run.status} />}
              <span className="rounded-full bg-surface-2 px-2.5 py-0.5 text-[11px] font-bold text-ink-soft border border-line">
                Phiên bản: v{c.revision}
              </span>
            </div>
            <h1 className="mt-3 font-heading text-[26px] font-extrabold text-ink tracking-tight">
              Bệnh nhân: {c.patient_id}
            </h1>
            <p className="mt-1 text-[12.5px] text-muted">
              Đợt nhập viện: <strong>{c.encounter_id}</strong> · Mốc đối chiếu:{" "}
              <strong>{new Date(c.reconciliation_at).toLocaleString("vi-VN")}</strong> · Nguồn tài liệu:{" "}
              <strong>{c.sources.length} văn bản TXT</strong>
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="subtle"
              icon="chat"
              onClick={() => setChatDrawerOpen(true)}
              title="Mở bảng hỏi đáp và trích xuất bằng chứng với Trợ lý AI Agent"
            >
              Hỏi AI về ca này
            </Button>
            <Button variant="secondary" icon="plus" onClick={() => setImporting(true)}>
              Bổ sung nguồn TXT
            </Button>
            <Link
              href={`/cases/${c.id}/review`}
              className={buttonClass("primary", "md", "shadow-md")}
            >
              Xem tổng hợp &amp; Ký duyệt →
            </Link>
          </div>
        </div>
      </div>

      {/* Alerts & Notifications */}
      {receipt && (
        <Notice tone="ok" role="status">
          ✓ {receipt}
        </Notice>
      )}
      {error && <ErrorBox message={error} retry={load} />}
      {mutation.error && <ErrorBox message={mutation.error} />}
      {c.lifecycle === "changes_pending" && (
        <Notice tone="warn">
          ⚠ Ca bệnh có nguồn tài liệu mới đến sau khi đã duyệt. Bản duyệt cũ được lưu trữ an toàn, cần rà soát lại trước khi phê duyệt phiên bản mới.
        </Notice>
      )}

      {/* 3 Status KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="card-lift rounded-2xl border border-line bg-surface p-4.5 shadow-2xs">
          <span className="text-[11px] font-bold tracking-[0.12em] text-muted uppercase">
            Vấn đề đang mở
          </span>
          <strong className="mt-2 block font-heading text-[28px] font-extrabold text-ink leading-none">
            {open}
          </strong>
          <span className="mt-2 block text-[11.5px] text-muted">Cần xác minh trước khi duyệt</span>
        </div>

        <div className="card-lift rounded-2xl border border-teal-500/20 bg-teal-50/30 dark:bg-teal-950/20 p-4.5 shadow-2xs">
          <span className="text-[11px] font-bold tracking-[0.12em] text-teal-700 dark:text-teal-400 uppercase">
            Đã giải quyết
          </span>
          <strong className="mt-2 block font-heading text-[28px] font-extrabold text-ok leading-none">
            {closed}
          </strong>
          <span className="mt-2 block text-[11.5px] text-ok">Đã đối chiếu hoặc xác nhận</span>
        </div>

        <div className="card-lift rounded-2xl border border-amber-500/20 bg-amber-50/30 dark:bg-amber-950/20 p-4.5 shadow-2xs">
          <span className="text-[11px] font-bold tracking-[0.12em] text-amber-700 dark:text-amber-400 uppercase">
            Bàn giao · Chưa giải quyết
          </span>
          <strong className="mt-2 block font-heading text-[28px] font-extrabold text-warn leading-none">
            {handed}
          </strong>
          <span className="mt-2 block text-[11.5px] text-amber-700 dark:text-amber-400">Đã bàn giao ca trực tiếp theo</span>
        </div>
      </div>

      {/* Two-Column Workspace Layout */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        {/* Main Left Column: Tabs Content */}
        <section className="min-w-0 space-y-4">
          <TabBar
            tabs={TABS.map((t) => ({ key: t.key, label: t.label, icon: t.icon }))}
            active={tab}
            onChange={setTab}
            label="Nội dung hồ sơ đối chiếu"
          />

          <Panel className="overflow-hidden border border-line">
            {tab === "medications" ? (
              <>
                <PanelHead
                  eyebrow="Bảng đối chiếu lâm sàng"
                  title="Danh Sách Thuốc &amp; Dữ Kiện Có Nguồn"
                  description="Dữ kiện đơn cũ dùng tại nhà và y lệnh nhập viện được đối chiếu đối sánh có bằng chứng trích xuất."
                  actions={
                    <div className="flex items-center gap-1.5 rounded-xl border border-line bg-surface-2 p-1 text-[11.5px] font-semibold">
                      <button
                        type="button"
                        onClick={() => setMedFilter("all")}
                        className={cx(
                          "rounded-lg px-2.5 py-1 transition-all",
                          medFilter === "all" ? "bg-surface text-ink font-bold shadow-xs" : "text-muted hover:text-ink",
                        )}
                      >
                        Tất cả ({c.assertions.length})
                      </button>
                      <button
                        type="button"
                        onClick={() => setMedFilter("history")}
                        className={cx(
                          "rounded-lg px-2.5 py-1 transition-all",
                          medFilter === "history" ? "bg-surface text-ink font-bold shadow-xs" : "text-muted hover:text-ink",
                        )}
                      >
                        Trước nhập viện
                      </button>
                      <button
                        type="button"
                        onClick={() => setMedFilter("order")}
                        className={cx(
                          "rounded-lg px-2.5 py-1 transition-all",
                          medFilter === "order" ? "bg-surface text-ink font-bold shadow-xs" : "text-muted hover:text-ink",
                        )}
                      >
                        Y lệnh nhập viện
                      </button>
                    </div>
                  }
                />

                {!filteredAssertions.length ? (
                  <PanelBody>
                    <Empty>Chưa có dữ kiện thuốc nào trong phân loại này.</Empty>
                  </PanelBody>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse text-[13px]">
                      <thead>
                        <tr className="bg-surface-2/80 text-left text-[10.5px] font-bold tracking-[0.1em] text-muted uppercase border-b border-line">
                          <th className="px-6 py-3.5 min-w-[220px]">Tên thuốc / Hoạt chất</th>
                          <th className="px-6 py-3.5 min-w-[150px]">Nguồn phát sinh</th>
                          <th className="px-6 py-3.5 min-w-[160px]">Liều &amp; Tần suất</th>
                          <th className="px-6 py-3.5 text-right min-w-[120px]">Thao tác</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredAssertions.map((a) => (
                          <tr key={a.id} className="border-t border-line/70 align-top transition-colors hover:bg-surface-2/40">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-2">
                                <span className="grid size-6 place-items-center rounded-md bg-teal-50 text-teal-600 dark:bg-teal-950 dark:text-teal-400 font-bold text-[11px]">
                                  💊
                                </span>
                                <strong className="font-heading text-[14px] text-ink">{a.name}</strong>
                              </div>
                              <small className="mt-1 block text-[11.5px] text-muted">
                                Mã sản phẩm: {a.product ?? "Chưa chuẩn hoá RxNorm"}
                              </small>
                              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                                <span className="text-[10px] font-bold text-muted uppercase">Bằng chứng:</span>
                                {sourceButtons(a.evidence_ids)}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span
                                className={cx(
                                  "inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-semibold border",
                                  a.side === "history"
                                    ? "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300"
                                    : "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950/60 dark:text-teal-300",
                                )}
                              >
                                {a.side === "history" ? "🏠 Trước nhập viện (Đơn cũ)" : "🏥 Y lệnh nhập viện"}
                              </span>
                              <div className="mt-2">
                                <Badge value={a.assertion_type} />
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <p className="font-semibold text-ink text-[13px]">
                                {a.dose ?? "Chưa rõ liều lượng"}
                              </p>
                              <small className="mt-0.5 block text-[11.5px] text-muted">
                                Tần suất: {a.frequency ?? "Chưa rõ tần suất dùng"}
                              </small>
                            </td>
                            <td className="px-6 py-4 text-right">
                              <Button
                                size="sm"
                                variant="secondary"
                                icon="edit"
                                onClick={() => setEditing(a)}
                              >
                                Sửa
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            ) : tab === "sources" ? (
              <PanelBody className="space-y-3">
                <h3 className="font-heading text-[14px] font-bold text-ink">Danh Sách Văn Bản Nguồn TXT Đã Nhập</h3>
                <div className="grid gap-2.5">
                  {c.sources.map((s) => (
                    <div
                      key={`${s.source_id}-${s.version}`}
                      className="flex items-center justify-between rounded-xl border border-line bg-surface-2 p-3.5 transition-all hover:border-line-strong"
                    >
                      <div className="flex items-center gap-3">
                        <Icon name="doc" className="size-5 text-teal-600" />
                        <div>
                          <p className="font-bold text-ink text-[13px]">{s.filename}</p>
                          <small className="text-muted text-[11.5px]">
                            Phiên bản: v{s.version} · Vai trò: {s.author_role} · Thời điểm: {s.event_time ? new Date(s.event_time).toLocaleString("vi-VN") : "Chưa rõ"}
                          </small>
                        </div>
                      </div>
                      <Button size="sm" variant="secondary" onClick={() => setSource(s)}>
                        Xem nội dung gốc →
                      </Button>
                    </div>
                  ))}
                </div>
              </PanelBody>
            ) : tab === "timeline" ? (
              <PanelBody>
                <h3 className="mb-4 font-heading text-[14px] font-bold text-ink">Trình Tự Thời Gian Xuất Hiện Tài Liệu</h3>
                <ol className="relative space-y-4 border-l-2 border-teal-500/30 pl-5.5 ml-2">
                  {[...c.sources]
                    .sort((a, b) =>
                      (a.event_time ?? "z").localeCompare(b.event_time ?? "z"),
                    )
                    .map((s) => (
                      <li key={`${s.source_id}-${s.version}`} className="relative">
                        <span className="absolute top-1 -left-[28px] size-3 rounded-full border-2 border-surface bg-teal-500 shadow-sm" />
                        <p className="text-[12.5px] font-bold text-ink">
                          {s.event_time
                            ? new Date(s.event_time).toLocaleString("vi-VN")
                            : "Không rõ thời điểm"}
                        </p>
                        <button
                          type="button"
                          onClick={() => setSource(s)}
                          className="mt-0.5 text-[12px] font-semibold text-brand-ink hover:underline"
                        >
                          📄 {s.filename} (Phiên bản v{s.version})
                        </button>
                      </li>
                    ))}
                </ol>
              </PanelBody>
            ) : (
              <PanelBody>
                <h3 className="mb-4 font-heading text-[14px] font-bold text-ink">Nhật Ký Kiểm Toán Thao Tác (Audit Trail)</h3>
                <ol className="relative space-y-3.5 border-l-2 border-line pl-5.5 ml-2">
                  {c.audit.map((entry, index) => (
                    <li key={index} className="relative text-[12.5px] text-ink-soft">
                      <span className="absolute top-1.5 -left-[28px] size-2.5 rounded-full border-2 border-surface bg-slate-400" />
                      {entry}
                    </li>
                  ))}
                </ol>
              </PanelBody>
            )}
          </Panel>
        </section>

        {/* Right Column: Issues & AI Co-pilot Trigger */}
        <section className="min-w-0 space-y-5">
          {/* Issue Tracking Panel */}
          <Panel className="overflow-hidden border border-line">
            <PanelHead
              eyebrow="Xung đột & Khoảng trống"
              title="Vấn Đề Lâm Sàng Cần Xử Lý"
              actions={
                <span className="grid size-7 place-items-center rounded-full bg-amber-500 text-[12px] font-bold text-white shadow-sm">
                  {open}
                </span>
              }
            />
            <PanelBody className="space-y-3.5">
              {!c.issues.length ? (
                <Empty>Hồ sơ đối chiếu hoàn toàn ăn khớp. Không có vấn đề mở.</Empty>
              ) : (
                c.issues.map((issue) => (
                  <article
                    key={issue.id}
                    className="card-lift rounded-xl border border-line bg-surface-2 p-4"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-heading text-[13.5px] font-bold text-ink leading-snug">
                        {issue.title}
                      </h4>
                      <Badge value={issue.work_status} />
                    </div>
                    <p className="mt-1 text-[11px] font-mono text-muted">{issue.id}</p>

                    <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] font-bold text-muted uppercase">Bằng chứng:</span>
                      {sourceButtons(issue.evidence_ids)}
                    </div>

                    {issue.confirmation && (
                      <div className="mt-2.5 rounded-lg bg-surface p-2.5 border border-line text-[11.5px] text-ink-soft">
                        <strong>Lý do xác nhận:</strong> {issue.confirmation.reason}
                      </div>
                    )}

                    <div className="mt-3.5 flex flex-wrap gap-2">
                      {!["closed", "handed_off"].includes(issue.work_status) && (
                        <>
                          <Button size="sm" onClick={() => setForm({ issue, kind: "task" })}>
                            Tạo yêu cầu xác minh
                          </Button>
                          <Button size="sm" onClick={() => setForm({ issue, kind: "confirm" })}>
                            Xác nhận
                          </Button>
                          <Button size="sm" onClick={() => setForm({ issue, kind: "handoff" })}>
                            Bàn giao ca
                          </Button>
                          <Button
                            size="sm"
                            variant="primary"
                            disabled={!issue.confirmation || mutation.busy}
                            onClick={() => act(`/issues/${issue.id}/close`, issue.revision)}
                          >
                            Đóng vấn đề
                          </Button>
                        </>
                      )}
                    </div>
                  </article>
                ))
              )}
            </PanelBody>
          </Panel>

          {/* AI Reconciliation Agent Box */}
          <Panel className="overflow-hidden border border-line">
            <PanelHead
              eyebrow="Tự động hoá đối chiếu"
              title="Khai Thác Trợ Lý AI VMEC-03"
            />
            <PanelBody className="space-y-4">
              <p className="text-[12px] text-muted leading-relaxed">
                {isLive
                  ? "AI tự động trích xuất các thực thể thuốc, so sánh liều dùng và phát hiện khoảng trống thông tin. Kết quả phải được Reviewer và Clinician thẩm định."
                  : "Mô phỏng quy trình xử lý kịch bản mẫu của đề tài VMEC-03."}
              </p>

              <Button
                variant="primary"
                className="w-full justify-center shadow-md"
                disabled={
                  (!isLive && (!c.scenario || c.extraction_pending)) ||
                  mutation.busy ||
                  c.lifecycle === "approved" ||
                  c.run?.status === "waiting_event" ||
                  (isLive &&
                    ["failed", "budget_exhausted"].includes(c.run?.status ?? "") &&
                    !runReason.trim())
                }
                onClick={async () => {
                  const result = await mutation.run(`/cases/${c.id}/runs`, {
                    expected_revision: c.revision,
                    ...(runReason.trim() ? { reason: runReason.trim() } : {}),
                  });
                  if (result) {
                    setRunReason("");
                    await load();
                  }
                }}
              >
                {isLive
                  ? c.run?.status === "failed"
                    ? "Chạy lại trợ lý AI"
                    : "Chạy trợ lý AI phân tích"
                  : "Chạy kịch bản mẫu đối chiếu"}
              </Button>

              <div className="pt-2 border-t border-line/60">
                <Link
                  href="/tasks"
                  className="flex items-center justify-between text-[12.5px] font-semibold text-brand-ink hover:underline no-underline"
                >
                  <span>Mở hàng đợi xác minh &amp; bàn giao</span>
                  <span>→</span>
                </Link>
              </div>
            </PanelBody>
          </Panel>

          <Notice tone="warn">
            <strong>Lưu ý lâm sàng:</strong> Tương tác thuốc chưa được đánh giá. Đơn thuốc cũ không tự chứng minh người bệnh đang sử dụng tại nhà.
          </Notice>
        </section>
      </div>

      {/* Modals & Drawers */}
      {evidenceId && (
        <EvidencePanel
          c={c}
          id={evidenceId}
          close={() => setEvidenceId(undefined)}
        />
      )}

      {source && (
        <Modal
          title={source.filename}
          onClose={() => setSource(undefined)}
          variant="drawer"
        >
          <p className="text-[12px] font-semibold text-muted">
            {labels[source.kind]} · v{source.version}
          </p>
          <div className="doc mt-3 whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-ink bg-surface-2 p-3.5 rounded-xl border border-line">
            {source.text}
          </div>
        </Modal>
      )}

      {importing && (
        <ImportForm c={c} close={() => setImporting(false)} done={load} />
      )}

      {editing && (
        <EditAssertion
          c={c}
          assertion={editing}
          close={() => setEditing(undefined)}
          done={load}
        />
      )}

      {form && (
        <IssueForm
          c={c}
          issue={form.issue}
          kind={form.kind}
          close={() => setForm(undefined)}
          done={load}
        />
      )}

      {chatDrawerOpen && (
        <Modal
          title={`Trợ lý AI · Đối chiếu Ca ${c.id}`}
          onClose={() => setChatDrawerOpen(false)}
          variant="drawer"
        >
          <div className="h-[calc(100vh-120px)] pt-2.5">
            <AgentChat caseId={c.id} />
          </div>
        </Modal>
      )}
    </div>
  );
}
