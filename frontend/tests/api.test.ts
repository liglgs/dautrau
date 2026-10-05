import { afterEach, describe, expect, it, vi } from "vitest";
import { createApiSource } from "@/lib/api/real";
import { responseError } from "@/lib/api/errors";

afterEach(() => vi.unstubAllGlobals());
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });

describe("backend contract", () => {
  it("does not invent config/usage or verified scope from a list summary", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ items: [{ investigation_id: "i", drug: "x", event: "y", assessment_status: "insufficient_evidence", run_status: "completed", version: 1 }] })));
    const result = await createApiSource().listInvestigations();
    expect(result.items[0]).toMatchObject({ summaryOnly: true, sources: [], assessment: { coverage: { drug: "not_specified" } } });
  });
  it("maps Person 3 annotations while preserving source scope, version, exclusion and Unicode quote", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ items: [{
      evidence_id: "E-P3", doc_id: "pubmed:1:2", stance: "support", excluded: true,
      scope_match: "mismatched", scope: { population: "adults", dose: "10 mg/day", route: "oral" },
      quote: "Tác dụng 😃", locator: { start: 5, end: 15 },
      notes: JSON.stringify({ schema_version: "person3.1", comparator: "placebo", uncertainty: "low", document_hash: "private-metadata" }),
      document: { version: 2, source: "pubmed", title: "Source", metadata: { coverage: "abstract-only" } },
    }] })));
    const [evidence] = await createApiSource().getEvidence("i");
    expect(evidence).toMatchObject({ id: "E-P3", excluded: true, version: 2,
      scopeValues: { route: "oral" }, studyPopulation: "adults", dose: "10 mg/day", coverageNote: "abstract-only",
      quotes: [{ start: 5, end: 15, text: "Tác dụng 😃" }],
    });
    expect(evidence.designNote).toContain("Đối chứng: placebo");
    expect(evidence.designNote).not.toMatch(/schema_version|private-metadata/);
  });
  it("keeps dose text without changing decimal or comparison semantics", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ investigation_id: "i", claim: { dose: ">2.5 mg" }, budget: {}, version: 1 })));
    expect((await createApiSource().getInvestigation("i")).claim.doseText).toBe(">2.5 mg");
  });
  it("uses the version the reviewer saw, never fetches a newer version to approve", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ error: { code: "version_conflict", message: "stale" } }, 409));
    vi.stubGlobal("fetch", fetch);
    const result = await createApiSource().submitReview("i", { action: "approve", expectedVersion: 3, checkpoint: "assessment", reason: "Reviewed current evidence", decisionId: "decision-1" });
    expect(result.ok).toBe(false);
    expect(result.code).toBe("version_conflict");
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toMatchObject({ expected_version: 3, decision_id: "decision-1", checkpoint: "assessment" });
  });
  it("sends custom source/budget preferences to the new backend contract", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ investigation_id: "i", started: true })); vi.stubGlobal("fetch", fetch);
    await createApiSource().createInvestigation({ claimText: "x", drug: "x", adverseEvent: "y", sources: ["pubmed"], maxSteps: 20, maxDocs: 100 }, "stable-key");
    expect(JSON.parse(fetch.mock.calls[0][1].body).config).toEqual({ sources: ["pubmed"], max_steps: 20, max_documents: 100 });
  });
  it("does not label normalized fields as verified evidence coverage", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ investigation_id: "i", claim: {}, normalized_claim: { drug_ingredient: "x", event_term: "y" }, assessment: { assessment_status: "insufficient_evidence" }, budget: {}, version: 1 })));
    expect((await createApiSource().getInvestigation("i")).assessment?.coverage.drug).toBe("not_specified");
  });
  it("keeps server permission failures when cancelling", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json({ error: { code: "forbidden", message: "not owner" } }, 403)));
    expect(await createApiSource().cancelRun("i")).toMatchObject({ ok: false, code: "forbidden" });
  });
  it("sends stable create idempotency key", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ investigation_id: "i", started: true })); vi.stubGlobal("fetch", fetch);
    await createApiSource().createInvestigation({ claimText: "x", drug: "x", adverseEvent: "y", sources: ["pubmed", "dailymed", "faers"], maxSteps: 8, maxDocs: 50 }, "stable-key");
    expect(fetch.mock.calls[0][1].headers["Idempotency-Key"]).toBe("stable-key");
  });
  it("incrementally merges events and keeps cursor after a failed poll", async () => {
    const event = (id: number) => ({ id, kind: "retrieve", message: `event ${id}`, payload: {}, created_at: "2026-10-02T00:00:00Z" });
    const fetch = vi.fn().mockResolvedValueOnce(json({ items: [event(1)], last_id: 1 })).mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(json({ items: [event(1), event(2)], last_id: 2 }));
    vi.stubGlobal("fetch", fetch);
    const api = createApiSource();
    expect((await api.getTimeline("i")).steps).toHaveLength(1);
    await expect(api.getTimeline("i")).rejects.toMatchObject({ code: "network_error" });
    expect((await api.getTimeline("i")).steps).toHaveLength(2);
    expect(fetch.mock.calls[1][0]).toContain("after_id=1");
    expect(fetch.mock.calls[2][0]).toContain("after_id=1");
  });
  it.each([401, 403, 409, 422, 429, 503])("handles %i with a safe common error envelope", (status) => {
    expect(responseError(status, "<script>secret raw proxy page</script>").message).not.toContain("<script>");
    expect(responseError(status, JSON.stringify({ error: { code: "code", request_id: "r" } })).requestId).toBe("r");
  });
});
