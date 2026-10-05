import type { NextRequest } from "next/server";

/**
 * Cầu nối server-side tới backend FastAPI.
 *
 * API mặc định chuyển cookie session và kiểm tra Origin cho thao tác ghi.
 * Chế độ token theo role browser chỉ dành cho fixture/demo local.
 */

const API_BASE = (process.env.VIGILENS_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const ROLE_TOKENS: Record<string, string | undefined> = {
  investigator: process.env.VIGILENS_INVESTIGATOR_TOKEN,
  reviewer: process.env.VIGILENS_REVIEWER_TOKEN,
};

const ROLE_HEADER = "x-vigilens-role";

/** Thời gian chờ tối đa cho một lượt gọi backend, tránh treo route khi backend không phản hồi. */
const UPSTREAM_TIMEOUT_MS = 30_000;

function resolveToken(role: string | null): { token?: string; reason?: string } {
  if (role !== "investigator" && role !== "reviewer") {
    return { reason: `vai trò không hợp lệ: ${role ?? "(thiếu header)"}` };
  }
  const token = ROLE_TOKENS[role];
  if (!token) return { reason: `chưa cấu hình token cho vai trò ${role}` };
  return { token };
}

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const tokenMode = process.env.NEXT_PUBLIC_VIGILENS_AUTH_MODE === "token";
  const authRoute = path.join("/").startsWith("api/v1/auth/");
  const mutating = !["GET", "HEAD", "OPTIONS"].includes(request.method);
  if (!tokenMode && mutating) {
    const origin = request.headers.get("origin");
    const expectedOrigin = `${request.nextUrl.protocol}//${request.headers.get("host") ?? request.nextUrl.host}`;
    if (!origin || origin !== expectedOrigin) {
      return Response.json({ error: { code: "csrf_rejected", message: "Yêu cầu phải xuất phát từ cùng trang web." } }, { status: 403 });
    }
  }
  const { token, reason } = tokenMode && !authRoute ? resolveToken(request.headers.get(ROLE_HEADER)) : {};
  if (tokenMode && !authRoute && !token) {
    console.error(`[vigilens-proxy] cấu hình sai: ${reason}`);
    return Response.json({ error: { code: "proxy_misconfigured", message: "Cầu nối chưa được cấu hình đúng." } }, { status: 500 });
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
    ...(token ? { "X-API-Token": token } : {}),
    Accept: request.headers.get("accept") ?? "application/json",
  };
  if (!tokenMode) {
    const session = request.cookies.get("session_id")?.value;
    if (session) headers.Cookie = `session_id=${encodeURIComponent(session)}`;
  }
  const contentType = request.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;

  const method = request.method.toUpperCase();
  let body =
    method === "GET" || method === "HEAD" || method === "OPTIONS" ? undefined : await request.text();

  if (!tokenMode && path.join("/") === "api/v1/auth/login") {
    let login: unknown;
    try {
      login = JSON.parse(body ?? "{}");
    } catch {
      return Response.json({ error: { code: "invalid_request", message: "Yêu cầu đăng nhập không hợp lệ." } }, { status: 422 });
    }
    // Backend also accepts an unverified role; the web gateway only allows verified token login.
    if (!login || typeof login !== "object" || !("token" in login) || typeof login.token !== "string" || !login.token.trim()) {
      return Response.json({ error: { code: "invalid_request", message: "Cần token đăng nhập hợp lệ." } }, { status: 422 });
    }
    body = JSON.stringify({ token: login.token.trim() });
  }
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

  let text = await upstream.text();
  if (authRoute && upstream.ok && path.at(-1) === "login") {
    const payload = JSON.parse(text);
    text = JSON.stringify({ user_id: payload.user_id, role: payload.role });
  }
  const responseHeaders = new Headers({
    "Content-Type": upstream.headers.get("content-type") ?? "application/json",
    "Cache-Control": "no-store",
  });
  if (!tokenMode && authRoute) {
    for (const cookie of upstream.headers.getSetCookie()) {
      if (cookie.startsWith("session_id=")) responseHeaders.append("Set-Cookie", request.nextUrl.protocol === "https:" ? `${cookie}; Secure` : cookie);
    }
  }
  return new Response(text, { status: upstream.status, headers: responseHeaders });
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
