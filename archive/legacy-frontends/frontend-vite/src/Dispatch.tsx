import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi, useMutation } from "./hooks";
import type { Case, DispatchRecord, Task } from "./types";
import { users } from "./mocks/seed";
import { Badge, Empty, ErrorBox, Modal } from "./components";

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
      <div className="panel panelbody">
        <ErrorBox message={error} retry={load} />
      </div>
    );
  }

  if (!data) {
    return <Empty>Đang tải danh sách điều phối và hàng đợi phân công…</Empty>;
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
      // handled by mutation
    }
  };

  const openTasks = data.tasks.filter((t) => t.status === "open");

  return (
    <>
      <div className="pagehead">
        <div>
          <p className="eyebrow">ĐIỀU PHỐI KÍP TRỰC & PHÂN BỔ CA</p>
          <h1>Trung tâm Phân phối Ca Bệnh & Nhiệm vụ</h1>
          <p className="muted">
            Phân công dược sĩ lâm sàng rà soát, chỉ định bác sĩ duyệt và điều phối các tác vụ xác minh
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={load} title="Làm mới hàng đợi">⟳ Cập nhật</button>
          <Link to="/cases" className="button">
            Xem danh sách ca →
          </Link>
        </div>
      </div>

      {notification && (
        <div className="result" role="status" style={{ marginBottom: "18px" }}>
          ✓ {notification}
        </div>
      )}

      {/* Overview Stats */}
      <div className="stats">
        <div className="stat">
          TỔNG CA ĐIỀU PHỐI
          <strong>{data.cases.length}</strong>
        </div>
        <div className="stat">
          CA CẦN RÀ SOÁT / KHẨN CẤP
          <strong>{data.dispatches.filter((d) => d.priority === "urgent" || d.priority === "high").length}</strong>
        </div>
        <div className="stat">
          NHIỆM VỤ XÁC MINH ĐANG MỞ
          <strong style={{ color: "#d97706" }}>{openTasks.length}</strong>
        </div>
      </div>

      {/* Case Dispatch Table */}
      <div className="panel">
        <div className="panelhead">
          <div>
            <p className="eyebrow">DANH SÁCH PHÂN CÔNG</p>
            <h2>Phân bổ Kíp trực theo Ca bệnh</h2>
          </div>
          <span className="muted small">Mỗi ca yêu cầu tối thiểu 1 Dược sĩ rà soát và 1 Bác sĩ duyệt</span>
        </div>

        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Ca / Bệnh nhân</th>
                <th>Mức độ ưu tiên</th>
                <th>Dược sĩ rà soát</th>
                <th>Bác sĩ phê duyệt</th>
                <th>Trạng thái rà soát</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {data.cases.map((c) => {
                const disp = data.dispatches.find((d) => d.case_id === c.id);
                const reviewerObj = users.find((u) => u.id === (disp?.assigned_reviewer ?? c.assigned[0]));
                const clinicianObj = users.find((u) => u.id === (disp?.assigned_clinician ?? c.assigned[1]));
                const priority = disp?.priority ?? "normal";

                return (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.id}</strong>
                      <small style={{ display: "block" }}>{c.patient_id} · {c.encounter_id}</small>
                      <small className="muted">
                        Kịch bản: {c.scenario === "matched" ? "Khớp dữ liệu" : c.scenario === "verification" ? "Xác minh đơn cũ" : "Nguồn bổ sung"}
                      </small>
                    </td>
                    <td>
                      <span className={`priority-pill ${priority}`}>
                        {priority === "normal" ? "Bình thường" : priority === "high" ? "Ưu tiên cao" : "Khẩn cấp"}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: "#087f83" }}>
                        👤 {reviewerObj?.name ?? "Chưa phân công"}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600, color: "#1e3a8a" }}>
                        🩺 {clinicianObj?.name ?? "Chưa chỉ định"}
                      </span>
                    </td>
                    <td>
                      <Badge value={c.lifecycle} />
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          style={{ padding: "6px 10px", fontSize: "12px", minHeight: "30px" }}
                          onClick={() => openAssignModal(c)}
                        >
                          Phân công ✎
                        </button>
                        <Link
                          to={`/cases/${c.id}`}
                          className="button"
                          style={{ padding: "6px 10px", fontSize: "12px", minHeight: "30px" }}
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
      </div>

      {/* Verification Queue Section */}
      <div className="panel" style={{ marginTop: "24px" }}>
        <div className="panelhead">
          <div>
            <p className="eyebrow">HÀNG ĐỢI XÁC MINH LÂM SÀNG TOÀN VIỆN</p>
            <h2>Nhiệm vụ đang giao cho Điều dưỡng / Người phản hồi</h2>
          </div>
          <span className="muted small">Tự động kích hoạt khi phát hiện khoảng trống thông tin</span>
        </div>

        <div className="panelbody">
          {openTasks.length === 0 ? (
            <Empty>Không có nhiệm vụ xác minh nào đang mở. Tất cả câu hỏi đã được trả lời!</Empty>
          ) : (
            <div style={{ display: "grid", gap: "12px" }}>
              {openTasks.map((t) => (
                <div
                  key={t.id}
                  style={{
                    padding: "16px",
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "16px",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "6px" }}>
                      <strong style={{ color: "#087f83" }}>{t.id}</strong>
                      <span className="badge waiting_response">Chờ phản hồi</span>
                      <small className="muted">Ca: {t.case_id} · Vấn đề: {t.issue_id}</small>
                    </div>
                    <p style={{ margin: 0, fontSize: "13px", color: "#1e293b", fontWeight: 600 }}>
                      {t.question}
                    </p>
                    <small className="muted" style={{ display: "block", marginTop: "4px" }}>
                      Giao cho: <strong>{users.find((u) => u.id === t.assignee)?.name ?? t.assignee}</strong> · Cần xác minh: {t.missing_fields.join(", ")}
                    </small>
                  </div>
                  <Link to="/tasks" className="button primary" style={{ minHeight: "34px", fontSize: "12px", whiteSpace: "nowrap" }}>
                    Phản hồi ngay →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Assignment Modal */}
      {selectedCase && (
        <Modal title={`Phân công Ca ${selectedCase.id}`} onClose={() => setSelectedCase(null)}>
          <form onSubmit={handleSaveAssign} className="panelbody" style={{ padding: "0 0 10px 0" }}>
            <p className="muted small">
              Bệnh nhân: <strong>{selectedCase.patient_id}</strong> · Đợt nhập viện: <strong>{selectedCase.encounter_id}</strong>
            </p>

            <label>
              Dược sĩ lâm sàng rà soát (Reviewer)
              <select
                value={editReviewer}
                onChange={(e) => setEditReviewer(e.target.value)}
                required
              >
                {reviewers.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.role})
                  </option>
                ))}
              </select>
            </label>

            <label>
              Bác sĩ điều trị phê duyệt (Clinician)
              <select
                value={editClinician}
                onChange={(e) => setEditClinician(e.target.value)}
                required
              >
                {clinicians.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.role})
                  </option>
                ))}
              </select>
            </label>

            <label>
              Mức độ ưu tiên xử lý
              <select
                value={editPriority}
                onChange={(e) => setEditPriority(e.target.value as "normal" | "high" | "urgent")}
              >
                <option value="normal">Bình thường (Ca khớp / thông thường)</option>
                <option value="high">Ưu tiên cao (Có khoảng trống thông tin)</option>
                <option value="urgent">Khẩn cấp (Nguồn muộn / nghi ngờ xung đột nghiêm trọng)</option>
              </select>
            </label>

            {mutation.error && <ErrorBox message={mutation.error} />}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "18px" }}>
              <button type="button" onClick={() => setSelectedCase(null)}>
                Hủy bỏ
              </button>
              <button type="submit" className="primary" disabled={mutation.busy}>
                {mutation.busy ? "Đang lưu…" : "Xác nhận phân công"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
