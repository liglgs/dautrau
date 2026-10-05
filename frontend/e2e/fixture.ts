import type { Page } from "@playwright/test";

/** Browser-side contract fixtures. No backend, real source, session or model is simulated as live. */
export async function workspace(page: Page, options: { role?: string; conflict?: boolean; approved?: boolean; running?: boolean; keepRunning?: boolean } = {}) {
  const calls: { method: string; path: string; body?: Record<string, unknown>; key?: string }[] = [];
  let version = 3;
  let approved = options.approved ?? false;
  let conflict = options.conflict ?? false;
  let running = options.running ?? false;
  const text = "😀 first quote / second quote";
  const state = () => ({ investigation_id: "fixture-1", version, run_status: approved ? "completed" : running ? "running" : "waiting_for_review", checkpoint: approved ? null : "dossier",
    next_stage: "build_dossier", claim: { claim_text: "Synthetic claim", drug: "TestDrug", event: "TestEvent" }, normalized_claim: null,
    assessment_status: "requires_human_review", assessment: { rationale: "Synthetic evidence requires review" }, budget: { max_steps: 8, max_documents: 50 },
    review_status: approved ? "approved" : "pending", searched_sources: ["pubmed"], counters: {}, created_at: "2026-10-02T00:00:00Z" });
  await page.addInitScript((role) => {
    if (!localStorage.getItem("vigilens-app")) localStorage.setItem("vigilens-app", JSON.stringify({ state: { role }, version: 0 }));
  }, options.role ?? "reviewer");
  await page.route("**/api/backend/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/backend", "");
    const body = request.method() === "POST" ? request.postDataJSON() as Record<string, unknown> : undefined;
    calls.push({ method: request.method(), path: path + url.search, body, key: request.headers()["idempotency-key"] });
    const json = (value: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(value) });
    if (path === "/api/v1/investigations" && request.method() === "POST") {
      await new Promise((resolve) => setTimeout(resolve, 100));
      return json({ investigation_id: "fixture-1", started: true }, 202);
    }
    if (path === "/api/v1/investigations") return json({ items: [state()] });
    if (path.endsWith("/reviews")) {
      if (conflict) { conflict = false; version += 1; return json({ error: { code: "version_conflict", message: "stale" } }, 409); }
      if (body?.expected_version !== version) return json({ error: { code: "version_conflict", message: "stale" } }, 409);
      version += 1; approved = body?.action === "approve";
      return json({ message: "Fixture decision recorded", invalidated: approved ? [] : ["dossier"] });
    }
    if (path.endsWith("/events")) {
      const after = Number(url.searchParams.get("after_id") ?? 0);
      if (after > 0 && !options.keepRunning) running = false;
      return json({ items: after ? [] : [{ id: 1, kind: "retrieve", message: "Frozen event survives refresh", payload: { source: "pubmed", query: "TestDrug TestEvent" }, created_at: "2026-10-02T00:00:00Z" }], last_id: Math.max(after, 1) });
    }
    if (path.endsWith("/evidence")) return json({ items: [
      { evidence_id: "e1", doc_id: "doc1", stance: "supports", quote: "second quote", locator: { start: 16, end: 28 }, scope: { population: "adults", dose: "10 mg" }, document: { doc_id: "doc1", source: "pubmed", source_id: "demo", title: "Synthetic adults", version: 1 } },
      { evidence_id: "e2", doc_id: "doc1", stance: "contradicts", quote: "first quote", locator: { start: 2, end: 13 }, scope: { population: "children", dose: "1 mg" }, document: { doc_id: "doc1", source: "pubmed", source_id: "demo", title: "Synthetic children", version: 1 } },
    ] });
    if (path.includes("/documents/")) return json({ document: { doc_id: "doc1", version: 1, source: "pubmed", source_id: "demo", title: "Synthetic text", text, hash: "a".repeat(64), retrieved_at: "2026-10-02T00:00:00Z", source_url: "javascript:window.__xss=1", metadata: { coverage: "abstract-only" } } });
    if (path.endsWith("/dossier")) return json({ dossier: { version, status: approved ? "approved" : "pending", content_hash: "a".repeat(64), sections: [{ title: "Synthetic dossier", body: "<script>window.__xss=1</script>\n\nSynthetic text.", evidence_ids: ["e1"] }] }, approved: approved ? {} : null, validation: { ok: true, errors: [], warnings: [] } });
    if (path.endsWith("/export")) return approved ? route.fulfill({ contentType: "text/markdown", body: "# Approved synthetic version\n" }) : json({ error: { code: "dossier_not_approved", message: "Not approved" } }, 409);
    return json(state());
  });
  return calls;
}
