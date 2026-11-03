"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ColumnDef } from "@tanstack/react-table";
import { Upload, FileText } from "lucide-react";

interface DocRow { id: string; name: string; collection: string; size: string; status: "indexed" | "processing" | "failed"; updated: string; }

const docs: DocRow[] = [
  { id: "d1", name: "refund-policy-v3.pdf", collection: "Support Playbooks", size: "142 KB", status: "indexed", updated: "2026-07-18" },
  { id: "d2", name: "api-rate-limits.md", collection: "Product Documentation", size: "8 KB", status: "indexed", updated: "2026-07-15" },
  { id: "d3", name: "incident-response.md", collection: "Engineering Runbooks", size: "22 KB", status: "processing", updated: "2026-07-20" },
  { id: "d4", name: "vendor-contract-template.docx", collection: "Legal & Compliance", size: "310 KB", status: "failed", updated: "2026-07-10" },
];

const columns: ColumnDef<DocRow>[] = [
  {
    accessorKey: "name",
    header: "Document",
    cell: ({ row }) => (
      <span className="flex items-center gap-2 font-medium">
        <FileText className="h-4 w-4 text-muted-foreground" /> {row.original.name}
      </span>
    ),
  },
  { accessorKey: "collection", header: "Collection" },
  { accessorKey: "size", header: "Size" },
  {
    accessorKey: "status",
    header: "Indexing status",
    cell: ({ row }) => (
      <Badge variant={row.original.status === "indexed" ? "success" : row.original.status === "processing" ? "warning" : "destructive"} className="capitalize">
        {row.original.status}
      </Badge>
    ),
  },
  { accessorKey: "updated", header: "Updated" },
];

export default function DocumentsPage() {
  return (
    <div>
      <PageHeader
        title="Document Management"
        description="Upload and manage source documents ingested into the knowledge base."
        actions={
          <Button size="sm">
            <Upload className="h-4 w-4" /> Upload document
          </Button>
        }
      />
      <DataTable columns={columns} data={docs} searchKey="documents" />
    </div>
  );
}
