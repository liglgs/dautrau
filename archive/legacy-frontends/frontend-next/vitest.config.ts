import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Vitest chạy độc lập với Next (jsdom + Testing Library), giữ nguyên
// bộ unit test hiện có: tests/components.test.tsx, tests/domain.test.ts.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
  },
});
