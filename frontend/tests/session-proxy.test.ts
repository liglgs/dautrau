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
  it("ignores browser role and server role tokens when forwarding a session", async () => {
    vi.stubEnv("NEXT_PUBLIC_VIGILENS_AUTH_MODE", "session");
    vi.stubEnv("VIGILENS_REVIEWER_TOKEN", "must-not-forward");
    const fetch = vi.fn().mockResolvedValue(Response.json({ role: "investigator" }));
    vi.stubGlobal("fetch", fetch);
    await GET(new NextRequest(`${origin}/api/backend/api/v1/auth/me`, { headers: { cookie: "session_id=verified", "X-Vigilens-Role": "reviewer" } }), context("auth/me"));
    expect(fetch.mock.calls[0][1].headers.Cookie).toBe("session_id=verified");
    expect(fetch.mock.calls[0][1].headers["X-API-Token"]).toBeUndefined();
  });
  it("rejects missing or foreign origins without contacting backend", async () => {
    vi.stubEnv("NEXT_PUBLIC_VIGILENS_AUTH_MODE", "session");
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    for (const headers of [{}, { origin: "https://foreign.example" }]) {
      expect((await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/logout`, { method: "POST", headers }), context("auth/logout"))).status).toBe(403);
    }
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each([null, [], { role: "reviewer" }, { token: 123 }, { token: " " }])("rejects malformed or role-only login: %j", async (body) => {
    const fetch = vi.fn(); vi.stubGlobal("fetch", fetch);
    const response = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/login`, { method: "POST", headers: { origin }, body: JSON.stringify(body) }), context("auth/login"));
    expect(response.status).toBe(422);
    expect(fetch).not.toHaveBeenCalled();
  });
  it("relays HttpOnly cookie without exposing session id in login response", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user_id: "reviewer", role: "reviewer", session_id: "private" }), { headers: { "Set-Cookie": "session_id=private; HttpOnly; Path=/; SameSite=lax" } }));
    vi.stubGlobal("fetch", fetch);
    const response = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/login`, { method: "POST", headers: { origin }, body: JSON.stringify({ token: "valid" }) }), context("auth/login"));
    expect(await response.json()).toEqual({ user_id: "reviewer", role: "reviewer" });
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });
  it("preserves expiry and logout cookie deletion from backend", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(Response.json({ error: { code: "unauthorized" } }, { status: 401 })).mockResolvedValueOnce(new Response('{"logged_out":true}', { headers: { "Set-Cookie": 'session_id=""; Max-Age=0; Path=/; HttpOnly' } })));
    expect((await GET(new NextRequest(`${origin}/api/backend/api/v1/auth/me`), context("auth/me"))).status).toBe(401);
    const logout = await POST(new NextRequest(`${origin}/api/backend/api/v1/auth/logout`, { method: "POST", headers: { origin } }), context("auth/logout"));
    expect(logout.headers.get("set-cookie")).toContain("Max-Age=0");
  });
});
