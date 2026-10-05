import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import type { Assertion, Case, Evidence, Issue, Source } from "./types";
import { labels } from "./types";
import { Badge, Empty, ErrorBox, Modal } from "./components";
import { useApi, useMutation } from "./hooks";
import { EditAssertion, ImportForm, IssueForm } from "./forms";
import AgentChat from "./AgentChat";

function EvidencePanel({
  c,
  id,
  close,
}: {
  c: Case;
  id: string;
  close: () => void;
}) {
  const { data, error, load } = useApi<Evidence>(
    `/cases/${c.id}/evidence/${id}`,
  );
  const source =
    data &&
    c.sources.find(
      (s) => s.source_id === data.source_id && s.version === data.version,
    );
  return (
    <Modal title="Nguồn và đoạn trích" onClose={close} variant="drawer">
      {error ? (
        <ErrorBox message={error} retry={load} />
      ) : !data ? (
        <Empty>Đang tải nguồn…</Empty>
      ) : (
        <>
          <p className="eyebrow">
            {data.source_id} · v{data.version}
          </p>
          <p>
            {source?.filename} · {source?.author_role}
          </p>
          <p className="muted small">
            Sự kiện: {source?.event_time ?? "Không rõ thời điểm"}
          </p>
          <div className="doc">
            <mark>{data.quote}</mark>
          </div>
          <h3>Ngữ cảnh</h3>
          <div className="doc">{data.context}</div>
          <p className="notice">
            Mở nguồn không đồng nghĩa đã xác nhận dữ kiện.
          </p>
        </>
      )}
    </Modal>
  );
}
export default function Workspace() {
  const { id } = useParams(),
    location = useLocation();
  const { data: c, error, load } = useApi<Case>(`/cases/${id}`, true);
  const [tab, setTab] = useState("medications"),
    [evidenceId, setEvidenceId] = useState<string>(),
    [source, setSource] = useState<Source>(),
    [runReason, setRunReason] = useState(""),
    [importing, setImporting] = useState(false),
    [editing, setEditing] = useState<Assertion>(),
    [chatDrawerOpen, setChatDrawerOpen] = useState(false),
    [form, setForm] = useState<{
      issue: Issue;
      kind: "confirm" | "task" | "handoff";
    }>();
  const mutation = useMutation();
  if (!c)
    return error ? (
      <ErrorBox message={error} retry={load} />
    ) : (
      <Empty>Đang tải hồ sơ…</Empty>
    );
  const sourceButtons = (ids: string[]) =>
    ids.map((eid) => (
      <button key={eid} className="source" onClick={() => setEvidenceId(eid)}>
        ↗ {c.evidence.find((e) => e.id === eid)?.source_id ?? eid}
      </button>
    ));
  const closed = c.issues.filter((i) => i.work_status === "closed").length,
    handed = c.issues.filter((i) => i.work_status === "handed_off").length;
  const act = async (path: string, revision: number) => {
    if (await mutation.run(path, { expected_revision: revision })) await load();
  };
  return (
    <>
      <Link to={location.state?.from ?? "/cases"}>← Danh sách ca</Link>
      <div className="pagehead">
        <div>
          <p className="eyebrow">HỒ SƠ NHẬP VIỆN / ĐỐI CHIẾU</p>
          <h1>Ca {c.id}</h1>
          <p className="muted">
            {c.patient_id} · Mốc đối chiếu{" "}
            {new Date(c.reconciliation_at).toLocaleString("vi-VN")}
          </p>
          <div className="statusline">
            <Badge value={c.lifecycle} />
            {c.run && <Badge value={c.run.status} />}
          </div>
        </div>
        <div className="actions">
          <button
            type="button"
            onClick={() => setChatDrawerOpen(true)}
            style={{ background: "#f0fdfa", color: "#087f83", borderColor: "#99f6e4" }}
            title="Mở bảng hỏi đáp và trích xuất bằng chứng với Trợ lý AI Agent"
          >
            💬 Hỏi AI về ca này
          </button>
          <button onClick={() => setImporting(true)}>Bổ sung nguồn</button>
          <Link className="button primary" to={`/cases/${c.id}/review`}>
            Xem tổng hợp →
          </Link>
        </div>
      </div>
      <div className="case-context">
        <span>ĐỐI CHIẾU TẠI <strong>{new Date(c.reconciliation_at).toLocaleString("vi-VN")}</strong></span>
        <span>NGUỒN HIỆN CÓ <strong>{c.sources.length}</strong></span>
        <span>PHIÊN BẢN CA <strong>v{c.revision}</strong></span>
      </div>
      {location.state?.receipt && (
        <p className="result" role="status">
          {location.state.receipt}
        </p>
      )}
      {error && <ErrorBox message={error} retry={load} />}{" "}
      {mutation.error && <ErrorBox message={mutation.error} />}
      {c.lifecycle === "changes_pending" && (
        <div className="notice">
          Có thông tin mới; cần rà lại. Bản đã duyệt trước đó được giữ nguyên.
        </div>
      )}
      {c.extraction_pending && (
        <div className="notice">
          Hồ sơ đã lưu. Chưa trích xuất — cần kết nối backend/AI thật. Giao diện
          không tạo dữ kiện từ nội dung tùy ý.
        </div>
      )}
      <div className="stats">
        <div className="stat">
          VIỆC ĐANG MỞ<strong>{c.issues.length - closed - handed}</strong>
        </div>
        <div className="stat">
          ĐÃ GIẢI QUYẾT<strong>{closed}</strong>
        </div>
        <div className="stat">
          BÀN GIAO · CHƯA GIẢI QUYẾT<strong>{handed}</strong>
        </div>
      </div>
      <div className="grid workspace-grid">
        <section className="case-main">
          <div className="tabs" role="tablist" aria-label="Nội dung hồ sơ">
            {[
              ["medications", "Thuốc"],
              ["timeline", "Timeline"],
              ["audit", "Nhật ký"],
              ["sources", "Nguồn"],
            ].map(([value, name]) => (
              <button
                role="tab"
                aria-selected={tab === value}
                key={value}
                onClick={() => setTab(value)}
              >
                {name}
              </button>
            ))}
          </div>
          <div className="panel medication-panel">
            {tab === "medications" ? (
              <>
                <div className="panelhead">
                  <h2>Bảng thuốc có nguồn</h2>
                  <span className="muted small">
                    Tiền sử và y lệnh được giữ riêng
                  </span>
                </div>
                {!c.assertions.length ? (
                  <Empty>Chưa có dữ kiện được trích xuất.</Empty>
                ) : (
                  <table className="med-table">
                    <thead>
                      <tr>
                        <th>Thuốc / nguồn</th>
                        <th>Loại ghi nhận</th>
                        <th>Liều / tần suất</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {c.assertions.map((a) => (
                        <tr key={a.id}>
                          <td>
                            <strong>{a.name}</strong>
                            <small>
                              {a.product ?? "Chưa xác định mã sản phẩm"}
                            </small>
                            {sourceButtons(a.evidence_ids)}
                          </td>
                          <td>
                            <span className="mobile-label">Loại ghi nhận</span>
                            <p>
                              {a.side === "history"
                                ? "Trước nhập viện"
                                : "Y lệnh nhập viện"}
                            </p>
                            <Badge value={a.assertion_type} />
                          </td>
                          <td>
                            <span className="mobile-label">
                              Liều / tần suất
                            </span>
                            {a.dose ?? "Chưa có thông tin"}
                            <small>
                              {a.frequency ?? "Chưa có thông tin tần suất"}
                            </small>
                          </td>
                          <td>
                            <button onClick={() => setEditing(a)}>
                              Sửa dữ kiện
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            ) : tab === "sources" ? (
              <div className="panelbody">
                <h2>Nguồn đã nhập</h2>
                {c.sources.map((s) => (
                  <p key={`${s.source_id}-${s.version}`}>
                    <button onClick={() => setSource(s)}>
                      {s.filename} · v{s.version}
                    </button>
                  </p>
                ))}
              </div>
            ) : tab === "timeline" ? (
              <div className="panelbody">
                <h2>Timeline có nguồn</h2>
                <ul className="timeline">
                  {[...c.sources]
                    .sort((a, b) =>
                      (a.event_time ?? "z").localeCompare(b.event_time ?? "z"),
                    )
                    .map((s) => (
                      <li key={`${s.source_id}-${s.version}`}>
                        {s.event_time
                          ? new Date(s.event_time).toLocaleString("vi-VN")
                          : "Không rõ thời điểm"}
                        <br />
                        <button className="source" onClick={() => setSource(s)}>
                          {s.filename}
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            ) : (
              <div className="panelbody">
                <h2>Nhật ký tác vụ</h2>
                <ul className="timeline">
                  {c.audit.map((entry, index) => (
                    <li key={index}>{entry}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
        <section className="case-side">
          <div className="panel issue-panel">
            <div className="panelhead">
              <div><p className="eyebrow">HÀNG CÔNG VIỆC</p><h2>Vấn đề cần xử lý</h2></div>
              <span className="issue-count">{c.issues.length - closed - handed}</span>
            </div>
            {!c.issues.length && (
              <Empty>Không có khác biệt trong các trường được so.</Empty>
            )}
            {c.issues.map((issue) => (
              <article className="issue" key={issue.id}>
                <h3>{issue.title}</h3>
                <p className="small muted">{issue.id}</p>
                <div className="statusline">
                  Công việc: <Badge value={issue.work_status} />
                </div>
                <div className="statusline">
                  Bằng chứng: <Badge value={issue.evidence_status} />
                </div>
                {sourceButtons(issue.evidence_ids)}
                {issue.confirmation && (
                  <p className="small">Xác nhận: {issue.confirmation.reason}</p>
                )}
                <div className="actions">
                  {!["closed", "handed_off"].includes(issue.work_status) && (
                    <>
                      <button onClick={() => setForm({ issue, kind: "task" })}>
                        Tạo yêu cầu
                      </button>
                      <button
                        onClick={() => setForm({ issue, kind: "confirm" })}
                      >
                        Xác nhận
                      </button>
                      <button
                        onClick={() => setForm({ issue, kind: "handoff" })}
                      >
                        Bàn giao
                      </button>
                      <button
                        disabled={!issue.confirmation || mutation.busy}
                        onClick={() =>
                          act(`/issues/${issue.id}/close`, issue.revision)
                        }
                      >
                        Đóng vấn đề
                      </button>
                    </>
                  )}
                </div>
                {issue.history.length > 0 && (
                  <details>
                    <summary>Lịch sử trước cập nhật</summary>
                    {issue.history.map((v, index) => (
                      <p key={index}>{v}</p>
                    ))}
                  </details>
                )}
              </article>
            ))}
          </div>
          <div className="panel">
          <div className="panelhead">
              <h2>Trợ lý đối chiếu</h2>
            </div>
            <div className="panelbody">
              <p className="muted small">
                {import.meta.env.VITE_API_MODE === "live"
                  ? "Trích xuất và tìm bước xử lý bằng AI; kết quả phải được người dùng kiểm tra."
                  : "Kịch bản mô phỏng trên 3 ca mẫu; chưa gọi AI."}
              </p>
              <button
                className="primary"
                disabled={
                  (import.meta.env.VITE_API_MODE !== "live" && (!c.scenario || c.extraction_pending)) ||
                  mutation.busy ||
                  c.lifecycle === "approved" ||
                  c.run?.status === "waiting_event" ||
                  (import.meta.env.VITE_API_MODE === "live" && ["failed", "budget_exhausted"].includes(c.run?.status ?? "") && !runReason.trim())
                }
                onClick={async () => {
                  const result = await mutation.run(`/cases/${c.id}/runs`, { expected_revision: c.revision, ...(runReason.trim() ? { reason: runReason.trim() } : {}) });
                  if (result) { setRunReason(""); await load(); }
                }}
              >
                {import.meta.env.VITE_API_MODE === "live" ? c.run?.status === "failed" ? "Chạy lại trợ lý AI" : "Chạy trợ lý AI" : "Chạy kịch bản mẫu"}
              </button>
              {import.meta.env.VITE_API_MODE === "live" && ["failed", "budget_exhausted"].includes(c.run?.status ?? "") && (
                <div className="notice" role="alert">
                  Trợ lý đã dừng ({c.run?.error ?? "lỗi xử lý"}); chưa tạo kết luận mới. Kiểm tra cấu hình model hoặc liên hệ người phụ trách.
                  <label>Lý do chạy lại<input value={runReason} onChange={(e) => setRunReason(e.target.value)} placeholder="Ví dụ: đã cấu hình khóa model" /></label>
                </div>
              )}
              {c.run?.status === "waiting_event" && (
                <p className="notice">
                  Đang chờ phản hồi. Không tự gọi AI trong lúc chờ.
                </p>
              )}
              <p style={{ marginTop: 16 }}>
                <Link to="/tasks">Mở nhiệm vụ và bàn giao →</Link>
              </p>
              {import.meta.env.VITE_API_MODE !== "live" && c.scenario === "late" && (
                <button
                  disabled={mutation.busy || c.lifecycle !== "approved"}
                  onClick={() => act(`/cases/${c.id}/demo-event`, c.revision)}
                >
                  Phát nguồn mới mẫu sau duyệt
                </button>
              )}
            </div>
          </div>
          <div className="notice">
            Tương tác thuốc chưa được đánh giá.
            <br />
            Đơn thuốc cũ không tự chứng minh người bệnh đang dùng.
          </div>
        </section>
      </div>
      {evidenceId && (
        <EvidencePanel
          c={c}
          id={evidenceId}
          close={() => setEvidenceId(undefined)}
        />
      )}
      {source && (
        <Modal title={source.filename} onClose={() => setSource(undefined)} variant="drawer">
          <p>
            {labels[source.kind]} · v{source.version}
          </p>
          <div className="doc">{source.text}</div>
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
          <div style={{ height: "calc(100vh - 120px)", marginTop: "10px" }}>
            <AgentChat caseId={c.id} />
          </div>
        </Modal>
      )}
    </>
  );
}
