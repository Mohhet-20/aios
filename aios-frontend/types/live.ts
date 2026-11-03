/** Shapes the console API returns: normalised views of the domain services' own records. */

export interface ServiceStatus {
  name: string;
  label: string;
  ready: boolean;
  latencyMs: number | null;
}

export interface LiveAgent {
  id: string;
  name: string;
  description: string | null;
  role: string | null;
  status: string;
  health: string | null;
  capabilities: string[];
  skills: string[];
  autonomous: boolean;
  updatedAt: string | null;
}

export interface LivePrompt {
  id: string;
  name: string;
  description: string | null;
  status: string;
  visibility: string | null;
  latestVersion: number;
  updatedAt: string | null;
}

export interface LiveWorkflow {
  id: string;
  name: string;
  description: string | null;
  category: string;
  status: string;
  priority: string | null;
  tags: string[];
  updatedAt: string | null;
}

export interface LiveTool {
  id: string;
  name: string;
  description: string | null;
  category: string;
  status: string;
  health: string | null;
  tags: string[];
  updatedAt: string | null;
}

export interface LiveEvaluation {
  id: string;
  name: string;
  description: string | null;
  category: string;
  status: string;
  updatedAt: string | null;
}

export interface LiveDataset {
  id: string;
  name: string;
  description: string | null;
  type: string;
  status: string;
  updatedAt: string | null;
}

export interface LiveModel {
  provider: string;
  name: string;
  status: string;
  contextWindow: number;
  capabilities: string[];
  tags: string[];
  inputCostPer1M: number;
  outputCostPer1M: number;
}

export interface Overview {
  counts: { agents: number; activeAgents: number; prompts: number; workflows: number; tools: number; evaluations: number; datasets: number };
  services: ServiceStatus[];
}

export interface GenerationResult {
  ok: boolean;
  content?: string;
  provider?: string;
  model?: string;
  inputTokens?: number;
  outputTokens?: number;
  /** Wall-clock time of the call, measured at the edge. */
  latencyMs: number;
  error?: string;
}
