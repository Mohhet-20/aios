import "server-only";

/**
 * Edge (backend-for-frontend) configuration. Read on the server only: nothing here reaches the browser bundle.
 *
 *   AIOS_<SERVICE>_URL      base URL of each domain service (defaults: the local ports scripts/dev.py uses)
 *   AIOS_SERVICES_BASE_URL  all services behind one host as <base>/<service> (the hosted demo's single process);
 *                           a per-service AIOS_<SERVICE>_URL still wins
 *   AIOS_INTERNAL_TOKEN     service-to-service token sent as X-Internal-Token (services enforce it when set)
 *   AIOS_JWT_SECRET         the identity service's signing key, to verify access tokens locally
 *   AIOS_GUEST_ACCESS       "true" on a hosted public demo: the sign-in page offers "Explore the live demo"
 *                           (the identity service's /auth/guest; no password is ever shown)
 */

export const SERVICES = {
  backend: { port: 8000, label: "Core backend" },
  "ai-core": { port: 8001, label: "AI Core & LLM gateway" },
  prompt: { port: 8002, label: "Prompt platform" },
  agent: { port: 8003, label: "Agent platform" },
  memory: { port: 8004, label: "Memory & knowledge" },
  workflow: { port: 8005, label: "Workflow engine" },
  tool: { port: 8006, label: "Tool execution" },
  evaluation: { port: 8007, label: "Evaluation" },
  identity: { port: 8008, label: "Identity & tenancy" },
  collaboration: { port: 8009, label: "Collaboration" },
  observability: { port: 8010, label: "Observability" },
  security: { port: 8011, label: "Security & governance" },
  infrastructure: { port: 8012, label: "Infrastructure & MLOps" },
  developer: { port: 8013, label: "Developer platform" },
  gateway: { port: 8014, label: "API gateway" },
  analytics: { port: 8015, label: "Analytics" },
  quality: { port: 8016, label: "Quality engineering" },
  docs: { port: 8017, label: "Docs portal" },
  release: { port: 8018, label: "Release engineering" },
  perf: { port: 8019, label: "Performance & cost" },
} as const;

export type ServiceName = keyof typeof SERVICES;

export function serviceUrl(name: ServiceName): string {
  const key = `AIOS_${name.toUpperCase().replace(/-/g, "_")}_URL`;
  const fromEnv = process.env[key]?.trim();
  if (fromEnv) return fromEnv.replace(/\/+$/, "");
  const base = process.env.AIOS_SERVICES_BASE_URL?.trim().replace(/\/+$/, "");
  return base ? `${base}/${name}` : `http://127.0.0.1:${SERVICES[name].port}`;
}

export function internalToken(): string {
  return process.env.AIOS_INTERNAL_TOKEN?.trim() ?? "";
}

const DEV_IDENTITY_SECRET = "dev-secret-key-change-me-in-production-32chars"; // identity service's dev default

export function jwtSecret(): Uint8Array {
  const secret = process.env.AIOS_JWT_SECRET?.trim();
  if (!secret && process.env.NODE_ENV === "production") {
    throw new Error("AIOS_JWT_SECRET must be set in production (the identity service's SECRET_KEY)");
  }
  return new TextEncoder().encode(secret || DEV_IDENTITY_SECRET);
}

export function guestAccessEnabled(): boolean {
  return process.env.AIOS_GUEST_ACCESS?.trim() === "true";
}

export const COOKIE = { access: "aios_at", refresh: "aios_rt" } as const;
