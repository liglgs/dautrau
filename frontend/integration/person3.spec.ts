import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

test("Person 3 graph integrates with claim, evidence, review and export UI", async ({ page, context }, testInfo) => {
  const request = context.request;
  const login = async (role: string) => {
    await page.goto("/login");
    await page.getByLabel("Token đăng nhập", { exact: true }).fill(`person4-integration-${role}`);
    await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
    await expect(page).toHaveURL(/\/app$/);
  };
  await login("investigator");
  // No page.route or API response stubs: requests traverse the Next server proxy.
  await page.goto("/app/investigations/new");
  await page.getByLabel("Câu nhận định cần kiểm chứng").fill("Fictional demo: Drug Alpha and Event Alpha in the stated scope.");
  await page.getByLabel("Hoạt chất *", { exact: true }).fill("Drug Alpha");
  await page.getByLabel("Biến cố bất lợi *").fill("Event Alpha");
  await page.getByLabel("Quần thể", { exact: true }).fill("adults");
  await page.getByLabel("Liều", { exact: true }).fill("10 mg/day");
  await page.getByLabel("Đường dùng", { exact: true }).fill("oral");
  await page.getByLabel("Cửa sổ thời gian", { exact: true }).fill("30 days");
  await page.getByLabel(/Số bước tối đa/).fill("12");
  await page.getByRole("button", { name: "Bắt đầu điều tra", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/investigations\/INV-[^/]+$/);
  const base = new URL(page.url()).pathname;
  const api = `/api/backend/api/v1/investigations/${base.split("/").at(-1)}`;
  const state = async () => {
    const response = await request.get(api, { headers: { "X-Vigilens-Role": "investigator" } });
    expect(response.ok()).toBeTruthy();
    return response.json();
  };
  await expect.poll(async () => (await state()).checkpoint).toBe("assessment");
  expect((await state()).claim.config.max_steps).toBe(12);
  expect((await state()).assessment_status).toBe("supported_for_scope");

  await page.goto(`${base}/evidence`);
  const evidenceResponse = await request.get(`${api}/evidence`, { headers: { "X-Vigilens-Role": "investigator" } });
  const { items } = await evidenceResponse.json();
  expect(items).toHaveLength(2);
  await page.getByRole("button", { name: `[${items[0].evidence_id}]`, exact: true }).first().click();
  await expect(page.locator("mark")).toHaveText(items[0].quote);
  await expect(page.getByText("Đối chứng: placebo", { exact: false })).toBeVisible();
  await expect(page.getByText(/schema_version|document_hash/)).toHaveCount(0);
  await page.getByRole("button", { name: "Đóng", exact: true }).click();
  await page.screenshot({ path: testInfo.outputPath("person3-evidence.png"), fullPage: true });

  const role = login;
  const approve = async (checkpoint: string) => {
    await page.goto(`${base}/review`);
    await expect(page.getByText(new RegExp(`Checkpoint: ${checkpoint}`))).toBeVisible();
    await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("Reviewed synthetic source quotations and scope for integration testing.");
    const response = page.waitForResponse((r) => r.url().endsWith("/reviews") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
    expect((await response).ok()).toBeTruthy();
  };
  await role("reviewer");
  await approve("assessment");
  await role("investigator");
  await page.goto(base);
  await page.getByRole("button", { name: "Tiếp tục chạy", exact: true }).click();
  await expect.poll(async () => (await state()).checkpoint).toBe("dossier");
  await page.goto(`${base}/dossier`);
  await expect(page.getByRole("button", { name: "Xuất .md", exact: true })).toBeDisabled();
  const unapproved = await request.get(`${api}/export`, { headers: { "X-Vigilens-Role": "reviewer" } });
  expect(unapproved.status()).toBe(409);

  await role("reviewer");
  await approve("dossier");
  await expect.poll(async () => (await state()).run_status).toBe("completed");
  await page.goto(`${base}/dossier`);
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất .md", exact: true }).click();
  const download = await downloaded;
  const file = await download.path();
  expect(file).toBeTruthy();
  const markdown = await readFile(file!, "utf8");
  expect(markdown).toContain(items[0].quote);
  expect(markdown).toContain(items[0].evidence_id);
  expect(markdown).toContain("v1");

  // Editing completed evidence reopens assessment and invalidates approval on the server.
  await page.goto(`${base}/review`);
  await page.getByLabel("Hành động", { exact: true }).selectOption("edit");
  await page.getByLabel("Bằng chứng", { exact: true }).selectOption(items[0].evidence_id);
  await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("Recheck synthetic evidence scope after reviewer correction.");
  const edited = page.waitForResponse((r) => r.url().endsWith("/reviews") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
  expect((await edited).ok()).toBeTruthy();
  await page.goto(`${base}/dossier`);
  await expect(page.getByRole("button", { name: "Xuất .md", exact: true })).toBeDisabled();
  const invalidated = await request.get(`${api}/export`, { headers: { "X-Vigilens-Role": "reviewer" } });
  expect(invalidated.status()).toBe(409);
});


test("cookie session protects workspace, cancel works and expiry keeps return path", async ({ page, context }) => {
  const request = context.request;
  await page.goto("/app/investigations/new");
  await expect(page).toHaveURL(/\/login\?returnTo=/);
  await page.getByLabel("Token đăng nhập", { exact: true }).fill("invalid-token");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page.getByText("Chưa đăng nhập được", { exact: true })).toBeVisible();
  await page.getByLabel("Token đăng nhập", { exact: true }).fill("person4-integration-investigator");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/investigations\/new$/);
  await expect(page.getByRole("button", { name: /Chế độ demo/ })).toHaveCount(0);
  expect((await context.cookies()).find((cookie) => cookie.name === "session_id")?.httpOnly).toBe(true);
  const me = await request.get("/api/backend/api/v1/auth/me", { headers: { "X-Vigilens-Role": "reviewer" } });
  expect((await me.json()).role).toBe("investigator");
  const crossOrigin = await request.post("/api/backend/api/v1/auth/logout", { headers: { Origin: "https://foreign.example" } });
  expect(crossOrigin.status()).toBe(403);
  await page.getByLabel("Hoạt chất *", { exact: true }).fill("Drug Alpha");
  await page.getByLabel("Biến cố bất lợi *").fill("Event Alpha");
  await page.getByRole("button", { name: "Bắt đầu điều tra", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/investigations\/INV-[^/]+$/);
  const destination = new URL(page.url()).pathname;
  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Hủy điều tra", exact: true }).click();
  await expect(page.getByText("Đã hủy", { exact: true })).toBeVisible();
  await context.clearCookies();
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`/login\\?returnTo=${encodeURIComponent(destination)}`));
  await page.getByLabel("Token đăng nhập", { exact: true }).fill("person4-integration-investigator");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${destination}$`));
  // A polling request can report expiry after logout succeeds but before the
  // login navigation commits. It must not replace explicit logout navigation.
  let expiryDuringLogout = false;
  await page.route((url) => url.pathname === "/login", async (route) => {
    if (!new URL(route.request().url()).searchParams.has("returnTo")) {
      await page.evaluate(() => window.dispatchEvent(new Event("vigilens-session-expired")));
      expiryDuringLogout = true;
    }
    await route.continue();
  });
  await page.getByRole("button", { name: "Đăng xuất", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(expiryDuringLogout).toBe(true);
  expect((await request.get("/api/backend/api/v1/auth/me")).status()).toBe(401);
});
