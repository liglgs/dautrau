import { test, expect } from "@playwright/test";

test("UI-01/UI-02 · ba màn chính ở desktop và mobile", async ({ page }, testInfo) => {
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/login");
    await page.getByRole("button", { name: /Linh · Người rà soát/ }).click();
    await expect(
      page.getByRole("heading", {
        name: "Bảng điều khiển Rà soát Thuốc Lâm sàng",
        exact: true,
      }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Danh sách ca", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Hồ sơ cần rà soát", exact: true }),
    ).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`cases-${width}.png`), fullPage: true });
    await page.getByRole("link", { name: /Mở ca/ }).first().click();
    await expect(page.getByRole("heading", { name: /Ca SIM-/ })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`workspace-${width}.png`), fullPage: true });
    await page.getByRole("link", { name: /Xem tổng hợp/ }).click();
    await expect(page.getByRole("heading", { name: "Tổng hợp và duyệt" })).toBeVisible();
    if (!(await page.getByTestId("review-snapshot").isVisible().catch(() => false))) {
      await page.getByRole("button", { name: "Tạo bản nháp" }).click();
      await expect(page.getByTestId("review-snapshot")).toBeVisible();
    }
    await page.screenshot({ path: testInfo.outputPath(`review-${width}.png`), fullPage: true });
  }
});
