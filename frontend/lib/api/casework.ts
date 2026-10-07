import { DATA_MODE } from "@/lib/api";
import { request } from "@/lib/api/real";
import type {
  CaseworkDataSource,
  CaseworkListResult,
  CaseworkRun,
  EditorDraft,
  IntakeCreateInput,
  ResponseRevision,
  WorkflowAggregate,
  WorkItemSummary,
} from "@/lib/api/casework-types";

const key = () => crypto.randomUUID();
const encoded = (id: string) => encodeURIComponent(id);

export function createCaseworkApiSource(): CaseworkDataSource {
  return {
    listWorkItems: (filters = {}) => {
      const query = new URLSearchParams();
      for (const [name, value] of Object.entries(filters)) if (value) query.set(name, value);
      return request<CaseworkListResult>(`/api/v2/work-items${query.size ? `?${query}` : ""}`);
    },
    createIntake: (input: IntakeCreateInput, idempotencyKey = key()) => request<WorkItemSummary>("/api/v2/work-items/intake", { method: "POST", body: input, headers: { "Idempotency-Key": idempotencyKey } }),
    getWorkflow: (id) => request<WorkflowAggregate>(`/api/v2/work-items/${encoded(id)}/workflow`),
    patchFields: (id, expected_version, operations, idempotencyKey = key()) => request<WorkflowAggregate>(`/api/v2/work-items/${encoded(id)}/fields`, { method: "PATCH", body: { expected_version, operations }, headers: { "Idempotency-Key": idempotencyKey } }),
    answerClarifications: (id, expected_version, answers, idempotencyKey = key()) => request<WorkflowAggregate>(`/api/v2/work-items/${encoded(id)}/clarification-answers`, { method: "POST", body: { expected_version, answers }, headers: { "Idempotency-Key": idempotencyKey } }),
    startRun: (id, expected_version, purpose, idempotencyKey = key()) => request<CaseworkRun>(`/api/v2/work-items/${encoded(id)}/runs`, { method: "POST", body: { expected_version, purpose }, headers: { "Idempotency-Key": idempotencyKey } }),
    createDraft: (id, input, idempotencyKey = key()) => request<ResponseRevision>(`/api/v2/work-items/${encoded(id)}/drafts`, { method: "POST", body: input, headers: { "Idempotency-Key": idempotencyKey } }),
    getEditorDraft: (id) => request<EditorDraft | null>(`/api/v2/work-items/${encoded(id)}/editor-draft`),
    saveEditorDraft: (id, input, idempotencyKey = key()) => request<EditorDraft>(`/api/v2/work-items/${encoded(id)}/editor-draft`, { method: "PATCH", body: input, headers: { "Idempotency-Key": idempotencyKey } }),
    submitReview: (responseId, input, idempotencyKey = key()) => request<void>(`/api/v2/responses/${encoded(responseId)}/submit-review`, { method: "POST", body: input, headers: { "Idempotency-Key": idempotencyKey } }),
    reviewResponse: (responseId, input, idempotencyKey = key()) => request<void>(`/api/v2/responses/${encoded(responseId)}/review`, { method: "POST", body: input, headers: { "Idempotency-Key": idempotencyKey } }),
    patchAdrIntake: (id, input, idempotencyKey = key()) => request<WorkflowAggregate>(`/api/v2/work-items/${encoded(id)}/adr-intake`, { method: "PATCH", body: input, headers: { "Idempotency-Key": idempotencyKey } }),
  };
}

const DEMO_WORK: WorkItemSummary = {
  id: "CW-DEMO-001", kind: "di", raw_text: "Có bằng chứng nào về nguy cơ xuất huyết khi dùng thuốc chống đông?", priority: "routine", version: 1, input_revision: 1,
  work_status: "awaiting_information", run_status: "running", review_status: "not_required", created_at: "2026-10-07T00:00:00Z", next_action: "Xác nhận quần thể hoặc tiếp tục tìm sơ bộ",
};

function demoAggregate(): WorkflowAggregate {
  return { work_item: DEMO_WORK, input_sources: [{ source_id: "raw-1", source_version: 1, kind: "raw_question", text: DEMO_WORK.raw_text, created_at: DEMO_WORK.created_at }], field_assertions: [], clarifications: [], readiness: { can_retrieve_preliminary: true, can_run_scoped_analysis: false, can_draft_limited: true, can_submit_review: false, blockers: ["Chưa xác nhận phạm vi người bệnh."], warnings: ["Kết quả sơ bộ chưa phải phản hồi được duyệt."], policy_version: "v1" }, runs: [{ id: "run-demo", version: 1, purpose: "preliminary", status: "running", source_results: [{ source: "PubMed", outcome: "partial", coverage: "abstract_only" }] }], current_response: null, version_basis: null, allowed_actions: ["retrieve_preliminary", "answer_clarification"] };
}

function mockSource(): CaseworkDataSource {
  const aggregate = demoAggregate();
  return {
    listWorkItems: async () => ({ items: [aggregate.work_item] }),
    createIntake: async (input) => ({ ...DEMO_WORK, id: `CW-${Math.random().toString(36).slice(2, 8).toUpperCase()}`, kind: input.kind, raw_text: input.raw_text, priority: input.priority ?? "routine" }),
    getWorkflow: async () => aggregate,
    patchFields: async () => aggregate,
    answerClarifications: async () => aggregate,
    startRun: async () => aggregate.runs[0],
    createDraft: async () => ({ response_id: "response-demo", version: 1, status: "draft", sections: {}, author_ids: [] }),
    getEditorDraft: async () => null,
    saveEditorDraft: async (_id, input) => ({ draft_id: "draft-demo", entity_type: "response", entity_id: "response-demo", actor_id: "demo", base_versions: input.base_versions, content: input.content, saved_at: new Date().toISOString(), version: 1 }),
    submitReview: async () => undefined,
    reviewResponse: async () => undefined,
    patchAdrIntake: async () => aggregate,
  };
}

let source: CaseworkDataSource | null = null;
export function getCaseworkSource(): CaseworkDataSource {
  if (!source) source = DATA_MODE === "api" ? createCaseworkApiSource() : mockSource();
  return source;
}
