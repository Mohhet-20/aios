"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UsersRound, Plus } from "lucide-react";

const teams = [
  { id: "t1", name: "Support Engineering", members: 8, workspaces: 2 },
  { id: "t2", name: "Data & ML", members: 5, workspaces: 3 },
  { id: "t3", name: "Platform", members: 4, workspaces: 4 },
];

export default function TeamsPage() {
  return (
    <div>
      <PageHeader
        title="Teams"
        description="Group users for access control and workspace assignment."
        actions={<Button size="sm"><Plus className="h-4 w-4" /> New team</Button>}
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {teams.map((t) => (
          <Card key={t.id}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <UsersRound className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium">{t.name}</p>
                <p className="text-xs text-muted-foreground">{t.members} members · {t.workspaces} workspaces</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
