import type { NextConfig } from "next";

// Backend FastAPI vẫn giữ nguyên; proxy same-origin để cookie phiên HttpOnly
// hoạt động ở cả chế độ dev (thay cho proxy của Vite) và `next start`.
const API_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_TARGET}/api/:path*` }];
  },
};

export default nextConfig;
