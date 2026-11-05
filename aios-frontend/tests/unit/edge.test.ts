// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "@/proxy";
import { safeNextPath } from "@/lib/safe-next";
import { callService, itemsOf, ServiceError } from "@/lib/server/services";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("proxy (route protection)", () => {
  it("redirects a signed-out visitor to /login and remembers the page", () => {
    const res = proxy(new NextRequest("http://console.test/agents"));
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toBe("http://console.test/login?next=%2Fagents");
  });

  it("lets a request with a session cookie through (the API verifies the token itself)", () => {
    const req = new NextRequest("http://console.test/agents", { headers: { cookie: "aios_rt=opaque" } });
    expect(proxy(req).headers.get("location")).toBeNull();
  });
});

describe("safeNextPath", () => {
  it.each(["/agents", "/models/playground?x=1"])("keeps same-site path %s", (p) => {
    expect(safeNextPath(p)).toBe(p);
  });

  it.each(["https://evil.example", "//evil.example", "/\\evil.example", "agents", "", undefined])(
    "rejects %s",
    (p) => {
      expect(safeNextPath(p)).toBe("/dashboard");
    },
  );
});

describe("callService", () => {
  function stubFetch(status: number, body: unknown) {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status }));
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("sends the internal token and the verified user id, never anything from the browser", async () => {
    vi.stubEnv("AIOS_INTERNAL_TOKEN", "edge-token-0123456789-0123456789-xx");
    const fetchMock = stubFetch(200, { ok: true });
    await callService("agent", "/api/v1/agents?workspace_id=w", { userId: "u-1" });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://127.0.0.1:8003/api/v1/agents?workspace_id=w");
    expect(init.headers).toMatchObject({ "X-Internal-Token": "edge-token-0123456789-0123456789-xx", "X-User-Id": "u-1" });
  });

  it("reads FastAPI's {detail} errors", async () => {
    stubFetch(404, { detail: "workspace not found" });
    await expect(callService("tool", "/x")).rejects.toMatchObject({ status: 404, message: "workspace not found" });
  });

  it("reads AI Core's {error: {type, message}} errors and keeps the type", async () => {
    stubFetch(503, { error: { type: "AllProvidersFailedError", message: "All 3 candidate(s) failed" } });
    const err = await callService("ai-core", "/v1/generate").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ServiceError);
    expect(err).toMatchObject({ status: 503, type: "AllProvidersFailedError", message: "All 3 candidate(s) failed" });
  });

  it("reports an unreachable service as 503 without leaking the URL", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("fetch failed"))));
    const err = (await callService("memory", "/x").catch((e: unknown) => e)) as ServiceError;
    expect(err.status).toBe(503);
    expect(err.message).toBe("memory service is unreachable");
  });
});

describe("itemsOf", () => {
  it("accepts bare arrays and {items} pages", () => {
    expect(itemsOf([1, 2])).toEqual([1, 2]);
    expect(itemsOf({ items: [3], total: 1 })).toEqual([3]);
    expect(itemsOf({ error: "x" })).toEqual([]);
  });
});

describe("serviceUrl", () => {
  it("defaults to the local development ports", async () => {
    const { serviceUrl } = await import("@/lib/server/config");
    expect(serviceUrl("identity")).toBe("http://127.0.0.1:8008");
  });

  it("puts every service under one host when AIOS_SERVICES_BASE_URL is set; a per-service URL still wins", async () => {
    vi.stubEnv("AIOS_SERVICES_BASE_URL", "https://aios-demo-api.example/svc/");
    const { serviceUrl } = await import("@/lib/server/config");
    expect(serviceUrl("ai-core")).toBe("https://aios-demo-api.example/svc/ai-core");
    vi.stubEnv("AIOS_IDENTITY_URL", "http://identity.internal:8008/");
    expect(serviceUrl("identity")).toBe("http://identity.internal:8008");
  });
});
