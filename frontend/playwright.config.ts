import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: { baseURL: "http://127.0.0.1:3102", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "node node_modules/next/dist/bin/next dev -p 3102 -H 127.0.0.1",
    url: "http://127.0.0.1:3102",
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      NEXT_DIST_DIR: ".next/e2e",
      NEXT_PUBLIC_VIGILENS_DATA_MODE: "api",
    },
  },
});
