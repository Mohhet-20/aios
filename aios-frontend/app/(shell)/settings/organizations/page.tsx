"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { organizations } from "@/lib/mock-data";
import type { Organization } from "@/types";
import type { ColumnDef } from "@tanstack/react-table";

const columns: ColumnDef<Organization>[] = [
  {
    accessorKey: "name",
    header: "Organization",
    cell: ({ row }) => (
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/15 text-[10px] font-bold text-primary">
          {row.original.logoInitials}
        </div>
        <span className="font-medium">{row.original.name}</span>
      </div>
    ),
  },
  { accessorKey: "plan", header: "Plan", cell: ({ row }) => <Badge variant="outline" className="capitalize">{row.original.plan}</Badge> },
];

export default function OrganizationsPage() {
  return (
    <div>
      <PageHeader title="Organizations" description="Organizations you belong to or administer." />
      <DataTable columns={columns} data={organizations} searchKey="organizations" />
    </div>
  );
}
