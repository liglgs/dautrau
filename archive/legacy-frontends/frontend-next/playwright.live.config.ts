import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/live",
  fullyParallel: false,
  workers: 1,
  timeout: 240000,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    browserName: "chromium",
    channel: "chromium",
  },
  webServer: {
    command: "npm run dev",
    env: { VITE_API_MODE: "live" },
    url: "http://127.0.0.1:5173",
    reuseExistingServer: true,
  },
});
