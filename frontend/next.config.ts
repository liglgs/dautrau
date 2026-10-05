import type { NextConfig } from "next";

const previewOrigins =
  process.env.NEXT_ALLOWED_DEV_ORIGINS?.split(",")
    .map((origin) => origin.trim())
    .filter(Boolean) ?? [];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Browser suites compile different public data/auth modes. Give each suite
  // its own cache so a previous run cannot leak compile-time NEXT_PUBLIC_* values.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // Hostname công khai của bản xem trước (chỉ khai qua biến môi trường, không hard-code).
  allowedDevOrigins: previewOrigins,
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
