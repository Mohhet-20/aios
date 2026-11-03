"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ColumnDef } from "@tanstack/react-table";
import { FlaskConical, Plus } from "lucide-react";

interface ExperimentRow { id: string; name: string; hypothesis: string; variant: string; metric: string; delta: number; status: "running" | "completed" | "draft"; }

const experiments: ExperimentRow[] = [
  { id: "e1", name: "Shorter system prompt", hypothesis: "Reduce latency without hurting accuracy", variant: "v3-short vs v3", metric: "-180ms latency", delta: 0.2, status: "completed" },
  { id: "e2", name: "Add few-shot examples", hypothesis: "Improve classification accuracy", variant: "v4-fewshot vs v3", metric: "+4.1% accuracy", delta: 4.1, status: "running" },
  { id: "e3", name: "Switch to Haiku for triage", hypothesis: "Cut cost while maintaining SLA", variant: "haiku vs sonnet", metric: "-71% cost", delta: -71, status: "completed" },
  { id: "e4", name: "Retrieval top-k = 8", hypothesis: "Improve groundedness on long docs", variant: "k=8 vs k=4", metric: "TBD", delta: 0, status: "draft" },
];

const columns: ColumnDef<ExperimentRow>[] = [
  { accessorKey: "name", header: "Experiment", cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
  { accessorKey: "hypothesis", header: "Hypothesis" },
  { accessorKey: "variant", header: "Variant" },
  { accessorKey: "metric", header: "Result" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge variant={row.original.status === "completed" ? "success" : row.original.status === "running" ? "warning" : "secondary"} className="capitalize">
        {row.original.status}
      </Badge>
    ),
  },
];

export default function ExperimentsPage() {
  return (
    <div>
      <PageHeader
        title="Experiment Tracking"
        description="A/B tests comparing prompt, model, and retrieval variants."
        actions={
          <Button size="sm">
            <Plus className="h-4 w-4" /> New experiment
          </Button>
        }
      />
      <DataTable columns={columns} data={experiments} searchKey="experiments" />
    </div>
  );
}
