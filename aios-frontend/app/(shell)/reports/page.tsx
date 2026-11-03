"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, FileBarChart, Plus } from "lucide-react";

const reports = [
  { id: "r1", name: "Weekly Executive Summary", period: "Jul 13 – Jul 19, 2026", generatedAt: "2026-07-20", format: "PDF" },
  { id: "r2", name: "Monthly Cost & Usage Report", period: "June 2026", generatedAt: "2026-07-01", format: "XLSX" },
  { id: "r3", name: "Evaluation Regression Report", period: "Jul 14 – Jul 20, 2026", generatedAt: "2026-07-20", format: "PDF" },
  { id: "r4", name: "Security & Access Audit", period: "Q2 2026", generatedAt: "2026-07-01", format: "PDF" },
];

export default function ReportsPage() {
  return (
    <div>
      <PageHeader
        title="Reports"
        description="Scheduled and on-demand reports for leadership, finance, and compliance."
        actions={
          <Button size="sm">
            <Plus className="h-4 w-4" /> Generate report
          </Button>
        }
      />
      <div className="space-y-2">
        {reports.map((r) => (
          <Card key={r.id}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <FileBarChart className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm font-medium">{r.name}</p>
                  <p className="text-xs text-muted-foreground">{r.period} · generated {r.generatedAt}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{r.format}</Badge>
                <Button size="sm" variant="outline">
                  <Download className="h-3.5 w-3.5" /> Download
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
