import { createMockSource } from "@/lib/api/mock";
import { createApiSource } from "@/lib/api/real";
import type { DataSource } from "@/lib/api/types";

export type DataMode = "mock" | "api";

export const DATA_MODE: DataMode = process.env.NEXT_PUBLIC_VIGILENS_DATA_MODE === "api" ? "api" : "mock";

let cached: DataSource | null = null;

/** Nguồn dữ liệu đang dùng. Đổi bằng biến môi trường `NEXT_PUBLIC_VIGILENS_DATA_MODE`. */
export function getDataSource(): DataSource {
  if (!cached) cached = DATA_MODE === "api" ? createApiSource() : createMockSource();
  return cached;
}

export type { DataSource } from "@/lib/api/types";
