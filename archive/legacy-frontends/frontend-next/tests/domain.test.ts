import { describe, it, expect } from "vitest";
import { seed } from "../src/mocks/seed";
import { dispatch, ServiceError } from "../src/mocks/service";
import { validateImport } from "../src/import";
import type { Review, Store } from "../src/types";
const time = "2026-09-01T08:00:00+07:00";
export const manifest = () => ({
  schema_version: "1.0",
  case_id: "IMPORTED",
  patient_id: "P-IMPORT",
  encounter_id: "E-IMPORT",
  reconciliation_at: time,
  initial_visible_at: time,
  documents: [
    {
      source_id: "NEW-S1",
      version: 1,
      kind: "medication_history",
      filename: "history.txt",
      author_role: "reviewer",
      event_time: null,
      recorded_at: time,
      available_at: time,
    },
  ],
});
function confirm(s: Store, n = 1) {
  const c = s.cases[n],
    i = c.issues[0];
  dispatch(s, "POST", `/issues/${i.id}/confirmations`, "reviewer", {
    expected_revision: i.revision,
    type: "confirmed_information_resolved",
    reason: "Đã kiểm tra nguồn mô phỏng",
    evidence_ids: i.evidence_ids,
  });
  dispatch(s, "POST", `/issues/${i.id}/close`, "reviewer", {
    expected_revision: i.revision,
  });
}
function createDraft(s: Store, n = 0) {
  const c = s.cases[n];
  return dispatch(s, "POST", `/cases/${c.id}/drafts`, "reviewer", {
    expected_revision: c.revision,
  }) as Review;
}
describe("T02 · Hợp đồng nhập nguồn", () => {
  it("nhập Unicode, giữ nguyên nội dung và không bịa extraction", () => {
    const s = seed();
    dispatch(s, "POST", "/cases/import", "reviewer", {
      manifest: manifest(),
      files: [{ name: "history.txt", text: "Tiếng Việt 🧪" }],
    });
    const c = s.cases.at(-1)!;
    expect(c.sources[0].text).toBe("Tiếng Việt 🧪");
    expect(c.assertions).toEqual([]);
    expect(c.extraction_pending).toBe(true);
    expect(() =>
      dispatch(s, "POST", `/cases/${c.id}/runs`, "reviewer", {
        expected_revision: c.revision,
      }),
    ).toThrow(/backend\/AI thật/);
  });
  it("thiếu file không tạo ca", () => {
    const s = seed();
    expect(() =>
      dispatch(s, "POST", "/cases/import", "reviewer", {
        manifest: manifest(),
        files: [],
      }),
    ).toThrow(/Thiếu tệp/);
    expect(s.cases).toHaveLength(3);
  });
  it.each(["../history.txt", "C:\\history.txt", "/history.txt"])(
    "chặn tên đường dẫn %s",
    (filename) => {
      const m = manifest();
      m.documents[0].filename = filename;
      expect(() => validateImport(m, [{ name: filename, text: "" }])).toThrow(
        /Tên tệp/,
      );
    },
  );
  it("đếm code point thay vì UTF-16", () => {
    expect(
      validateImport(manifest(), [
        { name: "history.txt", text: "🧪".repeat(12000) },
      ]).sources,
    ).toHaveLength(1);
    expect(() =>
      validateImport(manifest(), [
        { name: "history.txt", text: "🧪".repeat(12001) },
      ]),
    ).toThrow(/12.000/);
  });
  it("chặn nguồn tương lai", () => {
    const m = manifest();
    m.documents[0].available_at = "2026-09-02T08:00:00+07:00";
    expect(() =>
      validateImport(m, [{ name: "history.txt", text: "" }]),
    ).toThrow(/tương lai/);
  });
  it("chặn ID trùng và quá 8 nguồn", () => {
    const m = manifest();
    m.documents.push(m.documents[0]);
    expect(() =>
      validateImport(m, [{ name: "history.txt", text: "" }]),
    ).toThrow(/trùng/);
    m.documents = Array(9).fill(m.documents[0]);
    expect(() => validateImport(m, [])).toThrow(/8 tài liệu/);
  });
});
describe("T04–T09 · Trạng thái và quyền mô phỏng", () => {
  it("không có phiên trả 401; responder không được đọc toàn ca", () => {
    const s = seed();
    try {
      dispatch(s, "GET", "/cases", "");
    } catch (e) {
      expect((e as ServiceError).status).toBe(401);
    }
    expect(() => dispatch(s, "GET", "/cases/SIM-002", "responder")).toThrow(
      /Không tìm thấy/,
    );
  });
  it("phản hồi trở thành nguồn nhưng không tự đóng", () => {
    const s = seed(),
      c = s.cases[1];
    dispatch(s, "POST", `/cases/${c.id}/runs`, "reviewer", {
      expected_revision: 1,
    });
    const t = s.tasks[0];
    expect(() =>
      dispatch(s, "POST", `/tasks/${t.id}/responses`, "responder", {
        expected_revision: 1,
        response: "  ",
      }),
    ).toThrow(/phản hồi/);
    dispatch(s, "POST", `/tasks/${t.id}/responses`, "responder", {
      expected_revision: 1,
      response: "Chưa biết 🧪",
    });
    expect(c.issues[0].work_status).toBe("ready_for_review");
    expect(c.issues[0].evidence_status).toBe("unknown");
    expect(c.sources.at(-1)?.text).toBe("Chưa biết 🧪");
  });
  it("nhiệm vụ chỉ chia sẻ evidence được cấp", () => {
    const s = seed();
    dispatch(s, "POST", "/cases/SIM-002/runs", "reviewer", {
      expected_revision: 1,
    });
    const t = dispatch(
      s,
      "GET",
      `/tasks/${s.tasks[0].id}`,
      "responder",
    ) as Record<string, unknown>;
    expect(t).not.toHaveProperty("sources");
    expect(t).toHaveProperty("shared_evidence");
  });
  it("đóng phải có xác nhận; xác nhận cần lý do, nguồn và đúng loại", () => {
    const s = seed(),
      i = s.cases[1].issues[0];
    expect(() =>
      dispatch(s, "POST", `/issues/${i.id}/close`, "reviewer", {
        expected_revision: 1,
      }),
    ).toThrow(/Cần xác nhận/);
    expect(() =>
      dispatch(s, "POST", `/issues/${i.id}/confirmations`, "reviewer", {
        expected_revision: 1,
        type: "confirmed_information_resolved",
        reason: "",
        evidence_ids: i.evidence_ids,
      }),
    ).toThrow(/lý do/);
    expect(() =>
      dispatch(s, "POST", `/issues/${i.id}/confirmations`, "reviewer", {
        expected_revision: 1,
        type: "confirmed_intentional",
        reason: "test",
        evidence_ids: i.evidence_ids,
      }),
    ).toThrow(/bác sĩ/);
    confirm(s);
    expect(i.work_status).toBe("closed");
  });
  it("bàn giao không hoàn tất trước ack, sai người bị chặn", () => {
    const s = seed(),
      c = s.cases[1],
      i = c.issues[0];
    dispatch(s, "POST", `/issues/${i.id}/handoffs`, "reviewer", {
      expected_revision: 1,
      recipient: "clinician2",
      reason: "Cần làm rõ",
    });
    expect(i.work_status).toBe("new");
    const h = s.handoffs[0];
    expect(() =>
      dispatch(s, "POST", `/handoffs/${h.id}/ack`, "clinician", {
        expected_revision: 1,
      }),
    ).toThrow(/Chỉ người nhận/);
    dispatch(s, "POST", `/handoffs/${h.id}/ack`, "clinician2", {
      expected_revision: 1,
    });
    expect(i.work_status).toBe("handed_off");
    expect(i.evidence_status).toBe("inconclusive");
    expect(c.issues.filter((i) => i.work_status === "closed")).toHaveLength(0);
  });
  it("reviewer không duyệt; còn issue mở không duyệt", () => {
    const s = seed(),
      r = createDraft(s, 1),
      c = s.cases[1],
      body = {
        expected_revision: r.revision,
        expected_case_revision: c.revision,
      };
    expect(() =>
      dispatch(s, "POST", `/reviews/${r.id}/approve`, "reviewer", body),
    ).toThrow(/bác sĩ/);
    expect(() =>
      dispatch(s, "POST", `/reviews/${r.id}/approve`, "clinician", body),
    ).toThrow(/Còn việc mở/);
  });
  it("nháp stale bị chặn", () => {
    const s = seed(),
      r = createDraft(s);
    s.cases[0].revision++;
    expect(() =>
      dispatch(s, "POST", `/reviews/${r.id}/approve`, "clinician", {
        expected_revision: 1,
        expected_case_revision: 1,
      }),
    ).toThrow(/đã thay đổi/);
    expect(r.status).toBe("draft");
  });
  it("nguồn sau duyệt giữ snapshot và tạo nháp mới", () => {
    const s = seed();
    confirm(s, 2);
    const c = s.cases[2],
      r = createDraft(s, 2);
    dispatch(s, "POST", `/reviews/${r.id}/approve`, "clinician", {
      expected_revision: r.revision,
      expected_case_revision: c.revision,
    });
    const old = JSON.stringify(r.snapshot);
    dispatch(s, "POST", `/cases/${c.id}/demo-event`, "reviewer", {
      expected_revision: c.revision,
    });
    expect(c.lifecycle).toBe("changes_pending");
    expect(c.issues[0].work_status).toBe("new");
    expect(JSON.stringify(r.snapshot)).toBe(old);
    expect(r.status).toBe("approved");
    expect(s.reviews.at(-1)?.status).toBe("draft");
  });
});
