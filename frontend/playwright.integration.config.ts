import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

// Real local HTTP backend/SQLite/graph; sources and LLM are explicitly synthetic.
const python = process.env.PERSON4_TEST_PYTHON ?? path.resolve("../.tools/venv/Scripts/python.exe");
export default defineConfig({
  testDir: "./integration",
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  use: { baseURL: "http://127.0.0.1:3103", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `"${python}" -X utf8 ../scripts/run_person4_integration.py --port 8203`,
      url: "http://127.0.0.1:8203/health", reuseExistingServer: false, timeout: 60_000,
    },
    {
      command: "node node_modules/next/dist/bin/next dev -p 3103 -H 127.0.0.1",
      url: "http://127.0.0.1:3103", reuseExistingServer: false, timeout: 120_000,
      env: {
        NEXT_DIST_DIR: ".next/integration",
        NEXT_PUBLIC_VIGILENS_DATA_MODE: "api", VIGILENS_API_BASE: "http://127.0.0.1:8203",
      },
    },
  ],
});
