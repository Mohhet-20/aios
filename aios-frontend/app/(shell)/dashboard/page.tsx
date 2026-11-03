"use client";

import Link from "next/link";
import { Bot, ClipboardCheck, FileText, GitBranch, Wrench, ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { StatusDot } from "@/components/shared/status-dot";
import { LiveState } from "@/components/shared/live-state";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PlatformHealth } from "@/features/dashboard/platform-health";
import { useAgents, useEvaluations, useOverview, useWorkflows } from "@/services/console";
import { humanize, timeAgo } from "@/lib/utils";

export default function DashboardPage() {
  const overview = useOverview();
  const agents = useAgents();
  const workflows = useWorkflows();
  const evaluations = useEvaluations();
  const c = overview.data?.counts;

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Your organisation's agents, prompts, workflows and quality gates, read live from the platform services."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {overview.isLoading
          ? Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-[104px]" />)
          : [
              { label: "Agents (active)", value: c ? `${c.agents} (${c.activeAgents})` : "—", icon: Bot },
              { label: "Prompts", value: c ? `${c.prompts}` : "—", icon: FileText },
              { label: "Workflows", value: c ? `${c.workflows}` : "—", icon: GitBranch },
              { label: "Tools", value: c ? `${c.tools}` : "—", icon: Wrench },
              { label: "Evaluations · datasets", value: c ? `${c.evaluations} · ${c.datasets}` : "—", icon: ClipboardCheck },
            ].map((s) => <StatCard key={s.label} label={s.label} value={s.value} icon={s.icon} />)}
      </div>

      <div className="mt-4">
        <LiveState query={overview} skeleton={<Skeleton className="h-40 w-full" />}>
          {(o) => <PlatformHealth services={o.services} />}
        </LiveState>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Agent roster</CardTitle>
            <CardDescription>From the agent platform: lifecycle status, health and declared capabilities.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            <LiveState query={agents} isEmpty={(a) => a.length === 0} empty="No agents yet. Run scripts/seed_demo.py or create one.">
              {(list) =>
                list.map((a) => (
                  <Link key={a.id} href="/agents" className="flex items-center justify-between rounded-lg px-2 py-2.5 text-sm transition-colors hover:bg-muted/60">
                    <div className="flex min-w-0 items-center gap-3">
                      <StatusDot status={a.status === "active" ? "healthy" : a.status === "paused" ? "degraded" : "idle"} pulse={a.status === "active"} />
                      <div className="min-w-0">
                        <p className="truncate font-medium">{a.name}</p>
                        <p className="truncate text-xs text-muted-foreground">
                          {a.role ?? "Agent"}
                          {a.capabilities.length > 0 && ` · ${a.capabilities.join(", ")}`}
                        </p>
                      </div>
                    </div>
                    <Badge variant={a.status === "active" ? "success" : "secondary"} className="capitalize">
                      {a.status}
                    </Badge>
                  </Link>
                ))
              }
            </LiveState>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quality gates</CardTitle>
            <CardDescription>Evaluation suites from the evaluation platform.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <LiveState query={evaluations} isEmpty={(e) => e.length === 0} empty="No evaluation suites yet.">
              {(list) =>
                list.map((e) => (
                  <div key={e.id} className="rounded-lg border border-border px-3 py-2 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{e.name}</p>
                      <Badge variant="outline" className="capitalize">{humanize(e.category)}</Badge>
                    </div>
                    {e.description && <p className="mt-0.5 text-xs text-muted-foreground">{e.description}</p>}
                  </div>
                ))
              }
            </LiveState>
            <Link href="/evaluation" className="flex items-center gap-1 pt-1 text-xs font-medium text-primary hover:underline">
              Open evaluation <ArrowRight className="h-3 w-3" />
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Workflows</CardTitle>
          <CardDescription>From the workflow engine.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 md:grid-cols-2">
          <LiveState query={workflows} isEmpty={(w) => w.length === 0} empty="No workflows yet.">
            {(list) =>
              list.map((w) => (
                <div key={w.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{w.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {humanize(w.category)}
                      {w.updatedAt && ` · updated ${timeAgo(w.updatedAt)}`}
                    </p>
                  </div>
                  <Badge variant={w.status === "published" || w.status === "active" ? "success" : "secondary"} className="capitalize">
                    {w.status}
                  </Badge>
                </div>
              ))
            }
          </LiveState>
        </CardContent>
      </Card>
    </div>
  );
}
