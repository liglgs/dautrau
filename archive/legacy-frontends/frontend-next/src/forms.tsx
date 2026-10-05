"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type { Case, Evidence, Issue, Assertion } from "./types";
import { labels } from "./types";
import { Button, ErrorBox, Modal, Notice, cx } from "./components/ui";
import { Icon } from "./components/icons";
import { readImport } from "./import";
import { useMutation } from "./hooks";
import { users } from "./mocks/seed";
import { isLive } from "./lib/env";

const inputClass =
  "mt-1.5 h-10 w-full rounded-[10px] border border-line bg-surface px-3 text-[13px] text-ink";
const textareaClass =
  "mt-1.5 min-h-[104px] w-full rounded-[10px] border border-line bg-surface px-3 py-2.5 text-[13px] leading-relaxed text-ink";
const labelClass = "block text-[12px] font-semibold text-ink-soft";
const checkRowClass =
  "flex items-start gap-2.5 rounded-[10px] border border-line bg-surface-2 px-3.5 py-3 text-[12.5px] font-medium text-ink-soft";

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
  const router = useRouter();

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
      setReceipt(`Đã nhập ${result.source_count} nguồn. Receipt: ${result.receipt}`);
      done();
      if (!c) {
        // Giữ thông báo "Đã nhập … nguồn" khi mở ca mới (thay cho router state cũ).
        router.push(
          `/cases/${result.case_id}?receipt=${encodeURIComponent(
            `Đã nhập ${result.source_count} nguồn · ${result.receipt}`,
          )}`,
        );
      }
    }
  };

  return (
    <Modal
      title={c ? "Bổ sung nguồn" : "Nhập hồ sơ mô phỏng"}
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
      footer={
        receipt ? (
          <div className="flex justify-end">
            <Button variant="primary" onClick={close}>
              Đóng
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-2.5">
            <Button
              variant="secondary"
              type="button"
              onClick={validate}
              disabled={mutation.busy || mutation.uncertain || !!receipt}
            >
              Kiểm tra gói
            </Button>
            <Button
              variant="primary"
              type="submit"
              form="import-form"
              disabled={!valid || !checked || mutation.busy}
            >
              {mutation.uncertain ? "Thử lại cùng thao tác" : "Nhập hồ sơ"}
            </Button>
          </div>
        )
      }
    >
      <form id="import-form" onSubmit={submit} className="space-y-4">
        <p className="text-[12.5px] text-muted">
          Chọn case.json và tệp TXT UTF-8. Tối đa 8 tệp/gói, 12.000 ký tự/tệp. Chỉ dữ liệu mô
          phỏng.
        </p>
        <fieldset
          disabled={mutation.busy || mutation.uncertain || !!receipt}
          className="space-y-3.5"
        >
          <label className={labelClass}>
            Manifest JSON
            <input
              type="file"
              accept=".json"
              className={inputClass}
              onChange={(e) => {
                setManifest(e.target.files?.[0]);
                setValid(undefined);
              }}
            />
          </label>
          <label className={labelClass}>
            Nguồn TXT
            <input
              type="file"
              accept=".txt"
              multiple
              className={inputClass}
              onChange={(e) => {
                setFiles(Array.from(e.target.files ?? []));
                setValid(undefined);
              }}
            />
          </label>
          <label className={checkRowClass}>
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-[var(--brand)]"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            Tôi xác nhận đây là dữ liệu mô phỏng
          </label>
        </fieldset>
        {valid && (
          <Notice tone="ok">
            Gói hợp lệ: {valid.manifest.case_id} · {valid.sources.length} nguồn
          </Notice>
        )}
        {(error || mutation.error) && <ErrorBox message={error || mutation.error} />}
        {receipt && (
          <Notice tone="ok">
            <span className="flex items-center gap-2">
              <Icon name="checkCircle" className="size-4" />
              {receipt}
            </span>
          </Notice>
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
    <fieldset className="space-y-2">
      <legend className="mb-1 text-[12px] font-semibold text-ink-soft">
        Nguồn bằng chứng *
      </legend>
      <div className="max-h-[240px] space-y-2 overflow-y-auto pr-1">
        {items.map((e) => (
          <label
            key={e.id}
            className={cx(
              checkRowClass,
              "cursor-pointer leading-relaxed",
              ids.includes(e.id) && "border-brand/40 bg-brand-soft",
            )}
          >
            <input
              type="checkbox"
              className="mt-0.5 size-4 shrink-0 accent-[var(--brand)]"
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
              <span className="font-semibold text-ink">{e.source_id}</span> ·{" "}
              {e.quote.slice(0, 85)}
            </span>
          </label>
        ))}
      </div>
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
  const live = isLive;
  const canNoDifference = !live || (issue.assertion_refs?.length ?? 0) >= 2;
  const [reason, setReason] = useState(""),
    [ids, setIds] = useState<string[]>([]),
    [type, setType] = useState(
      issue.type === "information_gap"
        ? "confirmed_information_resolved"
        : canNoDifference
          ? "confirmed_no_difference"
          : user.role === "clinician"
            ? "confirmed_intentional"
            : "",
    ),
    [recipient, setRecipient] = useState(kind === "task" ? "responder" : "clinician2"),
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
      ...(live && kind === "confirm"
        ? {
            verified_fields:
              type === "confirmed_information_resolved" ? [verifiedField.trim()] : undefined,
            compared_assertion_ids:
              type === "confirmed_no_difference" ? issue.assertion_refs : undefined,
            comparison_fields:
              type === "confirmed_no_difference" ? [comparisonField] : undefined,
          }
        : {}),
      question: reason,
      missing_field: field,
      assignee: recipient,
      recipient,
    };
    const result = await mutation.run(
      `/issues/${issue.id}/${
        kind === "confirm" ? "confirmations" : kind === "task" ? "tasks" : "handoffs"
      }`,
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
      <form onSubmit={submit} className="space-y-4">
        <fieldset disabled={mutation.busy || mutation.uncertain} className="space-y-3.5">
          {kind === "confirm" ? (
            <label className={labelClass}>
              Loại xác nhận
              <select
                className={inputClass}
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                {(issue.type === "information_gap"
                  ? ["confirmed_information_resolved", ...(!live ? ["confirmed_no_difference"] : [])]
                  : user.role === "clinician"
                    ? [
                        ...(canNoDifference ? ["confirmed_no_difference"] : []),
                        "confirmed_intentional",
                        "confirmed_unintentional",
                      ]
                    : canNoDifference
                      ? ["confirmed_no_difference"]
                      : []
                ).map((t) => (
                  <option value={t} key={t}>
                    {labels[t]}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label className={labelClass}>
              Người nhận
              <select
                className={inputClass}
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
            <Notice tone="warn">
              Cần ít nhất hai dữ kiện liên quan để xác nhận không có khác biệt; chuyển cho
              clinician nếu cần phân loại ý định.
            </Notice>
          )}

          {kind === "confirm" && live && type === "confirmed_information_resolved" && (
            <label className={labelClass}>
              Trường đã xác minh *
              <input
                required
                className={inputClass}
                value={verifiedField}
                onChange={(e) => setVerifiedField(e.target.value)}
                placeholder="Ví dụ: tình trạng còn dùng thuốc"
              />
            </label>
          )}

          {kind === "confirm" && live && type === "confirmed_no_difference" && (
            <label className={labelClass}>
              Trường đã đối chiếu *
              <select
                className={inputClass}
                value={comparisonField}
                onChange={(e) => setComparisonField(e.target.value)}
              >
                <option value="product">Thuốc</option>
                <option value="presence">Sự hiện diện</option>
                <option value="dose">Liều</option>
                <option value="frequency">Tần suất</option>
              </select>
            </label>
          )}

          {kind === "task" && (
            <label className={labelClass}>
              Trường cần xác minh
              <input
                required
                className={inputClass}
                value={field}
                onChange={(e) => setField(e.target.value)}
              />
            </label>
          )}

          <label className={labelClass}>
            {kind === "task" ? "Câu hỏi" : "Lý do"}
            <textarea
              required
              className={textareaClass}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>

          {kind !== "handoff" && <EvidenceChoices items={c.evidence} ids={ids} setIds={setIds} />}
        </fieldset>

        {mutation.error && <ErrorBox message={mutation.error} />}

        <div className="flex justify-end">
          <Button
            variant="primary"
            type="submit"
            disabled={
              mutation.busy ||
              (kind === "confirm" &&
                (!type || (live && type === "confirmed_information_resolved" && !verifiedField.trim()))) ||
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
          </Button>
        </div>
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
        className="space-y-4"
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
        <fieldset disabled={mutation.busy || mutation.uncertain} className="space-y-3.5">
          <label className={labelClass}>
            Tên gốc
            <input
              className={inputClass}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className={labelClass}>
            Liều mỗi lần
            <input
              className={inputClass}
              value={dose}
              onChange={(e) => setDose(e.target.value)}
            />
          </label>
          <label className={labelClass}>
            Tần suất
            <input
              className={inputClass}
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
            />
          </label>
          <EvidenceChoices items={c.evidence} ids={ids} setIds={setIds} />
        </fieldset>
        {mutation.error && <ErrorBox message={mutation.error} />}
        <div className="flex justify-end">
          <Button
            variant="primary"
            type="submit"
            disabled={mutation.busy || !name.trim() || !ids.length}
          >
            {mutation.uncertain ? "Thử lại cùng thao tác" : "Lưu dữ kiện"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
