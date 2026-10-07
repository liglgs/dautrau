/** Additive `/api/v2` workflow contract. Kept separate from legacy Investigation types. */

export type WorkKind = "di" | "adr";
export type WorkStatus = "draft" | "accepted" | "in_progress" | "awaiting_information" | "awaiting_review" | "completed" | "cancelled";
export type RunStatus = "not_started" | "queued" | "running" | "waiting_for_review" | "completed" | "failed" | "interrupted" | "cancelled";
export type ReviewStatus = "not_required" | "pending" | "approved" | "rejected" | "changes_requested";
export type FieldStatus = "proposed" | "confirmed" | "unknown";
export type ClarificationClassification = "required_for_next_step" | "useful_for_completeness";
export type ClarificationStatus = "open" | "answered" | "unknown" | "superseded";

export interface WorkItemSummary {
  id: string;
  kind: WorkKind;
  raw_text: string;
  priority: string;
  version: number;
  input_revision: number;
  work_status: WorkStatus;
  run_status: RunStatus;
  review_status: ReviewStatus;
  created_at: string;
  updated_at?: string;
  next_action?: string | null;
}

export interface FollowUp {
  follow_up_id: string;
  version?: number;
  kind: string;
  status: "open" | "in_progress" | "done" | "cancelled" | string;
  note: string;
  resolution?: string | null;
}

export interface SourceSpan {
  source_id: string;
  source_version: number;
  start: number;
  end: number;
  quote: string;
}

export interface FieldAssertion {
  assertion_id: string;
  version: number;
  field_key: string;
  value: string | null;
  status: FieldStatus;
  source_spans: SourceSpan[];
  proposed_by?: string | null;
  extractor_version?: string | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  unknown_reason?: string | null;
  supersedes?: string | null;
}

export interface Clarification {
  id: string;
  version: number;
  field_keys: string[];
  question: string;
  classification: ClarificationClassification;
  blocked_step?: string | null;
  reason?: string | null;
  status: ClarificationStatus;
  based_on_input_revision: number;
  dedupe_key?: string | null;
  answer_source_id?: string | null;
  answered_by?: string | null;
  answered_at?: string | null;
  reopened_from?: string | null;
}

export interface Readiness {
  can_retrieve_preliminary: boolean;
  can_run_scoped_analysis: boolean;
  can_draft_limited: boolean;
  can_submit_review: boolean;
  blockers: string[];
  warnings: string[];
  policy_version?: string | null;
}

export interface CaseworkRun {
  id: string;
  version: number;
  purpose: "preliminary" | "scoped_analysis" | "recheck" | string;
  status: RunStatus;
  created_at?: string;
  updated_at?: string;
  source_results?: SourceResult[];
}

export interface SourceResult {
  source: string;
  outcome: "ok" | "empty" | "partial" | "timeout" | "rate_limited" | "http_error" | "unavailable" | "parse_error" | "budget_exhausted" | "invalid_query" | "skipped" | string;
  coverage?: "complete" | "partial" | "abstract_only" | "empty" | "unavailable" | "not_requested" | string;
  detail?: string | null;
  retryable?: boolean;
}

export interface ResponseRevision {
  response_id: string;
  version: number;
  status: "receipt" | "preliminary" | "draft" | "pending_review" | "approved" | "stale" | string;
  sections: Record<string, string>;
  content_hash?: string | null;
  author_ids: string[];
  basis_hash?: string | null;
  updated_at?: string;
}

export interface AdrMinimumGroup {
  status: "present" | "missing" | "unknown";
  assertion_refs?: string[];
  confirmed_by?: { id: string; role?: string } | null;
}

export interface AdrIntake {
  groups: Record<string, AdrMinimumGroup>;
  validity: "complete" | "incomplete" | "undetermined";
  reportability: {
    status: "not_assessed" | "needs_information" | "reportable" | "not_reportable";
    basis_input_revision?: number;
    assessor?: { id: string; role?: string } | null;
    reason?: string | null;
    policy_reference?: string | null;
  };
}

export interface VersionBasis {
  basis_hash: string;
  input_revision?: number;
  response_id?: string;
  response_version?: number;
  bundle_id?: string;
  stale_reason?: string | null;
}

export interface WorkflowAggregate {
  work_item: WorkItemSummary;
  input_sources: { source_id: string; source_version: number; kind: string; text: string; created_at: string }[];
  field_assertions: FieldAssertion[];
  clarifications: Clarification[];
  readiness: Readiness;
  runs: CaseworkRun[];
  current_response?: ResponseRevision | null;
  version_basis?: VersionBasis | null;
  adr_intake?: AdrIntake | null;
  allowed_actions: string[];
  follow_ups?: FollowUp[];
  stale_approval_reason?: string | null;
  aggregate_etag?: string;
}

export interface EditorDraft {
  draft_id: string;
  entity_type: string;
  entity_id: string;
  actor_id: string;
  base_versions: Record<string, number>;
  content: Record<string, string>;
  saved_at: string;
  version: number;
}

export interface IntakeCreateInput {
  kind: WorkKind;
  raw_text: string;
  language?: string;
  priority?: string;
}

export interface CaseworkListResult { items: WorkItemSummary[]; next_cursor?: string | null; }

export interface CaseworkDataSource {
  listWorkItems(filters?: Partial<Pick<WorkItemSummary, "kind" | "work_status" | "run_status" | "review_status">>): Promise<CaseworkListResult>;
  createIntake(input: IntakeCreateInput, idempotencyKey: string): Promise<WorkItemSummary>;
  getWorkflow(id: string): Promise<WorkflowAggregate>;
  patchFields(id: string, expectedVersion: number, operations: { assertion_id: string; expected_assertion_version: number; action: "confirm" | "correct" | "mark_unknown"; value?: string; reason?: string }[], idempotencyKey: string): Promise<WorkflowAggregate>;
  answerClarifications(id: string, expectedVersion: number, answers: { clarification_id: string; expected_clarification_version: number; text?: string; answer_state: "answered" | "unknown" }[], idempotencyKey: string): Promise<WorkflowAggregate>;
  startRun(id: string, expectedVersion: number, purpose: CaseworkRun["purpose"], idempotencyKey: string): Promise<CaseworkRun>;
  createDraft(id: string, input: { expected_version: number; expected_input_revision: number; bundle_id?: string; previous_response_id?: string; sections?: Record<string, string> }, idempotencyKey: string): Promise<ResponseRevision>;
  getEditorDraft(id: string): Promise<EditorDraft | null>;
  saveEditorDraft(id: string, input: Pick<EditorDraft, "base_versions" | "content"> & { version?: number }, idempotencyKey: string): Promise<EditorDraft>;
  submitReview(responseId: string, input: { expected_version: number; expected_work_version: number; basis_hash: string }, idempotencyKey: string): Promise<void>;
  reviewResponse(responseId: string, input: { expected_version: number; expected_work_version: number; basis_hash: string; action: "approve" | "reject" | "changes_requested"; reason: string }, idempotencyKey: string): Promise<void>;
  patchAdrIntake(id: string, input: { expected_version: number; patch: Record<string, unknown>; reason?: string }, idempotencyKey: string): Promise<WorkflowAggregate>;
  setAdrReportability(id: string, input: { expected_version: number; status: "not_assessed" | "needs_information" | "reportable" | "not_reportable"; reason?: string; policy_reference?: string }, idempotencyKey: string): Promise<WorkflowAggregate>;
  closeFollowUp(id: string, followUpId: string, input: { expected_version: number; status: "done" | "cancelled"; resolution: string }, idempotencyKey: string): Promise<FollowUp>;
  exportApprovedResponse(id: string): Promise<{ response_id: string; version: number; sections: { key?: string; title?: string; text?: string }[]; basis_hash: string; approved_at?: string }>;
  getEvents(id: string): Promise<{ events: { id: number; kind: string; operation_id?: string; state?: string; created_at?: string }[] }>;
}
