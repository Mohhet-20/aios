// Deterministic mock data powering the UI. The console is frontend-only per the
// scope boundary ("do NOT generate backend APIs") — this module stands in for
// the real API responses the services/ layer will fetch once the backend
// (the core backend+) exists. Every mock shape matches types/index.ts exactly so
// swapping this for a real fetch later is a one-line change in services/.

import type {
  Agent,
  ApiKey,
  AuditLogEntry,
  ChatMessage,
  EvalRun,
  MemoryItem,
  ModelInfo,
  NotificationItem,
  Organization,
  Prompt,
  ToolDefinition,
  UserProfile,
  Workspace,
  WorkflowDefinition,
  ActivityItem,
} from "@/types";

export const currentUser: UserProfile = {
  id: "u_1",
  name: "Mohhet",
  email: "balakamohit@gmail.com",
  role: "owner",
};

export const organizations: Organization[] = [
  { id: "org_1", name: "Acme Corp", plan: "enterprise", logoInitials: "AC" },
  { id: "org_2", name: "Sandbox Labs", plan: "team", logoInitials: "SL" },
];

export const workspaces: Workspace[] = [
  { id: "ws_1", name: "Customer Support AI", organizationId: "org_1", memberCount: 12, color: "chart-1" },
  { id: "ws_2", name: "Internal Knowledge Ops", organizationId: "org_1", memberCount: 6, color: "chart-2" },
  { id: "ws_3", name: "Fraud Detection", organizationId: "org_1", memberCount: 9, color: "chart-3" },
  { id: "ws_4", name: "R&D Sandbox", organizationId: "org_2", memberCount: 3, color: "chart-4" },
];

export const models: ModelInfo[] = [
  { id: "claude-opus-4.8", name: "Claude Opus 4.8", provider: "anthropic", contextWindow: 200000, costPer1kInput: 0.015, costPer1kOutput: 0.075, modality: ["text", "vision"], status: "available" },
  { id: "claude-sonnet-5", name: "Claude Sonnet 5", provider: "anthropic", contextWindow: 200000, costPer1kInput: 0.003, costPer1kOutput: 0.015, modality: ["text", "vision"], status: "available" },
  { id: "claude-haiku-4.5", name: "Claude Haiku 4.5", provider: "anthropic", contextWindow: 200000, costPer1kInput: 0.0008, costPer1kOutput: 0.004, modality: ["text"], status: "available" },
  { id: "gpt-4.1", name: "GPT-4.1", provider: "openai", contextWindow: 128000, costPer1kInput: 0.01, costPer1kOutput: 0.03, modality: ["text", "vision"], status: "available" },
  { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "google", contextWindow: 1000000, costPer1kInput: 0.007, costPer1kOutput: 0.021, modality: ["text", "vision", "audio"], status: "beta" },
  { id: "llama-3.3-70b", name: "Llama 3.3 70B", provider: "local", contextWindow: 128000, costPer1kInput: 0, costPer1kOutput: 0, modality: ["text"], status: "available" },
];

export const agents: Agent[] = [
  { id: "ag_1", name: "Support Triage", role: "Classifier", description: "Routes inbound tickets to the right specialist agent or human queue.", model: "claude-haiku-4.5", tools: ["zendesk", "kb-search"], status: "active", avatarColor: "chart-1", runsToday: 4213, successRate: 98.2 },
  { id: "ag_2", name: "Research Analyst", role: "Retriever", description: "Answers deep questions over internal knowledge base with citations.", model: "claude-opus-4.8", tools: ["kb-search", "web-search"], status: "active", avatarColor: "chart-2", runsToday: 891, successRate: 95.6 },
  { id: "ag_3", name: "Code Reviewer", role: "Specialist", description: "Reviews pull requests for security and style issues.", model: "claude-sonnet-5", tools: ["github", "static-analyzer"], status: "idle", avatarColor: "chart-3", runsToday: 152, successRate: 92.1 },
  { id: "ag_4", name: "Fraud Scorer", role: "Classifier", description: "Scores transactions for fraud risk in real time.", model: "llama-3.3-70b", tools: ["transaction-db"], status: "error", avatarColor: "chart-4", runsToday: 15029, successRate: 99.4 },
  { id: "ag_5", name: "Data Analyst", role: "Analyst", description: "Generates SQL and charts from natural language questions.", model: "gpt-4.1", tools: ["sql-runner", "chart-gen"], status: "training", avatarColor: "chart-5", runsToday: 0, successRate: 0 },
];

export const prompts: Prompt[] = [
  {
    id: "pr_1",
    name: "Support Ticket Classifier",
    description: "Classifies inbound support tickets into priority + category.",
    tags: ["support", "classification"],
    targetModel: "claude-haiku-4.5",
    updatedAt: "2026-07-18T10:00:00Z",
    versions: [
      { id: "v3", version: 3, content: "You are a support ticket classifier...", createdAt: "2026-07-18T10:00:00Z", author: "Mohhet", status: "production", evalScore: 94.2 },
      { id: "v2", version: 2, content: "You classify support tickets...", createdAt: "2026-07-10T10:00:00Z", author: "Priya S.", status: "archived", evalScore: 89.5 },
      { id: "v1", version: 1, content: "Classify this ticket.", createdAt: "2026-06-28T10:00:00Z", author: "Priya S.", status: "archived", evalScore: 74.0 },
    ],
  },
  {
    id: "pr_2",
    name: "Knowledge Base Answerer",
    description: "Answers questions using retrieved KB context with citations.",
    tags: ["retrieval", "support"],
    targetModel: "claude-opus-4.8",
    updatedAt: "2026-07-16T14:00:00Z",
    versions: [
      { id: "v5", version: 5, content: "Using the provided context, answer...", createdAt: "2026-07-16T14:00:00Z", author: "Mohhet", status: "production", evalScore: 91.0 },
      { id: "v4", version: 4, content: "Answer using context...", createdAt: "2026-07-01T09:00:00Z", author: "Mohhet", status: "staged", evalScore: 88.3 },
    ],
  },
  {
    id: "pr_3",
    name: "Fraud Risk Rationale",
    description: "Generates a human-readable rationale for a fraud score.",
    tags: ["fraud", "risk"],
    targetModel: "llama-3.3-70b",
    updatedAt: "2026-07-12T08:00:00Z",
    versions: [{ id: "v1", version: 1, content: "Explain the fraud score...", createdAt: "2026-07-12T08:00:00Z", author: "Dana K.", status: "draft", evalScore: undefined }],
  },
];

export const workflows: WorkflowDefinition[] = [
  {
    id: "wf_1",
    name: "Support Ticket Resolution",
    description: "Triage → retrieve → resolve → escalate if needed.",
    status: "published",
    successRate: 96.4,
    lastRun: "2026-07-20T08:12:00Z",
    nodes: [
      { id: "n1", type: "start", label: "New Ticket", position: { x: 40, y: 160 } },
      { id: "n2", type: "agent", label: "Support Triage", position: { x: 260, y: 160 } },
      { id: "n3", type: "tool", label: "KB Search", position: { x: 480, y: 60 } },
      { id: "n4", type: "agent", label: "Research Analyst", position: { x: 480, y: 260 } },
      { id: "n5", type: "condition", label: "Confidence > 90%?", position: { x: 700, y: 160 } },
      { id: "n6", type: "human", label: "Escalate to Human", position: { x: 920, y: 260 } },
      { id: "n7", type: "end", label: "Resolved", position: { x: 920, y: 60 } },
    ],
    edges: [
      { id: "e1", source: "n1", target: "n2" },
      { id: "e2", source: "n2", target: "n3", label: "lookup" },
      { id: "e3", source: "n2", target: "n4", label: "delegate" },
      { id: "e4", source: "n4", target: "n5" },
      { id: "e5", source: "n5", target: "n7", label: "yes" },
      { id: "e6", source: "n5", target: "n6", label: "no" },
    ],
  },
  {
    id: "wf_2",
    name: "Weekly Fraud Digest",
    description: "Aggregates flagged transactions and drafts a summary report.",
    status: "draft",
    successRate: 0,
    nodes: [
      { id: "n1", type: "start", label: "Cron: Monday 8am", position: { x: 40, y: 120 } },
      { id: "n2", type: "tool", label: "Query Transactions", position: { x: 260, y: 120 } },
      { id: "n3", type: "agent", label: "Fraud Scorer", position: { x: 480, y: 120 } },
      { id: "n4", type: "end", label: "Report Sent", position: { x: 700, y: 120 } },
    ],
    edges: [
      { id: "e1", source: "n1", target: "n2" },
      { id: "e2", source: "n2", target: "n3" },
      { id: "e3", source: "n3", target: "n4" },
    ],
  },
];

export const evalRuns: EvalRun[] = [
  { id: "ev_1", suiteName: "Support Classifier Golden Set", target: "Support Ticket Classifier v3", score: 94.2, previousScore: 89.5, passed: 188, failed: 12, total: 200, createdAt: "2026-07-18T10:05:00Z", status: "completed" },
  { id: "ev_2", suiteName: "KB Answerer Groundedness", target: "Knowledge Base Answerer v5", score: 91.0, previousScore: 88.3, passed: 91, failed: 9, total: 100, createdAt: "2026-07-16T14:10:00Z", status: "completed" },
  { id: "ev_3", suiteName: "Fraud Rationale Clarity", target: "Fraud Risk Rationale v1", score: 0, passed: 0, failed: 0, total: 60, createdAt: "2026-07-20T09:00:00Z", status: "running" },
  { id: "ev_4", suiteName: "Code Review Precision", target: "Code Reviewer agent", score: 82.5, previousScore: 85.0, passed: 66, failed: 14, total: 80, createdAt: "2026-07-14T11:00:00Z", status: "completed" },
];

export const memoryItems: MemoryItem[] = [
  { id: "m1", type: "semantic", scope: "org_1 / kb", content: "Refund policy: full refunds within 30 days of purchase with receipt.", relevance: 0.94, createdAt: "2026-07-01T00:00:00Z" },
  { id: "m2", type: "episodic", scope: "ag_1 / session_882", content: "User asked about refund on a damaged item; resolved via store credit.", relevance: 0.81, createdAt: "2026-07-19T15:22:00Z" },
  { id: "m3", type: "session", scope: "session_991", content: "User previously mentioned they are on the Enterprise plan.", createdAt: "2026-07-20T09:40:00Z" },
  { id: "m4", type: "semantic", scope: "org_1 / kb", content: "API rate limit is 500 req/min on the Enterprise plan.", relevance: 0.77, createdAt: "2026-06-20T00:00:00Z" },
];

export const tools: ToolDefinition[] = [
  { id: "t1", name: "Zendesk Connector", description: "Read/update tickets in Zendesk.", category: "Support", sideEffect: "mutating", installs: 412, verified: true, icon: "Headset" },
  { id: "t2", name: "KB Search", description: "Semantic search over the internal knowledge base.", category: "Retrieval", sideEffect: "read-only", installs: 980, verified: true, icon: "Search" },
  { id: "t3", name: "GitHub", description: "Read PRs, post review comments.", category: "Engineering", sideEffect: "mutating", installs: 261, verified: true, icon: "Github" },
  { id: "t4", name: "SQL Runner", description: "Execute read-only SQL against the analytics warehouse.", category: "Data", sideEffect: "read-only", installs: 178, verified: false, icon: "Database" },
  { id: "t5", name: "Transaction DB", description: "Query transaction records for fraud scoring.", category: "Finance", sideEffect: "read-only", installs: 64, verified: true, icon: "Landmark" },
];

export const notifications: NotificationItem[] = [
  { id: "n1", title: "Evaluation completed", description: "Support Ticket Classifier v3 scored 94.2% (+4.7pts).", createdAt: "2026-07-20T10:05:00Z", read: false, type: "success" },
  { id: "n2", title: "Agent error rate spike", description: "Fraud Scorer error rate crossed 2% threshold.", createdAt: "2026-07-20T09:40:00Z", read: false, type: "error" },
  { id: "n3", title: "Prompt promoted", description: "Knowledge Base Answerer v5 promoted to production.", createdAt: "2026-07-19T16:00:00Z", read: true, type: "info" },
  { id: "n4", title: "Budget warning", description: "Fraud Detection workspace at 82% of monthly token budget.", createdAt: "2026-07-19T08:00:00Z", read: true, type: "warning" },
];

export const activity: ActivityItem[] = [
  { id: "a1", actor: "Mohhet", action: "promoted", target: "Knowledge Base Answerer v5", createdAt: "2026-07-19T16:00:00Z" },
  { id: "a2", actor: "Priya S.", action: "created workflow", target: "Weekly Fraud Digest", createdAt: "2026-07-19T11:20:00Z" },
  { id: "a3", actor: "Dana K.", action: "registered tool", target: "SQL Runner", createdAt: "2026-07-18T14:00:00Z" },
  { id: "a4", actor: "System", action: "flagged", target: "Fraud Scorer error rate", createdAt: "2026-07-20T09:40:00Z" },
];

export const auditLogs: AuditLogEntry[] = [
  { id: "al1", actor: "mohhet@acme.com", action: "prompt.promote", resource: "pr_2 / v5", ip: "203.0.113.4", createdAt: "2026-07-19T16:00:00Z", status: "success" },
  { id: "al2", actor: "priya@acme.com", action: "workflow.create", resource: "wf_2", ip: "203.0.113.9", createdAt: "2026-07-19T11:20:00Z", status: "success" },
  { id: "al3", actor: "api-key:sk-***f3a1", action: "tool.invoke", resource: "t4 / SQL Runner", ip: "10.0.4.12", createdAt: "2026-07-18T20:11:00Z", status: "failed" },
  { id: "al4", actor: "dana@acme.com", action: "apikey.create", resource: "key_991", ip: "203.0.113.2", createdAt: "2026-07-18T14:00:00Z", status: "success" },
];

export const apiKeys: ApiKey[] = [
  { id: "key_1", name: "Production Backend", prefix: "sk-live-8f2a", createdAt: "2026-05-01T00:00:00Z", lastUsed: "2026-07-20T09:00:00Z", scopes: ["agents:run", "prompts:read"] },
  { id: "key_2", name: "CI Eval Runner", prefix: "sk-live-01cd", createdAt: "2026-06-10T00:00:00Z", lastUsed: "2026-07-20T02:00:00Z", scopes: ["evaluation:*"] },
  { id: "key_3", name: "Local Dev (Mohhet)", prefix: "sk-test-77bb", createdAt: "2026-07-01T00:00:00Z", scopes: ["*"] },
];

export const sampleConversation: ChatMessage[] = [
  { id: "c1", role: "user", content: "A customer wants a refund on a damaged blender purchased 20 days ago.", createdAt: "2026-07-20T09:39:00Z" },
  { id: "c2", role: "assistant", content: "Based on the refund policy (full refunds within 30 days with receipt), this customer qualifies for a full refund. I'll check if we have their receipt on file.", createdAt: "2026-07-20T09:39:05Z", toolCalls: [{ name: "kb_search", args: { query: "refund policy damaged item" } }] },
  { id: "c3", role: "tool", content: "Found: Refund policy — full refunds within 30 days of purchase with receipt.", createdAt: "2026-07-20T09:39:06Z" },
  { id: "c4", role: "assistant", content: "Confirmed — this order was placed 20 days ago and is within policy. I'm issuing a full refund to the original payment method.", createdAt: "2026-07-20T09:39:10Z" },
];

// Time-series generators for charts (Recharts) — deterministic, no Math.random
// jank across server/client renders.
export function generateTimeSeries(points: number, base: number, variance: number, seed = 7) {
  const out: { date: string; value: number }[] = [];
  let v = base;
  for (let i = 0; i < points; i++) {
    const wobble = Math.sin((i + seed) * 0.7) * variance;
    v = Math.max(0, base + wobble + (i / points) * variance * 0.5);
    const d = new Date(2026, 6, 1 + i);
    out.push({ date: `${d.getMonth() + 1}/${d.getDate()}`, value: Math.round(v * 100) / 100 });
  }
  return out;
}

export const tokenUsageSeries = generateTimeSeries(14, 1_200_000, 300_000, 3);
export const costSeries = generateTimeSeries(14, 420, 90, 11);
export const latencyP95Series = generateTimeSeries(14, 820, 140, 5);
export const errorRateSeries = generateTimeSeries(14, 1.2, 0.6, 9);
