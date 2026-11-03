"use client";

import Link from "next/link";
import { PageHeader } from "@/components/shared/page-header";
import { LiveTable, NameCell } from "@/components/shared/live-table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useWorkflows } from "@/services/console";
import { humanize, timeAgo } from "@/lib/utils";

export default function WorkflowsPage() {
  const workflows = useWorkflows();
  return (
    <div>
      <PageHeader
        title="Workflows"
        description="Workflow definitions in the workflow engine: category, lifecycle status and priority."
        actions={
          <Button size="sm" variant="outline" asChild>
            <Link href="/workflows/builder">Open builder</Link>
          </Button>
        }
      />
      <LiveTable
        caption="Workflows"
        query={workflows}
        empty="No workflows yet. Run scripts/seed_demo.py to load the demo set."
        columns={[
          { header: "Workflow", cell: (w) => <NameCell name={w.name} description={w.description} /> },
          { header: "Category", cell: (w) => humanize(w.category) },
          {
            header: "Status",
            cell: (w) => (
              <Badge variant={w.status === "published" || w.status === "active" ? "success" : "secondary"} className="capitalize">
                {humanize(w.status)}
              </Badge>
            ),
          },
          { header: "Priority", cell: (w) => <span className="capitalize">{w.priority ?? "—"}</span> },
          { header: "Updated", cell: (w) => <span className="text-muted-foreground">{timeAgo(w.updatedAt) ?? "—"}</span> },
        ]}
      />
    </div>
  );
}
