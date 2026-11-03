"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { auditLogs } from "@/lib/mock-data";
import type { AuditLogEntry } from "@/types";
import type { ColumnDef } from "@tanstack/react-table";

const columns: ColumnDef<AuditLogEntry>[] = [
  { accessorKey: "actor", header: "Actor", cell: ({ row }) => <span className="font-mono text-xs">{row.original.actor}</span> },
  { accessorKey: "action", header: "Action", cell: ({ row }) => <span className="font-mono text-xs">{row.original.action}</span> },
  { accessorKey: "resource", header: "Resource" },
  { accessorKey: "ip", header: "IP address", cell: ({ row }) => <span className="font-mono text-xs">{row.original.ip}</span> },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <Badge variant={row.original.status === "success" ? "success" : "destructive"} className="capitalize">{row.original.status}</Badge>,
  },
  {
    accessorKey: "createdAt",
    header: "Time",
    cell: ({ row }) => new Date(row.original.createdAt).toLocaleString(),
  },
];

export default function AuditLogsPage() {
  return (
    <div>
      <PageHeader title="Audit Logs" description="Every sensitive action across the platform, for compliance and security review." />
      <DataTable columns={columns} data={auditLogs} searchKey="audit logs" />
    </div>
  );
}
