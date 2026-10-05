import { test, expect } from "@playwright/test";

async function login(page: import("@playwright/test").Page) {
  const password = process.env.DEMO_PASSWORD;
  await page.goto("/login");
  await page.getByRole("button", { name: /Linh · Người rà soát/ }).click();
  await page.getByLabel("Mật khẩu demo").fill(password!);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.getByRole("heading", { name: "Hồ sơ cần rà soát" })).toBeVisible();
  await expect(page.getByText("SIM-001").first()).toBeVisible();
}

test("live: session server và ca thật", async ({ page }) => {
  test.skip(!process.env.DEMO_PASSWORD, "Set DEMO_PASSWORD for live integration test");
  await login(page);
  await page.getByRole("link", { name: /Mở ca/ }).first().click();
  await expect(page.getByRole("heading", { name: "Ca SIM-001" })).toBeVisible();
});

test("live: thiếu khóa model không thành công giả", async ({ page }) => {
  test.skip(!process.env.DEMO_PASSWORD || process.env.EXPECT_MODEL_UNAVAILABLE !== "1", "Run only without a configured model key");
  await login(page);
  await page.getByRole("link", { name: /Mở ca/ }).first().click();
  await page.getByRole("button", { name: "Chạy trợ lý AI" }).click();
  await expect(page.getByText("Lỗi xử lý")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Chưa có dữ kiện được trích xuất.")).toBeVisible();
});
