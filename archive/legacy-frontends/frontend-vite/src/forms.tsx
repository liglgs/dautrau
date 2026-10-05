import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { Case, Evidence, Issue, Assertion } from "./types";
import { labels } from "./types";
import { Modal, ErrorBox } from "./components";
import { readImport } from "./import";
import { useMutation } from "./hooks";
import { users } from "./mocks/seed";

export function ImportForm({
  c,
  close,
  done,
}: {
  c?: Case;
  close: () => void;
  done: () => void;
}) {
  const [manifest, setManifest] = useState<File>();
  const [files, setFiles] = useState<File[]>([]);
  const [checked, setChecked] = useState(false);
  const [valid, setValid] = useState<Awaited<ReturnType<typeof readImport>>>();
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState("");
  const mutation = useMutation();
  const navigate = useNavigate();
  const validate = async () => {
    setError("");
    setValid(undefined);
    try {
      if (!manifest) throw new Error("Chọn case.json.");
      setValid(await readImport(manifest, files));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid || !checked) return;
    const data = new FormData();
    data.set("manifest", JSON.stringify(valid.manifest));
    files.forEach((f) => data.append("files", f));
    if (c) data.set("expected_revision", String(c.revision));
    const result = await mutation.run<{
      case_id: string;
      source_count: number;
      receipt: string;
    }>(c ? `/cases/${c.id}/sources` : "/cases/import", data);
    if (result) {
      setReceipt(
        `Đã nhập ${result.source_count} nguồn. Receipt: ${result.receipt}`,
      );
      done();
      if (!c)
        navigate(`/cases/${result.case_id}`, {
          state: {
            receipt: `Đã nhập ${result.source_count} nguồn · ${result.receipt}`,
          },
        });
    }
  };
  return (
    <Modal
      title={c ? "Bổ sung nguồn" : "Nhập hồ sơ mô phỏng"}
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
    >
      <form onSubmit={submit}>
        <p className="muted">
          Chọn case.json và tệp TXT UTF-8. Tối đa 8 tệp/gói, 12.000 ký tự/tệp.
          Chỉ dữ liệu mô phỏng.
        </p>
        <fieldset disabled={mutation.busy || mutation.uncertain || !!receipt}>
          <label>
            Manifest JSON
            <input
              type="file"
              accept=".json"
              onChange={(e) => {
                setManifest(e.target.files?.[0]);
                setValid(undefined);
              }}
            />
          </label>
          <label>
            Nguồn TXT
            <input
              type="file"
              accept=".txt"
              multiple
              onChange={(e) => {
                setFiles(Array.from(e.target.files ?? []));
                setValid(undefined);
              }}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            Tôi xác nhận đây là dữ liệu mô phỏng
          </label>
          <button type="button" onClick={validate}>
            Kiểm tra gói
          </button>
        </fieldset>
        {valid && (
          <p className="result" role="status">
            Gói hợp lệ: {valid.manifest.case_id} · {valid.sources.length} nguồn
          </p>
        )}
        {(error || mutation.error) && (
          <ErrorBox message={error || mutation.error} />
        )}{" "}
        {receipt ? (
          <>
            <p role="status" className="result">
              {receipt}
            </p>
            <button type="button" onClick={close}>
              Đóng
            </button>
          </>
        ) : (
          <button
            className="primary"
            disabled={!valid || !checked || mutation.busy}
            type="submit"
          >
            {mutation.uncertain ? "Thử lại cùng thao tác" : "Nhập hồ sơ"}
          </button>
        )}
      </form>
    </Modal>
  );
}
export function EvidenceChoices({
  items,
  ids,
  setIds,
}: {
  items: Evidence[];
  ids: string[];
  setIds: (v: string[]) => void;
}) {
  return (
    <fieldset>
      <legend>Nguồn bằng chứng *</legend>
      {items.map((e) => (
        <label className="check" key={e.id}>
          <input
            type="checkbox"
            checked={ids.includes(e.id)}
            onChange={(ev) =>
              setIds(
                ev.target.checked
                  ? [...ids, e.id]
                  : ids.filter((id) => id !== e.id),
              )
            }
          />
          <span>
            {e.source_id} · {e.quote.slice(0, 85)}
          </span>
        </label>
      ))}
    </fieldset>
  );
}
export function IssueForm({
  c,
  issue,
  kind,
  close,
  done,
}: {
  c: Case;
  issue: Issue;
  kind: "confirm" | "task" | "handoff";
  close: () => void;
  done: () => void;
}) {
  const user = users.find((u) => u.id === sessionStorage.getItem("demo-user"))!;
  const live = import.meta.env.VITE_API_MODE === "live";
  const canNoDifference = !live || (issue.assertion_refs?.length ?? 0) >= 2;
  const [reason, setReason] = useState(""),
    [ids, setIds] = useState<string[]>([]),
    [type, setType] = useState(
      issue.type === "information_gap"
        ? "confirmed_information_resolved"
        : canNoDifference ? "confirmed_no_difference" : user.role === "clinician" ? "confirmed_intentional" : "",
    ),
    [recipient, setRecipient] = useState(
      kind === "task" ? "responder" : "clinician2",
    ),
    [field, setField] = useState(""),
    [verifiedField, setVerifiedField] = useState(""),
    [comparisonField, setComparisonField] = useState("product");
  const mutation = useMutation();
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const data = {
      expected_revision: issue.revision,
      reason,
      evidence_ids: ids,
      type,
      ...(live && kind === "confirm" ? {
        verified_fields: type === "confirmed_information_resolved" ? [verifiedField.trim()] : undefined,
        compared_assertion_ids: type === "confirmed_no_difference" ? issue.assertion_refs : undefined,
        comparison_fields: type === "confirmed_no_difference" ? [comparisonField] : undefined,
      } : {}),
      question: reason,
      missing_field: field,
      assignee: recipient,
      recipient,
    };
    const result = await mutation.run(
      `/issues/${issue.id}/${kind === "confirm" ? "confirmations" : kind === "task" ? "tasks" : "handoffs"}`,
      data,
    );
    if (result) {
      done();
      close();
    }
  };
  return (
    <Modal
      title={
        kind === "confirm"
          ? "Xác nhận có nguồn"
          : kind === "task"
            ? "Tạo yêu cầu xác minh"
            : "Đề nghị bàn giao"
      }
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
    >
      <form onSubmit={submit}>
        <fieldset disabled={mutation.busy || mutation.uncertain}>
          {kind === "confirm" ? (
            <label>
              Loại xác nhận
              <select value={type} onChange={(e) => setType(e.target.value)}>
                {(issue.type === "information_gap"
                  ? ["confirmed_information_resolved", ...(!live ? ["confirmed_no_difference"] : [])]
                  : user.role === "clinician"
                    ? [
                        ...(canNoDifference ? ["confirmed_no_difference"] : []),
                        "confirmed_intentional",
                        "confirmed_unintentional",
                      ]
                    : canNoDifference ? ["confirmed_no_difference"] : []
                ).map((t) => (
                  <option value={t} key={t}>
                    {labels[t]}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label>
              Người nhận
              <select
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
              >
                {users
                  .filter((u) =>
                    kind === "task"
                      ? c.assigned.includes(u.id) || u.id === "responder"
                      : c.assigned.includes(u.id) && u.id !== user.id,
                  )
                  .map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
              </select>
            </label>
          )}
          {kind === "confirm" && live && !type && (
            <p className="muted">Cần ít nhất hai dữ kiện liên quan để xác nhận không có khác biệt; chuyển cho clinician nếu cần phân loại ý định.</p>
          )}
          {kind === "confirm" && live && type === "confirmed_information_resolved" && (
            <label>
              Trường đã xác minh *
              <input required value={verifiedField} onChange={(e) => setVerifiedField(e.target.value)} placeholder="Ví dụ: tình trạng còn dùng thuốc" />
            </label>
          )}
          {kind === "confirm" && live && type === "confirmed_no_difference" && (
            <label>
              Trường đã đối chiếu *
              <select value={comparisonField} onChange={(e) => setComparisonField(e.target.value)}>
                <option value="product">Thuốc</option>
                <option value="presence">Sự hiện diện</option>
                <option value="dose">Liều</option>
                <option value="frequency">Tần suất</option>
              </select>
            </label>
          )}
          {kind === "task" && (
            <label>
              Trường cần xác minh
              <input
                required
                value={field}
                onChange={(e) => setField(e.target.value)}
              />
            </label>
          )}
          <label>
            {kind === "task" ? "Câu hỏi" : "Lý do"}
            <textarea
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          {kind !== "handoff" && (
            <EvidenceChoices items={c.evidence} ids={ids} setIds={setIds} />
          )}
        </fieldset>
        {mutation.error && <ErrorBox message={mutation.error} />}
        <button
          className="primary"
          disabled={
            mutation.busy ||
            (kind === "confirm" && (!type || (live && type === "confirmed_information_resolved" && !verifiedField.trim()))) ||
            !reason.trim() ||
            (kind !== "handoff" && !ids.length) ||
            (kind === "task" && !field.trim())
          }
        >
          {mutation.uncertain
            ? "Thử lại cùng thao tác"
            : kind === "confirm"
              ? "Lưu xác nhận"
              : kind === "task"
                ? "Gửi yêu cầu"
                : "Gửi đề nghị bàn giao"}
        </button>
      </form>
    </Modal>
  );
}
export function EditAssertion({
  c,
  assertion,
  close,
  done,
}: {
  c: Case;
  assertion: Assertion;
  close: () => void;
  done: () => void;
}) {
  const [name, setName] = useState(assertion.name),
    [dose, setDose] = useState(assertion.dose ?? ""),
    [frequency, setFrequency] = useState(assertion.frequency ?? ""),
    [ids, setIds] = useState(assertion.evidence_ids);
  const mutation = useMutation();
  return (
    <Modal
      title="Sửa dữ kiện có nguồn"
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const r = await mutation.run(
            `/cases/${c.id}/assertions/${assertion.id}`,
            {
              expected_revision: c.revision,
              name,
              dose: dose.trim() || null,
              frequency: frequency.trim() || null,
              evidence_ids: ids,
            },
            "PATCH",
          );
          if (r) {
            done();
            close();
          }
        }}
      >
        <fieldset disabled={mutation.busy || mutation.uncertain}>
          <label>
            Tên gốc
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label>
            Liều mỗi lần
            <input value={dose} onChange={(e) => setDose(e.target.value)} />
          </label>
          <label>
            Tần suất
            <input
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            />
          </label>
          <EvidenceChoices items={c.evidence} ids={ids} setIds={setIds} />
        </fieldset>
        {mutation.error && <ErrorBox message={mutation.error} />}
        <button
          className="primary"
          disabled={mutation.busy || !name.trim() || !ids.length}
        >
          {mutation.uncertain ? "Thử lại cùng thao tác" : "Lưu dữ kiện"}
        </button>
      </form>
    </Modal>
  );
}
