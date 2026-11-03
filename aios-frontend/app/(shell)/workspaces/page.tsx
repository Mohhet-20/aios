"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { workspaces, organizations } from "@/lib/mock-data";
import type { Workspace } from "@/types";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";

const columns: ColumnDef<Workspace>[] = [
  {
    accessorKey: "name",
    header: "Workspace",
    cell: ({ row }) => (
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: `hsl(var(--${row.original.color}))` }} />
        <span className="font-medium">{row.original.name}</span>
      </div>
    ),
  },
  {
    accessorKey: "organizationId",
    header: "Organization",
    cell: ({ row }) => organizations.find((o) => o.id === row.original.organizationId)?.name,
  },
  { accessorKey: "memberCount", header: "Members" },
  {
    id: "status",
    header: "Status",
    cell: () => <Badge variant="success">Active</Badge>,
  },
];

export default function WorkspacesPage() {
  return (
    <div>
      <PageHeader
        title="Workspaces"
        description="Isolated environments for a team, project, or environment within your organization."
        actions={
          <Button size="sm">
            <Plus className="h-4 w-4" /> New workspace
          </Button>
        }
      />
      <DataTable columns={columns} data={workspaces} searchKey="workspaces" />
    </div>
  );
}
