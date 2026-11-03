import "server-only";
import { SERVICES, serviceUrl, internalToken, type ServiceName } from "./config";
import { callService, itemsOf, workspaceFor } from "./services";
import type { Session } from "./session";
import type {
  LiveAgent,
  LiveDataset,
  LiveEvaluation,
  LiveModel,
  LivePrompt,
  LiveTool,
  LiveWorkflow,
  ServiceStatus,
} from "@/types/live";

type Raw = Record<string, unknown>;
const str = (v: unknown) => (typeof v === "string" ? v : null);
const arr = (v: unknown) => (Array.isArray(v) ? (v as string[]) : []);

/** List a workspace-scoped collection for the caller's organisation (empty when the org has no workspace yet). */
async function listScoped(service: ServiceName, collection: string, session: Session, paged = true): Promise<Raw[]> {
  if (!session.organizationId) return [];
  const ws = await workspaceFor(service, session.organizationId);
  if (!ws) return [];
  const query = `workspace_id=${encodeURIComponent(ws)}${paged ? "&page_size=100" : ""}`;
  return itemsOf<Raw>(await callService(service, `/api/v1/${collection}?${query}`, { userId: session.userId }));
}

export const resources = {
  async agents(s: Session): Promise<LiveAgent[]> {
    return (await listScoped("agent", "agents", s)).map((a) => ({
      id: String(a.id), name: String(a.name), description: str(a.description), role: str(a.role),
      status: String(a.status), health: str(a.health_status), capabilities: arr(a.capabilities),
      skills: arr(a.skills), autonomous: Boolean(a.is_autonomous), updatedAt: str(a.updated_at),
    }));
  },
  async prompts(s: Session): Promise<LivePrompt[]> {
    return (await listScoped("prompt", "prompts", s, false)).map((p) => ({
      id: String(p.id), name: String(p.name), description: str(p.description), status: String(p.status),
      visibility: str(p.visibility), latestVersion: Number(p.latest_version_number ?? 0), updatedAt: str(p.updated_at),
    }));
  },
  async workflows(s: Session): Promise<LiveWorkflow[]> {
    return (await listScoped("workflow", "workflows", s)).map((w) => ({
      id: String(w.id), name: String(w.name), description: str(w.description), category: String(w.category),
      status: String(w.status), priority: str(w.priority), tags: arr(w.tags), updatedAt: str(w.updated_at),
    }));
  },
  async tools(s: Session): Promise<LiveTool[]> {
    return (await listScoped("tool", "tools", s)).map((t) => ({
      id: String(t.id), name: String(t.name), description: str(t.description), category: String(t.category),
      status: String(t.status), health: str(t.health), tags: arr(t.tags), updatedAt: str(t.updated_at),
    }));
  },
  async evaluations(s: Session): Promise<LiveEvaluation[]> {
    return (await listScoped("evaluation", "evaluations", s)).map((e) => ({
      id: String(e.id), name: String(e.name), description: str(e.description), category: String(e.category),
      status: String(e.status), updatedAt: str(e.updated_at),
    }));
  },
  async datasets(s: Session): Promise<LiveDataset[]> {
    return (await listScoped("evaluation", "datasets", s)).map((d) => ({
      id: String(d.id), name: String(d.name), description: str(d.description), type: String(d.dataset_type),
      status: String(d.status), updatedAt: str(d.updated_at),
    }));
  },
  async models(): Promise<LiveModel[]> {
    return itemsOf<Raw>(await callService("ai-core", "/v1/models")).map((m) => {
      const pricing = (m.pricing ?? {}) as Raw;
      return {
        provider: String(m.provider), name: String(m.name), status: String(m.status),
        contextWindow: Number(m.context_window ?? 0), capabilities: arr(m.capabilities), tags: arr(m.tags),
        inputCostPer1M: Number(pricing.input_cost_per_1m ?? 0), outputCostPer1M: Number(pricing.output_cost_per_1m ?? 0),
      };
    });
  },
} as const;

export type ResourceName = keyof typeof resources;

/** Readiness of every service, probed in parallel with a short timeout; latency is measured, never estimated. */
export async function platformStatus(): Promise<ServiceStatus[]> {
  const token = internalToken();
  return Promise.all(
    (Object.keys(SERVICES) as ServiceName[]).map(async (name) => {
      const started = performance.now();
      try {
        const res = await fetch(`${serviceUrl(name)}/health/ready`, {
          cache: "no-store",
          headers: token ? { "X-Internal-Token": token } : undefined,
          signal: AbortSignal.timeout(3_000),
        });
        return { name, label: SERVICES[name].label, ready: res.ok, latencyMs: Math.round(performance.now() - started) };
      } catch {
        return { name, label: SERVICES[name].label, ready: false, latencyMs: null };
      }
    }),
  );
}
