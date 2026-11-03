import "server-only";
import { internalToken, serviceUrl, type ServiceName } from "./config";

export class ServiceError extends Error {
  constructor(
    public readonly service: ServiceName,
    public readonly status: number,
    message: string,
    /** The service's own error type when it reports one, e.g. "AllProvidersFailedError". */
    public readonly type: string | null = null,
  ) {
    super(message);
  }
}

/** Services report errors as {detail} (FastAPI) or {error: {type, message}} (AI Core); accept both. */
function errorDetail(data: unknown, fallback: string): string {
  if (data && typeof data === "object") {
    const d = data as { detail?: unknown; error?: { message?: unknown } };
    if (typeof d.detail === "string") return d.detail;
    if (d.error && typeof d.error.message === "string") return d.error.message;
  }
  return fallback;
}

function errorType(data: unknown): string | null {
  const e = data && typeof data === "object" ? (data as { error?: unknown }).error : null;
  if (typeof e === "string") return e;
  if (e && typeof e === "object" && typeof (e as { type?: unknown }).type === "string") return (e as { type: string }).type;
  return null;
}

interface CallOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  /** Verified user id, forwarded as X-User-Id; services trust it only because the edge token vouches for us. */
  userId?: string;
  timeoutMs?: number;
}

/** One server-to-server call to a domain service, with the internal token and a timeout. */
export async function callService<T>(service: ServiceName, path: string, opts: CallOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token = internalToken();
  if (token) headers["X-Internal-Token"] = token;
  if (opts.userId) headers["X-User-Id"] = opts.userId;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(`${serviceUrl(service)}${path}`, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(opts.timeoutMs ?? 10_000),
    });
  } catch (err) {
    const reason = err instanceof Error && err.name === "TimeoutError" ? "timed out" : "is unreachable";
    throw new ServiceError(service, 503, `${service} service ${reason}`);
  }
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) {
    throw new ServiceError(service, res.status, errorDetail(data, text || res.statusText).slice(0, 300), errorType(data));
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/** Collections come back either as a bare array or as {items: [...]}; normalise to the array. */
export function itemsOf<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === "object" && Array.isArray((payload as { items?: unknown }).items)) {
    return (payload as { items: T[] }).items;
  }
  return [];
}

const workspaceCache = new Map<string, { id: string | null; at: number }>();
const WORKSPACE_TTL_MS = 60_000;

/**
 * Each domain service keeps its own workspaces, keyed by organisation. Resolve the caller's organisation to that
 * service's workspace (the first one; the console works in one workspace per organisation). Cached briefly.
 */
export async function workspaceFor(service: ServiceName, organizationId: string): Promise<string | null> {
  const key = `${service}:${organizationId}`;
  const hit = workspaceCache.get(key);
  if (hit && Date.now() - hit.at < WORKSPACE_TTL_MS) return hit.id;
  const list = itemsOf<{ id: string }>(
    await callService(service, `/api/v1/workspaces?organization_id=${encodeURIComponent(organizationId)}`),
  );
  const id = list[0]?.id ?? null;
  workspaceCache.set(key, { id, at: Date.now() });
  return id;
}
