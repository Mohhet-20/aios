"use client";

import { PageHeader } from "@/components/shared/page-header";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";

interface UserRow { id: string; name: string; email: string; role: "owner" | "admin" | "member" | "viewer"; lastActive: string; status: "active" | "invited"; }

const users: UserRow[] = [
  { id: "u1", name: "Mohhet", email: "balakamohit@gmail.com", role: "owner", lastActive: "Just now", status: "active" },
  { id: "u2", name: "Priya Sharma", email: "priya@acme.com", role: "admin", lastActive: "2 hours ago", status: "active" },
  { id: "u3", name: "Dana Kim", email: "dana@acme.com", role: "member", lastActive: "1 day ago", status: "active" },
  { id: "u4", name: "Sam Torres", email: "sam@acme.com", role: "viewer", lastActive: "—", status: "invited" },
];

const columns: ColumnDef<UserRow>[] = [
  {
    accessorKey: "name",
    header: "User",
    cell: ({ row }) => (
      <div className="flex items-center gap-2.5">
        <Avatar className="h-7 w-7">
          <AvatarFallback className="text-[10px]">{row.original.name.split(" ").map((n) => n[0]).join("")}</AvatarFallback>
        </Avatar>
        <div>
          <p className="font-medium">{row.original.name}</p>
          <p className="text-xs text-muted-foreground">{row.original.email}</p>
        </div>
      </div>
    ),
  },
  { accessorKey: "role", header: "Role", cell: ({ row }) => <Badge variant="outline" className="capitalize">{row.original.role}</Badge> },
  { accessorKey: "lastActive", header: "Last active" },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <Badge variant={row.original.status === "active" ? "success" : "warning"} className="capitalize">{row.original.status}</Badge>,
  },
];

export default function UsersPage() {
  return (
    <div>
      <PageHeader
        title="Users"
        description="Everyone with access to this organization."
        actions={<Button size="sm"><Plus className="h-4 w-4" /> Invite user</Button>}
      />
      <DataTable columns={columns} data={users} searchKey="users" />
    </div>
  );
}
