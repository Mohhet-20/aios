// The one fetch wrapper every console hook goes through. It talks only to this app's own edge (/api/...), which
// holds the session in httpOnly cookies and calls the domain services server-side, so the browser never sees a
// token or a service URL.

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public service?: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: { method?: "GET" | "POST"; body?: unknown }): Promise<T> {
  const res = await fetch(path, {
    method: init?.method ?? "GET",
    credentials: "same-origin",
    headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/")) {
    window.location.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
  }
  if (!res.ok) {
    const d = (data ?? {}) as { detail?: string; error?: string; service?: string };
    throw new ApiError(d.detail ?? d.error ?? `Request failed (${res.status})`, res.status, d.service);
  }
  return data as T;
}
