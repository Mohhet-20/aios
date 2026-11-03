"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bot, Download, Star } from "lucide-react";
import { toast } from "sonner";

const marketplaceAgents = [
  { id: "m1", name: "SOC2 Compliance Auditor", author: "AIOS Team", rating: 4.8, installs: 1240, description: "Reviews policies and evidence against SOC2 controls." },
  { id: "m2", name: "SQL Query Optimizer", author: "Community", rating: 4.5, installs: 812, description: "Rewrites slow SQL queries and explains the tradeoffs." },
  { id: "m3", name: "Meeting Notes Summarizer", author: "AIOS Team", rating: 4.9, installs: 3021, description: "Turns transcripts into action items and decisions." },
  { id: "m4", name: "Legal Contract Reviewer", author: "Community", rating: 4.3, installs: 455, description: "Flags risky clauses in vendor contracts." },
];

export default function AgentMarketplacePage() {
  return (
    <div>
      <PageHeader title="Agent Marketplace" description="Install pre-built specialist agents from AIOS and the community." />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {marketplaceAgents.map((a) => (
          <Card key={a.id}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <Bot className="h-4.5 w-4.5 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">{a.name}</p>
                  <p className="text-xs text-muted-foreground">by {a.author}</p>
                </div>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{a.description}</p>
              <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Star className="h-3 w-3 fill-warning text-warning" /> {a.rating} · {a.installs} installs
                </span>
                <Button size="sm" variant="outline" onClick={() => toast.success(`${a.name} added to your agents`)}>
                  <Download className="h-3.5 w-3.5" /> Install
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
