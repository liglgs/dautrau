import type {
  Case,
  EvidenceStatus,
  Review,
  Source,
  Store,
  User,
} from "../types";
import { users } from "./seed";
import { validateImport } from "../import";
export class ServiceError extends Error {
  constructor(
    public status: number,
    message: string,
    public code = "VALIDATION_ERROR",
  ) {
    super(message);
  }
}
const fail = (message: string, status = 422, code?: string): never => {
  throw new ServiceError(status, message, code);
};
const uid = (prefix: string) => `${prefix}-${crypto.randomUUID()}`;
const required = (v: unknown, field: string): string =>
  typeof v === "string" && v.trim() ? v.trim() : fail(`Thiếu ${field}.`);
function revision(actual: number, expected: unknown) {
  if (actual !== expected)
    fail(
      `Hồ sơ đã thay đổi (revision ${actual}). Tải bản mới trước khi tiếp tục.`,
      409,
      "REVISION_CONFLICT",
    );
}
function reviewer(user: User) {
  if (!["reviewer", "clinician"].includes(user.role))
    fail("Bạn không có quyền thao tác này.", 403, "FORBIDDEN");
}
function clinician(user: User) {
  if (user.role !== "clinician")
    fail(
      "Chỉ tài khoản bác sĩ được xác nhận ý định và duyệt.",
      403,
      "FORBIDDEN",
    );
}
function getCase(s: Store, id: string, user: User) {
  return (
    s.cases.find((c) => c.id === id && c.assigned.includes(user.id)) ??
    fail("Không tìm thấy ca trong phạm vi của bạn.", 404, "NOT_FOUND")
  );
}
function touch(c: Case, action: string) {
  c.revision++;
  if (c.lifecycle === "approved") c.lifecycle = "changes_pending";
  c.audit.push(action);
}
function evidence(c: Case, ids: unknown): string[] {
  if (
    !Array.isArray(ids) ||
    !ids.length ||
    ids.some(
      (id) => typeof id !== "string" || !c.evidence.some((e) => e.id === id),
    )
  )
    fail("Cần chọn nguồn bằng chứng hợp lệ.");
  return ids as string[];
}
function draft(s: Store, c: Case): Review {
  const r: Review = {
    id: uid("REV"),
    case_id: c.id,
    revision: 1,
    case_revision: c.revision,
    status: "draft",
    snapshot: structuredClone({
      assertions: c.assertions,
      issues: c.issues,
      sources: c.sources,
      evidence: c.evidence,
      audit: c.audit,
      reconciliation_at: c.reconciliation_at,
    }),
  };
  s.reviews.push(r);
  return r;
}
function parseImport(body: any) {
  try {
    return validateImport(body.manifest, body.files);
  } catch (e) {
    return fail((e as Error).message);
  }
}
export function dispatch(
  s: Store,
  method: string,
  path: string,
  userId: string,
  body: any = {},
): unknown {
  const user =
    users.find((u) => u.id === userId) ??
    fail("Chọn tài khoản demo để tiếp tục.", 401, "SESSION_REQUIRED");
  const p = path.split("/").filter(Boolean);
  if (path === "/sessions/current" && method === "GET") return user;
  if (path === "/users" && method === "GET") return users;
  if (path === "/cases" && method === "GET")
    return s.cases.filter((c) => c.assigned.includes(user.id));
  if (path === "/cases/import" && method === "POST") {
    reviewer(user);
    const { manifest: m, sources } = parseImport(body);
    if (s.cases.some((c) => c.id === m.case_id))
      fail("Mã ca đã tồn tại; không nhập đè hồ sơ.", 409, "CASE_EXISTS");
    const c: Case = {
      id: m.case_id,
      patient_id: m.patient_id,
      encounter_id: m.encounter_id,
      reconciliation_at: m.reconciliation_at,
      visible_at: m.initial_visible_at,
      lifecycle: "draft",
      revision: 1,
      assigned: ["reviewer", "clinician", "clinician2"],
      scenario: null,
      run: null,
      sources,
      evidence: [],
      assertions: [],
      issues: [],
      audit: ["Đã nhập gói TXT/JSON"],
      extraction_pending: true,
    };
    s.cases.push(c);
    return {
      case_id: c.id,
      source_count: sources.length,
      receipt: uid("IMPORT"),
    };
  }
  if (p[0] === "cases" && p[1]) {
    const c = getCase(s, p[1], user);
    if (method === "GET") {
      if (p.length === 2) return c;
      if (p[2] === "evidence")
        return (
          c.evidence.find((e) => e.id === p[3]) ??
          fail("Không tìm thấy evidence.", 404)
        );
      if (p[2] === "sources") return c.sources;
      if (p[2] === "assertions") return c.assertions;
      if (p[2] === "issues") return c.issues;
      if (p[2] === "timeline")
        return c.sources.map((source) => ({
          source_id: source.source_id,
          event_time: source.event_time,
          label: source.filename,
        }));
      if (p[2] === "audit") return c.audit;
      if (p[2] === "reviews")
        return s.reviews.filter((r) => r.case_id === c.id);
    }
    reviewer(user);
    revision(c.revision, body.expected_revision);
    if (p[2] === "runs" && method === "POST") {
      if (!c.scenario || c.extraction_pending)
        fail(
          "Hồ sơ này cần backend/AI thật để trích xuất. Không có kịch bản mô phỏng.",
          422,
          "NO_FIXTURE",
        );
      if (
        c.run &&
        ["queued", "running", "waiting_event"].includes(c.run.status)
      )
        return c.run;
      if (c.lifecycle === "draft") c.lifecycle = "reviewing";
      c.run = { id: uid("RUN"), status: "completed" };
      const issue = c.issues.find(
        (i) => !["closed", "handed_off"].includes(i.work_status),
      );
      if (issue) {
        if (
          !s.tasks.some((t) => t.issue_id === issue.id && t.status === "open")
        )
          s.tasks.push({
            id: uid("TASK"),
            case_id: c.id,
            issue_id: issue.id,
            revision: 1,
            assignee: "responder",
            question:
              "Tại mốc nhập viện, người bệnh còn dùng Thuốc A không? Ghi rõ nguồn thông tin.",
            missing_fields: ["trạng thái dùng"],
            evidence_ids: issue.evidence_ids,
            status: "open",
          });
        issue.work_status = "waiting_response";
        issue.revision++;
        c.run.status = "waiting_event";
      }
      touch(c, "Kịch bản mô phỏng: đối chiếu dữ liệu mẫu, không gọi AI");
      return c.run;
    }
    if (p[2] === "drafts" && method === "POST") return draft(s, c);
    if (p[2] === "assertions" && method === "PATCH") {
      const a =
        c.assertions.find((a) => a.id === p[3]) ??
        fail("Không có dữ kiện.", 404);
      const ids = evidence(c, body.evidence_ids);
      for (const field of ["name", "product", "dose", "frequency"] as const)
        if (field in body) {
          if (body[field] !== null && typeof body[field] !== "string")
            fail("Giá trị không hợp lệ.");
          a[field] = body[field];
        }
      a.name = required(a.name, "tên thuốc");
      a.evidence_ids = ids;
      a.revision++;
      c.issues.forEach((i) => {
        i.history.push(`Giữ xác nhận cũ: ${i.evidence_status}`);
        i.work_status = "new";
        i.evidence_status = "unknown";
        delete i.confirmation;
        i.revision++;
      });
      touch(c, `${user.name}: sửa dữ kiện có nguồn`);
      return a;
    }
    if (p[2] === "sources" && method === "POST") {
      const parsed = parseImport(body);
      if (
        parsed.manifest.case_id !== c.id ||
        parsed.manifest.patient_id !== c.patient_id ||
        parsed.manifest.encounter_id !== c.encounter_id ||
        parsed.manifest.reconciliation_at !== c.reconciliation_at
      )
        fail("Metadata không khớp ca đang mở.");
      if (c.sources.length + parsed.sources.length > 30)
        fail("Tối đa 30 nguồn mọi phiên bản/ca.");
      if (
        parsed.sources.some((source) =>
          c.sources.some(
            (old) =>
              old.source_id === source.source_id &&
              old.version === source.version,
          ),
        )
      )
        fail("Nguồn/phiên bản đã tồn tại.", 409);
      if (parsed.manifest.initial_visible_at !== c.visible_at)
        fail("Không được tự đổi đồng hồ ca trong giao diện nhập nguồn.");
      c.sources.push(...parsed.sources);
      c.extraction_pending = true;
      touch(c, `${user.name}: bổ sung nguồn; cần trích xuất/rà soát mới`);
      draft(s, c);
      return {
        case_id: c.id,
        source_count: parsed.sources.length,
        receipt: uid("SOURCE"),
      };
    }
    if (p[2] === "demo-event" && method === "POST") {
      if (c.scenario !== "late") fail("Chỉ có kịch bản này ở SIM-003.");
      if (!s.reviews.some((r) => r.case_id === c.id && r.status === "approved"))
        fail("Cần duyệt v1 trước khi phát nguồn mẫu.");
      if (c.sources.some((source) => source.source_id === `${c.id}-LATE`))
        fail("Nguồn mẫu đã phát hành.", 409);
      const text =
        "Nguồn bổ sung mô phỏng: đề nghị xác minh lại trạng thái dùng Thuốc A. 🧪";
      const source: Source = {
        source_id: `${c.id}-LATE`,
        version: 1,
        kind: "clinical_note",
        filename: "late-note.txt",
        author_role: "clinician",
        event_time: c.reconciliation_at,
        recorded_at: c.visible_at,
        available_at: c.visible_at,
        text,
      };
      c.sources.push(source);
      const e = {
        id: uid("EVID"),
        source_id: source.source_id,
        version: 1,
        quote: text,
        context: text,
      };
      c.evidence.push(e);
      c.issues.forEach((i) => {
        i.history.push(`Trước cập nhật: ${i.evidence_status}`);
        i.work_status = "new";
        i.evidence_status = "unknown";
        i.evidence_ids.push(e.id);
        i.revision++;
        delete i.confirmation;
      });
      c.run = { id: uid("RUN"), status: "completed" };
      touch(c, "Phát nguồn bổ sung theo kịch bản mô phỏng");
      draft(s, c);
      return c;
    }
    if (p[2] === "chat") {
      if (!s.chatMessages) s.chatMessages = [];
      if (method === "GET") {
        return s.chatMessages.filter((m) => m.case_id === c.id);
      }
      if (method === "POST") {
        const text = required(body.text, "nội dung câu hỏi");
        const userMsg = {
          id: uid("MSG-U"),
          case_id: c.id,
          sender: "user" as const,
          text,
          timestamp: new Date().toISOString(),
        };
        s.chatMessages.push(userMsg);

        let replyText = `Tôi đã tiếp nhận câu hỏi về ca ${c.id}: "${text}". `;
        const citations: { source_id: string; version: number; quote: string }[] = [];
        const reasoning: string[] = [
          `Tiếp nhận truy vấn từ người dùng ${user.name}`,
          `Nạp hồ sơ ca ${c.id} gồm ${c.sources.length} nguồn văn bản, ${c.assertions.length} dữ kiện thuốc`,
        ];

        const lower = text.toLowerCase();
        if (lower.includes("thuốc") || lower.includes("khác") || lower.includes("tóm tắt") || lower.includes("liệt kê")) {
          const names = c.assertions.map((a) => `${a.name} (${a.side === "history" ? "Đơn cũ" : "Y lệnh"})`).join(", ");
          replyText += `Hiện tại hồ sơ ghi nhận các phát biểu thuốc: ${names || "chưa có trích xuất"}. `;
          if (c.evidence.length > 0) {
            const ev = c.evidence[0];
            citations.push({ source_id: ev.source_id, version: ev.version, quote: ev.quote });
            reasoning.push(`Đối chiếu trực tiếp với đoạn trích ${ev.source_id} v${ev.version}`);
          }
          if (c.issues.length > 0) {
            replyText += `Phát hiện ${c.issues.length} vấn đề cần xác minh lâm sàng: ${c.issues.map((i) => i.title).join("; ")}.`;
            reasoning.push(`Đã ghi nhận ${c.issues.length} vấn đề mở thuộc loại ${c.issues.map((i) => i.type).join(", ")}`);
          } else {
            replyText += "Tất cả thuốc đều khớp đối chiếu, không phát hiện chênh lệch hay khoảng trống thông tin.";
            reasoning.push("Không có vấn đề chênh lệch chưa giải quyết");
          }
        } else if (lower.includes("tại sao") || lower.includes("lý do") || lower.includes("gap") || lower.includes("quy tắc")) {
          replyText += `Theo quy tắc bảo vệ lâm sàng của đề tài VMEC-03: Mọi dữ kiện thuốc từ đơn cũ nếu không có bằng chứng khẳng định người bệnh đang tiếp tục dùng thì hệ thống TUYỆT ĐỐI KHÔNG tự suy diễn, mà bắt buộc gán nhãn 'information_gap' và yêu cầu điều dưỡng xác minh thực tế.`;
          reasoning.push("Kích hoạt quy tắc an toàn: không suy diễn thuốc đang dùng từ đơn cũ");
          if (c.evidence.length > 0) {
            citations.push({ source_id: c.evidence[0].source_id, version: c.evidence[0].version, quote: c.evidence[0].quote });
          }
        } else {
          replyText += `Dựa trên phân tích của AI Agent: Ca ${c.id} đang ở trạng thái '${c.lifecycle}'. Hệ thống luôn sẵn sàng hỗ trợ đối chiếu chi tiết liều lượng, dạng dùng và trích dẫn bằng chứng gốc.`;
          reasoning.push("Phân tích tổng quan trạng thái vòng đời ca bệnh");
        }

        const agentMsg = {
          id: uid("MSG-A"),
          case_id: c.id,
          sender: "agent" as const,
          text: replyText,
          timestamp: new Date(Date.now() + 500).toISOString(),
          citations,
          reasoning,
        };
        s.chatMessages.push(agentMsg);
        return agentMsg;
      }
    }
  }
  if (p[0] === "runs" && method === "GET")
    return (
      s.cases.find((c) => c.run?.id === p[1] && c.assigned.includes(user.id))
        ?.run ?? fail("Không có lượt chạy.", 404)
    );
  if (p[0] === "tasks") {
    const allowed = (t: Store["tasks"][number]) =>
      t.assignee === user.id ||
      s.cases.some((c) => c.id === t.case_id && c.assigned.includes(user.id));
    if (p.length === 1 && method === "GET") return s.tasks.filter(allowed);
    const t =
      s.tasks.find((t) => t.id === p[1] && allowed(t)) ??
      fail("Không tìm thấy nhiệm vụ.", 404);
    const c = s.cases.find((c) => c.id === t.case_id)!;
    if (method === "GET")
      return {
        ...t,
        shared_evidence: c.evidence.filter((e) =>
          t.evidence_ids.includes(e.id),
        ),
      };
    revision(t.revision, body.expected_revision);
    if (t.status !== "open") fail("Nhiệm vụ không còn mở.", 409);
    if (p[2] === "responses" && method === "POST") {
      if (
        user.id !== t.assignee &&
        !["reviewer", "clinician"].includes(user.role)
      )
        fail("Không được trả lời nhiệm vụ này.", 403);
      const response = required(body.response, "phản hồi");
      if (Array.from(response).length > 12000 || c.sources.length >= 30)
        fail("Phản hồi hoặc số nguồn vượt giới hạn.");
      t.response = response;
      t.status = "answered";
      t.revision++;
      const sourceId = uid("RESP"),
        eid = uid("EVID");
      c.sources.push({
        source_id: sourceId,
        version: 1,
        kind: "verification_response",
        filename: `${sourceId}.txt`,
        author_role: user.role,
        event_time: null,
        recorded_at: c.visible_at,
        available_at: c.visible_at,
        text: response,
      });
      c.evidence.push({
        id: eid,
        source_id: sourceId,
        version: 1,
        quote: response,
        context: response,
      });
      const issue = c.issues.find((i) => i.id === t.issue_id)!;
      issue.work_status = "ready_for_review";
      issue.evidence_ids.push(eid);
      issue.revision++;
      c.run = {
        id: c.run?.id ?? uid("RUN"),
        status: s.tasks.some(
          (task) => task.case_id === c.id && task.status === "open",
        )
          ? "waiting_event"
          : "completed",
      };
      touch(c, `${user.name}: lưu phản hồi thành nguồn; chờ người rà soát`);
      return { receipt: uid("RESPONSE"), task: t };
    }
    if (p[2] === "cancel" && method === "POST") {
      reviewer(user);
      t.reason = required(body.reason, "lý do hủy");
      t.status = "cancelled";
      t.revision++;
      const i = c.issues.find((i) => i.id === t.issue_id)!;
      i.work_status = "ready_for_review";
      i.revision++;
      touch(c, `${user.name}: hủy nhiệm vụ — ${t.reason}`);
      return t;
    }
  }
  if (p[0] === "issues") {
    const parent = s.cases.find((c) => c.issues.some((i) => i.id === p[1]));
    const c = getCase(s, parent?.id ?? "", user);
    reviewer(user);
    const i = c.issues.find((i) => i.id === p[1])!;
    revision(i.revision, body.expected_revision);
    if (["closed", "handed_off"].includes(i.work_status))
      fail("Vấn đề đã kết thúc; cần nguồn mới để rà lại.", 409);
    if (p[2] === "tasks" && method === "POST") {
      const assignee =
        users.find(
          (u) =>
            u.id === body.assignee &&
            (c.assigned.includes(u.id) || u.id === "responder"),
        ) ?? fail("Người nhận không thuộc phạm vi demo.");
      const question = required(body.question, "câu hỏi"),
        field = required(body.missing_field, "trường cần xác minh"),
        ids = evidence(c, body.evidence_ids);
      const old = s.tasks.find(
        (t) =>
          t.issue_id === i.id &&
          t.assignee === assignee.id &&
          t.missing_fields.includes(field) &&
          t.status === "open",
      );
      if (old) return old;
      const t = {
        id: uid("TASK"),
        case_id: c.id,
        issue_id: i.id,
        revision: 1,
        assignee: assignee.id,
        question,
        missing_fields: [field],
        evidence_ids: ids,
        status: "open" as const,
      };
      s.tasks.push(t);
      i.work_status = "waiting_response";
      i.revision++;
      touch(c, `${user.name}: tạo yêu cầu xác minh`);
      return t;
    }
    if (p[2] === "confirmations" && method === "POST") {
      const type = body.type as EvidenceStatus;
      if (
        ![
          "confirmed_information_resolved",
          "confirmed_no_difference",
          "confirmed_intentional",
          "confirmed_unintentional",
        ].includes(type)
      )
        fail("Loại xác nhận không hợp lệ.");
      if (
        type === "confirmed_information_resolved" &&
        i.type !== "information_gap"
      )
        fail("Chỉ dùng cho thông tin thiếu.");
      if (["confirmed_intentional", "confirmed_unintentional"].includes(type)) {
        clinician(user);
        if (i.type === "information_gap")
          fail("Xác nhận ý định cần vấn đề khác biệt riêng.");
      }
      const reason = required(body.reason, "lý do"),
        ids = evidence(c, body.evidence_ids);
      i.confirmation = { type, reason, actor: user.id, evidence_ids: ids };
      i.evidence_status = type;
      i.revision++;
      i.work_status = "ready_for_review";
      touch(c, `${user.name}: ${reason}`);
      return i;
    }
    if (p[2] === "close" && method === "POST") {
      const confirmation =
        i.confirmation ?? fail("Cần xác nhận có nguồn trước khi đóng.");
      if (
        ["confirmed_intentional", "confirmed_unintentional"].includes(
          confirmation.type,
        )
      )
        clinician(user);
      i.work_status = "closed";
      i.revision++;
      touch(c, `${user.name}: đóng ${i.id}`);
      return i;
    }
    if (p[2] === "handoffs" && method === "POST") {
      const recipient =
        users.find(
          (u) =>
            u.id === body.recipient &&
            c.assigned.includes(u.id) &&
            u.id !== user.id,
        ) ?? fail("Chọn người nhận khác được phân công ca.");
      const reason = required(body.reason, "lý do bàn giao");
      const old = s.handoffs.find(
        (h) => h.issue_id === i.id && !h.acknowledged,
      );
      if (old) return old;
      const h = {
        id: uid("HANDOFF"),
        case_id: c.id,
        issue_id: i.id,
        revision: 1,
        recipient: recipient.id,
        reason,
        acknowledged: false,
      };
      s.handoffs.push(h);
      i.revision++;
      touch(c, `${user.name}: đề nghị bàn giao, chờ nhận`);
      return h;
    }
  }
  if (p[0] === "handoffs") {
    if (p.length === 1 && method === "GET")
      return s.handoffs.filter((h) =>
        s.cases.some((c) => c.id === h.case_id && c.assigned.includes(user.id)),
      );
    const h =
      s.handoffs.find((h) => h.id === p[1]) ??
      fail("Không tìm thấy bàn giao.", 404);
    const c = getCase(s, h.case_id, user);
    revision(h.revision, body.expected_revision);
    if (p[2] === "ack" && method === "POST") {
      if (h.recipient !== user.id)
        fail("Chỉ người nhận được xác nhận nhận việc.", 403);
      const i = c.issues.find((i) => i.id === h.issue_id)!;
      if (i.work_status === "closed")
        fail("Vấn đề đã được đóng; không nhận bàn giao cũ.", 409);
      h.acknowledged = true;
      h.revision++;
      i.work_status = "handed_off";
      i.evidence_status = "inconclusive";
      i.revision++;
      touch(c, `${user.name}: đã nhận bàn giao — ${h.reason}`);
      return h;
    }
  }
  if (p[0] === "reviews") {
    const r =
      s.reviews.find((r) => r.id === p[1]) ?? fail("Không có phiên bản.", 404);
    const c = getCase(s, r.case_id, user);
    if (method === "GET") return r;
    if (p[2] === "approve" && method === "POST") {
      clinician(user);
      revision(r.revision, body.expected_revision);
      revision(c.revision, body.expected_case_revision);
      revision(c.revision, r.case_revision);
      if (
        r.status !== "draft" ||
        c.extraction_pending ||
        c.issues.some((i) => !["closed", "handed_off"].includes(i.work_status))
      )
        fail("Còn việc mở hoặc dữ kiện chưa được trích xuất/kiểm tra.");
      s.reviews
        .filter((old) => old.case_id === c.id && old.status === "approved")
        .forEach((old) => (old.status = "superseded"));
      r.status = "approved";
      r.revision++;
      r.approved_by = user.name;
      r.approved_at = new Date().toISOString();
      c.lifecycle = "approved";
      c.audit.push(`${user.name}: duyệt ${r.id}`);
      return r;
    }
  }
  if (p[0] === "dashboard" && p[1] === "metrics" && method === "GET") {
    const totalCases = s.cases.length;
    const matchedCount = s.cases.filter((c) => c.scenario === "matched" || c.issues.length === 0).length;
    const gapCount = s.cases.filter((c) => c.issues.some((i) => i.type === "information_gap")).length;
    const diffCount = s.cases.filter((c) => c.issues.some((i) => i.type === "presence_difference" || i.type === "regimen_difference")).length;
    const approvedCount = s.cases.filter((c) => c.lifecycle === "approved").length;
    return {
      total_cases: totalCases,
      matched_count: matchedCount,
      gap_count: gapCount,
      diff_count: diffCount,
      approved_count: approvedCount,
      avg_time_mins: 3.5,
      agent_status: "online",
      agent_model: "Claude Fable 5.1 / MedReview-Agent-v1",
      total_tokens: 14250,
      avg_latency_ms: 640,
      calls_today: 48,
      recent_audits: s.cases.flatMap((c) =>
        c.audit.map((a, idx) => ({
          id: `${c.id}-audit-${idx}`,
          time: c.reconciliation_at,
          actor: a.includes(":") ? a.split(":")[0] : "Hệ thống",
          action: a.includes(":") ? a.split(":")[1].trim() : a,
          case_id: c.id,
        }))
      ).slice(-8).reverse(),
    };
  }
  if (p[0] === "dispatch") {
    if (!s.dispatches) s.dispatches = [];
    if (p[1] === "queue" && method === "GET") {
      s.cases.forEach((c, idx) => {
        if (!s.dispatches!.some((d) => d.case_id === c.id)) {
          s.dispatches!.push({
            id: `DISP-00${idx + 1}`,
            case_id: c.id,
            patient_id: c.patient_id,
            assigned_reviewer: c.assigned[0] ?? "reviewer",
            assigned_clinician: c.assigned[1] ?? "clinician",
            priority: c.scenario === "matched" ? "normal" : c.scenario === "verification" ? "high" : "urgent",
            status: c.lifecycle === "draft" ? "assigned" : "in_progress",
            updated_at: c.reconciliation_at,
          });
        }
      });
      return {
        dispatches: s.dispatches,
        cases: s.cases,
        tasks: s.tasks,
      };
    }
    if (p[1] === "assign" && method === "POST") {
      const caseId = required(body.case_id, "mã ca");
      const reviewerId = body.assigned_reviewer ? String(body.assigned_reviewer) : "reviewer";
      const clinicianId = body.assigned_clinician ? String(body.assigned_clinician) : "clinician";
      const priority = (body.priority as "normal" | "high" | "urgent") || "normal";
      const c = s.cases.find((item) => item.id === caseId);
      if (c) {
        if (!c.assigned.includes(reviewerId)) c.assigned.push(reviewerId);
        if (!c.assigned.includes(clinicianId)) c.assigned.push(clinicianId);
        touch(c, `${user.name}: phân công rà soát cho ${reviewerId}, duyệt bởi ${clinicianId}`);
      }
      let disp = s.dispatches.find((d) => d.case_id === caseId);
      if (!disp) {
        disp = {
          id: uid("DISP"),
          case_id: caseId,
          patient_id: c?.patient_id ?? caseId,
          assigned_reviewer: reviewerId,
          assigned_clinician: clinicianId,
          priority,
          status: "assigned",
          updated_at: new Date().toISOString(),
        };
        s.dispatches.push(disp);
      } else {
        disp.assigned_reviewer = reviewerId;
        disp.assigned_clinician = clinicianId;
        disp.priority = priority;
        disp.status = "assigned";
        disp.updated_at = new Date().toISOString();
      }
      return disp;
    }
  }
  return fail("Endpoint chưa được hỗ trợ.", 404, "NOT_FOUND");
}
