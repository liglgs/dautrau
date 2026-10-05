import { expect, test } from "@playwright/test";
import { workspace } from "./fixture";

test("stale review preserves reason and only retries after loading new version", async ({ page }) => {
  const calls = await workspace(page, { conflict: true });
  await page.goto("/app/investigations/fixture-1/review");
  await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("I reviewed the original evidence and source.");
  await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
  await expect(page.getByText("Phiên bản đã thay đổi", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Lý do (ít nhất 15 ký tự)")).toHaveValue("I reviewed the original evidence and source.");
  await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
  await expect(page.getByText(/Phiên bản đang xem: v4/)).toBeVisible();
  await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
  await expect(page.getByText("Fixture decision recorded")).toBeVisible();
  const reviews = calls.filter((call) => call.path.endsWith("/reviews"));
  expect(reviews.map((call) => call.body?.expected_version)).toEqual([3, 4]);
});

test("viewer cannot submit a review", async ({ page }) => {
  const calls = await workspace(page, { role: "investigator" });
  await page.goto("/app/investigations/fixture-1/review");
  await expect(page.getByText("Chỉ người duyệt được gửi quyết định", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Gửi quyết định" })).toHaveCount(0);
  expect(calls.some((call) => call.path.endsWith("/reviews"))).toBe(false);
});

test("failed evidence refresh preserves the viewed version and conflict until recovery", async ({ page }) => {
  const calls = await workspace(page, { conflict: true });
  let failEvidence = false;
  await page.route("**/api/backend/api/v1/investigations/fixture-1/evidence", (route) =>
    failEvidence ? route.abort("failed") : route.fallback());
  await page.goto("/app/investigations/fixture-1/review");
  const reason = page.getByLabel("Lý do (ít nhất 15 ký tự)");
  const submit = page.getByRole("button", { name: "Gửi quyết định", exact: true });
  await reason.fill("Keep my review while the evidence endpoint is unavailable.");
  await expect(submit).toBeEnabled();
  failEvidence = true;
  await submit.click();
  await expect(page.getByText("Phiên bản đã thay đổi", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
  await expect(page.getByText("Chưa tải đủ nội dung mới", { exact: true })).toBeVisible();
  await expect(page.getByText(/Phiên bản đang xem: v3/)).toBeVisible();
  await expect(page.getByText("Phiên bản đã thay đổi", { exact: true })).toBeVisible();
  await expect(reason).toHaveValue("Keep my review while the evidence endpoint is unavailable.");
  await expect(submit).toBeDisabled();
  expect(calls.filter((call) => call.path.endsWith("/reviews"))).toHaveLength(1);

  failEvidence = false;
  await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
  await expect(page.getByText(/Phiên bản đang xem: v4/)).toBeVisible();
  await submit.click();
  await expect(page.getByText("Fixture decision recorded")).toBeVisible();
  expect(calls.filter((call) => call.path.endsWith("/reviews")).map((call) => call.body?.expected_version)).toEqual([3, 4]);
});

test("refresh preserves edited claim fields and blocks submission while evidence is loading", async ({ page }) => {
  const calls = await workspace(page, { conflict: true });
  await page.goto("/app/investigations/fixture-1/review");
  await page.getByLabel("Hành động", { exact: true }).selectOption("edit_claim");
  await page.getByLabel("Hoạt chất", { exact: true }).fill("CorrectedDrug");
  await page.getByLabel("Biến cố", { exact: true }).fill("CorrectedEvent");
  await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("Preserve my independently reviewed claim correction.");
  const submit = page.getByRole("button", { name: "Gửi quyết định", exact: true });
  await submit.click();
  await expect(page.getByText("Phiên bản đã thay đổi", { exact: true })).toBeVisible();

  let releaseEvidence!: () => void;
  const gate = new Promise<void>((resolve) => { releaseEvidence = resolve; });
  let loadingEvidence = false;
  await page.route("**/api/backend/api/v1/investigations/fixture-1/evidence", async (route) => {
    loadingEvidence = true;
    await gate;
    await route.fallback();
  });
  try {
    await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
    await expect.poll(() => loadingEvidence).toBe(true);
    await expect(submit).toBeDisabled();
    await expect(page.getByLabel("Hành động", { exact: true })).toBeDisabled();
    await expect(page.getByText(/Phiên bản đang xem: v3/)).toBeVisible();
  } finally {
    releaseEvidence();
  }
  await expect(page.getByText(/Phiên bản đang xem: v4/)).toBeVisible();
  await expect(page.getByLabel("Hoạt chất", { exact: true })).toHaveValue("CorrectedDrug");
  await expect(page.getByLabel("Biến cố", { exact: true })).toHaveValue("CorrectedEvent");
  await submit.click();
  await expect(page.getByText("Fixture decision recorded")).toBeVisible();
  const reviews = calls.filter((call) => call.path.endsWith("/reviews"));
  expect(reviews[1].body).toMatchObject({ expected_version: 4, payload: { drug: "CorrectedDrug", event: "CorrectedEvent" } });
});

test("a conflict blocks resubmission even when the newer state cannot be fetched", async ({ page }) => {
  const calls = await workspace(page, { conflict: true });
  let failState = false;
  await page.route("**/api/backend/api/v1/investigations/fixture-1", (route) =>
    failState ? route.abort("failed") : route.fallback());
  await page.goto("/app/investigations/fixture-1/review");
  await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("Do not retry a stale decision without loading the new state.");
  const submit = page.getByRole("button", { name: "Gửi quyết định", exact: true });
  await expect(submit).toBeEnabled();
  failState = true;
  await submit.click();
  await expect(page.getByText("Phiên bản đã thay đổi", { exact: true })).toBeVisible();
  await expect(submit).toBeDisabled();
  await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
  await expect(page.getByText("Chưa tải đủ nội dung mới", { exact: true })).toBeVisible();
  await expect(page.getByText(/Phiên bản đang xem: v3/)).toBeVisible();
  await expect(submit).toBeDisabled();
  expect(calls.filter((call) => call.path.endsWith("/reviews"))).toHaveLength(1);
  failState = false;
  await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
  await expect(page.getByText(/Phiên bản đang xem: v4/)).toBeVisible();
  await expect(submit).toBeEnabled();
});

test("evidence comparison shows scope differences and exact Unicode quote", async ({ page }, testInfo) => {
  await workspace(page);
  await page.goto("/app/investigations/fixture-1/evidence");
  await page.getByLabel("Chọn e1", { exact: true }).check();
  await page.getByLabel("Chọn e2", { exact: true }).check();
  await page.getByRole("button", { name: /So sánh mâu thuẫn/ }).click();
  await expect(page.getByRole("region", { name: "So sánh bằng chứng" }).getByText("Quần thể: adults", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "So sánh bằng chứng" }).getByText("Quần thể: children", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("evidence-comparison.png"), fullPage: true });
  await page.getByRole("button", { name: "[e1]", exact: true }).first().click();
  await expect(page.locator("mark")).toHaveText("second quote");
  await expect(page.getByRole("link", { name: "Trang nguồn" })).toHaveCount(0);
});

test("Markdown HTML does not execute and approved version downloads", async ({ page }) => {
  await workspace(page, { approved: true });
  await page.goto("/app/investigations/fixture-1/dossier");
  await expect(page.getByText("Synthetic text.", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất .md" }).click();
  expect((await download).suggestedFilename()).toBe("fixture-1-dossier.md");
});

test("unapproved dossier cannot download", async ({ page }) => {
  await workspace(page);
  await page.goto("/app/investigations/fixture-1/dossier");
  await expect(page.getByRole("button", { name: "Xuất .md" })).toBeDisabled();
});

test("editing evidence removes current approval and blocks export", async ({ page }) => {
  const calls = await workspace(page, { approved: true });
  await page.goto("/app/investigations/fixture-1/review");
  await page.getByLabel("Hành động", { exact: true }).selectOption("edit");
  await page.getByLabel("Bằng chứng", { exact: true }).selectOption("e1");
  await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("Scope was reviewed and changed with source.");
  await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
  await expect(page.getByText(/Fixture decision recorded/)).toBeVisible();
  const post = calls.find((call) => call.path.endsWith("/reviews"));
  expect(post?.body?.action).toBe("edit_evidence");
  expect(post?.body?.target_evidence_id).toBe("e1");
  await page.goto("/app/investigations/fixture-1/dossier");
  await expect(page.getByRole("button", { name: "Xuất .md" })).toBeDisabled();
  await expect(page.getByText("Đã duyệt", { exact: true })).toHaveCount(0);
});

test("dossier citation opens its original evidence", async ({ page }) => {
  await workspace(page, { approved: true });
  await page.goto("/app/investigations/fixture-1/dossier");
  await page.getByRole("button", { name: "e1", exact: true }).click();
  await expect(page.locator("mark")).toHaveText("second quote");
});

for (const resource of ["evidence", "dossier"] as const) {
  test(`failed ${resource} refetch keeps cached content and warns that it is stale`, async ({ page }) => {
    await workspace(page, { approved: true });
    let fail = false;
    await page.route("**/api/backend/api/v1/investigations/fixture-1", (route) => route.fulfill({ json: {
      investigation_id: "fixture-1", version: fail ? 4 : 3, run_status: "running",
      claim: { drug: "TestDrug", event: "TestEvent" }, budget: {},
    } }));
    await page.route(`**/api/backend/api/v1/investigations/fixture-1/${resource}`, (route) =>
      fail ? route.abort("failed") : route.fallback());
    await page.goto(`/app/investigations/fixture-1/${resource}`);
    const content = resource === "evidence"
      ? page.getByText("Synthetic adults", { exact: true })
      : page.getByText("Synthetic text.", { exact: true });
    await expect(content).toBeVisible();
    fail = true;
    const title = resource === "evidence" ? "Không làm mới được bằng chứng" : "Không làm mới được hồ sơ";
    await expect(page.getByText(title, { exact: true })).toBeVisible();
    await expect(content).toBeVisible();
    if (resource === "dossier") {
      await expect(page.getByRole("button", { name: "Xuất .md" })).toBeDisabled();
      await expect(page.getByText("Đã duyệt", { exact: true })).toHaveCount(0);
    }
  });
}
