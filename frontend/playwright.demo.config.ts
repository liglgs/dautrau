import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  testDir: "./demo",
  outputDir: "./test-results/demo-recording",
  timeout: 120_000,
  use: {
    ...base.use,
    viewport: { width: 1440, height: 900 },
    video: { mode: "on", size: { width: 1440, height: 900 } },
  },
  projects: [{ name: "chromium" }],
});
