import type { AgentStep, AuditEntry, Cov, CoverageField, EvidenceItem, Gap, Investigation, ReviewAction, SourceId } from "@/lib/types";
import type { CreateInvestigationInput, DataSource, DossierPayload, TimelinePayload } from "@/lib/api/types";
import type {
  DrugLookupResult,
  IngestDocumentInput,
  IngestDocumentResult,
  IngestionEventsResult,
  RagSearchInput,
  RagSearchResult,
  WarehouseDocumentDetail,
  WarehouseDocumentsParams,
  WarehouseDocumentsResult,
  WarehouseOverview,
} from "@/lib/api/types";
import { useAppStore } from "@/lib/store/app-store";
import { BackendError, responseError } from "@/lib/api/errors";
import { evidenceDetails } from "@/lib/api/evidence-details";
import { validateClaim } from "@/lib/claim-form";
import type { ClaimInput, ReviewRequest } from "@/generated/api-types";
export { BackendError } from "@/lib/api/errors";

/**
 * Adapter gọi backend FastAPI thật (M07).
 *
 * Bản đồ endpoint:
 *   POST /api/v1/investigations                    → tạo (202)
 *   GET  /api/v1/investigations                    → danh sách
 *   GET  /api/v1/investigations/{id}               → trạng thái để polling
 *   GET  /api/v1/investigations/{id}/events        → timeline sự kiện (after_id)
 *   GET  /api/v1/investigations/{id}/evidence      → bằng chứng + tài liệu
 *   GET  /api/v1/investigations/{id}/documents/{d} → văn bản gốc
 *   GET  /api/v1/investigations/{id}/dossier       → hồ sơ + báo cáo kiểm tra
 *   POST /api/v1/investigations/{id}/reviews       → quyết định reviewer
 *   POST /api/v1/investigations/{id}/continue      → chạy tiếp (202)
 *   GET  /api/v1/investigations/{id}/export        → Markdown (khi đã duyệt)
 */

/**
 * Mọi lời gọi đi qua cầu nối cùng gốc `/api/backend/*` (xem `app/api/backend/[...path]/route.ts`).
 * Token vai trò nằm ở biến môi trường phía máy chủ, không bao giờ vào bundle trình duyệt.
 */
export const SESSION_AUTH = process.env.NEXT_PUBLIC_VIGILENS_AUTH_MODE !== "token";
const API_PREFIX = process.env.NEXT_PUBLIC_VIGILENS_API_PREFIX ?? "/api/backend";

type Role = "investigator" | "reviewer";

/** Vai trò đang chọn trong UI; quyết định token mà cầu nối máy chủ dùng. */
function currentRole(): Role {
  try {
    const role = useAppStore.getState().role;
    return role === "reviewer" || role === "admin" ? "reviewer" : "investigator";
  } catch {
    return "investigator";
  }
}

export async function request<T>(
  path: string,
  options: { method?: string; role?: Role; body?: unknown; headers?: Record<string, string> } = {},
): Promise<T> {
  const role = options.role ?? currentRole();
  let response: Response;
  try { response = await fetch(`${API_PREFIX}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(SESSION_AUTH ? {} : { "X-Vigilens-Role": role }),
      ...(options.headers ?? {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
    signal: AbortSignal.timeout(30_000),
  }); } catch {
    throw new BackendError(0, "network_error", "Chưa xác định kết quả gửi. Giữ nguyên nội dung và thử lại cùng yêu cầu.");
  }
  const text = await response.text();
  const payload = text ? safeJson(text) : null;
  if (!response.ok) {
    if (response.status === 401 && SESSION_AUTH && typeof window !== "undefined" && !path.includes("/auth/")) window.dispatchEvent(new Event("vigilens-session-expired"));
    throw responseError(response.status, text);
  }
  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------------------
// Ánh xạ state của backend → kiểu dữ liệu của giao diện
// ---------------------------------------------------------------------------------------

interface BackendState {
  investigation_id: string;
  created_at?: string | null;
  updated_at?: string | null;
  claim: Record<string, unknown>;
  normalized_claim: Record<string, unknown> | null;
  run_status: string;
  assessment_status: string | null;
  assessment: { status?: string; assessment_status?: string; rationale?: string; coverage?: Record<string, string> } | null;
  stop_reason: string | null;
  checkpoint: string | null;
  next_stage: string | null;
  review_status?: string | null;
  last_review?: BackendLastReview | null;
  version: number;
  budget: { max_steps?: number; max_documents?: number } & Record<string, number>;
  step_index: number;
  config?: { sources: SourceId[] };
  searched_sources?: string[];
  source_status?: Record<string, string>;
  counters?: { evidence: number; documents: number; queries: number; gaps: number };
  gaps?: { gap_id: string; description: string; kind?: string; field?: string }[];
}

interface BackendLastReview {
  action: string;
  checkpoint?: string | null;
  created_at?: string | null;
}

interface BackendListed {
  investigation_id: string;
  run_status: string;
  assessment_status: string | null;
  checkpoint?: string | null;
  review_status?: string | null;
  last_review?: BackendLastReview | null;
  version: number;
  drug?: string | null;
  event?: string | null;
  created_at?: string;
  updated_at?: string;
}

/** Mục trong danh sách: backend chỉ trả bản tóm tắt nên dựng Investigation từ các trường phẳng. */
function listedToInvestigation(item: BackendListed): Investigation {
  return {
    id: item.investigation_id,
    backendId: item.investigation_id,
    claim: { drug: String(item.drug ?? ""), adverseEvent: String(item.event ?? "") },
    sources: [],
    summaryOnly: true,
    budget: { maxSteps: 8, maxDocs: 50, ceilingSteps: 20, ceilingDocs: 100 },
    usage: { steps: 0, docs: 0, tokens: 0, elapsedMs: 0 },
    runStatus: (item.run_status as Investigation["runStatus"]) ?? "queued",
    assessment: item.assessment_status
      ? {
          status: item.assessment_status as NonNullable<Investigation["assessment"]>["status"],
          rationale: "",
          // The summary carries a conclusion, not evidence coverage.
          coverage: {
            drug: "not_specified",
            adverseEvent: "not_specified",
            population: "not_specified",
            dose: "not_specified",
            route: "not_specified",
            timeWindow: "not_specified",
          } satisfies Record<CoverageField, Cov>,
        }
      : undefined,
    reviewState: reviewStateFromBackend(item.review_status),
    checkpoint: item.checkpoint ?? null,
    lastReview: lastReviewFromBackend(item.last_review),
    version: item.version,
    createdAt: item.created_at ?? item.updated_at ?? new Date().toISOString(),
  };
}

/**
 * Trạng thái duyệt lấy từ `review_status` của backend (trạng thái phiên bản hồ sơ mới nhất).
 *
 * Không suy diễn từ `run_status`: một hồ sơ bị từ chối cũng kết thúc ở `completed`, nên suy diễn
 * sẽ biến "đã từ chối" thành "đã duyệt".
 */
function lastReviewFromBackend(
  lastReview?: BackendLastReview | null,
): Investigation["lastReview"] | undefined {
  if (!lastReview?.action) return undefined;
  return {
    action: lastReview.action,
    checkpoint: lastReview.checkpoint ?? null,
    createdAt: lastReview.created_at ?? undefined,
  };
}

function reviewStateFromBackend(reviewStatus?: string | null): Investigation["reviewState"] {
  switch (reviewStatus) {
    case "approved":
      return "approved";
    case "rejected":
      return "rejected";
    case "changes_requested":
      return "changes_requested";
    case "pending":
      return "not_reviewed";
    default:
      return "not_reviewed";
  }
}

function claimFromBackend(claim: Record<string, unknown> | null | undefined) {
  const source = claim ?? {};
  return {
    drug: String(source.drug ?? ""),
    adverseEvent: String(source.event ?? ""),
    population: source.population ? String(source.population) : undefined,
    doseText: typeof source.dose === "string" && source.dose.trim() ? source.dose : undefined,
    route: source.route ? String(source.route) : undefined,
    timeWindow: source.time_window ? String(source.time_window) : undefined,
    rawText: source.claim_text ? String(source.claim_text) : undefined,
  };
}

const COVERAGE_KEYS = ["drug", "adverseEvent", "population", "dose", "route", "timeWindow"] as const;

/** Normalization is not evidence coverage; fields remain unverified without explicit backend coverage. */
function coverageFromNormalized(normalized: Record<string, unknown> | null | undefined) {
  const unknowns = Array.isArray(normalized?.unknowns) ? (normalized?.unknowns as string[]) : [];
  const field = (name: string, value: unknown): Cov => {
    if (value) return "not_specified";
    return unknowns.includes(name) ? "not_specified" : "missing";
  };
  return {
    drug: normalized?.drug_ingredient ? "not_specified" : "missing",
    adverseEvent: normalized?.event_term ? "not_specified" : "missing",
    population: field("population", normalized?.population),
    dose: field("dose", normalized?.dose),
    route: field("route", normalized?.route),
    timeWindow: field("time_window", normalized?.time_window),
  } satisfies Record<CoverageField, Cov>;
}

function coverageFromBackend(raw: Record<string, string> | undefined) {
  const map: Record<string, "verified" | "partial" | "missing" | "not_specified"> = {};
  for (const key of COVERAGE_KEYS) {
    const snake = key === "adverseEvent" ? "adverse_event" : key === "timeWindow" ? "time_window" : key;
    const value = raw?.[snake] ?? raw?.[key];
    map[key] =
      value === "verified" || value === "partial" || value === "missing" || value === "not_specified"
        ? value
        : "not_specified";
  }
  return map as Investigation["assessment"] extends undefined ? never : NonNullable<Investigation["assessment"]>["coverage"];
}

function toInvestigation(state: BackendState): Investigation {
  const budget = state.budget ?? {};
  const counters = state.counters ?? { evidence: 0, documents: 0, queries: 0, gaps: 0 };
  return {
    id: state.investigation_id,
    backendId: state.investigation_id,
    claim: claimFromBackend(state.claim),
    // Chỉ hiện nguồn agent đã thật sự tìm; chưa tìm nguồn nào thì để trống.
    sources: (state.config?.sources ?? (state.claim.config as { sources?: SourceId[] } | undefined)?.sources ?? state.searched_sources ?? []) as SourceId[],
    budget: {
      maxSteps: budget.max_steps ?? 8,
      maxDocs: budget.max_documents ?? 50,
      ceilingSteps: 20,
      ceilingDocs: 100,
    },
    usage: {
      steps: budget.steps_used ?? state.step_index ?? 0,
      docs: budget.documents_used ?? counters.documents ?? 0,
      tokens: (budget.input_tokens ?? 0) + (budget.output_tokens ?? 0),
      elapsedMs: 0,
    },
    runStatus: (state.run_status as Investigation["runStatus"]) ?? "queued",
    assessment: state.assessment
      ? {
          status: (state.assessment_status ?? state.assessment.assessment_status ?? "requires_human_review") as NonNullable<
            Investigation["assessment"]
          >["status"],
          rationale: state.assessment.rationale ?? "",
          coverage: state.assessment.coverage
            ? coverageFromBackend(state.assessment.coverage)
            : coverageFromNormalized(state.normalized_claim),
        }
      : undefined,
    reviewState: reviewStateFromBackend(state.review_status),
    checkpoint: state.checkpoint ?? null,
    nextStage: state.next_stage ?? null,
    stopReason: state.stop_reason,
    sourceStatus: state.source_status ?? {},
    lastReview: lastReviewFromBackend(state.last_review),
    version: state.version,
    // Backend trả mốc thật; chỉ khi thiếu mới tạm dùng thời điểm hiện tại để không vỡ giao diện.
    createdAt: state.created_at ?? state.updated_at ?? new Date().toISOString(),
  };
}

/** `EvidenceUnit.stance` của backend → từ vựng của UI. */
const STANCE_MAP: Record<string, EvidenceItem["stance"]> = {
  supports: "supporting",
  supporting: "supporting",
  contradicts: "contradicting",
  contradicting: "contradicting",
  uncertain: "uncertain",
  background: "background",
};

/** Backend chưa trả kết quả so khớp phạm vi; chỉ nhận khi có giá trị đúng từ vựng. */
const SCOPE_MAP: Record<string, EvidenceItem["scope"]> = {
  match: "matched",
  matched: "matched",
  partial: "partial",
  mismatch: "mismatched",
  mismatched: "mismatched",
};

/** Trường trong `EvidenceGap.field` → trường phạm vi của UI (chỉ những trường thật sự tương ứng). */
const GAP_FIELD_MAP: Record<string, CoverageField> = {
  drug: "drug",
  event: "adverseEvent",
  population: "population",
  dose: "dose",
  route: "route",
  time_window: "timeWindow",
};

function stepFromEvent(event: { id: number; kind: string; message: string; payload: Record<string, unknown>; created_at: string }, index: number): AgentStep {
  const payload = event.payload ?? {};
  // Khớp với từ vựng sự kiện thật của runner (xem GET /{id}/events).
  const kindToType: Record<string, AgentStep["type"]> = {
    search: "search",
    retrieve: "search",
    replan: "replan",
    source_switch: "source_switch",
    contradiction: "contradiction_found",
    contradiction_found: "contradiction_found",
    scope_mismatch: "scope_mismatch",
    checklist: "gap_identified",
    gap: "gap_identified",
    gaps: "gap_identified",
    assess: "assess",
    normalize: "read",
    created: "read",
    running: "read",
    resumed: "read",
    queued: "read",
    waiting_for_review: "reviewer_request",
    checkpoint: "reviewer_request",
    review_approved: "human_review",
    review_rejected: "human_review",
    review_edit: "human_review",
    review_request_more: "human_review",
    dossier: "dossier",
    conclude: "conclude",
    failed: "abstain",
  };
  return {
    index: index + 1,
    type: kindToType[event.kind] ?? "read",
    source: (payload.source as SourceId) ?? undefined,
    query: typeof payload.query === "string" ? payload.query : undefined,
    rationale: event.message,
    resultSummary: typeof payload.summary === "string" ? payload.summary : undefined,
    docsFound: typeof payload.documents === "number" ? payload.documents : undefined,
    newDocs: typeof payload.new_documents === "number" ? payload.new_documents : undefined,
    tokens: typeof payload.tokens === "number" ? payload.tokens : 0,
    durationMs: typeof payload.duration_ms === "number" ? payload.duration_ms : 0,
    startedAt: event.created_at,
    status: "done",
  };
}

export function createApiSource(): DataSource {
  type BackendEvent = { id: number; kind: string; message: string; payload: Record<string, unknown>; created_at: string };
  const timelines = new Map<string, { cursor: number; items: BackendEvent[] }>();
  const timelinePending = new Map<string, Promise<TimelinePayload>>();
  return {
    async listInvestigations() {
      const payload = await request<{ items: BackendListed[] }>(`/api/v1/investigations${SESSION_AUTH && currentRole() === "investigator" ? "?mine_only=true" : ""}`);
      const items = payload.items.map(listedToInvestigation);
      return { items, source: "api" as const };
    },

    async getInvestigation(id: string) {
      const state = await request<BackendState>(`/api/v1/investigations/${id}`);
      return toInvestigation(state);
    },

    async createInvestigation(input: CreateInvestigationInput, idempotencyKey = crypto.randomUUID()) {
      const error = validateClaim(input);
      if (error) throw new BackendError(422, "invalid_request", error);
      const body: ClaimInput = {
        claim_text: input.claimText,
        drug: input.drug,
        event: input.adverseEvent,
        population: input.population || "",
        dose: input.dose || "",
        route: input.route || "",
        time_window: input.timeWindow || "",
        config: { sources: input.sources, max_steps: input.maxSteps, max_documents: input.maxDocs },
      };
      const payload = await request<{ investigation_id: string; started: boolean }>("/api/v1/investigations", {
        method: "POST",
        body,
        headers: { "Idempotency-Key": idempotencyKey },
      });
      return { id: payload.investigation_id, started: payload.started };
    },

    async getTimeline(id: string): Promise<TimelinePayload> {
      const pending = timelinePending.get(id);
      if (pending) return pending;
      const operation = (async () => {
        const previous = timelines.get(id) ?? { cursor: 0, items: [] };
        const payload = await request<{ items: BackendEvent[]; last_id: number }>(
          `/api/v1/investigations/${encodeURIComponent(id)}/events?after_id=${previous.cursor}&limit=200`,
        );
        const merged = new Map(previous.items.map((item) => [item.id, item]));
        payload.items.forEach((item) => merged.set(item.id, item));
        const items = [...merged.values()].sort((a, b) => a.id - b.id);
        timelines.set(id, { cursor: payload.last_id ?? previous.cursor, items });
        return { steps: items.map(stepFromEvent), events: [] };
      })();
      timelinePending.set(id, operation);
      try { return await operation; } finally { timelinePending.delete(id); }
    },

    async getEvidence(id: string) {
      const payload = await request<{ items: Record<string, unknown>[] }>(`/api/v1/investigations/${id}/evidence`);
      return payload.items.map((item, index) => {
        const document = item.document as { doc_id?: string; source?: string; title?: string; source_id?: string; version?: number; metadata?: Record<string, unknown> } | null;
        const scope = item.scope as EvidenceItem["scopeValues"];
        const locator = item.locator as { start?: number; end?: number; section?: string } | undefined;
        return {
          id: String(item.evidence_id ?? `E${index + 1}`),
          label: String(item.evidence_id ?? `E${index + 1}`),
          docId: String(item.doc_id ?? document?.doc_id ?? ""),
          source: (document?.source ?? "pubmed") as SourceId,
          title: document?.title ?? String(item.doc_id ?? ""),
          externalId: document?.source_id ?? String(item.doc_id ?? ""),
          stance: STANCE_MAP[String(item.stance)] ?? "uncertain",
          excluded: Boolean(item.excluded),
          version: document?.version,
          scopeValues: scope,
          ...evidenceDetails(item),
          coverageNote: document?.metadata?.coverage ? String(document.metadata.coverage) : undefined,
          // Backend trả `scope` dạng đối tượng trường phạm vi, không trả kết luận so khớp,
          // nên để trống thay vì gán "Khớp một phần" cho mọi dòng.
          scope: SCOPE_MAP[String(item.scope_match)],
          quotes: [
            {
              start: locator?.start ?? 0,
              end: locator?.end ?? String(item.quote ?? "").length,
              text: String(item.quote ?? ""),
            },
          ],
          foundAtStep: item.found_at_step == null ? undefined : Number(item.found_at_step),
        } satisfies EvidenceItem;
      });
    },

    async getDocument(id: string, docId: string) {
      const payload = await request<{ document: Record<string, unknown> }>(
        `/api/v1/investigations/${id}/documents/${docId}`,
      );
      const document = payload.document;
      return {
        id: String(document.doc_id),
        version: Number(document.version ?? 1),
        source: document.source as SourceId,
        title: String(document.title ?? ""),
        origin: "auto" as const,
        text: String(document.text ?? ""),
        sha256: String(document.hash ?? ""),
        hashStatus: "unchecked" as const,
        retrievedAt: String(document.retrieved_at ?? new Date().toISOString()),
        url: document.source_url ? String(document.source_url) : undefined,
        meta: Object.fromEntries(Object.entries((document.metadata ?? {}) as Record<string, unknown>).map(([key, value]) => [key, String(value)])),
      };
    },

    async getDossier(id: string): Promise<DossierPayload | null> {
      const payload = await request<{
        dossier: Record<string, unknown> | null;
        approved: Record<string, unknown> | null;
        validation: { ok: boolean; errors: string[]; warnings: string[] } | null;
      }>(`/api/v1/investigations/${id}/dossier`);
      if (!payload.dossier) return null;
      const sections = (payload.dossier.sections as { title: string; body: string; evidence_ids?: string[] }[]) ?? [];
      const markdown = [
        `# Hồ sơ điều tra ${id}`,
        "",
        `- Phiên bản: v${payload.dossier.version ?? 1}`,
        `- Trạng thái: ${payload.dossier.status ?? "pending"}`,
        `- Đánh giá: ${payload.dossier.assessment_status ?? "chưa có"}`,
        "",
        String(payload.dossier.summary ?? ""),
        "",
        ...sections.flatMap((section) => [`## ${section.title}`, "", section.body, "",
          (section.evidence_ids ?? []).map((ref) => `[${ref}](#evidence-${encodeURIComponent(ref)})`).join(" · "), ""]),
        "## Hạn chế", ...((payload.dossier.limitations ?? []) as string[]).map((value) => `- ${value}`),
        "", "## Khoảng trống", ...((payload.dossier.gaps ?? []) as { description?: string }[]).map((gap) => `- ${gap.description ?? "Chưa mô tả"}`),
      ].join("\n");
      return {
        markdown,
        approved: Boolean(payload.approved),
        contentHash: payload.dossier.content_hash ? String(payload.dossier.content_hash) : undefined,
        validation: payload.validation ?? null,
      };
    },

    async submitReview(id: string, action: ReviewAction) {
      // Bind approval to the state the reviewer actually read. Do not fetch-and-replace its version here.
      if (typeof action.expectedVersion !== "number" || !Number.isInteger(action.expectedVersion) || !action.checkpoint) {
        return { ok: false, code: "invalid_request", message: "Tải phiên bản và checkpoint trước khi gửi quyết định." };
      }
      try {
        const result = await request<{ message?: string; invalidated?: string[]; review_status?: string }>(
          `/api/v1/investigations/${id}/reviews`,
          {
            method: "POST",
            role: "reviewer",
            body: {
              decision_id: action.decisionId ?? crypto.randomUUID(),
              action: action.action === "edit" ? "edit_evidence" : action.action === "request_more" ? "request_more" : action.action,
              checkpoint: action.checkpoint,
              expected_version: action.expectedVersion,
              reason: action.reason ?? "",
              target_evidence_id: action.target ?? null,
              payload: action.payload ?? {},
            } satisfies ReviewRequest,
          },
        );
        const invalidated = result.invalidated?.length
          ? ` Vô hiệu hoá: ${result.invalidated.join(", ")}.`
          : "";
        return {
          ok: true,
          message: `${result.message ?? "Đã ghi nhận quyết định của reviewer."}${invalidated}`,
        };
      } catch (error) {
        const err = error as BackendError;
        return { ok: false, code: err.code, message: err.message };
      }
    },

    async cancelRun(id: string) {
      try {
        const result = await request<{ message: string }>(`/api/v1/investigations/${encodeURIComponent(id)}/cancel`, { method: "POST" });
        return { ok: true, message: result.message };
      } catch (error) {
        const err = error as BackendError;
        return { ok: false, code: err.code, message: err.message };
      }
    },

    async continueRun(id: string, expectedVersion?: number) {
      if (typeof expectedVersion !== "number") return { ok: false, code: "invalid_request", message: "Tải phiên bản trước khi chạy tiếp." };
      try {
        await request(`/api/v1/investigations/${id}/continue`, {
          method: "POST",
          body: { expected_version: expectedVersion },
          headers: { "Idempotency-Key": `continue-${id}-v${expectedVersion}` },
        });
        return { ok: true, message: "Đã yêu cầu chạy tiếp." };
      } catch (error) {
        const err = error as BackendError;
        return { ok: false, code: err.code, message: err.message };
      }
    },

    async getAudit(id: string): Promise<AuditEntry[]> {
      const payload = await request<{ items: { id: number; kind: string; message: string; created_at: string }[] }>(
        `/api/v1/investigations/${id}/events`,
      );
      return payload.items.map((item) => ({
        id: String(item.id),
        at: item.created_at,
        // `review_*` do người duyệt tạo; `resumed` do điều tra viên bấm chạy tiếp; vòng đời run do
        // hệ thống tạo; còn lại là agent.
        actor: item.kind.startsWith("review_")
          ? { name: "reviewer", kind: "human" as const }
          : item.kind === "resumed"
            ? { name: "investigator", kind: "human" as const }
            : ["checkpoint", "created", "waiting_for_review", "queued"].includes(item.kind)
              ? { name: "system", kind: "system" as const }
              : { name: "agent", kind: "ai" as const },
        action: item.message,
      }));
    },

    async getGaps(id: string): Promise<Gap[]> {
      const state = await request<BackendState>(`/api/v1/investigations/${id}`);
      return (state.gaps ?? []).map((gap) => ({
        id: gap.gap_id,
        kind: gap.kind,
        description: gap.description,
        tried: [],
        // Backend dùng `time_window`; nguồn/contrary/ambiguity không phải trường phạm vi nên để trống
        // thay vì gán bừa một trường nào đó.
        relatedField: GAP_FIELD_MAP[String(gap.field)] ?? undefined,
      }));
    },

    async exportDossier(id: string) {
      try {
        const response = await fetch(`${API_PREFIX}/api/v1/investigations/${id}/export`, {
          headers: SESSION_AUTH ? {} : { "X-Vigilens-Role": currentRole() },
          signal: AbortSignal.timeout(30_000),
          cache: "no-store",
        });
        if (!response.ok) {
          if (response.status === 401 && SESSION_AUTH && typeof window !== "undefined") window.dispatchEvent(new Event("vigilens-session-expired"));
          const text = await response.text();
          const error = responseError(response.status, text);
          return { ok: false, code: error.code, message: error.message };
        }
        return { ok: true, markdown: await response.text() };
      } catch (error) {
        return { ok: false, code: "network_error", message: (error as Error).message };
      }
    },

    // -----------------------------------------------------------------------------------
    // Kho bằng chứng (ELT + Postgres + ChromaDB)
    // -----------------------------------------------------------------------------------

    async lookupDrug(name: string) {
      return request<DrugLookupResult>(`/api/v1/drugs/lookup?name=${encodeURIComponent(name)}`);
    },

    async warehouseOverview() {
      return request<WarehouseOverview>("/api/v1/warehouse/overview");
    },

    async warehouseDocuments(params: WarehouseDocumentsParams = {}) {
      const query = new URLSearchParams();
      if (params.source) query.set("source", params.source);
      if (params.pairId) query.set("pair_id", params.pairId);
      if (params.qualityStatus) query.set("quality_status", params.qualityStatus);
      if (params.limit != null) query.set("limit", String(params.limit));
      const suffix = query.toString() ? `?${query.toString()}` : "";
      return request<WarehouseDocumentsResult>(`/api/v1/warehouse/documents${suffix}`);
    },

    async warehouseDocument(docId: string, previewChars?: number) {
      // `doc_id` chứa dấu hai chấm (ví dụ `pubmed:39466269:1`) nên phải mã hoá cả đoạn đường dẫn.
      const suffix = previewChars != null ? `?preview_chars=${previewChars}` : "";
      return request<WarehouseDocumentDetail>(
        `/api/v1/warehouse/documents/${encodeURIComponent(docId)}${suffix}`,
      );
    },

    async ragSearch(input: RagSearchInput) {
      return request<RagSearchResult>("/api/v1/rag/search", {
        method: "POST",
        body: {
          query: input.query,
          ...(input.k != null ? { k: input.k } : {}),
          ...(input.source ? { source: input.source } : {}),
          ...(input.pairId ? { pair_id: input.pairId } : {}),
        },
      });
    },

    async ingestionEvents(limit?: number) {
      const suffix = limit != null ? `?limit=${limit}` : "";
      return request<IngestionEventsResult>(`/api/v1/ingestion/events${suffix}`, { role: "reviewer" });
    },

    async ingestDocument(input: IngestDocumentInput) {
      return request<IngestDocumentResult>("/api/v1/ingestion/documents", {
        method: "POST",
        role: "reviewer",
        body: {
          source: input.source,
          source_id: input.source_id,
          version: input.version,
          title: input.title,
          text: input.text,
          source_url: input.source_url || undefined,
          metadata: input.metadata,
        },
      });
    },
  };
}

