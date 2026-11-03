"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiKeys } from "@/lib/mock-data";
import type { ApiKey } from "@/types";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus, Copy, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";

const columns: ColumnDef<ApiKey>[] = [
  { accessorKey: "name", header: "Name", cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
  {
    accessorKey: "prefix",
    header: "Key",
    cell: ({ row }) => (
      <span className="flex items-center gap-2 font-mono text-xs">
        {row.original.prefix}••••••••
        <button onClick={() => toast.success("Copied to clipboard")}>
          <Copy className="h-3.5 w-3.5 text-muted-foreground hover:text-foreground" />
        </button>
      </span>
    ),
  },
  {
    id: "scopes",
    header: "Scopes",
    cell: ({ row }) => (
      <div className="flex gap-1">
        {row.original.scopes.map((s) => (
          <Badge key={s} variant="secondary" className="font-mono text-[10px]">{s}</Badge>
        ))}
      </div>
    ),
  },
  { accessorKey: "lastUsed", header: "Last used", cell: ({ row }) => row.original.lastUsed ? new Date(row.original.lastUsed).toLocaleDateString() : "Never" },
  {
    id: "actions",
    header: "",
    cell: () => (
      <Button variant="ghost" size="icon" onClick={() => toast.error("Key revoked")}>
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    ),
  },
];

export default function ApiKeysPage() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <PageHeader
        title="API Keys"
        description="Manage programmatic access to the AIOS API."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm"><Plus className="h-4 w-4" /> Create key</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create API key</DialogTitle>
                <DialogDescription>The key will be shown once — store it securely.</DialogDescription>
              </DialogHeader>
              <div className="space-y-1.5">
                <Label htmlFor="key-name">Name</Label>
                <Input id="key-name" placeholder="e.g. Production Backend" />
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button onClick={() => { toast.success("API key created"); setOpen(false); }}>Create</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />
      <DataTable columns={columns} data={apiKeys} searchKey="keys" />
    </div>
  );
}
