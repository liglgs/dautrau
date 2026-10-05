import type {
  AgentEvent,
  AuditEntry,
  DocumentRecord,
  EvidenceItem,
  Gap,
  Investigation,
  ReviewAction,
} from "@/lib/types";

export interface CreateInvestigationInput {
  claimText: string;
  drug: string;
  adverseEvent: string;
  population?: string;
  dose?: string;
  route?: string;
  timeWindow?: string;
  sources: ("pubmed" | "dailymed" | "faers")[];
  maxSteps: number;
  maxDocs: number;
}

export interface InvestigationListResult {
  items: Investigation[];
  source: "mock" | "api";
  warning?: string;
}

export interface DossierPayload {
  markdown: string;
  approved: boolean;
  /** `content_hash` do backend tính cho phiên bản hồ sơ; rỗng khi backend không trả. */
  contentHash?: string;
  validation?: { ok: boolean; errors: string[]; warnings: string[] } | null;
}

export interface TimelinePayload {
  steps: import("@/lib/types").AgentStep[];
  events: AgentEvent[];
}

export interface DataSource {
  listInvestigations(): Promise<InvestigationListResult>;
  getInvestigation(id: string): Promise<Investigation>;
  createInvestigation(input: CreateInvestigationInput, idempotencyKey?: string): Promise<{ id: string; started: boolean }>;
  getTimeline(id: string): Promise<TimelinePayload>;
  getEvidence(id: string): Promise<EvidenceItem[]>;
  getDocument(id: string, docId: string): Promise<DocumentRecord | null>;
  getDossier(id: string): Promise<DossierPayload | null>;
  submitReview(id: string, action: ReviewAction): Promise<{ ok: boolean; message: string; code?: string }>;
  cancelRun(id: string): Promise<{ ok: boolean; message: string; code?: string }>;
  continueRun(id: string, expectedVersion?: number): Promise<{ ok: boolean; message: string; code?: string }>;
  getAudit(id: string): Promise<AuditEntry[]>;
  getGaps(id: string): Promise<Gap[]>;
  exportDossier(id: string): Promise<{ ok: boolean; markdown?: string; code?: string; message?: string }>;
}
