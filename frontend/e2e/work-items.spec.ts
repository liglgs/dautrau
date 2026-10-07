import { expect, test } from "@playwright/test";
import { workspace } from "./fixture";

test("work-item workspace keeps work, run, and review statuses distinct", async ({ page }) => {
  await workspace(page, { role: "reviewer" });
  await page.route("**/api/backend/api/v1/auth/me", (route) => route.fulfill({ contentType: "application/json", body: JSON.stringify({ user_id: "reviewer-fixture", role: "reviewer" }) }));
  await page.route("**/api/backend/api/v2/work-items/CW-DEMO-001/workflow", async (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
      work_item: { id: "CW-DEMO-001", kind: "di", raw_text: "Câu hỏi thử nghiệm", priority: "routine", version: 1, input_revision: 1, work_status: "awaiting_information", run_status: "running", review_status: "not_required", created_at: "2026-10-07T00:00:00Z" },
      input_sources: [], field_assertions: [], clarifications: [],
      readiness: { can_retrieve_preliminary: true, can_run_scoped_analysis: false, can_draft_limited: true, can_submit_review: false, blockers: [], warnings: [] },
      runs: [], current_response: null, allowed_actions: [],
      }),
    }));
  await page.goto("/app/work-items/CW-DEMO-001");
  await expect(page.getByText(/Công việc:/)).toBeVisible();
  await expect(page.getByText(/Lần chạy:/)).toBeVisible();
  await expect(page.getByText(/Duyệt:/)).toBeVisible();
  await page.getByRole("link", { name: "Tiếp nhận", exact: true }).click();
  await expect(page.getByText("Thông tin được trích xuất")).toBeVisible();
  await expect(page.getByText("Câu hỏi làm rõ")).toBeVisible();
});
