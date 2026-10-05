import { test, expect } from "@playwright/test";
test("T01 · chọn tài khoản, tìm ca, mở và tải lại giữ URL/bộ lọc", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Linh · Người rà soát" }).click();
  // Sau đăng nhập app chuyển tới /dashboard (đồng bộ bản Vite); sang /cases để kiểm tra danh sách ca.
  await expect(
    page.getByRole("heading", { name: "Bảng điều khiển Rà soát Thuốc Lâm sàng" }),
  ).toBeVisible();
  await page.goto("/cases");
  await expect(
    page.getByRole("heading", { name: "Hồ sơ cần rà soát" }),
  ).toBeVisible();
  await page.getByLabel("Tìm theo mã ca").fill("SIM-002");
  await page.getByRole("link", { name: "Mở ca →" }).click();
  await expect(page.getByRole("heading", { name: "Ca SIM-002" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Ca SIM-002" })).toBeVisible();
  await page.getByRole("link", { name: "← Danh sách ca" }).click();
  await expect(page.getByLabel("Tìm theo mã ca")).toHaveValue("SIM-002");
  await page.getByLabel("Tìm theo mã ca").fill("KHONG-CO");
  await expect(page.getByText("Không có ca phù hợp bộ lọc.")).toBeVisible();
});
