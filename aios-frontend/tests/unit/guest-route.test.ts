// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";

const writeSessionCookies = vi.hoisted(() => vi.fn(async () => {}));
vi.mock("@/lib/server/session", () => ({ writeSessionCookies }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  writeSessionCookies.mockClear();
});

async function post() {
  const { POST } = await import("@/app/api/auth/guest/route");
  return POST(new Request("http://console.test/api/auth/guest", { method: "POST", body: "{}" }));
}

describe("POST /api/auth/guest", () => {
  it("is not found unless the deployment enables guest access", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    expect((await post()).status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("asks identity for the guest session, behind the internal token, and sets the session cookies", async () => {
    vi.stubEnv("AIOS_GUEST_ACCESS", "true");
    vi.stubEnv("AIOS_INTERNAL_TOKEN", "edge-token-0123456789-0123456789-xx");
    const tokens = { user: { id: "u", email: "guest@northwind.example", display_name: "Guest" }, access_token: "a", refresh_token: "r" };
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(tokens), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const res = await post();
    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/auth\/guest$/);
    expect(new Headers(init.headers).get("x-internal-token")).toBe("edge-token-0123456789-0123456789-xx");
    expect(writeSessionCookies).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(await res.json())).not.toContain("access_token");
  });

  it("answers 503, not a token, when identity refuses (for example an administrator configured as the guest)", async () => {
    vi.stubEnv("AIOS_GUEST_ACCESS", "true");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: "AuthorizationError", detail: "no" }), { status: 403 })));
    const res = await post();
    expect(res.status).toBe(503);
    expect(writeSessionCookies).not.toHaveBeenCalled();
  });
});
