import { afterEach, describe, expect, it, vi } from "vitest";
import { createCaseworkApiSource } from "@/lib/api/casework";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
afterEach(() => vi.unstubAllGlobals());

describe("casework v2 route contract", () => {
  it("saves raw-only intake with the stable idempotency key", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ id: "CW-1", kind: "di", raw_text: "Câu hỏi 😃", priority: "routine", version: 1, input_revision: 1, work_status: "accepted", run_status: "queued", review_status: "not_required", created_at: "2026-10-07T00:00:00Z" }));
    vi.stubGlobal("fetch", fetch);
    await createCaseworkApiSource().createIntake({ kind: "di", raw_text: "Câu hỏi 😃", language: "vi" }, "intake-key");
    expect(fetch.mock.calls[0][0]).toContain("/api/v2/work-items/intake");
    expect(fetch.mock.calls[0][1].headers["Idempotency-Key"]).toBe("intake-key");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ kind: "di", raw_text: "Câu hỏi 😃", language: "vi" });
  });

  it("pins versions and does not calculate a review basis in the browser", async () => {
    const fetch = vi.fn().mockResolvedValue(json({})); vi.stubGlobal("fetch", fetch);
    await createCaseworkApiSource().reviewResponse("R/1", { expected_version: 4, expected_work_version: 8, basis_hash: "server-basis", action: "approve", reason: "Đã đối chiếu" }, "review-key");
    expect(fetch.mock.calls[0][0]).toContain("/api/v2/responses/R%2F1/review");
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ expected_version: 4, expected_work_version: 8, basis_hash: "server-basis", action: "approve", reason: "Đã đối chiếu" });
  });

  it("uses actor-bound editor draft endpoint rather than creating a response per keystroke", async () => {
    const fetch = vi.fn().mockResolvedValue(json({ draft_id: "D1", entity_type: "response", entity_id: "R1", actor_id: "a", base_versions: { work_item: 2 }, content: { summary: "nháp" }, saved_at: "2026-10-07T00:00:00Z", version: 1 })); vi.stubGlobal("fetch", fetch);
    await createCaseworkApiSource().saveEditorDraft("CW/1", { base_versions: { work_item: 2 }, content: { summary: "nháp" } }, "draft-key");
    expect(fetch.mock.calls[0][0]).toContain("/api/v2/work-items/CW%2F1/editor-draft");
    expect(fetch.mock.calls[0][1].method).toBe("PATCH");
  });
});
