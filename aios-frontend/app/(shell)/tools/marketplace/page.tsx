"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { tools } from "@/lib/mock-data";
import { Search, ShieldCheck, Download } from "lucide-react";
import { toast } from "sonner";

export default function ToolMarketplacePage() {
  return (
    <div>
      <PageHeader title="Tool Marketplace" description="Register internal tools or install verified integrations for agents to use." />
      <div className="relative mb-4 max-w-sm">
        <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search tools..." className="pl-8" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {tools.map((t) => (
          <Card key={t.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <p className="font-medium">{t.name}</p>
                {t.verified && <ShieldCheck className="h-4 w-4 text-primary" />}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{t.description}</p>
              <div className="mt-3 flex items-center gap-1.5">
                <Badge variant="outline" className="text-[10px]">{t.category}</Badge>
                <Badge variant={t.sideEffect === "mutating" ? "warning" : "secondary"} className="text-[10px]">
                  {t.sideEffect}
                </Badge>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
                <span>{t.installs} installs</span>
                <Button size="sm" variant="outline" onClick={() => toast.success(`${t.name} installed`)}>
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
