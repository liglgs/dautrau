"use client";

import Link from "next/link";
import { useState } from "react";
import { useApi, useMutation } from "./hooks";
import type { Case, DispatchRecord, Task } from "./types";
import { users } from "./mocks/seed";
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
  cx,
} from "./components/ui";

type DispatchQueueData = {
  dispatches: DispatchRecord[];
  cases: Case[];
  tasks: Task[];
};

export default function Dispatch() {
  const { data, error, load } = useApi<DispatchQueueData>("/dispatch/queue", true);
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [editReviewer, setEditReviewer] = useState("reviewer");
  const [editClinician, setEditClinician] = useState("clinician");
  const [editPriority, setEditPriority] = useState<"normal" | "high" | "urgent">("normal");
  const [notification, setNotification] = useState("");
  const mutation = useMutation();

  if (error) {
    return (
      <Panel>
        <PanelBody>
          <ErrorBox message={error} retry={load} />
        </PanelBody>
      </Panel>
    );
  }

  if (!data) {
    return (
      <Panel>
        <PanelBody>
          <Empty>Đang tải danh sách điều phối và hàng đợi phân công…</Empty>
        </PanelBody>
      </Panel>
    );
  }

  const reviewers = users.filter((u) => u.role === "reviewer" || u.role === "clinician");
  const clinicians = users.filter((u) => u.role === "clinician");

  const openAssignModal = (c: Case) => {
    setSelectedCase(c);
    const disp = data.dispatches.find((d) => d.case_id === c.id);
    setEditReviewer(disp?.assigned_reviewer ?? c.assigned[0] ?? "reviewer");
    setEditClinician(disp?.assigned_clinician ?? c.assigned[1] ?? "clinician");
    setEditPriority(disp?.priority ?? "normal");
  };

  const handleSaveAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    try {
      await mutation.run("/dispatch/assign", {
        case_id: selectedCase.id,
        assigned_reviewer: editReviewer,
        assigned_clinician: editClinician,
        priority: editPriority,
      });
      setSelectedCase(null);
      setNotification(`Đã phân công ca ${selectedCase.id} cho ${users.find((u) => u.id === editReviewer)?.name}.`);
      setTimeout(() => setNotification(""), 3500);
      await load();
    } catch {
      // Handled by mutation hook
    }
  };

  const openTasks = data.tasks.filter((t) => t.status === "open");
  const highPriorityCount = data.dispatches.filter(
    (d) => d.priority === "urgent" || d.priority === "high",
  ).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Điều phối kíp trực & phân bổ ca"
        title="Trung tâm Phân phối Ca Bệnh & Nhiệm vụ"
        description="Phân công dược sĩ lâm sàng rà soát, chỉ định bác sĩ duyệt và điều phối các tác vụ xác minh"
        actions={
          <>
            <Button variant="secondary" icon="refresh" onClick={load} title="Làm mới hàng đợi">
              Cập nhật
            </Button>
            <Link
              href="/cases"
              className="inline-flex items-center gap-1.5 rounded-[10px] border border-line bg-surface px-3 py-1.5 text-[12.5px] font-semibold text-ink no-underline hover:border-line-strong"
            >
              Xem danh sách ca →
            </Link>
          </>
        }
      />

      {notification && (
        <Notice tone="ok" role="status">
          ✓ {notification}
        </Notice>
      )}

      {/* Overview Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-[14px] border border-line bg-surface p-4 text-[10.5px] font-bold tracking-[0.1em] text-muted">
          TỔNG CA ĐIỀU PHỐI
          <strong className="mt-1.5 block text-[26px] leading-none font-bold text-ink">
            {data.cases.length}
          </strong>
        </div>
        <div className="rounded-[14px] border border-line bg-surface p-4 text-[10.5px] font-bold tracking-[0.1em] text-muted">
          CA CẦN RÀ SOÁT / KHẨN CẤP
          <strong className="mt-1.5 block text-[26px] leading-none font-bold text-ink">
            {highPriorityCount}
          </strong>
        </div>
        <div className="rounded-[14px] border border-line bg-surface p-4 text-[10.5px] font-bold tracking-[0.1em] text-muted">
          NHIỆM VỤ XÁC MINH ĐANG MỞ
          <strong className="mt-1.5 block text-[26px] leading-none font-bold text-warn">
            {openTasks.length}
          </strong>
        </div>
      </div>

      {/* Case Dispatch Table */}
      <Panel className="overflow-hidden">
        <PanelHead
          eyebrow="Danh sách phân công"
          title="Phân bổ Kíp trực theo Ca bệnh"
          description="Mỗi ca yêu cầu tối thiểu 1 Dược sĩ rà soát và 1 Bác sĩ duyệt"
        />

        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] border-collapse text-[13px]">
            <thead>
              <tr className="bg-surface-2 text-left text-[10px] font-bold tracking-[0.1em] text-muted uppercase">
                <th className="min-w-[180px] px-5 py-3">Ca / Bệnh nhân</th>
                <th className="min-w-[130px] px-5 py-3">Mức độ ưu tiên</th>
                <th className="min-w-[170px] px-5 py-3">Dược sĩ rà soát</th>
                <th className="min-w-[170px] px-5 py-3">Bác sĩ phê duyệt</th>
                <th className="min-w-[130px] px-5 py-3">Trạng thái</th>
                <th className="min-w-[170px] px-5 py-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {data.cases.map((c) => {
                const disp = data.dispatches.find((d) => d.case_id === c.id);
                const reviewerObj = users.find(
                  (u) => u.id === (disp?.assigned_reviewer ?? c.assigned[0]),
                );
                const clinicianObj = users.find(
                  (u) => u.id === (disp?.assigned_clinician ?? c.assigned[1]),
                );
                const priority = disp?.priority ?? "normal";

                return (
                  <tr key={c.id} className="border-t border-line align-top">
                    <td className="px-5 py-4">
                      <strong className="block text-[13.5px] text-ink">{c.id}</strong>
                      <small className="block text-[11.5px] text-muted">
                        {c.patient_id} · {c.encounter_id}
                      </small>
                      <small className="mt-1 block text-[11px] text-muted">
                        Kịch bản:{" "}
                        {c.scenario === "matched"
                          ? "Khớp dữ liệu"
                          : c.scenario === "verification"
                            ? "Xác minh đơn cũ"
                            : "Nguồn bổ sung"}
                      </small>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={cx(
                          "inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                          priority === "urgent"
                            ? "bg-err-soft text-err-ink"
                            : priority === "high"
                              ? "bg-warn-soft text-warn"
                              : "bg-surface-2 text-ink-soft",
                        )}
                      >
                        {priority === "normal"
                          ? "Bình thường"
                          : priority === "high"
                            ? "Ưu tiên cao"
                            : "Khẩn cấp"}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span className="font-semibold text-brand-ink">
                        👤 {reviewerObj?.name ?? "Chưa phân công"}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span className="font-semibold text-ink">
                        🩺 {clinicianObj?.name ?? "Chưa chỉ định"}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <Badge value={c.lifecycle} />
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => openAssignModal(c)}
                        >
                          Phân công ✎
                        </Button>
                        <Link
                          href={`/cases/${c.id}`}
                          className="inline-flex items-center gap-1 rounded-[8px] border border-line bg-surface px-2.5 py-1 text-[12px] font-semibold text-ink no-underline hover:border-line-strong"
                        >
                          Mở ca →
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Verification Queue Section */}
      <Panel className="overflow-hidden">
        <PanelHead
          eyebrow="Hàng đợi xác minh lâm sàng toàn viện"
          title="Nhiệm vụ đang giao cho Điều dưỡng / Người phản hồi"
          description="Tự động kích hoạt khi phát hiện khoảng trống thông tin"
        />

        <PanelBody>
          {openTasks.length === 0 ? (
            <Empty>
              Không có nhiệm vụ xác minh nào đang mở. Tất cả câu hỏi đã được trả lời!
            </Empty>
          ) : (
            <div className="grid gap-3">
              {openTasks.map((t) => (
                <div
                  key={t.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-[12px] border border-line bg-surface-2 p-4"
                >
                  <div className="min-w-0 flex-1">
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <strong className="text-brand-ink">{t.id}</strong>
                      <span className="rounded-full bg-warn-soft px-2 py-0.5 text-[11px] font-semibold text-warn">
                        Chờ phản hồi
                      </span>
                      <small className="text-muted">
                        Ca: {t.case_id} · Vấn đề: {t.issue_id}
                      </small>
                    </div>
                    <p className="text-[13px] font-semibold text-ink">{t.question}</p>
                    <small className="mt-1 block text-muted">
                      Giao cho:{" "}
                      <strong>
                        {users.find((u) => u.id === t.assignee)?.name ?? t.assignee}
                      </strong>{" "}
                      · Cần xác minh: {t.missing_fields.join(", ")}
                    </small>
                  </div>
                  <Link
                    href="/tasks"
                    className="inline-flex items-center rounded-[10px] bg-brand px-3.5 py-2 text-[12px] font-bold text-white no-underline transition-all hover:bg-brand-ink"
                  >
                    Phản hồi ngay →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </PanelBody>
      </Panel>

      {/* Assignment Modal */}
      {selectedCase && (
        <Modal
          title={`Phân công Ca ${selectedCase.id}`}
          onClose={() => setSelectedCase(null)}
        >
          <form onSubmit={handleSaveAssign} className="space-y-4 text-[13px]">
            <p className="text-muted">
              Bệnh nhân: <strong>{selectedCase.patient_id}</strong> · Đợt nhập viện:{" "}
              <strong>{selectedCase.encounter_id}</strong>
            </p>

            <label className="block space-y-1 font-semibold text-ink">
              <span>Dược sĩ lâm sàng rà soát (Reviewer)</span>
              <select
                value={editReviewer}
                onChange={(e) => setEditReviewer(e.target.value)}
                required
                className="w-full rounded-[8px] border border-line bg-surface-2 px-3 py-2 text-[13px] font-normal text-ink outline-none"
              >
                {reviewers.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.role})
                  </option>
                ))}
              </select>
            </label>

            <label className="block space-y-1 font-semibold text-ink">
              <span>Bác sĩ điều trị phê duyệt (Clinician)</span>
              <select
                value={editClinician}
                onChange={(e) => setEditClinician(e.target.value)}
                required
                className="w-full rounded-[8px] border border-line bg-surface-2 px-3 py-2 text-[13px] font-normal text-ink outline-none"
              >
                {clinicians.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.role})
                  </option>
                ))}
              </select>
            </label>

            <label className="block space-y-1 font-semibold text-ink">
              <span>Mức độ ưu tiên xử lý</span>
              <select
                value={editPriority}
                onChange={(e) =>
                  setEditPriority(e.target.value as "normal" | "high" | "urgent")
                }
                className="w-full rounded-[8px] border border-line bg-surface-2 px-3 py-2 text-[13px] font-normal text-ink outline-none"
              >
                <option value="normal">Bình thường (Ca khớp / thông thường)</option>
                <option value="high">Ưu tiên cao (Có khoảng trống thông tin)</option>
                <option value="urgent">
                  Khẩn cấp (Nguồn muộn / nghi ngờ xung đột nghiêm trọng)
                </option>
              </select>
            </label>

            {mutation.error && <ErrorBox message={mutation.error} />}

            <div className="flex justify-end gap-2.5 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setSelectedCase(null)}
              >
                Hủy bỏ
              </Button>
              <Button type="submit" variant="primary" disabled={mutation.busy}>
                {mutation.busy ? "Đang lưu…" : "Xác nhận phân công"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
