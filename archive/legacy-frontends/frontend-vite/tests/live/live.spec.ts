import { expect, test, type Page } from "@playwright/test";

const password = process.env.DEMO_PASSWORD ?? "demo12345";
const at = "2026-09-01T08:15:00+07:00";

async function login(page: Page, name: RegExp) {
  await page.goto("/login");
  await page.getByRole("button", { name }).click();
  await page.getByLabel("Mật khẩu demo").fill(password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.getByRole("heading", { name: "Hồ sơ cần rà soát" })).toBeVisible();
}

test("live PostgreSQL flow: import, evidence, clinician approval", async ({ page }) => {
  const caseId = `LIVE-${Date.now()}`;
  const manifest = {
    schema_version: "1.0", case_id: caseId, patient_id: `P-${caseId}`,
    encounter_id: `E-${caseId}`, reconciliation_at: "2026-09-01T08:00:00+07:00",
    initial_visible_at: at,
    documents: [
      { source_id: "H", version: 1, kind: "medication_history", filename: "history.txt",
        author_role: "reviewer", event_time: null, recorded_at: at, available_at: at },
      { source_id: "O", version: 1, kind: "admission_order", filename: "order.txt",
        author_role: "clinician", event_time: null, recorded_at: at, available_at: at },
    ],
  };
  await login(page, /Linh/);
  await page.getByRole("button", { name: "+ Nhập hồ sơ mô phỏng" }).click();
  await page.getByLabel("Manifest JSON").setInputFiles({
    name: "case.json", mimeType: "application/json", buffer: Buffer.from(JSON.stringify(manifest)),
  });
  await page.getByLabel("Nguồn TXT").setInputFiles([
    { name: "history.txt", mimeType: "text/plain", buffer: Buffer.from("Người bệnh khai đang dùng Thuốc B 500 mg, 1 lần/ngày.") },
    { name: "order.txt", mimeType: "text/plain", buffer: Buffer.from("Y lệnh Thuốc B 500 mg, 1 lần/ngày.") },
  ]);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Kiểm tra gói" }).click();
  await page.getByRole("button", { name: "Nhập hồ sơ", exact: true }).click();
  await expect(page.getByRole("heading", { name: `Ca ${caseId}` })).toBeVisible();
  await page.getByRole("tab", { name: "Nguồn" }).click();
  await expect(page.getByText("history.txt", { exact: false })).toBeVisible();
  await page.getByRole("tab", { name: "Thuốc" }).click();
  await page.getByRole("button", { name: "Chạy trợ lý AI" }).click();
  await expect.poll(async () => {
    return page.evaluate(async (id) => {
      const response = await fetch(`/api/v1/cases/${id}`, { credentials: "include" });
      const data = await response.json();
      return data.run?.status;
    }, caseId);
  }, { timeout: 180000, intervals: [3000] }).toBe("completed");
  await page.reload();
  await expect(page.locator(".med-table tbody tr")).toHaveCount(2);
  await page.locator(".med-table .source").first().click();
  await expect(page.getByRole("dialog", { name: "Nguồn và đoạn trích" })).toContainText("Thuốc B");
  await page.getByRole("button", { name: "Đóng panel" }).click();
  await login(page, /Minh/);
  await page.goto(`/cases/${caseId}/review`);
  await page.getByRole("button", { name: "Tạo bản nháp" }).click();
  await page.getByRole("button", { name: "Duyệt phiên bản", exact: true }).click();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Xác nhận duyệt" }).click();
  await expect(page.getByText("Đã duyệt", { exact: true })).toBeVisible();
});

test("live session error and responder inbox", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: /Hà/ }).click();
  await page.getByLabel("Mật khẩu demo").fill("incorrect-password");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByLabel("Mật khẩu demo").fill(password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.getByRole("heading", { name: "Nhiệm vụ của tôi" })).toBeVisible();
});
