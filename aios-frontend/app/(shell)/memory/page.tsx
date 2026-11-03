"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { memoryItems } from "@/lib/mock-data";
import { Search, BrainCircuit, Clock, Database } from "lucide-react";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDistanceToNow } from "date-fns";

const TYPE_ICON = { session: Clock, semantic: Database, episodic: BrainCircuit } as const;

export default function MemoryExplorerPage() {
  const [type, setType] = useState<"all" | "session" | "semantic" | "episodic">("all");
  const [query, setQuery] = useState("");

  const filtered = memoryItems.filter(
    (m) => (type === "all" || m.type === type) && m.content.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div>
      <PageHeader title="Memory Explorer" description="Inspect session, semantic, and episodic memory across agents and scopes." />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={type} onValueChange={(v) => setType(v as typeof type)}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="session">Session</TabsTrigger>
            <TabsTrigger value="semantic">Semantic</TabsTrigger>
            <TabsTrigger value="episodic">Episodic</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search memory content..." value={query} onChange={(e) => setQuery(e.target.value)} className="pl-8" />
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={BrainCircuit} title="No memory items match" description="Try a different query or memory type filter." />
      ) : (
        <div className="space-y-2">
          {filtered.map((m) => {
            const Icon = TYPE_ICON[m.type];
            return (
              <Card key={m.id}>
                <CardContent className="flex items-start gap-3 p-4">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-[10px] capitalize">{m.type}</Badge>
                      <span className="text-xs text-muted-foreground">{m.scope}</span>
                      {m.relevance && <span className="ml-auto font-mono text-xs text-muted-foreground">{Math.round(m.relevance * 100)}% relevance</span>}
                    </div>
                    <p className="mt-1.5 text-sm">{m.content}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">{formatDistanceToNow(new Date(m.createdAt), { addSuffix: true })}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
