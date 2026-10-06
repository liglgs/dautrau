import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET, POST } from "@/app/api/backend/[...path]/route";

const origin = "http://localhost:3103";
const context = (endpoint: string) => ({ params: Promise.resolve(["api", "v1", ...endpoint.split("/")]).then((path) => ({ path })) });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("session gateway", () => {
  it("uses actual request host when Next normalizes loopback URLs", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ logged_out: true })));
    const response = await POST(new NextRequest("http://localhost:3103/api/backend/api/v1/auth/logout", { method: "POST", headers: { host: "127.0.0.1:3103", origin: "http://127.0.0.1:3103" } }), context("auth/logout"));
    expect(response.status).toBe(200);
  });
  it("ignores a browser-declared role and never forwards a server role token", async () => {
    // AUTH-01: the bridge used to trust `X-Vigilens-Role` and swap in a server token. It must not,
    // and it must never read the role tokens from the environment at all.
    vi.stubEnv("VIGILENS_REVIEWER_TOKEN", "must-not-forward");
    vi.stubEnv("VIGILENS_INVESTIGATOR_TOKEN", "must-not-forward-either");
    const fetch = vi.fn().mockResolvedValue(Response.json({ role: "investigator" }));
    vi.stubGlobal("fetch", fetch);
    await GET(new NextRequest(`${origin}/api/backend/api/v1/auth/me`, { headers: { cookie: "session_id=verified", "X-Vigilens-Role": "reviewer", "X-API-Token": "must-not-forward" } }), context("auth/me"));
    expect(fetch.mock.calls[0][1].headers.Cookie).toBe("session_id=verified");
    expect(fetch.mock.calls[0][1].headers["X-API-Token"]).toBeUndefined();
    expect(fetch.mock.calls[0][1].headers["X-Vigilens-Role"]).toBeUndefined();
  });
  it("forwards the Authorization header for the Supabase provider", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ role: "reviewer" }));
    vi.stubGlobal("fetch", fetch);
    await GET(new NextRequest(`${origin}/api/backend/api/v1/auth/me`, { headers: { authorization: "Bearer access-token" } }), context("auth/me"));
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe("Bearer access-token");
  });
  it("rejects missing or foreign origins without contacting backend", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    for (const headers of [{}, { origin: "https://foreign.example" }]) {
      expect((await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/logout`, { method: "POST", headers }), context("auth/logout"))).status).toBe(403);
    }
    expect(fetch).not.toHaveBeenCalled();
  });
  it("passes the login body straight through so the backend is the only validator", async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ user_id: "u1", role: "reviewer" }));
    vi.stubGlobal("fetch", fetch);
    const body = { email: "duyet@benhvien.vn", password: "mat-khau-that" };
    const response = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/login`, { method: "POST", headers: { origin }, body: JSON.stringify(body) }), context("auth/login"));
    expect(response.status).toBe(200);
    expect(fetch.mock.calls[0][1].body).toBe(JSON.stringify(body));
  });
  it("does not turn a role-only login body into a session", async () => {
    // The backend answers 422 for these; the bridge must not invent a credential before forwarding.
    const fetch = vi.fn().mockResolvedValue(Response.json({ error: { code: "validation_error" } }, { status: 422 }));
    vi.stubGlobal("fetch", fetch);
    const response = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/login`, { method: "POST", headers: { origin }, body: JSON.stringify({ role: "reviewer" }) }), context("auth/login"));
    expect(response.status).toBe(422);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(response.headers.get("set-cookie")).toBeNull();
  });
  it("relays the HttpOnly cookie without rewriting the login response", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user_id: "reviewer", role: "reviewer" }), { headers: { "Set-Cookie": "session_id=private; HttpOnly; Path=/; SameSite=lax" } }));
    vi.stubGlobal("fetch", fetch);
    const response = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/login`, { method: "POST", headers: { origin }, body: JSON.stringify({ email: "duyet@benhvien.vn", password: "mat-khau-that" }) }), context("auth/login"));
    expect(await response.json()).toEqual({ user_id: "reviewer", role: "reviewer" });
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });
  it("preserves expiry and logout cookie deletion from backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(Response.json({ error: { code: "unauthorized" } }, { status: 401 })).mockResolvedValueOnce(new Response('{"logged_out":true}', { headers: { "Set-Cookie": 'session_id=""; Max-Age=0; Path=/; HttpOnly' } })));
    expect((await GET(new NextRequest(`${origin}/api/backend/api/v1/auth/me`), context("auth/me"))).status).toBe(401);
    const logout = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/logout`, { method: "POST", headers: { origin } }), context("auth/logout"));
    expect(logout.headers.get("set-cookie")).toContain("Max-Age=0");
  });
  it("does not repeat the Secure attribute when the backend already set it", async () => {
    // The bridge used to append `; Secure` unconditionally on https, producing a duplicate attribute.
    const upstream = new Response('{"logged_out":true}', { headers: { "Set-Cookie": "session_id=abc; HttpOnly; Path=/; Secure" } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(upstream));
    const response = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/logout`, { method: "POST", headers: { origin } }), context("auth/logout"));
    const cookie = response.headers.get("set-cookie") ?? "";
    expect(cookie.match(/secure/gi) ?? []).toHaveLength(1);
  });
  it("refuses to proxy anything outside /api/v1/*", async () => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const response = await GET(new NextRequest(`${origin}/api/backend/health`, { headers: { origin } }), { params: Promise.resolve({ path: ["health"] }) });
    expect(response.status).toBe(404);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("answers 502 instead of hanging when the backend is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("ECONNREFUSED")));
    const response = await GET(new NextRequest(`${origin}/api/backend/api/v1/investigations`), context("investigations"));
    expect(response.status).toBe(502);
    expect((await response.json()).error.code).toBe("backend_unreachable");
  });
});
