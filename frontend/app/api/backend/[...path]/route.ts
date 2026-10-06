import type { NextRequest } from "next/server";

/**
 * Cầu nối server-side tới backend FastAPI.
 *
 * AUTH-01: trước đây cầu nối có một "chế độ token" lấy vai từ header do **trình duyệt** khai
 * (`X-Vigilens-Role`) rồi gắn token vai trò ở phía máy chủ. Chỉ cần đổi header trong trình duyệt
 * là đổi được quyền — cùng một lỗi với việc đăng nhập tự khai vai, chỉ khác đường vào. Chế độ đó
 * đã bị gỡ hẳn.
 *
 * Nay cầu nối chỉ **chuyển tiếp danh tính đã có sẵn**:
 *   * cookie phiên `session_id` (chế độ nội bộ), hoặc
 *   * header `Authorization` (chế độ Supabase, trình duyệt giữ access token).
 *
 * Cầu nối không tự tạo, không tự chọn, và không nâng quyền cho bất kỳ ai.
 */

const API_BASE = (process.env.VIGILENS_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/** Thời gian chờ tối đa cho một lượt gọi backend, tránh treo route khi backend không phản hồi. */
const UPSTREAM_TIMEOUT_MS = 30_000;

/** Tuyến xác thực: chuyển tiếp nguyên vẹn, không viết lại thân yêu cầu hay thân phản hồi. */
const AUTH_ROUTE_PREFIX = "api/v1/auth/";

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const joined = path.join("/");
  const authRoute = joined.startsWith(AUTH_ROUTE_PREFIX);
  const mutating = !["GET", "HEAD", "OPTIONS"].includes(request.method);
  if (mutating) {
    const origin = request.headers.get("origin");
    const expectedOrigin = `${request.nextUrl.protocol}//${request.headers.get("host") ?? request.nextUrl.host}`;
    if (!origin || origin !== expectedOrigin) {
      return Response.json({ error: { code: "csrf_rejected", message: "Yêu cầu phải xuất phát từ cùng trang web." } }, { status: 403 });
    }
  }
  // Chỉ cho phép đúng nhánh API của backend, không mở proxy tới mọi tuyến.
  if (path[0] !== "api" || path[1] !== "v1") {
    return Response.json(
      { error: { code: "proxy_path_rejected", message: "Cầu nối chỉ phục vụ các tuyến /api/v1/* của backend." } },
      { status: 404 },
    );
  }

  const target = `${API_BASE}/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const headers: Record<string, string> = {
    Accept: request.headers.get("accept") ?? "application/json",
  };
  const session = request.cookies.get("session_id")?.value;
  if (session) headers.Cookie = `session_id=${encodeURIComponent(session)}`;
  const authorization = request.headers.get("authorization");
  if (authorization) headers.Authorization = authorization;
  const contentType = request.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const method = request.method.toUpperCase();
  const body =
    method === "GET" || method === "HEAD" || method === "OPTIONS" ? undefined : await request.text();

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch (cause) {
    console.error(`[vigilens-proxy] không gọi được backend (${API_BASE}):`, cause);
    return Response.json(
      {
        error: {
          code: "backend_unreachable",
          message: "Không gọi được backend. Kiểm tra log máy chủ.",
        },
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers({
    "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    "Cache-Control": "no-store",
  });
  if (authRoute) {
    for (const cookie of upstream.headers.getSetCookie()) {
      if (cookie.startsWith("session_id=")) {
        // Đừng lặp thuộc tính: upstream đã đặt `Secure` khi chạy sau HTTPS thì giữ nguyên.
        const alreadySecure = /(^|;)\s*secure\s*(;|$)/i.test(cookie);
        const needsSecure = request.nextUrl.protocol === "https:" && !alreadySecure;
        responseHeaders.append("Set-Cookie", needsSecure ? `${cookie}; Secure` : cookie);
      }
    }
  }
  return new Response(await upstream.text(), { status: upstream.status, headers: responseHeaders });
}

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}
