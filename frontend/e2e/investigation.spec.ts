import { expect, test } from "@playwright/test";
import { workspace } from "./fixture";

test("double submit creates one investigation and shows server budget", async ({ page }) => {
  const calls = await workspace(page, { role: "investigator" });
  await page.goto("/app/investigations/new");
  await page.getByLabel("Hoạt chất *", { exact: true }).fill("TestDrug");
  await page.getByLabel("Biến cố bất lợi *").fill("TestEvent");
  await expect(page.getByLabel(/Số bước tối đa/)).toBeEnabled();
  await page.getByLabel(/Số bước tối đa/).fill("12");
  await page.getByRole("button", { name: /openFDA FAERS/ }).click();
  await page.locator("form").evaluate((form: HTMLFormElement) => { form.requestSubmit(); form.requestSubmit(); });
  await expect(page).toHaveURL(/fixture-1/);
  const creates = calls.filter((call) => call.method === "POST" && call.path === "/api/v1/investigations");
  expect(creates).toHaveLength(1);
  expect(creates[0].key).toBeTruthy();
  expect(creates[0].body?.config).toEqual({ sources: ["pubmed", "dailymed"], max_steps: 12, max_documents: 50 });
});

test("network failure during polling keeps previously loaded state and evidence", async ({ page }) => {
  await workspace(page, { running: true, keepRunning: true });
  let fail = false;
  await page.route("**/api/backend/api/v1/investigations/fixture-1", (route) => fail ? route.abort("failed") : route.fallback());
  await page.goto("/app/investigations/fixture-1");
  await expect(page.getByText("TestDrug → TestEvent", { exact: true })).toBeVisible();
  fail = true;
  await expect(page.getByText(/Không làm mới được trạng thái:/)).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("TestDrug → TestEvent", { exact: true })).toBeVisible();
  await expect(page.getByText("Lý do: Frozen event survives refresh", { exact: true })).toBeVisible();
});

test("reload restores saved timeline and polling uses cursor", async ({ page }) => {
  const calls = await workspace(page, { running: true });
  await page.goto("/app/investigations/fixture-1");
  await expect(page.getByText("Lý do: Frozen event survives refresh", { exact: true })).toBeVisible();
  await expect.poll(() => calls.some((call) => call.path.includes("after_id=1"))).toBe(true);
  await page.reload();
  await expect(page.getByText("Lý do: Frozen event survives refresh", { exact: true })).toBeVisible();
  expect(calls.filter((call) => call.path.includes("after_id=0")).length).toBeGreaterThanOrEqual(2);
});


test("cancel updates status and prevents further cancellation", async ({ page }) => {
  await workspace(page, { running: true, keepRunning: true });
  let cancelled = false;
  await page.route("**/api/backend/api/v1/investigations/fixture-1/cancel", async (route) => {
    cancelled = true;
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ cancelled: true, message: "Cancelled" }) });
  });
  await page.route("**/api/backend/api/v1/investigations/fixture-1", async (route) => {
    if (!cancelled) return route.fallback();
    await route.fulfill({ contentType: "application/json", body: JSON.stringify({ investigation_id: "fixture-1", claim: { drug: "TestDrug", event: "TestEvent" }, run_status: "cancelled", version: 2, budget: {} }) });
  });
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/app/investigations/fixture-1");
  await page.getByRole("button", { name: "Hủy điều tra", exact: true }).click();
  await expect(page.getByText("Đã hủy", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Hủy điều tra", exact: true })).toHaveCount(0);
});
