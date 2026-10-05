import {
  DEMO_AUDIT,
  DEMO_DOCUMENTS,
  DEMO_DOSSIER_MD,
  DEMO_EVIDENCE,
  DEMO_GAPS,
  DEMO_INVESTIGATIONS,
  DEMO_TIMELINE,
} from "@/lib/mock/seed";
import { assertNoCausalClaim } from "@/lib/guardrails";
import { validateClaim } from "@/lib/claim-form";
import type { AgentEvent, AgentStep, AuditEntry, EvidenceItem, Gap, Investigation } from "@/lib/types";
import type {
  CreateInvestigationInput,
  DataSource,
  DossierPayload,
  InvestigationListResult,
  TimelinePayload,
} from "@/lib/api/types";

/** Hash minh hoạ cho hồ sơ ở chế độ dữ liệu mẫu. */
const DEMO_DOSSIER_HASH = "9f2c1a7d4b8e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcd";

/** Độ trễ giả lập 200–600ms để UI trông như đang gọi mạng. */
const delay = (min = 200, max = 600) =>
  new Promise<void>((resolve) => setTimeout(resolve, min + Math.random() * (max - min)));

const investigations = new Map<string, Investigation>(DEMO_INVESTIGATIONS.map((item) => [item.id, structuredClone(item)]));
const evidence = new Map<string, EvidenceItem[]>(
  Object.entries(DEMO_EVIDENCE).map(([key, value]) => [key, structuredClone(value)]),
);
const gaps = new Map<string, Gap[]>(Object.entries(DEMO_GAPS).map(([key, value]) => [key, structuredClone(value)]));
const audit = new Map<string, AuditEntry[]>(Object.entries(DEMO_AUDIT).map(([key, value]) => [key, structuredClone(value)]));
const timelines = new Map<string, AgentStep[]>(
  Object.entries(DEMO_TIMELINE).map(([key, value]) => [key, structuredClone(value)]),
);

let counter = DEMO_INVESTIGATIONS.length;
const creations = new Map<string, { fingerprint: string; id: string }>();
const decisions = new Map<string, string>();
const STORAGE_KEY = "vigilens-fixture-workspace-v1";
// This is fixture persistence, never a session or authorization store.
try {
  if (typeof localStorage !== "undefined") {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
    if (saved) {
      for (const [map, entries] of [[investigations, saved.investigations], [evidence, saved.evidence], [gaps, saved.gaps], [audit, saved.audit], [timelines, saved.timelines], [creations, saved.creations], [decisions, saved.decisions]] as const) {
        for (const [key, value] of entries ?? []) (map as Map<string, unknown>).set(key, value);
      }
      counter = saved.counter ?? counter;
    }
  }
} catch { /* A corrupt fixture cache must not prevent loading the sample workspace. */ }
function persistFixture() {
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(STORAGE_KEY, JSON.stringify({ counter,
      investigations: [...investigations], evidence: [...evidence], gaps: [...gaps], audit: [...audit],
      timelines: [...timelines], creations: [...creations], decisions: [...decisions] }));
  } catch { /* Quota errors do not change a successful in-memory operation. */ }
}

function nextId() {
  counter += 1;
  return `INV-${String(counter).padStart(4, "0")}`;
}

function toEvents(id: string, steps: AgentStep[]): AgentEvent[] {
  return steps.map((step, index) => ({
    id: `${id}-EV-${index + 1}`,
    type: step.status === "running" ? "step.started" : "step.completed",
    at: step.startedAt,
    investigationId: id,
    step,
  }));
}

export function createMockSource(): DataSource {
  return {
    async listInvestigations(): Promise<InvestigationListResult> {
      await delay();
      return { items: [...investigations.values()].sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1)), source: "mock" };
    },

    async getInvestigation(id: string) {
      await delay(120, 320);
      const found = investigations.get(id);
      if (!found) throw new Error(`Không tìm thấy cuộc điều tra ${id}`);
      return structuredClone(found);
    },

    async createInvestigation(input: CreateInvestigationInput, key?: string) {
      await delay();
      const invalid = validateClaim(input);
      if (invalid) throw new Error(invalid);
      const fingerprint = JSON.stringify(input);
      const previous = key ? creations.get(key) : undefined;
      if (previous) {
        if (previous.fingerprint !== fingerprint) throw new Error("Idempotency key đã dùng cho nội dung khác.");
        return { id: previous.id, started: true };
      }
      const id = nextId();
      const record: Investigation = {
        id,
        claim: {
          drug: input.drug,
          adverseEvent: input.adverseEvent,
          population: input.population || undefined,
          doseText: input.dose || undefined,
          route: input.route || undefined,
          timeWindow: input.timeWindow || undefined,
          rawText: input.claimText,
        },
        sources: input.sources,
        budget: { maxSteps: input.maxSteps, maxDocs: input.maxDocs, ceilingSteps: 20, ceilingDocs: 100 },
        usage: { steps: 1, docs: 0, tokens: 1_200, elapsedMs: 4_000 },
        runStatus: "running",
        reviewState: "not_reviewed",
        version: 1,
        createdBy: "investigator@demo",
        createdAt: new Date().toISOString(),
      };
      investigations.set(id, record);
      if (key) creations.set(key, { fingerprint, id });
      timelines.set(id, [
        {
          index: 1,
          type: "search",
          source: input.sources[0] ?? "pubmed",
          query: `${input.drug} ${input.adverseEvent}`,
          rationale: "Truy vấn đầu tiên theo hoạt chất và biến cố trong nhận định.",
          resultSummary: "Đang tìm…",
          docsFound: 0,
          newDocs: 0,
          tokens: 1200,
          durationMs: 4000,
          startedAt: new Date().toISOString(),
          status: "running",
        },
      ]);
      audit.set(id, [
        { id: `${id}-AUD-1`, at: new Date().toISOString(), actor: { name: "investigator@demo", kind: "human" }, action: "Tạo cuộc điều tra", target: id },
      ]);
      persistFixture();
      return { id, started: true };
    },

    async getTimeline(id: string): Promise<TimelinePayload> {
      await delay(120, 320);
      const steps = timelines.get(id) ?? [];
      return { steps: structuredClone(steps), events: toEvents(id, steps) };
    },

    async getEvidence(id: string) {
      await delay(120, 320);
      return structuredClone(evidence.get(id) ?? []);
    },

    async getDocument(_id: string, docId: string) {
      await delay(120, 320);
      const found = DEMO_DOCUMENTS.find((doc) => doc.id === docId);
      return found ? structuredClone(found) : null;
    },

    async getDossier(id: string): Promise<DossierPayload | null> {
      await delay();
      const record = investigations.get(id);
      if (!record?.assessment) return null;
      const markdown = DEMO_DOSSIER_MD.replaceAll("INV-0001", id);
      assertNoCausalClaim(markdown);
      const approved = record.reviewState === "approved";
      return {
        markdown,
        approved,
        contentHash: DEMO_DOSSIER_HASH,
        validation: {
          ok: true,
          errors: [],
          warnings: record.reviewState === "needs_rereview" ? ["Bằng chứng đã bị chỉnh sửa sau lần duyệt trước."] : [],
        },
      };
    },

    async submitReview(id: string, action) {
      await delay();
      const record = investigations.get(id);
      if (!record) return { ok: false, message: `Không tìm thấy ${id}`, code: "not_found" };
      const fingerprint = JSON.stringify({ id, action });
      if (action.decisionId && decisions.has(action.decisionId)) {
        return decisions.get(action.decisionId) === fingerprint
          ? { ok: true, message: "Quyết định này đã được ghi nhận." }
          : { ok: false, code: "idempotency_conflict", message: "Decision ID đã dùng cho nội dung khác." };
      }
      if (action.expectedVersion !== record.version) return { ok: false, code: "version_conflict", message: "Phiên bản đã thay đổi. Tải lại nội dung trước khi duyệt." };
      if (action.action !== "approve" && action.action !== "reject" && (action.reason ?? "").trim().length < 15) {
        return { ok: false, message: "Lý do phải có ít nhất 15 ký tự.", code: "invalid_request" };
      }
      if (action.action === "edit" || action.action === "exclude_evidence") {
        const item = evidence.get(id)?.find((row) => row.id === action.target);
        if (!item) return { ok: false, code: "invalid_request", message: "Không tìm thấy bằng chứng cần sửa." };
        if (action.action === "exclude_evidence") item.excluded = true;
        else {
          const newQuote = String(action.payload?.quote ?? "");
          const doc = DEMO_DOCUMENTS.find((row) => row.id === item.docId);
          const offset = doc?.text.indexOf(newQuote) ?? -1;
          if (!newQuote || offset < 0) return { ok: false, code: "invalid_request", message: "Đoạn trích không có trong tài liệu gốc." };
          const start = [...doc!.text.slice(0, offset)].length;
          item.quotes = [{ start, end: start + [...newQuote].length, text: newQuote }];
          item.stance = action.payload?.stance === "supports" ? "supporting" : action.payload?.stance === "contradicts" ? "contradicting" : "uncertain";
          item.scopeValues = action.payload?.scope as EvidenceItem["scopeValues"];
        }
        item.editedByReviewer = { by: "Reviewer minh họa", at: new Date().toISOString(), reason: action.reason ?? "" };
      }
      if (action.action === "edit_claim") record.claim = { ...record.claim, drug: String(action.payload?.drug ?? record.claim.drug), adverseEvent: String(action.payload?.event ?? record.claim.adverseEvent) };
      if (action.action === "approve") {
        if (action.checkpoint === "dossier") {
          record.reviewState = "approved";
          record.reviewedBy = "DS. Trần Minh";
          record.reviewedAt = new Date().toISOString();
          record.runStatus = "completed";
        } else {
          record.runStatus = "waiting_for_review";
          record.nextStage = action.checkpoint === "normalization" ? "checklist" : "build_dossier";
        }
      } else if (action.action === "reject") {
        record.reviewState = "rejected";
        record.reviewedBy = "DS. Trần Minh";
        record.reviewedAt = new Date().toISOString();
      } else {
        record.reviewState = "needs_rereview";
        record.invalidatedReason = action.reason ?? "Reviewer đã chỉnh sửa nội dung.";
        record.runStatus = "waiting_for_review";
      }
      record.version += 1;
      record.checkpoint = null;
      const log = audit.get(id) ?? [];
      log.push({
        id: `${id}-AUD-${log.length + 1}`,
        at: new Date().toISOString(),
        actor: { name: "DS. Trần Minh", kind: "human" },
        action:
          action.action === "approve" ? "Duyệt" : action.action === "reject" ? "Từ chối" : action.action === "edit" ? "Sửa" : "Yêu cầu tìm thêm",
        reason: action.reason,
        target: action.target,
      });
      audit.set(id, log);
      investigations.set(id, record);
      if (action.decisionId) decisions.set(action.decisionId, fingerprint);
      persistFixture();
      return { ok: true, message: "Đã ghi nhận quyết định của reviewer." };
    },

    async cancelRun(id: string) {
      const record = investigations.get(id);
      if (!record) return { ok: false, code: "not_found", message: `Không tìm thấy ${id}` };
      if (["completed", "failed", "cancelled"].includes(record.runStatus)) return { ok: false, code: "invalid_state", message: "Cuộc điều tra đã kết thúc." };
      record.runStatus = "cancelled";
      record.version += 1;
      record.reviewState = "needs_rereview";
      record.checkpoint = null;
      persistFixture();
      return { ok: true, message: "Đã hủy cuộc điều tra minh họa." };
    },

    async continueRun(id: string, expectedVersion?: number) {
      await delay();
      const record = investigations.get(id);
      if (!record) return { ok: false, message: `Không tìm thấy ${id}`, code: "not_found" };
      if (expectedVersion !== record.version) return { ok: false, code: "version_conflict", message: "Tải phiên bản mới trước khi chạy tiếp." };
      if (record.runStatus === "completed") {
        return { ok: false, message: "Cuộc điều tra đã hoàn tất; không chạy tiếp.", code: "invalid_state" };
      }
      record.runStatus = "running";
      record.version += 1;
      investigations.set(id, record);
      persistFixture();
      return { ok: true, message: "Đã yêu cầu chạy tiếp." };
    },

    async getAudit(id: string) {
      await delay(120, 320);
      return structuredClone(audit.get(id) ?? []);
    },

    async getGaps(id: string) {
      await delay(120, 320);
      return structuredClone(gaps.get(id) ?? []);
    },

    async exportDossier(id: string) {
      await delay();
      const record = investigations.get(id);
      if (!record) return { ok: false, code: "not_found", message: `Không tìm thấy ${id}` };
      if (record.reviewState !== "approved") {
        return {
          ok: false,
          code: "dossier_not_approved",
          message: "Hồ sơ chưa được reviewer duyệt nên không thể export.",
        };
      }
      return { ok: true, markdown: DEMO_DOSSIER_MD.replaceAll("INV-0001", id) };
    },
  };
}

