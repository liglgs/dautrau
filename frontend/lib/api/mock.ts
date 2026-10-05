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
import { BackendError } from "@/lib/api/errors";
import { useAppStore } from "@/lib/store/app-store";
import type { AgentEvent, AgentStep, AuditEntry, EvidenceItem, Gap, Investigation } from "@/lib/types";
import type {
  CreateInvestigationInput,
  DataSource,
  DossierPayload,
  DrugLookupDrug,
  DrugLookupPair,
  DrugLookupResult,
  IngestDocumentInput,
  IngestDocumentResult,
  IngestionEventRecord,
  InvestigationListResult,
  RagHit,
  RagSearchInput,
  RagSearchResult,
  TimelinePayload,
  WarehouseDocumentDetail,
  WarehouseDocumentSummary,
  WarehouseDocumentsParams,
  WarehouseDocumentsResult,
  WarehouseOverview,
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

// ---------------------------------------------------------------------------------------
// Kho bằng chứng (demo) — dữ liệu nhỏ, dán nhãn rõ là minh hoạ, cùng hình dạng với backend thật.
// ---------------------------------------------------------------------------------------

const DEMO_WAREHOUSE_TIME = "2026-10-05T09:00:00+00:00";
const DEMO_WAREHOUSE_SHA = "9f2c1a7d4b8e5f60718293a4b5c6d7e8f9012345678abcdef0123456789abcd";

const DEMO_WAREHOUSE_DRUGS: DrugLookupDrug[] = [
  { drug_id: "drug:ibuprofen", name: "ibuprofen", ingredient: "ibuprofen", verified: true, aliases: ["brufen", "advil"] },
  { drug_id: "drug:metformin", name: "metformin", ingredient: "metformin", verified: true, aliases: ["glucophage"] },
  { drug_id: "drug:lisinopril", name: "lisinopril", ingredient: "lisinopril", verified: true, aliases: [] },
  { drug_id: "drug:atorvastatin", name: "atorvastatin", ingredient: "atorvastatin", verified: true, aliases: ["lipitor"] },
  { drug_id: "drug:amoxicillin", name: "amoxicillin", ingredient: "amoxicillin", verified: true, aliases: ["amoxil"] },
];

const DEMO_WAREHOUSE_PAIRS: DrugLookupPair[] = [
  { pair_id: "ibuprofen__gastrointestinal-haemorrhage", drug_name: "ibuprofen", event_term: "Gastrointestinal haemorrhage", status: "candidate_not_gold", source: "bundle" },
  { pair_id: "metformin__diarrhoea", drug_name: "metformin", event_term: "Diarrhoea", status: "candidate_not_gold", source: "bundle" },
  { pair_id: "lisinopril__cough", drug_name: "lisinopril", event_term: "Cough", status: "candidate_not_gold", source: "bundle" },
  { pair_id: "atorvastatin__myalgia", drug_name: "atorvastatin", event_term: "Myalgia", status: "candidate_not_gold", source: "bundle" },
  { pair_id: "amoxicillin__rash", drug_name: "amoxicillin", event_term: "Rash", status: "candidate_not_gold", source: "bundle" },
];

const DEMO_WAREHOUSE_DOCUMENTS: WarehouseDocumentSummary[] = [
  { doc_id: "pubmed:39466269:1", source: "pubmed", source_id: "39466269", version: 1, title: "Peptic Ulcer Disease: A Review.", source_url: "https://pubmed.ncbi.nlm.nih.gov/39466269/", quality_status: "keep", quality_flags: ["has_abstract", "has_journal"], pair_id: "ibuprofen__gastrointestinal-haemorrhage", retrieved_at: DEMO_WAREHOUSE_TIME },
  { doc_id: "pubmed:40915652:1", source: "pubmed", source_id: "40915652", version: 1, title: "Nonsteroidal Anti-Inflammatory Drugs and Risk of Gastrointestinal Bleeding.", source_url: "https://pubmed.ncbi.nlm.nih.gov/40915652/", quality_status: "keep", quality_flags: ["has_abstract"], pair_id: "ibuprofen__gastrointestinal-haemorrhage", retrieved_at: DEMO_WAREHOUSE_TIME },
  { doc_id: "dailymed:ibuprofen-label:2", source: "dailymed", source_id: "ibuprofen-label", version: 2, title: "IBUPROFEN tablet, film coated", source_url: "https://dailymed.nlm.nih.gov/dailymed/", quality_status: "keep", quality_flags: [], pair_id: "ibuprofen__gastrointestinal-haemorrhage", retrieved_at: DEMO_WAREHOUSE_TIME },
  { doc_id: "faers:10001234:1", source: "faers", source_id: "10001234", version: 1, title: "FAERS report 10001234 (minh hoạ)", source_url: "", quality_status: "quarantine", quality_flags: ["missing_age"], pair_id: "ibuprofen__gastrointestinal-haemorrhage", retrieved_at: DEMO_WAREHOUSE_TIME },
  { doc_id: "reference:who-umc-causality:1", source: "reference", source_id: "who-umc-causality", version: 1, title: "WHO-UMC causality assessment", source_url: "", quality_status: "keep", quality_flags: [], pair_id: null, retrieved_at: DEMO_WAREHOUSE_TIME },
  { doc_id: "pubmed:30000001:1", source: "pubmed", source_id: "30000001", version: 1, title: "Metformin and gastrointestinal intolerance (minh hoạ)", source_url: "https://pubmed.ncbi.nlm.nih.gov/30000001/", quality_status: "keep", quality_flags: ["has_abstract"], pair_id: "metformin__diarrhoea", retrieved_at: DEMO_WAREHOUSE_TIME },
];

const DEMO_WAREHOUSE_DOCUMENT_TEXTS: Record<string, string> = {
  "pubmed:39466269:1":
    "Peptic Ulcer Disease: A Review.\n\nAbstract\nIMPORTANCE: In the US, peptic ulcer disease affects 1% of the population...\n\n(Dữ liệu minh hoạ ở chế độ mock; nội dung thật nằm trong kho Postgres.)",
  "pubmed:40915652:1":
    "Nonsteroidal Anti-Inflammatory Drugs and Risk of Gastrointestinal Bleeding: A Systematic Review and Meta-Analysis.\n\nAbstract\nNSAIDs are associated with gastrointestinal bleeding...\n\n(Dữ liệu minh hoạ ở chế độ mock.)",
  "dailymed:ibuprofen-label:2":
    "IBUPROFEN tablet, film coated\n\nWARNING: CARDIOVASCULAR AND GASTROINTESTINAL RISK\nGastrointestinal bleeding, ulceration and perforation can occur...\n\n(Dữ liệu minh hoạ ở chế độ mock.)",
  "faers:10001234:1":
    "FAERS report 10001234 (minh hoạ)\nReaction: Gastrointestinal haemorrhage\nSuspect drug: ibuprofen\n\nBáo cáo tự nguyện, không có mẫu số.\n\n(Dữ liệu minh hoạ ở chế độ mock.)",
  "reference:who-umc-causality:1":
    "WHO-UMC causality assessment\nCertain / Probable / Possible / Unlikely...\n\n(Dữ liệu minh hoạ ở chế độ mock.)",
  "pubmed:30000001:1":
    "Metformin and gastrointestinal intolerance (minh hoạ)\n\nAbstract\nDiarrhoea is a common adverse effect of metformin...\n\n(Dữ liệu minh hoạ ở chế độ mock.)",
};

const DEMO_INGESTION_EVENTS: IngestionEventRecord[] = [
  {
    event_id: "elt-demo-all",
    kind: "elt_run",
    status: "completed",
    title: "ELT demo: 5 tài liệu đạt, 1 cách ly (dữ liệu minh hoạ)",
    detail: { demo: true, by_source: { pubmed: 3, dailymed: 1, faers: 1, reference: 1 } },
    created_at: DEMO_WAREHOUSE_TIME,
  },
];

/** Tài liệu đã nạp trong phiên mock; giữ trong bộ nhớ để bảng sự kiện có phản hồi ngay. */
const mockIngestedDocuments = new Map<string, { text: string; docId: string }>();
const mockIngestionEvents: IngestionEventRecord[] = [...DEMO_INGESTION_EVENTS];

function mockDocumentDetail(docId: string): WarehouseDocumentDetail {
  const summary = DEMO_WAREHOUSE_DOCUMENTS.find((doc) => doc.doc_id === docId);
  if (!summary) throw new BackendError(404, "not_found", `Không tìm thấy tài liệu ${docId} trong kho minh hoạ.`);
  const text = DEMO_WAREHOUSE_DOCUMENT_TEXTS[docId] ?? summary.title;
  return {
    ...summary,
    text_sha256: DEMO_WAREHOUSE_SHA,
    sections: [{ title: text.split("\n")[0] || "Nội dung", start: 0, end: text.length }],
    text_preview: text.slice(0, 600),
    ...(summary.source === "pubmed"
      ? {
          pubmed: {
            pmid: summary.source_id,
            journal: "Tạp chí minh hoạ",
            publication_date: "2026-01-01",
            publication_types: ["Journal Article"],
            doi: [],
            authors: ["Tác giả minh hoạ"],
            has_abstract: true,
          },
        }
      : {}),
  };
}

function mockWarehouseOverview(): WarehouseOverview {
  const bySource = new Map<string, { documents: number; latest: string; levels: Record<string, number> }>();
  for (const doc of DEMO_WAREHOUSE_DOCUMENTS) {
    const entry = bySource.get(doc.source) ?? { documents: 0, latest: doc.retrieved_at, levels: {} };
    entry.documents += 1;
    entry.levels[doc.source === "pubmed" ? "abstract_only" : "reference_material"] =
      (entry.levels[doc.source === "pubmed" ? "abstract_only" : "reference_material"] ?? 0) + 1;
    bySource.set(doc.source, entry);
  }
  const quality: Record<string, number> = {};
  for (const doc of DEMO_WAREHOUSE_DOCUMENTS) quality[doc.quality_status] = (quality[doc.quality_status] ?? 0) + 1;
  return {
    documents_by_source: [...bySource.entries()].map(([source, entry]) => ({
      source,
      documents: entry.documents,
      latest_retrieved_at: entry.latest,
      by_content_level: entry.levels,
    })),
    documents_by_quality_status: quality,
    quality_findings: [
      { check_name: "has_abstract", severity: "info", count: 3 },
      { check_name: "missing_age", severity: "warn", count: 1 },
    ],
    table_counts: { documents: DEMO_WAREHOUSE_DOCUMENTS.length, document_chunks: 42, drugs: DEMO_WAREHOUSE_DRUGS.length, drug_event_pairs: DEMO_WAREHOUSE_PAIRS.length },
    rag: {
      collection: "vigilens_docs__mock",
      chroma_chunks: 42,
      postgres_chunks: 42,
      embedding_provider: "mock",
      embedding_model: "mock-embedding",
      persist_dir: "./data/chroma",
    },
  };
}

function mockRagHits(input: RagSearchInput): RagHit[] {
  const k = input.k ?? 5;
  const words = input.query.toLowerCase().split(/\s+/).filter((word) => word.length > 2);
  const scored = DEMO_WAREHOUSE_DOCUMENTS.filter((doc) => !input.source || doc.source === input.source)
    .filter((doc) => !input.pairId || doc.pair_id === input.pairId)
    .map((doc) => {
      const haystack = `${doc.title} ${DEMO_WAREHOUSE_DOCUMENT_TEXTS[doc.doc_id] ?? ""}`.toLowerCase();
      const ratio = words.length ? words.filter((word) => haystack.includes(word)).length / words.length : 0;
      return { doc, ratio };
    })
    .filter((entry) => entry.ratio > 0)
    .sort((a, b) => b.ratio - a.ratio)
    .slice(0, k);
  return scored.map(({ doc, ratio }, index) => {
    const text = DEMO_WAREHOUSE_DOCUMENT_TEXTS[doc.doc_id] ?? doc.title;
    return {
      chunk_id: `${doc.doc_id}#${String(index).padStart(4, "0")}`,
      score: Math.round(Math.min(0.95, 0.4 + 0.55 * ratio) * 1000) / 1000,
      text: text.slice(0, 400),
      ordinal: index,
      char_start: 0,
      char_end: Math.min(text.length, 400),
      in_postgres: true,
      document: doc,
    };
  });
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

    // -----------------------------------------------------------------------------------
    // Kho bằng chứng (demo)
    // -----------------------------------------------------------------------------------

    async lookupDrug(name: string): Promise<DrugLookupResult> {
      await delay(120, 320);
      const query = name.trim().toLowerCase();
      const drugs = DEMO_WAREHOUSE_DRUGS.filter(
        (drug) =>
          drug.name.toLowerCase().includes(query) ||
          drug.ingredient.toLowerCase().includes(query) ||
          drug.aliases.some((alias) => alias.toLowerCase().includes(query)),
      );
      const names = new Set(drugs.map((drug) => drug.name));
      const pairs = DEMO_WAREHOUSE_PAIRS.filter((pair) => names.has(pair.drug_name));
      const documents: Record<string, number> = {};
      for (const doc of DEMO_WAREHOUSE_DOCUMENTS) {
        if (doc.pair_id && pairs.some((pair) => pair.pair_id === doc.pair_id)) {
          documents[doc.source] = (documents[doc.source] ?? 0) + 1;
        }
      }
      return {
        query: name,
        matched: drugs.length > 0,
        origin: drugs.length > 0 ? "warehouse" : "dictionary",
        drugs,
        pairs,
        documents,
      };
    },

    async warehouseOverview(): Promise<WarehouseOverview> {
      await delay(120, 320);
      return structuredClone(mockWarehouseOverview());
    },

    async warehouseDocuments(params: WarehouseDocumentsParams = {}): Promise<WarehouseDocumentsResult> {
      await delay(120, 320);
      const filtered = DEMO_WAREHOUSE_DOCUMENTS.filter(
        (doc) =>
          (!params.source || doc.source === params.source) &&
          (!params.pairId || doc.pair_id === params.pairId) &&
          (!params.qualityStatus || doc.quality_status === params.qualityStatus),
      );
      const documents = params.limit != null ? filtered.slice(0, params.limit) : filtered;
      return { documents: structuredClone(documents), count: documents.length };
    },

    async warehouseDocument(docId: string): Promise<WarehouseDocumentDetail> {
      await delay(120, 320);
      const detail = mockDocumentDetail(docId);
      const ingested = mockIngestedDocuments.get(docId);
      if (ingested) detail.text_preview = ingested.text.slice(0, 600);
      return structuredClone(detail);
    },

    async ragSearch(input: RagSearchInput): Promise<RagSearchResult> {
      await delay(120, 320);
      return {
        query: input.query,
        k: input.k ?? 5,
        embedding_model: "mock-embedding",
        hits: mockRagHits(input),
      };
    },

    async ingestionEvents(): Promise<{ events: IngestionEventRecord[]; count: number }> {
      await delay(120, 320);
      const events = [...mockIngestionEvents].sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      return { events: structuredClone(events), count: events.length };
    },

    async ingestDocument(input: IngestDocumentInput): Promise<IngestDocumentResult> {
      await delay();
      const role = useAppStore.getState().role;
      if (role !== "reviewer" && role !== "admin") {
        throw new BackendError(403, "forbidden", "Chỉ vai trò dược sĩ duyệt hoặc quản trị được nạp tài liệu.");
      }
      if (!input.title.trim() || input.text.trim().length < 40 || input.text.length > 200_000 || input.version < 1) {
        throw new BackendError(422, "invalid_request", "Dữ liệu chưa hợp lệ: cần tiêu đề, phiên bản ≥ 1 và văn bản 40..200.000 ký tự.");
      }
      const key = `${input.source}:${input.source_id}:${input.version}`;
      const previous = mockIngestedDocuments.get(key);
      if (previous && previous.text !== input.text) {
        throw new BackendError(409, "INGEST_CONFLICT", "Cùng mã nguồn và phiên bản đã tồn tại với nội dung khác. Tạo phiên bản mới.");
      }
      const docId = `${input.source}:${input.source_id}:${input.version}`;
      mockIngestedDocuments.set(key, { text: input.text, docId });
      const created = !previous;
      const event: IngestionEventRecord = {
        event_id: `ingest-demo-${mockIngestionEvents.length + 1}`,
        kind: "document_ingest",
        status: "completed",
        title: `Nạp ${docId} (dữ liệu minh hoạ)`,
        detail: { doc_id: docId, created, quality_status: "keep" },
        created_at: new Date().toISOString(),
      };
      mockIngestionEvents.unshift(event);
      return {
        doc_id: docId,
        created,
        sha256: DEMO_WAREHOUSE_SHA,
        text_chars: input.text.length,
        quality_status: "keep",
        quality_flags: [],
        rag: { indexed: true, chunks_written: 3, documents_indexed: 1, collection: "vigilens_docs__mock", embedding_model: "mock-embedding" },
        event_id: event.event_id,
      };
    },
  };
}

