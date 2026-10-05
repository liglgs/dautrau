"use client";

import Link from "next/link";
import { useState } from "react";
import type { Case, Evidence, Review as ReviewType } from "./types";
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
  cx,
} from "./components/ui";
import { Icon } from "./components/icons";

function Approval({
  review,
  c,
  close,
  done,
}: {
  review: ReviewType;
  c: Case;
  close: () => void;
  done: () => void;
}) {
  const [checked, setChecked] = useState(false);
  const mutation = useMutation();
  const [revision] = useState({
    expected_revision: review.revision,
    expected_case_revision: c.revision,
  });

  const handedOffCount = review.snapshot.issues.filter(
    (i) => i.work_status === "handed_off",
  ).length;

  return (
    <Modal
      title="Ký Duyệt Biên Bản Đối Chiếu Thuốc Lâm Sàng"
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
    >
      <div className="space-y-4 text-[13px]">
        <div className="rounded-xl border border-line bg-surface-2 p-3.5">
          <p className="text-[11px] font-bold tracking-[0.1em] text-muted uppercase">
            Hồ sơ ca bệnh: <strong>{c.id}</strong> · Mã phiên bản: <strong>{review.id}</strong>
          </p>
          <div className="mt-2 flex items-center justify-between text-[12.5px]">
            <span className="text-muted">Bàn giao ca chưa giải quyết:</span>
            <span className={handedOffCount > 0 ? "font-bold text-amber-600" : "font-bold text-ok"}>
              {handedOffCount} vấn đề
            </span>
          </div>
        </div>

        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-teal-500/30 bg-teal-50/30 dark:bg-teal-950/30 p-3.5 text-[12.5px] text-ink leading-relaxed">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            className="mt-0.5 size-4 rounded accent-teal-600 cursor-pointer"
          />
          <span className="font-medium">
            Tôi xác nhận với tư cách <strong>Bác sĩ điều trị (Clinician)</strong>: Đã thẩm định toàn bộ dữ kiện thuốc, kiểm tra các đoạn trích dẫn nguồn tài liệu gốc và đồng thuận với phương án đối chiếu này.
          </span>
        </label>

        {mutation.error && <ErrorBox message={mutation.error} />}

        <div className="flex justify-end gap-2.5 pt-2 border-t border-line">
          <Button variant="secondary" disabled={mutation.busy} onClick={close}>
            Hủy bỏ
          </Button>
          <Button
            variant="primary"
            disabled={!checked || mutation.busy}
            onClick={async () => {
              if (await mutation.run(`/reviews/${review.id}/approve`, revision)) {
                done();
                close();
              }
            }}
          >
            {mutation.uncertain ? "Thử lại thao tác" : "Ký duyệt chính thức"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function Review({ caseId }: { caseId: string }) {
  const { data: c, error, load } = useApi<Case>(`/cases/${caseId}`);
  const {
    data: reviews,
    error: reviewsError,
    load: reloadReviews,
  } = useApi<ReviewType[]>(`/cases/${caseId}/reviews`);
  const [selected, setSelected] = useState<string>();
  const [approving, setApproving] = useState<ReviewType>();
  const [evidence, setEvidence] = useState<Evidence>();
  const [creating, setCreating] = useState(false);
  const mutation = useMutation();

  const reload = async () => {
    await Promise.all([load(), reloadReviews()]);
  };

  if (error || reviewsError) {
    return (
      <div className="p-6">
        <ErrorBox message={error || reviewsError} retry={reload} />
      </div>
    );
  }

  if (!c || !reviews) {
    return (
      <Panel>
        <PanelBody>
          <Empty>Đang tải dữ liệu tổng hợp biên bản phê duyệt…</Empty>
        </PanelBody>
      </Panel>
    );
  }

  const r = selected ? reviews.find((item) => item.id === selected) : reviews.at(-1);
  const clinician =
    typeof window !== "undefined" &&
    users.find((u) => u.id === sessionStorage.getItem("demo-user"))?.role === "clinician";
  const open = c.issues.filter((i) => !["closed", "handed_off"].includes(i.work_status)).length;
  const canApprove =
    !creating &&
    !mutation.busy &&
    r?.status === "draft" &&
    clinician &&
    !open &&
    !c.extraction_pending &&
    r.case_revision === c.revision;

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/cases/${caseId}`}
          className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1.5 text-[12px] font-semibold text-ink-soft shadow-xs no-underline hover:border-line-strong hover:bg-surface-2 transition-all"
        >
          <Icon name="arrowLeft" className="size-3.5" /> Quay lại không gian đối chiếu (Workspace)
        </Link>
      </div>

      <PageHeader
        eyebrow="Hồ sơ nhập viện / Biên bản đối chiếu"
        title="Tổng Hợp &amp; Phê Duyệt Lâm Sàng"
        description={`Ca bệnh ${c.id} (Mã BN: ${c.patient_id}) · Quản lý lịch sử các phiên bản nháp và biên bản đã ký duyệt.`}
        actions={
          <Button
            variant="primary"
            icon="plus"
            disabled={mutation.busy || creating}
            onClick={async () => {
              setCreating(true);
              try {
                const result = await mutation.run<ReviewType>(`/cases/${caseId}/drafts`, {
                  expected_revision: c.revision,
                });
                if (result) {
                  setSelected(result.id);
                  await reloadReviews();
                }
              } finally {
                setCreating(false);
              }
            }}
          >
            Tạo bản nháp mới
          </Button>
        }
      />

      {(error || reviewsError || mutation.error) && (
        <ErrorBox message={error || reviewsError || mutation.error} retry={reload} />
      )}

      {c.lifecycle === "changes_pending" && (
        <Notice tone="warn">
          ⚠ Có thông tin nguồn tài liệu mới đến sau khi duyệt. Bản duyệt cũ được lưu trữ bất biến. Cần tạo bản nháp mới để rà soát lại.
        </Notice>
      )}

      {!r ? (
        <Panel className="border border-line">
          <PanelBody className="py-12 text-center">
            <Empty>Chưa có bản tổng hợp nào. Hãy bấm "Tạo bản nháp mới" để bắt đầu quy trình ký duyệt.</Empty>
          </PanelBody>
        </Panel>
      ) : (
        <div className="space-y-6">
          {/* Version Selector Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-line bg-surface p-4.5 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="text-[12px] font-bold text-muted uppercase tracking-wider">
                Chọn phiên bản xem xét:
              </span>
              <select
                value={r.id}
                onChange={(e) => setSelected(e.target.value)}
                className="h-9 rounded-xl border border-line bg-surface-2 px-3 text-[13px] font-semibold text-ink outline-none cursor-pointer hover:border-brand"
              >
                {reviews.map((version, index) => (
                  <option key={version.id} value={version.id}>
                    v{index + 1} ({version.id}) —{" "}
                    {version.status === "draft"
                      ? "Bản nháp"
                      : version.status === "approved"
                        ? "Đã ký duyệt"
                        : "Bản lưu trữ"}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Badge value={r.status} />
              {r.approved_by && (
                <span className="text-[12px] font-medium text-ok">
                  ✓ Người duyệt: <strong>{r.approved_by}</strong> ({new Date(r.approved_at!).toLocaleString("vi-VN")})
                </span>
              )}
            </div>
          </div>

          {/* Clinical Snapshot Two Columns */}
          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]" data-testid="review-snapshot">
            {/* Left Column: Snapshot Medication Table */}
            <Panel className="overflow-hidden border border-line">
              <PanelHead
                eyebrow="Biên bản đối chiếu tổng hợp"
                title="Bảng Thuốc Sau Khi Thẩm Định"
                description={`Snapshot lưu lại tại mốc: ${new Date(r.snapshot.reconciliation_at).toLocaleString("vi-VN")}`}
              />
              <PanelBody className="space-y-3.5">
                <div className="space-y-2.5">
                  {r.snapshot.assertions.map((a) => (
                    <div
                      key={a.id}
                      className="rounded-xl border border-line/80 bg-surface-2/70 p-4 transition-all hover:bg-surface-2"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <strong className="font-heading text-[14.5px] text-ink">{a.name}</strong>
                          <p className="mt-1 text-[12.5px] text-ink-soft">
                            Liều lượng: <strong>{a.dose ?? "Chưa rõ"}</strong> · Tần suất:{" "}
                            <strong>{a.frequency ?? "Chưa rõ"}</strong>
                          </p>
                        </div>
                        <Badge value={a.assertion_type} />
                      </div>

                      <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line/50 pt-2.5">
                        <span className="text-[10.5px] font-bold text-muted uppercase">Bằng chứng:</span>
                        {a.evidence_ids.map((eid) => {
                          const e = r.snapshot.evidence.find((item) => item.id === eid);
                          return (
                            e && (
                              <button
                                type="button"
                                key={eid}
                                onClick={() => setEvidence(e)}
                                className="inline-flex items-center gap-1 rounded-full border border-teal-500/30 bg-teal-50/50 dark:bg-teal-950/40 px-2.5 py-0.5 text-[11px] font-semibold text-brand-ink hover:bg-teal-100 transition-colors"
                              >
                                ↗ {e.source_id}
                              </button>
                            )
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </PanelBody>
            </Panel>

            {/* Right Column: Pre-approval checklist & Timeline */}
            <aside className="space-y-5">
              <Panel className="overflow-hidden border border-line">
                <PanelHead
                  eyebrow="Điều kiện tiền kiểm lâm sàng"
                  title="Kết Quả Rà Soát &amp; Việc Chưa Xong"
                />
                <PanelBody className="space-y-3">
                  {!r.snapshot.issues.length ? (
                    <Empty>Không có khác biệt hay xung đột nào trong hồ sơ.</Empty>
                  ) : (
                    r.snapshot.issues.map((i) => (
                      <div
                        key={i.id}
                        className="rounded-xl border border-line bg-surface-2 p-3.5 text-[12.5px]"
                      >
                        <p className="font-heading font-bold text-ink">{i.title}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Badge value={i.work_status} />
                          <Badge value={i.evidence_status} />
                        </div>
                        {i.confirmation && (
                          <p className="mt-2 text-[11.5px] text-muted">
                            Lý do: {i.confirmation.reason}
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </PanelBody>
              </Panel>

              {/* Approval Action Box */}
              {r.status === "draft" && (
                <div className="rounded-2xl border-2 border-teal-500/30 bg-teal-50/20 dark:bg-teal-950/20 p-5 shadow-sm">
                  <h3 className="font-heading text-[15px] font-bold text-ink">
                    Ký Duyệt Biên Bản Phiên Bản Này
                  </h3>
                  <p className="mt-1.5 text-[12px] text-muted leading-relaxed">
                    {!clinician
                      ? "Chỉ tài khoản Bác sĩ phê duyệt (Clinician) mới có quyền ký duyệt bản cuối."
                      : c.extraction_pending
                        ? "Còn dữ kiện chưa trích xuất hoặc chưa được thẩm định."
                        : open
                          ? `Còn ${open} vấn đề chưa đóng hoặc bàn giao hợp lệ. Vui lòng xử lý trước.`
                          : r.case_revision !== c.revision
                            ? "Bản nháp đã cũ so với phiên bản ca bệnh. Hãy tải lại và tạo bản nháp mới."
                            : "Hồ sơ đã đạt điều kiện phê duyệt lâm sàng."}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2.5">
                    <Button variant="secondary" onClick={reload}>
                      Cập nhật lại
                    </Button>
                    <Button
                      variant="primary"
                      disabled={!canApprove}
                      onClick={() => setApproving(r)}
                      className="shadow-md"
                    >
                      Ký duyệt phiên bản →
                    </Button>
                  </div>
                </div>
              )}
            </aside>
          </div>
        </div>
      )}

      {approving && (
        <Approval
          review={approving}
          c={c}
          close={() => setApproving(undefined)}
          done={reload}
        />
      )}

      {evidence && (
        <Modal
          title="Trích Dẫn Nguồn Trong Snapshot"
          onClose={() => setEvidence(undefined)}
          variant="drawer"
        >
          <div className="space-y-3">
            <span className="rounded-full bg-teal-500/10 px-3 py-1 font-mono text-[11px] font-bold text-brand-ink border border-teal-500/30">
              {evidence.source_id} · v{evidence.version}
            </span>
            <div className="quote-block mt-3">
              <mark>{evidence.quote}</mark>
            </div>
            <p className="mt-2 text-[12px] text-muted font-mono leading-relaxed">
              {evidence.context}
            </p>
          </div>
        </Modal>
      )}
    </div>
  );
}
