"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Plus, FolderKanban } from "lucide-react";

const projects = [
  { id: "p1", name: "Customer Support Automation", workspace: "Customer Support AI", progress: 82, status: "on-track", agents: 3, workflows: 2 },
  { id: "p2", name: "Internal Docs Q&A", workspace: "Internal Knowledge Ops", progress: 45, status: "at-risk", agents: 1, workflows: 1 },
  { id: "p3", name: "Real-time Fraud Scoring", workspace: "Fraud Detection", progress: 95, status: "on-track", agents: 2, workflows: 1 },
  { id: "p4", name: "Code Review Copilot", workspace: "R&D Sandbox", progress: 20, status: "planning", agents: 1, workflows: 0 },
];

export default function ProjectsPage() {
  return (
    <div>
      <PageHeader
        title="Projects"
        description="Group agents, prompts, and workflows into a shippable initiative."
        actions={
          <Button size="sm">
            <Plus className="h-4 w-4" /> New project
          </Button>
        }
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {projects.map((p) => (
          <Card key={p.id}>
            <CardHeader className="flex-row items-start justify-between space-y-0">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <FolderKanban className="h-4.5 w-4.5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-sm">{p.name}</CardTitle>
                  <CardDescription>{p.workspace}</CardDescription>
                </div>
              </div>
              <Badge variant={p.status === "on-track" ? "success" : p.status === "at-risk" ? "warning" : "secondary"} className="capitalize">
                {p.status.replace("-", " ")}
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>Progress</span>
                <span className="font-mono">{p.progress}%</span>
              </div>
              <Progress value={p.progress} />
              <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
                <span>{p.agents} agents</span>
                <span>{p.workflows} workflows</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
