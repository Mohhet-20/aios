"use client";

import { PageHeader } from "@/components/shared/page-header";
import { LiveTable, NameCell } from "@/components/shared/live-table";
import { StatusDot } from "@/components/shared/status-dot";
import { Badge } from "@/components/ui/badge";
import { useTools } from "@/services/console";
import { humanize, timeAgo } from "@/lib/utils";

export default function ToolsPage() {
  const tools = useTools();
  return (
    <div>
      <PageHeader
        title="Tools"
        description="Tools registered in the tool execution platform. Each runs through a typed connector, with credentials kept in the platform's vault."
      />
      <LiveTable
        caption="Tools"
        query={tools}
        empty="No tools yet. Run scripts/seed_demo.py to register the demo tools."
        columns={[
          { header: "Tool", cell: (t) => <NameCell name={t.name} description={t.description} /> },
          { header: "Connector", cell: (t) => <Badge variant="outline">{humanize(t.category)}</Badge> },
          { header: "Status", cell: (t) => <span className="capitalize">{humanize(t.status)}</span> },
          {
            header: "Health",
            cell: (t) => (
              <span className="flex items-center gap-1.5 capitalize">
                <StatusDot status={t.health === "healthy" ? "healthy" : t.health === "unhealthy" ? "down" : "idle"} />
                {t.health ?? "unknown"}
              </span>
            ),
          },
          { header: "Updated", cell: (t) => <span className="text-muted-foreground">{timeAgo(t.updatedAt) ?? "—"}</span> },
        ]}
      />
    </div>
  );
}
