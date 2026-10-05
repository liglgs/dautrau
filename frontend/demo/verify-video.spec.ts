import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "@playwright/test";

test("saved fixture video decodes and plays through its final frames", async ({ browser }, testInfo) => {
  const file = path.resolve(process.cwd(), "../presentation/person4_ui_fixture_demo.webm");
  const bytes = await readFile(file);
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  try {
    const page = await context.newPage();
    await page.setContent(`<body style="margin:0;background:black"><video controls muted style="width:100%;height:100%" src="data:video/webm;base64,${bytes.toString("base64")}"></video></body>`);
    await expect.poll(() => page.evaluate(() => {
      const video = document.querySelector("video")!;
      return video.readyState >= 2 && Number.isFinite(video.duration);
    })).toBe(true);
    const metadata = await page.evaluate(() => {
      const video = document.querySelector("video")!;
      return { duration_seconds: video.duration, width: video.videoWidth, height: video.videoHeight };
    });
    expect(metadata.width).toBe(1440);
    expect(metadata.height).toBe(900);
    expect(metadata.duration_seconds).toBeGreaterThan(40);
    expect(metadata.duration_seconds).toBeLessThan(300);
    for (const seconds of [10, 24, metadata.duration_seconds - 3]) {
      await page.evaluate((time) => new Promise<void>((resolve, reject) => {
        const video = document.querySelector("video")!;
        video.addEventListener("seeked", () => resolve(), { once: true });
        video.addEventListener("error", () => reject(new Error("Video decode failed")), { once: true });
        video.currentTime = time;
      }), seconds);
      await page.locator("video").screenshot({ path: testInfo.outputPath(`frame-${Math.round(seconds)}.png`) });
    }
    await page.evaluate(() => document.querySelector("video")!.play());
    await expect.poll(() => page.evaluate(() => document.querySelector("video")!.ended), { timeout: 7000 }).toBe(true);
    await writeFile(path.resolve(file, "../person4_ui_fixture_demo.media.json"), JSON.stringify({
      ...metadata,
      sha256: createHash("sha256").update(bytes).digest("hex"),
      browser_decode: "passed",
      has_audio: false,
      synthetic: true,
      scope: "Saved video decodes in Chromium, seeks to three positions and plays to end. Not live-system verification.",
    }, null, 2) + "\n", "utf8");
  } finally {
    await context.close();
  }
});
