import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { Case, Evidence, Review as ReviewType } from "./types";
import { users } from "./mocks/seed";
import { useApi, useMutation } from "./hooks";
import { Badge, Empty, ErrorBox, Modal } from "./components";
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
  // Captured revisions intentionally remain fixed while this modal is open.
  const [revision] = useState({
    expected_revision: review.revision,
    expected_case_revision: c.revision,
  });
  return (
    <Modal
      title="Duyệt phiên bản"
      onClose={() => {
        if (!mutation.busy && !mutation.uncertain) close();
      }}
    >
      <p>
        {c.id} · {review.id}
      </p>
      <p>
        Bàn giao chưa giải quyết:{" "}
        {
          review.snapshot.issues.filter((i) => i.work_status === "handed_off")
            .length
        }
      </p>
      <label className="check">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
        />
        Tôi đã rà nội dung, nguồn và phần việc chưa giải quyết.
      </label>
      {mutation.error && <ErrorBox message={mutation.error} />}
      <button
        className="primary"
        disabled={!checked || mutation.busy}
        onClick={async () => {
          if (await mutation.run(`/reviews/${review.id}/approve`, revision)) {
            done();
            close();
          }
        }}
      >
        {mutation.uncertain ? "Thử lại cùng thao tác" : "Xác nhận duyệt"}
      </button>
    </Modal>
  );
}
export default function Review() {
  const { id } = useParams();
  const { data: c, error, load } = useApi<Case>(`/cases/${id}`);
  const {
    data: reviews,
    error: reviewsError,
    load: reloadReviews,
  } = useApi<ReviewType[]>(`/cases/${id}/reviews`);
  const [selected, setSelected] = useState(""),
    [approving, setApproving] = useState<ReviewType>(),
    [evidence, setEvidence] = useState<Evidence>();
  const [creating, setCreating] = useState(false);
  const mutation = useMutation();
  const reload = () => {
    void load();
    void reloadReviews();
  };
  if (!c || !reviews)
    return error || reviewsError ? (
      <ErrorBox message={error || reviewsError} retry={reload} />
    ) : (
      <Empty>Đang tải tổng hợp…</Empty>
    );
  const r = selected ? reviews.find((r) => r.id === selected) : reviews.at(-1);
  const clinician =
    users.find((u) => u.id === sessionStorage.getItem("demo-user"))?.role ===
    "clinician";
  const open = c.issues.filter(
    (i) => !["closed", "handed_off"].includes(i.work_status),
  ).length;
  const canApprove =
    !creating &&
    !mutation.busy &&
    r?.status === "draft" &&
    clinician &&
    !open &&
    !c.extraction_pending &&
    r.case_revision === c.revision;
  return (
    <>
      <Link to={`/cases/${id}`}>← Về đối chiếu</Link>
      <div className="pagehead">
        <div>
          <p className="eyebrow">HỒ SƠ NHẬP VIỆN / TỔNG HỢP</p>
          <h1>Tổng hợp và duyệt</h1>
          <p className="muted">
            {c.id} · Dữ liệu có nguồn và lịch sử phiên bản
          </p>
        </div>
        <button
          className="primary"
          disabled={mutation.busy || creating}
          onClick={async () => {
            setCreating(true);
            try {
              const result = await mutation.run<ReviewType>(
                `/cases/${id}/drafts`,
                { expected_revision: c.revision },
              );
              if (result) {
                setSelected(result.id);
                await reloadReviews();
              }
            } finally {
              setCreating(false);
            }
          }}
        >
          Tạo bản nháp
        </button>
      </div>
      {(error || reviewsError || mutation.error) && (
        <ErrorBox
          message={error || reviewsError || mutation.error}
          retry={reload}
        />
      )}
      {c.lifecycle === "changes_pending" && (
        <div className="notice">
          Có thông tin mới; cần rà lại. Bản đã duyệt cũ được giữ nguyên.
        </div>
      )}
      {!r ? (
        <Empty>Chưa có bản tổng hợp. Tạo bản nháp để rà soát.</Empty>
      ) : (
        <>
          <label>
            Phiên bản
            <select value={r.id} onChange={(e) => setSelected(e.target.value)}>
              {reviews.map((version, index) => (
                <option key={version.id} value={version.id}>
                  v{index + 1} ·{" "}
                  {version.status === "draft"
                    ? "Nháp"
                    : version.status === "approved"
                      ? "Đã duyệt"
                      : "Bản cũ"}
                </option>
              ))}
            </select>
          </label>
          <div className="statusline">
            <Badge value={r.status} />
            {r.approved_by && (
              <span>
                {r.approved_by} ·{" "}
                {new Date(r.approved_at!).toLocaleString("vi-VN")}
              </span>
            )}
          </div>
          {r.status !== "draft" &&
            r.snapshot.issues.some((i) => i.work_status === "handed_off") && (
              <div className="notice">Đã duyệt — còn việc chưa giải quyết</div>
            )}
          <div className="review-layout" data-testid="review-snapshot">
          <div className="panel panelbody review-document">
            <p className="eyebrow">BẢN TỔNG HỢP CÓ NGUỒN · {c.id}</p>
            <h2>Bối cảnh và mốc đối chiếu</h2>
            <p>
              Mốc:{" "}
              {new Date(r.snapshot.reconciliation_at).toLocaleString("vi-VN")}.
              Bối cảnh bệnh chưa được cung cấp trong dữ liệu mẫu.
            </p>
            <h2>Bảng thuốc</h2>
            {r.snapshot.assertions.map((a) => (
              <p key={a.id}>
                <strong>{a.name}</strong> · {a.dose ?? "Chưa có thông tin"} ·{" "}
                {a.frequency ?? "Chưa rõ tần suất"}{" "}
                {a.evidence_ids.map((eid) => {
                  const e = r.snapshot.evidence.find((e) => e.id === eid);
                  return (
                    e && (
                      <button
                        className="source"
                        key={eid}
                        onClick={() => setEvidence(e)}
                      >
                        ↗ {e.source_id}
                      </button>
                    )
                  );
                })}
              </p>
            ))}
          </div>
          <div className="review-aside">
            <div className="panel panelbody">
            <p className="eyebrow">CẦN KIỂM TRA TRƯỚC DUYỆT</p>
            <h2>Kết quả và việc chưa giải quyết</h2>
            {!r.snapshot.issues.length && (
              <p>Không có khác biệt trong các trường được so.</p>
            )}
            {r.snapshot.issues.map((i) => (
              <div className="issue" key={i.id}>
                <p>{i.title}</p>
                <div className="statusline">
                  <Badge value={i.work_status} />
                  <Badge value={i.evidence_status} />
                </div>
                {i.confirmation && <p>Xác nhận: {i.confirmation.reason}</p>}
              </div>
            ))}
            </div>
            <div className="panel panelbody">
            <h2>Timeline nguồn</h2>
            <ul className="timeline">
              {r.snapshot.sources.map((s) => (
                <li key={`${s.source_id}-${s.version}`}>
                  {s.event_time ?? "Không rõ thời điểm"} · {s.filename} · v
                  {s.version}
                </li>
              ))}
            </ul>
            <h2>Nhật ký trong bản tổng hợp</h2>
            <ul>
              {r.snapshot.audit.map((entry, index) => (
                <li key={index}>{entry}</li>
              ))}
            </ul>
            <p className="notice">Tương tác thuốc chưa được đánh giá.</p>
            </div>
          </div>
          </div>
          {r.status === "draft" && (
            <>
              <p className="muted">
                {!clinician
                  ? "Chỉ tài khoản bác sĩ được duyệt bản cuối."
                  : c.extraction_pending
                    ? "Còn dữ kiện chưa trích xuất/kiểm tra."
                    : open
                      ? `Còn ${open} vấn đề chưa đóng hoặc bàn giao hợp lệ.`
                      : r.case_revision !== c.revision
                        ? "Bản nháp đã cũ; tải lại và tạo bản nháp mới."
                        : "Đủ điều kiện trình duyệt."}
              </p>
              <div className="actions">
                <button onClick={reload}>Tải bản mới</button>
                <button
                  className="primary"
                  disabled={!canApprove}
                  onClick={() => setApproving(r)}
                >
                  Duyệt phiên bản
                </button>
              </div>
            </>
          )}
        </>
      )}
      {approving && (
        <Approval
          review={approving}
          c={c}
          close={() => setApproving(undefined)}
          done={reload}
        />
      )}{" "}
      {evidence && (
        <Modal
          title="Nguồn trong snapshot"
          onClose={() => setEvidence(undefined)}
        >
          <p>
            {evidence.source_id} · v{evidence.version}
          </p>
          <div className="doc">
            <mark>{evidence.quote}</mark>
          </div>
          <p>{evidence.context}</p>
        </Modal>
      )}
    </>
  );
}
