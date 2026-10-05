import { useState } from "react";
import type { Evidence, Handoff, Task } from "./types";
import { users } from "./mocks/seed";
import { useApi, useMutation } from "./hooks";
import { Badge, Empty, ErrorBox, Modal } from "./components";
import { Link } from "react-router-dom";
function TaskPanel({
  task,
  close,
  done,
}: {
  task: Task;
  close: () => void;
  done: () => void;
}) {
  const { data, error, load } = useApi<Task & { shared_evidence: Evidence[] }>(
    `/tasks/${task.id}`,
  );
  const [response, setResponse] = useState(""),
    [reason, setReason] = useState(""),
    [receipt, setReceipt] = useState("");
  const mutation = useMutation();
  const user = users.find((u) => u.id === sessionStorage.getItem("demo-user"))!;
  return (
    <Modal
      title="Yêu cầu xác minh"
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
    >
      {error ? (
        <ErrorBox message={error} retry={load} />
      ) : !data ? (
        <Empty>Đang tải nhiệm vụ…</Empty>
      ) : (
        <>
          <p>{data.question}</p>
          <Badge value={data.status} />
          <h3>Trích đoạn được chia sẻ</h3>
          {data.shared_evidence.map((e) => (
            <div className="doc" key={e.id}>
              {e.quote}
            </div>
          ))}
          {data.response && (
            <p className="result">Phản hồi đã lưu: {data.response}</p>
          )}
          {data.status === "open" && !receipt && (
            <>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const result = await mutation.run<{ receipt: string }>(
                    `/tasks/${data.id}/responses`,
                    { expected_revision: data.revision, response },
                  );
                  if (result) {
                    setReceipt(result.receipt);
                    done();
                    await load();
                  }
                }}
              >
                <label>
                  Phản hồi
                  <textarea
                    required
                    disabled={mutation.busy || mutation.uncertain}
                    value={response}
                    onChange={(e) => setResponse(e.target.value)}
                    placeholder="Ghi rõ thông tin và người cung cấp; có thể trả lời chưa biết."
                  />
                </label>
                <button
                  className="primary"
                  disabled={!response.trim() || mutation.busy}
                >
                  {mutation.uncertain
                    ? "Thử lại cùng thao tác"
                    : "Gửi phản hồi"}
                </button>
              </form>
              {user.role !== "responder" && (
                <details>
                  <summary>Hủy yêu cầu</summary>
                  <label>
                    Lý do hủy
                    <input
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      disabled={mutation.busy || mutation.uncertain}
                    />
                  </label>
                  <button
                    disabled={
                      !reason.trim() || mutation.busy || mutation.uncertain
                    }
                    onClick={async () => {
                      if (
                        await mutation.run(`/tasks/${data.id}/cancel`, {
                          expected_revision: data.revision,
                          reason,
                        })
                      ) {
                        done();
                        close();
                      }
                    }}
                  >
                    Hủy yêu cầu có lý do
                  </button>
                </details>
              )}
            </>
          )}
          {receipt && (
            <p className="result" role="status">
              Đã lưu phản hồi; kết quả sẽ được rà soát. Receipt: {receipt}
            </p>
          )}
          {mutation.error && <ErrorBox message={mutation.error} />}
        </>
      )}
    </Modal>
  );
}
export default function Tasks() {
  const { data: tasks, error, load } = useApi<Task[]>("/tasks", true);
  const { data: handoffs, load: loadHandoffs } = useApi<Handoff[]>(
    "/handoffs",
    true,
  );
  const [selected, setSelected] = useState<Task>();
  const mutation = useMutation();
  const userId = sessionStorage.getItem("demo-user");
  return (
    <>
      <p className="eyebrow">HÀNG CÔNG VIỆC</p>
      <h1>Nhiệm vụ của tôi</h1>
      <p className="muted">
        Phản hồi cung cấp bằng chứng; không tự xác nhận hoặc đóng vấn đề.
      </p>
      {error && <ErrorBox message={error} retry={load} />}
      <div className="panel">
        <div className="panelhead">
          <h2>Yêu cầu xác minh</h2>
        </div>
        {!tasks ? (
          <Empty>Đang tải…</Empty>
        ) : !tasks.length ? (
          <Empty>Chưa có nhiệm vụ.</Empty>
        ) : (
          tasks.map((t) => (
            <div className="issue" key={t.id}>
              <p>{t.question}</p>
              <div className="statusline">
                <Badge value={t.status} />
                <span className="muted small">
                  {users.find((u) => u.id === t.assignee)?.name}
                </span>
              </div>
              <button onClick={() => setSelected(t)}>Mở nhiệm vụ</button>
            </div>
          ))
        )}
      </div>
      {!!handoffs?.length && (
        <div className="panel">
          <div className="panelhead">
            <h2>Bàn giao</h2>
          </div>
          {handoffs.map((h) => (
            <div className="issue" key={h.id}>
              <p>{h.reason}</p>
              <p className="small muted">
                Người nhận: {users.find((u) => u.id === h.recipient)?.name}
              </p>
              <div className="actions">
                <span>
                  {h.acknowledged
                    ? "Đã nhận bàn giao · Chưa thể kết luận"
                    : "Đang chờ nhận bàn giao"}
                </span>
                {!h.acknowledged && h.recipient === userId && (
                  <button
                    disabled={mutation.busy}
                    onClick={async () => {
                      if (
                        await mutation.run(`/handoffs/${h.id}/ack`, {
                          expected_revision: h.revision,
                        })
                      )
                        await loadHandoffs();
                    }}
                  >
                    Nhận bàn giao
                  </button>
                )}
                <Link to={`/cases/${h.case_id}`}>Mở ca</Link>
              </div>
            </div>
          ))}
        </div>
      )}
      {mutation.error && <ErrorBox message={mutation.error} />}{" "}
      {selected && (
        <TaskPanel
          task={selected}
          close={() => setSelected(undefined)}
          done={load}
        />
      )}
    </>
  );
}
