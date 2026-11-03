"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "./api-client";
import type {
  GenerationResult,
  LiveAgent,
  LiveDataset,
  LiveEvaluation,
  LiveModel,
  LivePrompt,
  LiveTool,
  LiveWorkflow,
  Overview,
  ServiceStatus,
} from "@/types/live";

export interface SessionInfo {
  authenticated: boolean;
  user: { id: string; email: string | null; displayName: string | null };
  organizationId: string | null;
  organization: { id: string; name: string } | null;
}

const list = <T,>(resource: string) => () => api<T[]>(`/api/console/${resource}`);

export const useSession = () => useQuery({ queryKey: ["session"], queryFn: () => api<SessionInfo>("/api/auth/session"), staleTime: 60_000 });
export const useOverview = () => useQuery({ queryKey: ["overview"], queryFn: () => api<Overview>("/api/console/overview"), refetchInterval: 30_000 });
export const usePlatformStatus = () =>
  useQuery({ queryKey: ["status"], queryFn: () => api<ServiceStatus[]>("/api/console/status"), refetchInterval: 15_000 });
export const useAgents = () => useQuery({ queryKey: ["agents"], queryFn: list<LiveAgent>("agents") });
export const usePrompts = () => useQuery({ queryKey: ["prompts"], queryFn: list<LivePrompt>("prompts") });
export const useWorkflows = () => useQuery({ queryKey: ["workflows"], queryFn: list<LiveWorkflow>("workflows") });
export const useTools = () => useQuery({ queryKey: ["tools"], queryFn: list<LiveTool>("tools") });
export const useEvaluations = () => useQuery({ queryKey: ["evaluations"], queryFn: list<LiveEvaluation>("evaluations") });
export const useDatasets = () => useQuery({ queryKey: ["datasets"], queryFn: list<LiveDataset>("datasets") });
export const useModels = () => useQuery({ queryKey: ["models"], queryFn: list<LiveModel>("models"), staleTime: 5 * 60_000 });

export const useGenerate = () =>
  useMutation({
    mutationFn: (input: { prompt: string; provider?: string; model?: string }) =>
      api<GenerationResult>("/api/console/generate", { method: "POST", body: input }),
  });

export async function signOut() {
  await api("/api/auth/logout", { method: "POST" });
  // A full page load, so no cached data from this session survives sign-out.
  window.location.replace("/login");
}
