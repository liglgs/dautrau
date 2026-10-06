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

// ---------------------------------------------------------------------------------------
// Kho bằng chứng (ELT + Postgres + ChromaDB) — hợp đồng của bảy endpoint mới.
// ---------------------------------------------------------------------------------------

/** Nguồn tài liệu trong kho; `reference` là tài liệu tham chiếu nội bộ, `manual` là tài liệu nạp tay. */
export type WarehouseSourceId = "pubmed" | "dailymed" | "faers" | "reference" | "manual";

export interface DrugLookupDrug {
  drug_id: string;
  name: string;
  ingredient: string;
  verified: boolean;
  aliases: string[];
}

export interface DrugLookupPair {
  pair_id: string;
  drug_name: string;
  event_term: string;
  /** Trạng thái cặp thuốc–biến cố; `candidate_not_gold` nghĩa là ứng viên, chưa phải gold chuẩn. */
  status: string;
  source: string;
}

export interface DrugLookupResult {
  query: string;
  matched: boolean;
  origin: "warehouse" | "dictionary";
  drugs: DrugLookupDrug[];
  pairs: DrugLookupPair[];
  /** Số tài liệu theo nguồn, ví dụ `{ pubmed: 5 }`; có thể rỗng. */
  documents: Record<string, number>;
}

export interface WarehouseSourceSummary {
  source: string;
  documents: number;
  latest_retrieved_at: string | null;
  by_content_level: Record<string, number>;
}

export interface QualityFinding {
  check_name: string;
  severity: string;
  count: number;
}

export interface RagIndexStatus {
  collection: string;
  chroma_chunks: number;
  postgres_chunks: number;
  embedding_provider: string;
  embedding_model: string;
  persist_dir: string;
}

export interface WarehouseOverview {
  documents_by_source: WarehouseSourceSummary[];
  documents_by_quality_status: Record<string, number>;
  quality_findings: QualityFinding[];
  table_counts: Record<string, number>;
  rag: RagIndexStatus;
}

export interface WarehouseDocumentSummary {
  doc_id: string;
  source: string;
  source_id: string;
  version: number;
  title: string;
  source_url: string;
  quality_status: string;
  quality_flags: string[];
  pair_id: string | null;
  retrieved_at: string;
}

export interface WarehouseSection {
  title: string;
  start: number;
  end: number;
}

export interface WarehouseDocumentDetail extends WarehouseDocumentSummary {
  text_sha256: string;
  sections: WarehouseSection[];
  text_preview: string;
  /** Khối đặc thù theo nguồn; backend chỉ trả khối tương ứng. */
  pubmed?: {
    pmid: string;
    journal: string;
    publication_date: string;
    publication_types: string[];
    doi: string[];
    authors: string[];
    has_abstract: boolean;
  };
  dailymed?: Record<string, unknown>;
  faers?: Record<string, unknown>;
}

export interface WarehouseDocumentsParams {
  source?: string;
  pairId?: string;
  qualityStatus?: string;
  limit?: number;
}

export interface WarehouseDocumentsResult {
  documents: WarehouseDocumentSummary[];
  count: number;
}

export interface RagHit {
  chunk_id: string;
  /** Điểm tương đồng 0..1, càng cao càng gần truy vấn. */
  score: number;
  text: string;
  ordinal: number;
  char_start: number;
  char_end: number;
  in_postgres: boolean;
  /** Khối tài liệu rút gọn: backend RAG không kèm `retrieved_at`, nên trường này là tùy chọn. */
  document: Omit<WarehouseDocumentSummary, "retrieved_at"> & { retrieved_at?: string; content_level?: string };
}

export interface RagSearchInput {
  query: string;
  k?: number;
  source?: string;
  pairId?: string;
}

export interface RagSearchResult {
  query: string;
  k: number;
  embedding_model: string;
  hits: RagHit[];
}

export interface IngestionEventRecord {
  event_id: string;
  kind: string;
  status: string;
  title: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface IngestionEventsResult {
  events: IngestionEventRecord[];
  count: number;
}

export interface IngestDocumentInput {
  source: WarehouseSourceId;
  source_id: string;
  version: number;
  title: string;
  /** Văn bản đầy đủ, backend yêu cầu 40..200.000 ký tự. */
  text: string;
  source_url?: string;
  metadata?: Record<string, unknown>;
}

export interface IngestDocumentResult {
  doc_id: string;
  created: boolean;
  sha256: string;
  text_chars: number;
  quality_status: string;
  quality_flags: string[];
  rag: {
    indexed: boolean;
    chunks_written: number;
    documents_indexed: number;
    collection: string;
    embedding_model: string;
  };
  event_id: string;
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
  /** Tra thuốc theo tên trong kho bằng chứng (từ điển + kho đã nạp). */
  lookupDrug(name: string): Promise<DrugLookupResult>;
  /** Tổng quan kho: tài liệu theo nguồn, chất lượng, chỉ mục RAG và số dòng bảng. */
  warehouseOverview(): Promise<WarehouseOverview>;
  /** Danh sách tài liệu trong kho, có bộ lọc. */
  warehouseDocuments(params?: WarehouseDocumentsParams): Promise<WarehouseDocumentsResult>;
  /** Chi tiết một tài liệu; `docId` chứa dấu hai chấm nên phải được mã hoá URL. */
  warehouseDocument(docId: string, previewChars?: number): Promise<WarehouseDocumentDetail>;
  /** Tìm ngữ nghĩa (RAG) trên kho bằng chứng. */
  ragSearch(input: RagSearchInput): Promise<RagSearchResult>;
  /** Dòng sự kiện nạp tài liệu (chỉ vai trò reviewer/admin). */
  ingestionEvents(limit?: number): Promise<IngestionEventsResult>;
  /** Nạp một tài liệu mới (chỉ vai trò reviewer/admin). */
  ingestDocument(input: IngestDocumentInput): Promise<IngestDocumentResult>;
}
