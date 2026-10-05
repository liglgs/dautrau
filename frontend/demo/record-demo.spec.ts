import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { workspace } from "../e2e/fixture";

/** A browser recording of actual UI actions against explicitly synthetic contract responses. */
test("record synthetic investigator and reviewer walkthrough", async ({ page, context }) => {
  const assets = path.resolve(process.cwd(), "../docs/demo_assets");
  const output = path.resolve(process.cwd(), "../presentation");
  await mkdir(assets, { recursive: true });
  await mkdir(output, { recursive: true });
  const started = Date.now();
  const chapters: { seconds: number; title: string }[] = [];
  const chapter = async (title: string, screenshot?: string) => {
    chapters.push({ seconds: Math.round((Date.now() - started) / 1000), title });
    await page.evaluate((label) => {
      let caption = document.getElementById("fixture-recording-disclosure");
      if (!caption) {
        caption = document.createElement("aside");
        caption.id = "fixture-recording-disclosure";
        caption.style.cssText = "position:fixed;bottom:0;left:0;right:0;z-index:9999;background:#fff3cd;color:#533f00;padding:10px 18px;font:600 15px sans-serif;border-top:1px solid #d8bd64;pointer-events:none";
        document.body.append(caption);
      }
      caption.textContent = `DEMO UI · API fixture · thuốc hư cấu · ${label}`;
    }, title);
    // Deliberate pacing for a recording, not a synchronisation condition for tests.
    await page.waitForTimeout(3500);
    if (screenshot) await page.screenshot({ path: path.join(assets, screenshot) });
  };

  const calls = await workspace(page, { role: "investigator", conflict: true });
  await page.goto("/app/investigations/new");
  await page.getByLabel("Câu nhận định cần kiểm chứng").fill("Synthetic claim");
  await page.getByLabel("Hoạt chất *", { exact: true }).fill("TestDrug");
  await page.getByLabel("Biến cố bất lợi *").fill("TestEvent");
  await chapter("Tạo nhận định kiểm thử, nguồn và ngân sách theo API", "01-claim.png");
  await page.getByRole("button", { name: "Bắt đầu điều tra", exact: true }).click();
  await expect(page).toHaveURL(/fixture-1$/);
  await expect(page.getByText("Lý do: Frozen event survives refresh", { exact: true })).toBeVisible();
  await chapter("Tiến trình được trả từ contract fixture", "02-timeline.png");

  await page.goto("/app/investigations/fixture-1/evidence");
  await page.getByLabel("Chọn e1", { exact: true }).check();
  await page.getByLabel("Chọn e2", { exact: true }).check();
  await page.getByRole("button", { name: /So sánh mâu thuẫn/ }).click();
  await page.getByRole("region", { name: "So sánh bằng chứng" }).scrollIntoViewIfNeeded();
  await chapter("Đối chiếu người lớn và trẻ em ở hai cột", "03-scope.png");
  await page.getByRole("button", { name: "[e1]", exact: true }).first().click();
  await expect(page.locator("mark")).toHaveText("second quote");
  await chapter("Đoạn nguyên văn và locator Unicode", "04-quote.png");
  await page.getByRole("button", { name: "Đóng", exact: true }).click();

  await page.goto("/app/investigations/fixture-1/dossier");
  await expect(page.getByRole("button", { name: "Xuất .md" })).toBeDisabled();
  await chapter("Hồ sơ chưa duyệt không xuất được qua UI");
  await page.goto("/app/settings");
  await page.getByLabel("Vai trò", { exact: true }).selectOption("reviewer");
  await chapter("Đổi vai trò minh họa trong cài đặt, chưa phải đăng nhập thật");
  await page.goto("/app/investigations/fixture-1/review");
  await page.getByLabel("Lý do (ít nhất 15 ký tự)").fill("Đã đối chiếu hai phạm vi và đoạn nguồn của fixture kỹ thuật.");
  await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
  await expect(page.getByText("Phiên bản đã thay đổi", { exact: true })).toBeVisible();
  await chapter("409 giữ nội dung reviewer đã nhập", "05-version-conflict.png");
  await page.getByRole("button", { name: "Tải phiên bản mới" }).click();
  await expect(page.getByText(/Phiên bản đang xem: v4/)).toBeVisible();
  await chapter("Reviewer đọc phiên bản mới trước khi gửi lại");
  await page.getByRole("button", { name: "Gửi quyết định", exact: true }).click();
  await expect(page.getByText("Fixture decision recorded")).toBeVisible();
  await page.goto("/app/investigations/fixture-1/dossier");
  await expect(page.getByRole("button", { name: "Xuất .md" })).toBeEnabled();
  await page.getByRole("button", { name: "Xuất .md" }).scrollIntoViewIfNeeded();
  await chapter("Phê duyệt fixture và tải hồ sơ Markdown", "06-approved.png");
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Xuất .md" }).click();
  const dossier = await download;
  await dossier.saveAs(path.join(assets, "approved-fixture-dossier.md"));
  await chapter("Chưa kiểm chứng nguồn live, model, session hay quyền server");

  expect(calls.filter((call) => call.path.endsWith("/reviews")).map((call) => call.body?.expected_version)).toEqual([3, 4]);
  const video = page.video();
  expect(video).not.toBeNull();
  await context.close();
  await video!.saveAs(path.join(output, "person4_ui_fixture_demo.webm"));
  await writeFile(path.join(output, "person4_ui_fixture_demo.chapters.json"), JSON.stringify({
    synthetic: true,
    mode: "browser_contract_fixture",
    audio: false,
    note: "UI recording, not live backend/model/auth verification. Times are approximate navigation markers.",
    chapters,
  }, null, 2) + "\n", "utf8");
});
