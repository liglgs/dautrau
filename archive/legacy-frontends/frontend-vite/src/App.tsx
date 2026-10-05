import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { api } from "./api";
import type { Case } from "./types";
import { users } from "./mocks/seed";
import { Badge, Empty, ErrorBox, Icon, Modal } from "./components";
import Workspace from "./Workspace";
import Tasks from "./Tasks";
import Review from "./Review";
import Dashboard from "./Dashboard";
import Dispatch from "./Dispatch";
import AgentChat from "./AgentChat";
import { ImportForm } from "./forms";

function Login() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login">
      <div className="brandmark"><Icon name="cross" /></div>
      <p className="eyebrow">MEDREVIEW / VMEC-03</p>
      <h1>
        Không gian rà soát
        <br />
        thuốc có nguồn
      </h1>
      <p className="muted">
        {import.meta.env.VITE_API_MODE === "live"
          ? "Đăng nhập tài khoản nghiên cứu để xử lý hồ sơ mô phỏng."
          : "Chọn tài khoản để trải nghiệm luồng công việc mô phỏng."}
      </p>
      <div className="panel">
        {users.map((user) => (
          <button
            className="account"
            key={user.id}
            onClick={() => {
              if (import.meta.env.VITE_API_MODE === "live") {
                setSelected(user.id);
                setError("");
              } else {
                sessionStorage.setItem("demo-user", user.id);
                navigate(user.role === "responder" ? "/tasks" : "/dashboard");
              }
            }}
          >
            <span>{user.name}</span>
            <span>→</span>
          </button>
        ))}
      </div>
      {import.meta.env.VITE_API_MODE === "live" && selected && (
        <form className="login-form panel panelbody" onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            const user = await api<{ id: string; role: string }>("/sessions", { user_id: selected, password });
            sessionStorage.setItem("demo-user", user.id);
            navigate(user.role === "responder" ? "/tasks" : "/dashboard");
          } catch (err) { setError((err as Error).message); }
          finally { setBusy(false); }
        }}>
          <strong>{users.find((u) => u.id === selected)?.name}</strong>
          <label>Mật khẩu demo<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          {error && <ErrorBox message={error} />}
          <button className="primary" disabled={busy}>Đăng nhập</button>
        </form>
      )}
      <p className="muted small">Bản nghiên cứu chỉ dùng dữ liệu mô phỏng.</p>
    </div>
  );
}
function CaseList() {
  const [importing, setImporting] = useState(false);
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "",
    status = params.get("status") ?? "";
  const [cases, setCases] = useState<Case[]>();
  const [error, setError] = useState("");
  const load = () => {
    setError("");
    api<Case[]>("/cases")
      .then(setCases)
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);
  const filtered = cases?.filter(
    (c) =>
      c.id.toLowerCase().includes(q.toLowerCase()) &&
      (!status || c.lifecycle === status),
  ).sort((a, b) => {
    const priority: Record<string, number> = { changes_pending: 0, reviewing: 1, draft: 2, approved: 3 };
    return priority[a.lifecycle] - priority[b.lifecycle] || a.id.localeCompare(b.id);
  });
  return (
    <>
      <div className="pagehead">
        <div>
          <p className="eyebrow">KHÔNG GIAN LÀM VIỆC</p>
          <h1>Hồ sơ cần rà soát</h1>
          <p className="muted">
            Các ca được phân công · Một ca, một lần nhập viện
          </p>
        </div>
        {users.find((u) => u.id === sessionStorage.getItem("demo-user"))
          ?.role !== "admin" && (
          <button className="primary" onClick={() => setImporting(true)}>
            + Nhập hồ sơ mô phỏng
          </button>
        )}
      </div>
      <div className="stats">
        <div className="stat">
          CA ĐƯỢC PHÂN CÔNG<strong>{cases?.length ?? "—"}</strong>
        </div>
        <div className="stat">
          ĐANG RÀ SOÁT
          <strong>
            {cases?.filter((c) => c.lifecycle === "reviewing").length ?? "—"}
          </strong>
        </div>
        <div className="stat">
          ĐÃ DUYỆT
          <strong>
            {cases?.filter((c) => c.lifecycle === "approved").length ?? "—"}
          </strong>
        </div>
      </div>
      <div className="panel">
        <div className="panelhead case-list-head">
          <div><p className="eyebrow">DANH SÁCH ƯU TIÊN</p><h2>Ca của tôi</h2></div>
          <span className="muted small">Ca cần rà lại được đưa lên trước</span>
        </div>
        <div className="filters">
          <label>
            Tìm theo mã ca
            <input
              value={q}
              onChange={(e) => setParams({ q: e.target.value, status })}
              placeholder="Ví dụ: SIM-002"
            />
          </label>
          <label>
            Trạng thái
            <select
              value={status}
              onChange={(e) => setParams({ q, status: e.target.value })}
            >
              <option value="">Tất cả trạng thái</option>
              <option value="draft">Chưa xử lý</option>
              <option value="reviewing">Đang rà soát</option>
              <option value="approved">Đã duyệt</option>
              <option value="changes_pending">Cần rà lại</option>
            </select>
          </label>
          <button onClick={() => setParams({})}>Xóa bộ lọc</button>
        </div>
        {error ? (
          <ErrorBox message={error} retry={load} />
        ) : !cases ? (
          <Empty>Đang tải danh sách ca…</Empty>
        ) : !filtered?.length ? (
          <Empty>
            {cases.length
              ? "Không có ca phù hợp bộ lọc."
              : "Bạn chưa có ca được phân công."}
          </Empty>
        ) : (
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Ca / đợt nhập viện</th>
                  <th>Trạng thái hồ sơ</th>
                  <th>Trợ lý</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((c) => (
                  <tr key={c.id} className={c.lifecycle === "changes_pending" ? "priority-row" : undefined}>
                    <td>
                      <strong>{c.id}</strong>
                      <small>
                        {c.patient_id} · {c.encounter_id}
                      </small>
                      <small className="case-need">{c.issues.filter((i) => !["closed", "handed_off"].includes(i.work_status)).length} việc mở · {c.issues.filter((i) => i.work_status === "handed_off").length} bàn giao</small>
                    </td>
                    <td>
                      <Badge value={c.lifecycle} />
                    </td>
                    <td>
                      {c.run ? <Badge value={c.run.status} /> : "Chưa bắt đầu"}
                    </td>
                    <td>
                      <Link
                        className="button"
                        to={`/cases/${c.id}`}
                        state={{ from: `/cases?${params}` }}
                      >
                        Mở ca →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {importing && (
        <ImportForm close={() => setImporting(false)} done={load} />
      )}
    </>
  );
}
function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = users.find((u) => u.id === sessionStorage.getItem("demo-user"));
  const [logoutModalOpen, setLogoutModalOpen] = useState(false);

  if (!user) return <Navigate to="/login" replace />;

  const handleRoleSwitch = (newUserId: string) => {
    if (import.meta.env.VITE_API_MODE === "live") {
      // In live mode, switch via logout & login
      navigate("/login");
      return;
    }
    sessionStorage.setItem("demo-user", newUserId);
    const target = users.find((u) => u.id === newUserId);
    if (target?.role === "responder") {
      navigate("/tasks");
    } else {
      navigate(location.pathname);
    }
    window.location.reload();
  };

  const handleLogout = async () => {
    if (import.meta.env.VITE_API_MODE === "live") {
      void api("/sessions/current", undefined, { method: "DELETE" }).catch(() => {});
    }
    sessionStorage.removeItem("demo-user");
    setLogoutModalOpen(false);
    navigate("/login");
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <Link
          className="brand"
          to={user.role === "responder" ? "/tasks" : "/dashboard"}
        >
          <span className="brandmark"><Icon name="cross" /></span>
          <span>
            MedReview<small>ĐỐI CHIẾU THUỐC CÓ NGUỒN</small>
          </span>
        </Link>

        {/* Navigation Section 1: Overview */}
        <p className="nav-category">TỔNG QUAN</p>
        <nav>
          {user.role !== "responder" && (
            <NavLink to="/dashboard">
              <span className="nav-icon"><Icon name="dashboard" /></span>
              <span>Bảng điều khiển</span>
            </NavLink>
          )}
        </nav>

        {/* Navigation Section 2: Clinical Operations */}
        <p className="nav-category">NGHIỆP VỤ RÀ SOÁT</p>
        <nav>
          {user.role !== "responder" && (
            <NavLink to="/cases">
              <span className="nav-icon"><Icon name="cases" /></span>
              <span>Danh sách ca</span>
            </NavLink>
          )}
          {user.role !== "responder" && (
            <NavLink to="/dispatch">
              <span className="nav-icon"><Icon name="dispatch" /></span>
              <span>Điều phối kíp trực</span>
            </NavLink>
          )}
          <NavLink to="/tasks">
            <span className="nav-icon"><Icon name="tasks" /></span>
            <span>Nhiệm vụ xác minh</span>
          </NavLink>
        </nav>

        {/* Navigation Section 3: AI Co-pilot */}
        <p className="nav-category">TRỢ LÝ AI AGENT</p>
        <nav>
          <NavLink to="/agent-chat">
            <span className="nav-icon"><Icon name="chat" /></span>
            <span>Trợ lý Agent Chat</span>
          </NavLink>
        </nav>

        <div className="navnote">
          <strong>Hệ thống VMEC-03</strong>
          <br />
          Trợ lý xác minh & đối chiếu thuốc khi nhập viện
          <br />
          <br />
          Quyết định do Bác sĩ phê duyệt
        </div>
      </aside>

      <div className="main">
        {/* Enhanced Modern Topbar */}
        <div className="topbar">
          <div className="topbar-left">
            <span className="demo-label">
              {import.meta.env.VITE_API_MODE === "live"
                ? "Dữ liệu mô phỏng · AI cần rà soát"
                : "Môi trường thử nghiệm mô phỏng"}
            </span>
            <div className="agent-status-indicator">
              <span className="pulse-dot" />
              <span>AI Agent: Sẵn sàng</span>
            </div>
          </div>

          <div className="topbar-right">
            {/* Quick Demo Role Switcher */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span className="muted" style={{ fontSize: "11px", fontWeight: 600 }}>
                Đổi vai trò:
              </span>
              <select
                className="quick-switcher-select"
                value={user.id}
                onChange={(e) => handleRoleSwitch(e.target.value)}
                title="Chuyển nhanh vai trò để kiểm thử luồng demo"
              >
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.role})
                  </option>
                ))}
              </select>
            </div>

            {/* User Profile Capsule */}
            <div className="user-profile-menu">
              <div className="user-avatar" title={user.name}>
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="user-info">
                <span className="user-name">{user.name}</span>
                <span className="user-role-tag">
                  {user.role === "clinician"
                    ? "Bác sĩ phê duyệt"
                    : user.role === "reviewer"
                    ? "Dược sĩ rà soát"
                    : user.role === "responder"
                    ? "Điều dưỡng tiếp nhận"
                    : "Quản trị viên"}
                </span>
              </div>
            </div>

            {/* Logout Button */}
            <button
              type="button"
              className="logout-btn"
              onClick={() => setLogoutModalOpen(true)}
              title="Đăng xuất khỏi hệ thống"
            >
              <Icon name="logout" />
              <span>Đăng xuất</span>
            </button>
          </div>
        </div>

        <main key={location.pathname}>
          <Routes>
            <Route
              path="/dashboard"
              element={
                user.role === "responder" ? (
                  <Navigate to="/tasks" />
                ) : (
                  <Dashboard />
                )
              }
            />
            <Route
              path="/cases"
              element={
                user.role === "responder" ? (
                  <Navigate to="/tasks" />
                ) : (
                  <CaseList />
                )
              }
            />
            <Route
              path="/cases/:id"
              element={
                user.role === "responder" ? (
                  <Navigate to="/tasks" />
                ) : (
                  <Workspace />
                )
              }
            />
            <Route
              path="/cases/:id/review"
              element={
                user.role === "responder" ? (
                  <Navigate to="/tasks" />
                ) : (
                  <Review />
                )
              }
            />
            <Route
              path="/dispatch"
              element={
                user.role === "responder" ? (
                  <Navigate to="/tasks" />
                ) : (
                  <Dispatch />
                )
              }
            />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/agent-chat" element={<AgentChat />} />
            <Route
              path="*"
              element={
                <Navigate
                  to={user.role === "responder" ? "/tasks" : "/dashboard"}
                />
              }
            />
          </Routes>
        </main>
        <footer>MedReview / VMEC-03 · Trợ lý xác minh & đối chiếu thuốc nhập viện</footer>
      </div>

      {/* Logout Confirmation Modal */}
      {logoutModalOpen && (
        <Modal title="Xác nhận Đăng xuất" onClose={() => setLogoutModalOpen(false)}>
          <div className="panelbody" style={{ padding: "0 0 10px 0" }}>
            <p style={{ fontSize: "14px", lineHeight: "1.6", color: "#334155" }}>
              Bạn có chắc chắn muốn kết thúc phiên làm việc của <strong>{user.name}</strong>?
            </p>
            <p className="muted small">
              Mọi dữ liệu nháp đã lưu trên hệ thống sẽ được bảo toàn an toàn cho ca trực tiếp theo.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "20px" }}>
              <button type="button" onClick={() => setLogoutModalOpen(false)}>
                Hủy bỏ
              </button>
              <button
                type="button"
                className="primary"
                style={{ background: "#dc2626", borderColor: "#dc2626" }}
                onClick={handleLogout}
              >
                Đăng xuất an toàn
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
export default function App() {
  const [ready, setReady] = useState(import.meta.env.VITE_API_MODE !== "live");
  useEffect(() => {
    if (import.meta.env.VITE_API_MODE !== "live") return;
    api<{ id: string }>("/sessions/current")
      .then((user) => sessionStorage.setItem("demo-user", user.id))
      .catch(() => sessionStorage.removeItem("demo-user"))
      .finally(() => setReady(true));
  }, []);
  if (!ready) return <div className="startup">Đang kiểm tra phiên đăng nhập…</div>;
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Shell />} />
      </Routes>
    </BrowserRouter>
  );
}
