"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { LiveState } from "@/components/shared/live-state";
import { StatusDot } from "@/components/shared/status-dot";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAgents } from "@/services/console";
import { humanize, timeAgo } from "@/lib/utils";

export default function AgentsPage() {
  const agents = useAgents();
  const [q, setQ] = useState("");
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!agents.data || !needle) return agents.data;
    return agents.data.filter((a) =>
      [a.name, a.role ?? "", a.description ?? "", ...a.capabilities].some((f) => f.toLowerCase().includes(needle)),
    );
  }, [agents.data, q]);

  return (
    <div>
      <PageHeader
        title="AI Agents"
        description="Agents registered in the agent platform for your organisation, with lifecycle status and declared capabilities."
      />
      <div className="mb-4 max-w-sm">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search name, role or capability…" className="pl-8" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search agents" />
        </div>
      </div>
      <LiveState
        query={{ ...agents, data: filtered }}
        isEmpty={(a) => a.length === 0}
        empty={q ? "No agent matches that search." : "No agents yet. Run scripts/seed_demo.py, or create one through the agent platform API."}
        skeleton={
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-44" />
            ))}
          </div>
        }
      >
        {(list) => (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {list.map((a) => (
              <Card key={a.id}>
                <CardHeader className="flex-row items-start justify-between space-y-0 pb-2">
                  <div className="min-w-0">
                    <CardTitle className="truncate text-sm">{a.name}</CardTitle>
                    <p className="mt-0.5 text-xs text-muted-foreground">{a.role ?? "Agent"}</p>
                  </div>
                  <Badge variant={a.status === "active" ? "success" : "secondary"} className="capitalize">
                    {a.status}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  {a.description && <p className="text-muted-foreground">{a.description}</p>}
                  <div className="flex flex-wrap gap-1.5">
                    {[...a.capabilities, ...a.skills].map((c) => (
                      <Badge key={c} variant="outline" className="font-normal">
                        {humanize(c)}
                      </Badge>
                    ))}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <StatusDot status={a.health === "healthy" ? "healthy" : a.health === "unhealthy" ? "down" : "idle"} />
                      Health: {a.health ?? "unknown"}
                      {a.autonomous && " · autonomous"}
                    </span>
                    {a.updatedAt && <span>Updated {timeAgo(a.updatedAt)}</span>}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </LiveState>
    </div>
  );
}
