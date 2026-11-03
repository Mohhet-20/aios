"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";

interface DatasetRow { id: string; name: string; rows: number; usedBy: string; lastUpdated: string; type: "golden" | "training" | "reference"; }

const datasets: DatasetRow[] = [
  { id: "ds1", name: "Support Classifier Golden Set", rows: 200, usedBy: "Evaluation Engine", lastUpdated: "2026-07-15", type: "golden" },
  { id: "ds2", name: "KB Answerer Groundedness Set", rows: 100, usedBy: "Evaluation Engine", lastUpdated: "2026-07-10", type: "golden" },
  { id: "ds3", name: "Historical Support Tickets", rows: 48213, usedBy: "Memory Engine (episodic seed)", lastUpdated: "2026-06-30", type: "reference" },
  { id: "ds4", name: "Fraud Labels 2026 H1", rows: 91442, usedBy: "Fraud Scorer training", lastUpdated: "2026-07-01", type: "training" },
];

const columns: ColumnDef<DatasetRow>[] = [
  { accessorKey: "name", header: "Dataset", cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
  { accessorKey: "rows", header: "Rows", cell: ({ row }) => row.original.rows.toLocaleString() },
  { accessorKey: "usedBy", header: "Used by" },
  {
    accessorKey: "type",
    header: "Type",
    cell: ({ row }) => <Badge variant="outline" className="capitalize">{row.original.type}</Badge>,
  },
  { accessorKey: "lastUpdated", header: "Last updated" },
];

export default function DatasetsPage() {
  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Golden sets, training data, and reference corpora used across the platform."
        actions={
          <Button size="sm">
            <Plus className="h-4 w-4" /> Upload dataset
          </Button>
        }
      />
      <DataTable columns={columns} data={datasets} searchKey="datasets" />
    </div>
  );
}
