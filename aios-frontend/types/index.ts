// Shared domain types consumed across features/, components/, and services/.
// These mirror (a frontend-friendly projection of) the backend contracts
// defined in the AIOS architecture blueprint (Phase 1) — Prompt/Agent/
// Workflow/Memory/Tool/Evaluation engines each own one section here.

export type ID = string;

export interface Organization {
  id: ID;
  name: string;
  plan: "starter" | "team" | "enterprise";
  logoInitials: string;
}

export interface Workspace {
  id: ID;
  name: string;
  organizationId: ID;
  memberCount: number;
  color: string;
}

export interface UserProfile {
  id: ID;
  name: string;
  email: string;
  avatarUrl?: string;
  role: "owner" | "admin" | "member" | "viewer";
}

export type ModelProvider = "anthropic" | "openai" | "google" | "local" | "azure";

export interface ModelInfo {
  id: ID;
  name: string;
  provider: ModelProvider;
  contextWindow: number;
  costPer1kInput: number;
  costPer1kOutput: number;
  modality: ("text" | "vision" | "audio")[];
  status: "available" | "deprecated" | "beta";
}

export interface PromptVersion {
  id: ID;
  version: number;
  content: string;
  createdAt: string;
  author: string;
  status: "draft" | "staged" | "production" | "archived";
  evalScore?: number;
}

export interface Prompt {
  id: ID;
  name: string;
  description: string;
  tags: string[];
  targetModel: string;
  versions: PromptVersion[];
  updatedAt: string;
}

export type AgentStatus = "active" | "idle" | "error" | "training";

export interface Agent {
  id: ID;
  name: string;
  role: string;
  description: string;
  model: string;
  tools: string[];
  status: AgentStatus;
  avatarColor: string;
  runsToday: number;
  successRate: number;
}

export interface WorkflowStepNode {
  id: ID;
  type: "agent" | "tool" | "condition" | "human" | "start" | "end";
  label: string;
  position: { x: number; y: number };
}

export interface WorkflowEdge {
  id: ID;
  source: ID;
  target: ID;
  label?: string;
}

export interface WorkflowDefinition {
  id: ID;
  name: string;
  description: string;
  status: "draft" | "published" | "paused";
  nodes: WorkflowStepNode[];
  edges: WorkflowEdge[];
  lastRun?: string;
  successRate: number;
}

export interface EvalRun {
  id: ID;
  suiteName: string;
  target: string;
  score: number;
  previousScore?: number;
  passed: number;
  failed: number;
  total: number;
  createdAt: string;
  status: "queued" | "running" | "completed" | "failed";
}

export interface MemoryItem {
  id: ID;
  type: "session" | "semantic" | "episodic";
  scope: string;
  content: string;
  relevance?: number;
  createdAt: string;
}

export interface ToolDefinition {
  id: ID;
  name: string;
  description: string;
  category: string;
  sideEffect: "read-only" | "mutating";
  installs: number;
  verified: boolean;
  icon: string;
}

export interface ChatMessage {
  id: ID;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: string;
  streaming?: boolean;
  toolCalls?: { name: string; args: Record<string, unknown> }[];
}

export interface NotificationItem {
  id: ID;
  title: string;
  description: string;
  createdAt: string;
  read: boolean;
  type: "info" | "success" | "warning" | "error";
}

export interface ActivityItem {
  id: ID;
  actor: string;
  action: string;
  target: string;
  createdAt: string;
}

export interface AuditLogEntry {
  id: ID;
  actor: string;
  action: string;
  resource: string;
  ip: string;
  createdAt: string;
  status: "success" | "failed";
}

export interface ApiKey {
  id: ID;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsed?: string;
  scopes: string[];
}
