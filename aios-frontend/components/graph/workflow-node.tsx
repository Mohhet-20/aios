"use client";

import { Handle, Position, type NodeProps } from "reactflow";
import { cn } from "@/lib/utils";
import { Bot, Wrench, GitBranch, UserCheck, Play, Flag } from "lucide-react";

const NODE_META: Record<string, { icon: typeof Bot; color: string; label: string }> = {
  agent: { icon: Bot, color: "chart-1", label: "Agent" },
  tool: { icon: Wrench, color: "chart-2", label: "Tool" },
  condition: { icon: GitBranch, color: "chart-4", label: "Condition" },
  human: { icon: UserCheck, color: "chart-5", label: "Human" },
  start: { icon: Play, color: "chart-3", label: "Trigger" },
  end: { icon: Flag, color: "chart-3", label: "End" },
};

export function WorkflowNode({ data, selected }: NodeProps<{ label: string; type: string }>) {
  const meta = NODE_META[data.type] ?? NODE_META.agent;
  const Icon = meta.icon;
  return (
    <div
      className={cn(
        "min-w-[160px] rounded-lg border bg-card px-3 py-2.5 shadow-sm transition-shadow",
        selected ? "border-primary ring-2 ring-primary/30" : "border-border"
      )}
    >
      <Handle type="target" position={Position.Left} className="!bg-border" />
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded" style={{ backgroundColor: `hsl(var(--${meta.color}) / 0.15)` }}>
          <Icon className="h-3.5 w-3.5" style={{ color: `hsl(var(--${meta.color}))` }} />
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">{data.label}</p>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{meta.label}</p>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-border" />
    </div>
  );
}
