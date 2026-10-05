/** Hợp đồng dữ liệu của giao diện (PHẦN N của brief). */

export type Role = "visitor" | "investigator" | "reviewer" | "admin";

export type RunStatus = "cancelled" | "queued" | "running" | "waiting_for_review" | "completed" | "failed" | "interrupted";

export type AssessmentStatus =
  | "supported_for_scope"
  | "contradicted_for_scope"
  | "insufficient_evidence"
  | "scope_mismatch"
  | "out_of_scope"
  | "requires_human_review";

export type ReviewState = "not_reviewed" | "approved" | "rejected" | "changes_requested" | "needs_rereview";

export type Stance = "supporting" | "contradicting" | "uncertain" | "background";

export type ScopeMatch = "matched" | "partial" | "mismatched";

export type SourceId = "pubmed" | "dailymed" | "faers";

export type CoverageField = "drug" | "adverseEvent" | "population" | "dose" | "route" | "timeWindow";

export type Cov = "verified" | "partial" | "missing" | "not_specified";

export interface Claim {
  drug: string;
  adverseEvent: string;
  population?: string;
  dose?: { op: "=" | ">=" | "<=" | "range"; value: number; value2?: number; unit: string };
  doseText?: string;
  route?: string;
  timeWindow?: string;
  rawText?: string;
}

export interface Budget {
  maxSteps: number;
  maxDocs: number;
  ceilingSteps: number;
  ceilingDocs: number;
}

export interface BudgetUsage {
  steps: number;
  docs: number;
  tokens: number;
  elapsedMs: number;
}

export type Coverage = Record<CoverageField, Cov>;

export interface Investigation {
  id: string;
  claim: Claim;
  sources: SourceId[];
  budget: Budget;
  usage: BudgetUsage;
  runStatus: RunStatus;
  assessment?: { status: AssessmentStatus; rationale: string; coverage: Coverage };
  reviewState: ReviewState;
  /** Checkpoint đang chờ người duyệt; `null` khi đã có quyết định và có thể chạy tiếp. */
  checkpoint?: string | null;
  /** Bước agent sẽ chạy khi được gọi `/continue`. */
  nextStage?: string | null;
  stopReason?: string | null;
  sourceStatus?: Record<string, string>;
  /** Quyết định người duyệt mới nhất ở bất kỳ checkpoint nào; `reviewState` chỉ nói về hồ sơ. */
  lastReview?: { action: string; checkpoint?: string | null; createdAt?: string };
  reviewedBy?: string;
  reviewedAt?: string;
  version: number;
  /** Người tạo; backend chưa trả nên có thể vắng. */
  createdBy?: string;
  createdAt: string;
  invalidatedReason?: string;
  backendId?: string;
  /** List endpoint omits usage/config; open detail before showing those values. */
  summaryOnly?: boolean;
}

export type StepType =
  | "search"
  | "read"
  | "replan"
  | "source_switch"
  | "contradiction_found"
  | "scope_mismatch"
  | "gap_identified"
  | "reviewer_request"
  | "human_review"
  | "assess"
  | "dossier"
  | "conclude"
  | "abstain";

export interface AgentStep {
  index: number;
  type: StepType;
  source?: SourceId;
  query?: string;
  prevQuery?: string;
  rationale: string;
  resultSummary?: string;
  docsFound?: number;
  newDocs?: number;
  tokens: number;
  durationMs: number;
  startedAt: string;
  docIds?: string[];
  status: "running" | "done" | "error";
}

export interface ScopeDiff {
  field: "population" | "dose" | "route" | "timeWindow";
  claim: string;
  evidence: string;
}

export interface EvidenceItem {
  id: string;
  label: string;
  docId: string;
  source: SourceId;
  title: string;
  year?: number;
  externalId: string;
  stance: Stance;
  excluded?: boolean;
  version?: number;
  scopeValues?: { population?: string; dose?: string; route?: string; time_window?: string; study_type?: string };
  coverageNote?: string;
  /** Kết luận so khớp phạm vi; backend chưa trả nên có thể vắng. */
  scope?: ScopeMatch;
  scopeDiffs?: ScopeDiff[];
  studyPopulation?: string;
  dose?: string;
  designNote?: string;
  quotes: { start: number; end: number; text: string }[];
  /** Bước agent tìm ra bằng chứng; backend chưa trả nên có thể vắng. */
  foundAtStep?: number;
  editedByReviewer?: { by: string; at: string; reason: string };
}

export interface DocumentRecord {
  id: string;
  version?: number;
  source: SourceId;
  title: string;
  origin: "auto" | "internal";
  text: string;
  record?: Record<string, string>;
  sha256: string;
  hashStatus: "verified" | "mismatch" | "unchecked";
  retrievedAt: string;
  url?: string;
  meta: Record<string, string>;
}

export interface Contradiction {
  id: string;
  aId: string;
  bId: string;
  diffs: string[];
  agentNote: string;
  resolved?: { by: string; note: string };
}

export interface Gap {
  id: string;
  kind?: string;
  description: string;
  tried: string[];
  relatedField: CoverageField;
}

export interface AuditEntry {
  id: string;
  at: string;
  actor: { name: string; kind: "human" | "ai" | "system" };
  action: string;
  target?: string;
  reason?: string;
  before?: unknown;
  after?: unknown;
}

export interface IngestionJob {
  id: string;
  kind: "file" | "identifier" | "manual" | "csv";
  source?: SourceId;
  total: number;
  ok: number;
  failed: number;
  stage: "uploaded" | "parsing" | "normalizing" | "hashing" | "indexing" | "done";
  status: "queued" | "running" | "completed" | "partial" | "failed";
  createdBy: string;
  createdAt: string;
}

export type ChatMessageKind =
  | "text"
  | "claim_card"
  | "evidence_list"
  | "step_stream"
  | "action_proposal"
  | "refusal"
  | "abstain"
  | "error";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  kind: ChatMessageKind;
  content: string;
  payload?: unknown;
  citations?: string[];
  createdAt: string;
}

export interface EvalRun {
  id: string;
  goldSet: string;
  agentVersion: string;
  baseline: boolean;
  metrics: Record<string, number>;
  confusion: number[][];
  createdAt: string;
}

export interface ReviewAction {
  action: "approve" | "reject" | "edit" | "edit_claim" | "exclude_evidence" | "request_more";
  expectedVersion?: number;
  checkpoint?: "normalization" | "assessment" | "dossier";
  decisionId?: string;
  target?: string;
  reason?: string;
  payload?: Record<string, unknown>;
}

export type AgentEventType =
  | "run.started"
  | "step.started"
  | "step.completed"
  | "replan"
  | "evidence.added"
  | "contradiction.detected"
  | "scope_mismatch.detected"
  | "gap.identified"
  | "budget.update"
  | "run.waiting_for_review"
  | "run.completed"
  | "run.failed"
  | "heartbeat";

export interface AgentEvent {
  id: string;
  type: AgentEventType;
  at: string;
  investigationId: string;
  delayMs?: number;
  step?: AgentStep;
  evidence?: EvidenceItem;
  contradiction?: Contradiction;
  gap?: Gap;
  usage?: BudgetUsage;
  message?: string;
}
