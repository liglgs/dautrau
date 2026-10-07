// @vitest-environment jsdom
import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ResponsePanel, ReviewPanel } from "@/components/casework/work-item-panels";

const create = vi.fn(); const submit = vi.fn(); const exportResponse = vi.fn(); const review = vi.fn();
const actorDraft = { draft_id: "D", entity_type: "work_item", entity_id: "CW-1", actor_id: "a", version: 1, base_versions: {}, content: { summary: "Bản nháp đã lưu" }, saved_at: "2026-10-07T00:00:00Z" };
const workflow = {
  work_item: { id: "CW-1", kind: "di", raw_text: "Q", priority: "routine", version: 4, input_revision: 2, work_status: "in_progress", run_status: "completed", review_status: "pending", created_at: "2026-10-07T00:00:00Z" },
  input_sources: [], field_assertions: [], clarifications: [], runs: [], follow_ups: [],
  readiness: { can_retrieve_preliminary: true, can_run_scoped_analysis: true, can_draft_limited: true, can_submit_review: true, blockers: [], warnings: [] },
  current_response: { response_id: "R-1", version: 3, status: "draft", sections: {}, author_ids: [], basis_hash: "b".repeat(64) },
  version_basis: { basis_hash: "b".repeat(64) }, allowed_actions: ["submit_review", "review_response"],
};
const mutation = (mutate: ReturnType<typeof vi.fn>) => ({ mutate, isPending: false, error: null });
vi.mock("@/lib/hooks/use-casework", () => ({
  useWorkflow: () => ({ data: workflow, error: null, isRefetchError: false, refetch: vi.fn() }),
  useEditorDraft: () => ({ data: actorDraft }),
  useSaveEditorDraft: () => mutation(vi.fn()), useCreateResponse: () => mutation(create), useSubmitReview: () => mutation(submit), useApprovedExport: () => mutation(exportResponse), useReviewDecision: () => mutation(review),
  useFieldUpdate: () => mutation(vi.fn()), useClarificationAnswer: () => mutation(vi.fn()), useStartCaseworkRun: () => mutation(vi.fn()), useAdrIntakePatch: () => mutation(vi.fn()), useAdrReportability: () => mutation(vi.fn()), useCloseFollowUp: () => mutation(vi.fn()), useCaseworkEvents: () => ({ data: { events: [] }, error: null, isFetching: false, refetch: vi.fn() }),
}));

describe("live DI response gates", () => {
  it("creates/submits only from saved draft and keeps export blocked until approved", async () => {
    render(<ResponsePanel id="CW-1" />);
    await waitFor(() => expect((screen.getByRole("button", { name: "Tạo phản hồi từ nháp đã lưu" }) as HTMLButtonElement).disabled).toBe(false));
    expect((screen.getByRole("button", { name: "Gửi chờ duyệt" }) as HTMLButtonElement).disabled).toBe(false);
    expect((screen.getByRole("button", { name: "Xuất bản đã duyệt" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows independent decision controls only when server capability allows it", () => {
    render(<ReviewPanel id="CW-1" />);
    expect((screen.getByRole("button", { name: "Duyệt phiên bản này" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
