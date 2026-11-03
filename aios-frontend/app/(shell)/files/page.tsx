"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import type { ColumnDef } from "@tanstack/react-table";
import { Upload, File, FolderOpen } from "lucide-react";

interface FileRow { id: string; name: string; kind: "folder" | "file"; size: string; modified: string; }

const files: FileRow[] = [
  { id: "f1", name: "eval-reports", kind: "folder", size: "—", modified: "2026-07-19" },
  { id: "f2", name: "prompt-exports", kind: "folder", size: "—", modified: "2026-07-14" },
  { id: "f3", name: "q2-fraud-summary.csv", kind: "file", size: "1.2 MB", modified: "2026-07-18" },
  { id: "f4", name: "support-transcripts-sample.json", kind: "file", size: "482 KB", modified: "2026-07-12" },
];

const columns: ColumnDef<FileRow>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => (
      <span className="flex items-center gap-2 font-medium">
        {row.original.kind === "folder" ? <FolderOpen className="h-4 w-4 text-muted-foreground" /> : <File className="h-4 w-4 text-muted-foreground" />}
        {row.original.name}
      </span>
    ),
  },
  { accessorKey: "size", header: "Size" },
  { accessorKey: "modified", header: "Modified" },
];

export default function FilesPage() {
  return (
    <div>
      <PageHeader
        title="Files"
        description="Shared file storage for exports, reports, and working data."
        actions={
          <Button size="sm">
            <Upload className="h-4 w-4" /> Upload
          </Button>
        }
      />
      <DataTable columns={columns} data={files} searchKey="files" />
    </div>
  );
}
