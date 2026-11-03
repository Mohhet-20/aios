"use client";

import { PageHeader } from "@/components/shared/page-header";
import { LiveTable, NameCell } from "@/components/shared/live-table";
import { Badge } from "@/components/ui/badge";
import { usePrompts } from "@/services/console";
import { humanize, timeAgo } from "@/lib/utils";

export default function PromptLibraryPage() {
  const prompts = usePrompts();
  return (
    <div>
      <PageHeader
        title="Prompt Library"
        description="Prompt templates in the prompt platform: versioning, visibility and promotion status per prompt."
      />
      <LiveTable
        caption="Prompts"
        query={prompts}
        empty="No prompts yet. Run scripts/seed_demo.py to load the demo library."
        columns={[
          { header: "Prompt", cell: (p) => <NameCell name={p.name} description={p.description} /> },
          {
            header: "Status",
            cell: (p) => (
              <Badge variant={p.status === "production" || p.status === "active" ? "success" : "secondary"} className="capitalize">
                {humanize(p.status)}
              </Badge>
            ),
          },
          { header: "Visibility", cell: (p) => <span className="capitalize">{p.visibility ?? "—"}</span> },
          { header: "Versions", cell: (p) => <span className="font-mono">{p.latestVersion}</span>, className: "text-right" },
          { header: "Updated", cell: (p) => <span className="text-muted-foreground">{timeAgo(p.updatedAt) ?? "—"}</span> },
        ]}
      />
    </div>
  );
}
