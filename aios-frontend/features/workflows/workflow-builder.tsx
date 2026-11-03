"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
import { WorkflowCanvas } from "./workflow-canvas";
import { workflows } from "@/lib/mock-data";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Bot, Wrench, GitBranch, UserCheck, Play, Save, Rocket } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const PALETTE = [
  { type: "agent", label: "Agent step", icon: Bot, color: "chart-1" },
  { type: "tool", label: "Tool call", icon: Wrench, color: "chart-2" },
  { type: "condition", label: "Condition / branch", icon: GitBranch, color: "chart-4" },
  { type: "human", label: "Human-in-the-loop", icon: UserCheck, color: "chart-5" },
];

export function WorkflowBuilder() {
  const [workflowId, setWorkflowId] = useState(workflows[0].id);
  const workflow = workflows.find((w) => w.id === workflowId)!;
  const [running, setRunning] = useState(false);

  function runTest() {
    setRunning(true);
    toast.promise(new Promise((r) => setTimeout(r, 1800)), {
      loading: "Running workflow with test input...",
      success: () => {
        setRunning(false);
        return "Test run completed — 7/7 steps succeeded";
      },
      error: "Run failed",
    });
  }

  return (
    <div className="h-[calc(100vh-9.5rem)] overflow-hidden rounded-xl border border-border">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={18} minSize={14} maxSize={26}>
          <div className="flex h-full flex-col border-r border-border">
            <div className="border-b border-border px-3 py-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Step palette</p>
            </div>
            <div className="space-y-1.5 p-3">
              {PALETTE.map((p) => (
                <div
                  key={p.type}
                  draggable
                  className="flex cursor-grab items-center gap-2 rounded-md border border-border bg-card px-2.5 py-2 text-xs shadow-sm active:cursor-grabbing"
                >
                  <p.icon className="h-3.5 w-3.5" style={{ color: `hsl(var(--${p.color}))` }} />
                  {p.label}
                </div>
              ))}
            </div>
            <div className="border-t border-border px-3 py-2.5">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Workflows</p>
            </div>
            <div className="space-y-1.5 overflow-y-auto p-3">
              {workflows.map((w) => (
                <button
                  key={w.id}
                  onClick={() => setWorkflowId(w.id)}
                  className={`w-full rounded-md border px-2.5 py-2 text-left text-xs ${
                    w.id === workflowId ? "border-primary bg-accent" : "border-border hover:bg-muted/50"
                  }`}
                >
                  <p className="font-medium">{w.name}</p>
                  <p className="text-muted-foreground">{w.status}</p>
                </button>
              ))}
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle />

        <ResizablePanel defaultSize={58} minSize={40}>
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <div>
                <p className="text-sm font-semibold">{workflow.name}</p>
                <p className="text-xs text-muted-foreground">{workflow.description}</p>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => toast.success("Draft saved")}>
                  <Save className="h-3.5 w-3.5" /> Save
                </Button>
                <Button size="sm" variant="outline" onClick={runTest} disabled={running}>
                  <Play className="h-3.5 w-3.5" /> {running ? "Running..." : "Test run"}
                </Button>
                <Button size="sm" onClick={() => toast.success("Workflow published")}>
                  <Rocket className="h-3.5 w-3.5" /> Publish
                </Button>
              </div>
            </div>
            <div className="flex-1">
              <WorkflowCanvas workflow={workflow} />
            </div>
          </div>
        </ResizablePanel>
        <ResizableHandle />

        <ResizablePanel defaultSize={24} minSize={18} maxSize={34}>
          <div className="flex h-full flex-col gap-4 overflow-y-auto scrollbar-thin p-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">State</span>
                  <Badge variant={workflow.status === "published" ? "success" : "secondary"} className="capitalize">
                    {workflow.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Success rate</span>
                  <span className="font-mono">{workflow.successRate}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Steps</span>
                  <span className="font-mono">{workflow.nodes.length}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Trigger</CardTitle>
              </CardHeader>
              <CardContent>
                <Select defaultValue="event">
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="event">On event (webhook)</SelectItem>
                    <SelectItem value="schedule">Scheduled (cron)</SelectItem>
                    <SelectItem value="manual">Manual trigger</SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Recent runs</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center justify-between rounded-md border border-border px-2.5 py-2">
                    <span>Run #{1042 - i}</span>
                    <Badge variant={i === 2 ? "destructive" : "success"} className="text-[10px]">
                      {i === 2 ? "failed" : "success"}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
