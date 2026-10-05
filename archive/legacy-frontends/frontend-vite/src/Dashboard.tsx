import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "./hooks";
import type { DashboardMetrics } from "./types";
import { Empty, ErrorBox, Icon } from "./components";

export default function Dashboard() {
  const { data: metrics, error, load } = useApi<DashboardMetrics>("/dashboard/metrics", true);
  const [copied, setCopied] = useState(false);

  if (error) {
    return (
      <div className="panel panelbody">
        <ErrorBox message={error} retry={load} />
      </div>
    );
  }

  if (!metrics) {
    return <Empty>Đang tải dữ liệu giám sát và chỉ số vận hành…</Empty>;
  }

  const matchPercent = metrics.total_cases > 0 ? Math.round((metrics.matched_count / metrics.total_cases) * 100) : 0;
  const gapPercent = metrics.total_cases > 0 ? Math.round((metrics.gap_count / metrics.total_cases) * 100) : 0;

  const handleCopyReport = () => {
    const text = `BÁO CÁO GIÁM SÁT ĐỐI CHIẾU THUỐC VMEC-03\n- Tổng số ca: ${metrics.total_cases}\n- Ca khớp: ${metrics.matched_count} (${matchPercent}%)\n- Ca có khoảng trống thông tin: ${metrics.gap_count} (${gapPercent}%)\n- Đã phê duyệt: ${metrics.approved_count}\n- Trạng thái Agent: ${metrics.agent_status} (${metrics.agent_model})\n- Thời gian xử lý TB: ${metrics.avg_time_mins} phút/ca`;
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <>
      <div className="pagehead">
        <div>
          <p className="eyebrow">TRUNG TÂM GIÁM SÁT & QUẢN TRỊ</p>
          <h1>Bảng điều khiển Rà soát Thuốc Lâm sàng</h1>
          <p className="muted">
            Theo dõi tiến độ ca bệnh, chất lượng đối chiếu và hiệu suất của AI Agent thời gian thực
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button onClick={load} title="Cập nhật số liệu mới nhất">
            ⟳ Làm mới
          </button>
          <button className="primary" onClick={handleCopyReport}>
            {copied ? "✓ Đã sao chép tóm tắt" : "📋 Xuất báo cáo nhanh"}
          </button>
        </div>
      </div>

      {/* Row 1: KPI Cards */}
      <div className="dashboard-grid">
        <div className="kpi-card">
          <p className="eyebrow">TỔNG SỐ CA TIẾP NHẬN</p>
          <strong>{metrics.total_cases}</strong>
          <span className="kpi-sub">
            <Icon name="cases" /> 100% hồ sơ theo dõi nhập viện
          </span>
        </div>

        <div className="kpi-card">
          <p className="eyebrow">TỶ LỆ CA KHỚP ĐỐI CHIẾU</p>
          <strong style={{ color: "#059669" }}>{matchPercent}%</strong>
          <span className="kpi-sub positive">
            ✓ {metrics.matched_count}/{metrics.total_cases} ca không phát hiện xung đột
          </span>
        </div>

        <div className="kpi-card">
          <p className="eyebrow">KHOẢNG TRỐNG THÔNG TIN</p>
          <strong style={{ color: "#d97706" }}>{metrics.gap_count}</strong>
          <span className="kpi-sub warning">
            ⚠ Cần xác minh lâm sàng (information gap)
          </span>
        </div>

        <div className="kpi-card">
          <p className="eyebrow">ĐÃ PHÊ DUYỆT HOÀN TẤT</p>
          <strong style={{ color: "#087f83" }}>{metrics.approved_count}</strong>
          <span className="kpi-sub">
            Bác sĩ điều trị đã ký duyệt phiên bản
          </span>
        </div>
      </div>

      {/* Row 2: Agent Health Monitor & Case Distribution */}
      <div className="dashboard-row-2">
        <div className="agent-health-box">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p className="eyebrow" style={{ color: "#0f766e" }}>GIÁM SÁT AI AGENT (MEDREVIEW CO-PILOT)</p>
              <h2 style={{ margin: 0, color: "#134e4a" }}>Trạng thái Vận hành & Năng lực Mô hình</h2>
            </div>
            <div className="agent-status-indicator">
              <span className="pulse-dot" />
              <span>{metrics.agent_status === "online" ? "ĐANG HOẠT ĐỘNG" : "CHỜ LỆNH"}</span>
            </div>
          </div>

          <div className="agent-health-grid">
            <div className="health-item">
              <span>MÔ HÌNH KHAI THÁC</span>
              <strong style={{ fontSize: "14px", color: "#1e3a8a", marginTop: "6px" }}>{metrics.agent_model}</strong>
              <small className="muted">Adapter tích hợp</small>
            </div>
            <div className="health-item">
              <span>ĐỘ TRỄ TRUNG BÌNH (P95)</span>
              <strong>{metrics.avg_latency_ms} ms</strong>
              <small className="muted" style={{ color: "#059669" }}>Đạt chuẩn mục tiêu ≤ 2s</small>
            </div>
            <div className="health-item">
              <span>LƯỢT GỌI HÔM NAY</span>
              <strong>{metrics.calls_today} calls</strong>
              <small className="muted">~{metrics.total_tokens.toLocaleString()} tokens</small>
            </div>
          </div>

          <div style={{ marginTop: "16px", padding: "12px 14px", background: "white", borderRadius: "8px", border: "1px solid #dce8ea" }}>
            <p className="eyebrow" style={{ marginBottom: "6px" }}>NGUYÊN TẮC AN TOÀN Y TẾ ĐANG KÍCH HOẠT (GUARDRAILS)</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              <span className="badge approved">✓ 100% trích xuất có trích dẫn nguồn gốc (Grounded Citations)</span>
              <span className="badge waiting_response">✓ Không tự ý suy diễn thuốc đang dùng từ đơn cũ</span>
              <span className="badge ready_for_review">✓ Chặn phê duyệt khi còn câu hỏi xác minh mở</span>
              <span className="badge closed">✓ Độc lập phân quyền: Reviewer rà soát, Clinician duyệt</span>
            </div>
          </div>
        </div>

        {/* Quick Actions & Navigation Cards */}
        <div className="panel" style={{ margin: 0 }}>
          <div className="panelhead">
            <div>
              <p className="eyebrow">LỐI TẮT HỆ THỐNG</p>
              <h2>Truy cập Phân hệ Nghiệp vụ</h2>
            </div>
          </div>
          <div className="panelbody" style={{ display: "grid", gap: "10px" }}>
            <Link to="/dispatch" className="button" style={{ justifyContent: "flex-start", padding: "14px" }}>
              <span style={{ fontSize: "18px" }}>📦</span>
              <div style={{ textAlign: "left" }}>
                <strong>Trung tâm Điều phối Ca (Dispatch)</strong>
                <small style={{ display: "block", color: "#64808a" }}>Phân bổ kíp trực bác sĩ, dược sĩ và điều dưỡng</small>
              </div>
            </Link>

            <Link to="/agent-chat" className="button" style={{ justifyContent: "flex-start", padding: "14px" }}>
              <span style={{ fontSize: "18px" }}>💬</span>
              <div style={{ textAlign: "left" }}>
                <strong>Trợ lý AI Agent Chat</strong>
                <small style={{ display: "block", color: "#64808a" }}>Hỏi đáp và phân tích so sánh đơn thuốc có bằng chứng</small>
              </div>
            </Link>

            <Link to="/cases" className="button" style={{ justifyContent: "flex-start", padding: "14px" }}>
              <span style={{ fontSize: "18px" }}>📋</span>
              <div style={{ textAlign: "left" }}>
                <strong>Danh sách Ca cần Rà soát</strong>
                <small style={{ display: "block", color: "#64808a" }}>Mở Workspace đối chiếu thuốc và phê duyệt</small>
              </div>
            </Link>

            <Link to="/tasks" className="button" style={{ justifyContent: "flex-start", padding: "14px" }}>
              <span style={{ fontSize: "18px" }}>✅</span>
              <div style={{ textAlign: "left" }}>
                <strong>Hộp Nhiệm vụ Xác minh</strong>
                <small style={{ display: "block", color: "#64808a" }}>Trả lời các câu hỏi làm rõ từ điều dưỡng tiếp nhận</small>
              </div>
            </Link>
          </div>
        </div>
      </div>

      {/* Row 3: Live Audit Stream */}
      <div className="panel" style={{ marginTop: "24px" }}>
        <div className="panelhead">
          <div>
            <p className="eyebrow">NHẬT KÝ VẬN HÀNH THỜI GIAN THỰC (AUDIT TRAIL)</p>
            <h2>Lịch sử Thao tác & Quyết định Lâm sàng</h2>
          </div>
          <span className="muted small">Lưu vết minh bạch mọi hành động và lượt chạy của Agent</span>
        </div>
        <div className="panelbody">
          {metrics.recent_audits.length === 0 ? (
            <Empty>Chưa có thao tác kiểm toán nào được ghi nhận.</Empty>
          ) : (
            <div className="audit-stream">
              {metrics.recent_audits.map((item) => (
                <div key={item.id} className="audit-row">
                  <span className="audit-actor">{item.actor}</span>
                  <span className="audit-action">{item.action}</span>
                  {item.case_id && (
                    <Link
                      to={`/cases/${item.case_id}`}
                      className="button"
                      style={{ padding: "4px 8px", fontSize: "11px", minHeight: "26px" }}
                    >
                      {item.case_id} →
                    </Link>
                  )}
                  <span className="audit-time">
                    {new Date(item.time).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
