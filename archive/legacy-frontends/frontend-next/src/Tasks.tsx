"use client";

import Link from "next/link";
import { useState } from "react";
import type { Evidence, Handoff, Task } from "./types";
import { users } from "./mocks/seed";
import { useApi, useMutation } from "./hooks";
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
  buttonClass,
} from "./components/ui";
import { Icon } from "./components/icons";
import { useSession } from "../app/providers";

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
  const { user } = useSession();
  const [response, setResponse] = useState(""),
    [reason, setReason] = useState(""),
    [receipt, setReceipt] = useState("");
  const mutation = useMutation();

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
        <div className="space-y-4">
          <p className="text-[14px] font-semibold text-ink">{data.question}</p>
          <Badge value={data.status} />
          <div>
            <h3 className="mb-2 text-[12px] font-bold tracking-[0.1em] text-muted uppercase">
              Trích đoạn được chia sẻ
            </h3>
            <div className="space-y-2">
              {data.shared_evidence.map((e) => (
                <div className="quote-block" key={e.id}>
                  <span className="mb-1 block text-[11px] font-bold text-brand-ink">
                    {e.source_id} · v{e.version}
                  </span>
                  {e.quote}
                </div>
              ))}
            </div>
          </div>

          {data.response && (
            <Notice tone="ok">
              <span className="flex items-center gap-2">
                <Icon name="checkCircle" className="size-4" />
                Phản hồi đã lưu: {data.response}
              </span>
            </Notice>
          )}

          {data.status === "open" && !receipt && (
            <>
              <form
                className="space-y-3"
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
                <label className="block text-[12px] font-semibold text-ink-soft">
                  Phản hồi
                  <textarea
                    required
                    disabled={mutation.busy || mutation.uncertain}
                    value={response}
                    onChange={(e) => setResponse(e.target.value)}
                    placeholder="Ghi rõ thông tin và người cung cấp; có thể trả lời chưa biết."
                    className="mt-1.5 min-h-[110px] w-full rounded-[10px] border border-line bg-surface px-3 py-2.5 text-[13px] leading-relaxed"
                  />
                </label>
                <Button
                  variant="primary"
                  type="submit"
                  disabled={!response.trim() || mutation.busy}
                >
                  {mutation.uncertain ? "Thử lại cùng thao tác" : "Gửi phản hồi"}
                </Button>
              </form>

              {user?.role !== "responder" && (
                <details className="rounded-[10px] border border-line bg-surface-2 px-4 py-3">
                  <summary className="cursor-pointer text-[12px] font-semibold text-ink-soft">
                    Hủy yêu cầu
                  </summary>
                  <div className="mt-3 space-y-3">
                    <label className="block text-[12px] font-semibold text-ink-soft">
                      Lý do hủy
                      <input
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        disabled={mutation.busy || mutation.uncertain}
                        className="mt-1.5 h-10 w-full rounded-[10px] border border-line bg-surface px-3 text-[13px]"
                      />
                    </label>
                    <Button
                      variant="danger"
                      disabled={!reason.trim() || mutation.busy || mutation.uncertain}
                      onClick={async () => {
                        const result = await mutation.run<{ receipt: string }>(
                          `/tasks/${data.id}/cancel`,
                          { expected_revision: data.revision, reason },
                        );
                        if (result) {
                          setReceipt(result.receipt);
                          done();
                          await load();
                        }
                      }}
                    >
                      {mutation.uncertain ? "Thử lại cùng thao tác" : "Hủy yêu cầu có lý do"}
                    </Button>
                  </div>
                </details>
              )}
            </>
          )}

          {receipt && (
            <Notice tone="ok" role="status">
              Đã lưu phản hồi; kết quả sẽ được rà soát. Receipt: {receipt}
            </Notice>
          )}
              {mutation.error && <ErrorBox message={mutation.error} />}
        </div>
      )}
    </Modal>
  );
}

export default function Tasks() {
  const { data: tasks, error, load } = useApi<Task[]>("/tasks", true);
  const { data: handoffs, load: loadHandoffs } = useApi<Handoff[]>("/handoffs", true);
  const { userId, user } = useSession();
  const [selected, setSelected] = useState<Task>();
  const mutation = useMutation();

  return (
    <>
      <PageHeader
        eyebrow="Hàng công việc"
        title="Nhiệm vụ của tôi"
        description="Phản hồi cung cấp bằng chứng; không tự xác nhận hoặc đóng vấn đề."
        actions={
          <StatusPill tone="info" icon="user">
            {user ? `${user.name} · ${user.role}` : "—"}
          </StatusPill>
        }
      />

      {error && <ErrorBox message={error} retry={load} />}
      {mutation.error && <ErrorBox message={mutation.error} />}

      <Panel className="mt-1 overflow-hidden">
        <PanelHead
          eyebrow="Yêu cầu xác minh"
          title="Yêu cầu xác minh"
          description="Trả lời kèm người cung cấp thông tin; có thể trả lời chưa biết."
        />
        <PanelBody className="space-y-3">
          {!tasks ? (
            <Empty>Đang tải nhiệm vụ…</Empty>
          ) : !tasks.length ? (
            <Empty>Chưa có nhiệm vụ.</Empty>
          ) : (
            tasks.map((t) => (
              <article
                key={t.id}
                className="rounded-[14px] border border-line bg-surface-2 px-4 py-3.5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[13.5px] font-semibold text-ink">{t.question}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Badge value={t.status} />
                      <span className="inline-flex items-center gap-1.5 text-[11.5px] text-muted">
                        <Icon name="user" className="size-3.5" />
                        {users.find((u) => u.id === t.assignee)?.name}
                      </span>
                      <span className="text-[11.5px] text-muted">· Ca {t.case_id}</span>
                    </div>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    iconRight="arrowRight"
                    onClick={() => setSelected(t)}
                  >
                    Mở nhiệm vụ
                  </Button>
                </div>
              </article>
            ))
          )}
        </PanelBody>
      </Panel>

      {!!handoffs?.length && (
        <Panel className="mt-5 overflow-hidden">
          <PanelHead
            eyebrow="Bàn giao"
            title="Bàn giao"
            description="Người nhận phải xác nhận; vấn đề đã bàn giao vẫn chưa được giải quyết."
          />
          <PanelBody className="space-y-3">
            {handoffs.map((h) => (
              <article
                key={h.id}
                className="rounded-[14px] border border-line bg-surface-2 px-4 py-3.5"
              >
                <p className="text-[13.5px] font-semibold text-ink">{h.reason}</p>
                <p className="mt-1.5 inline-flex items-center gap-1.5 text-[11.5px] text-muted">
                  <Icon name="user" className="size-3.5" />
                  Người nhận: {users.find((u) => u.id === h.recipient)?.name}
                  <span>· Ca {h.case_id}</span>
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2.5">
                  <StatusPill
                    tone={h.acknowledged ? "warn" : "info"}
                    icon={h.acknowledged ? "alert" : "clock"}
                  >
                    {h.acknowledged
                      ? "Đã nhận bàn giao · Chưa thể kết luận"
                      : "Đang chờ nhận bàn giao"}
                  </StatusPill>
                  {!h.acknowledged && h.recipient === userId && (
                    <Button
                      size="sm"
                      disabled={mutation.busy}
                      onClick={async () => {
                        if (
                          await mutation.run(`/handoffs/${h.id}/ack`, {
                            expected_revision: h.revision,
                          })
                        ) {
                          await loadHandoffs();
                        }
                      }}
                    >
                      Nhận bàn giao
                    </Button>
                  )}
                  <Link href={`/cases/${h.case_id}`} className={buttonClass("ghost", "sm")}>
                    Mở ca
                  </Link>
                </div>
              </article>
            ))}
          </PanelBody>
        </Panel>
      )}

      {selected && (
        <TaskPanel task={selected} close={() => setSelected(undefined)} done={load} />
      )}
    </>
  );
}

