export const APP_NAME = "AIOS";

export const NAV_SECTIONS = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
      { label: "Projects", href: "/projects", icon: "FolderKanban" },
      { label: "Workspaces", href: "/workspaces", icon: "Layers" },
    ],
  },
  {
    label: "Build",
    items: [
      { label: "Agents", href: "/agents", icon: "Bot" },
      { label: "Prompt Studio", href: "/prompts/studio", icon: "SquareTerminal" },
      { label: "Prompt Library", href: "/prompts/library", icon: "Library" },
      { label: "Workflows", href: "/workflows", icon: "Workflow" },
      { label: "Workflow Builder", href: "/workflows/builder", icon: "Workflow" },
      { label: "Memory Explorer", href: "/memory", icon: "BrainCircuit" },
      { label: "Knowledge Base", href: "/knowledge-base", icon: "BookOpen" },
      { label: "Documents", href: "/documents", icon: "FileText" },
    ],
  },
  {
    label: "AI Core",
    items: [
      { label: "Model Registry", href: "/models/registry", icon: "Boxes" },
      { label: "Model Playground", href: "/models/playground", icon: "FlaskConical" },
      { label: "Inference Studio", href: "/inference", icon: "Zap" },
      { label: "Evaluation", href: "/evaluation", icon: "CheckCircle2" },
      { label: "Experiments", href: "/experiments", icon: "TestTube2" },
      { label: "Embeddings Explorer", href: "/embeddings", icon: "Network" },
    ],
  },
  {
    label: "Extend",
    items: [
      { label: "Tool Marketplace", href: "/tools/marketplace", icon: "Wrench" },
      { label: "Tools", href: "/tools/plugins", icon: "Puzzle" },
      { label: "Agent Marketplace", href: "/agents/marketplace", icon: "Store" },
    ],
  },
  {
    label: "Operate",
    items: [
      { label: "Monitoring", href: "/monitoring", icon: "Activity" },
      { label: "Observability", href: "/observability", icon: "Radar" },
      { label: "Analytics", href: "/analytics", icon: "BarChart3" },
      { label: "Reports", href: "/reports", icon: "FileBarChart" },
      { label: "Datasets", href: "/datasets", icon: "Database" },
      { label: "Files", href: "/files", icon: "Folder" },
    ],
  },
  {
    label: "Administration",
    items: [
      { label: "API Keys", href: "/settings/api-keys", icon: "KeyRound" },
      { label: "Users", href: "/settings/users", icon: "Users" },
      { label: "Teams", href: "/settings/teams", icon: "UsersRound" },
      { label: "Organizations", href: "/settings/organizations", icon: "Building2" },
      { label: "Billing", href: "/settings/billing", icon: "CreditCard" },
      { label: "Audit Logs", href: "/settings/audit-logs", icon: "ScrollText" },
      { label: "Administration", href: "/settings/administration", icon: "ShieldCheck" },
      { label: "Settings", href: "/settings/general", icon: "Settings" },
      { label: "Documentation", href: "/docs", icon: "HelpCircle" },
    ],
  },
] as const;
