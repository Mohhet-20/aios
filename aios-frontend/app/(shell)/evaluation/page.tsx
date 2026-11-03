"use client";

import { PageHeader } from "@/components/shared/page-header";
import { LiveTable, NameCell } from "@/components/shared/live-table";
import { Badge } from "@/components/ui/badge";
import { useDatasets, useEvaluations } from "@/services/console";
import { humanize, timeAgo } from "@/lib/utils";

export default function EvaluationPage() {
  const evaluations = useEvaluations();
  const datasets = useDatasets();
  return (
    <div className="space-y-6">
      <PageHeader
        title="Evaluation"
        description="Evaluation suites and datasets in the evaluation platform: the quality gates prompts and agents are promoted through."
      />
      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Evaluation suites</h2>
        <LiveTable
          caption="Evaluation suites"
          query={evaluations}
          empty="No evaluation suites yet."
          columns={[
            { header: "Suite", cell: (e) => <NameCell name={e.name} description={e.description} /> },
            { header: "Category", cell: (e) => <Badge variant="outline">{humanize(e.category)}</Badge> },
            { header: "Status", cell: (e) => <span className="capitalize">{humanize(e.status)}</span> },
            { header: "Updated", cell: (e) => <span className="text-muted-foreground">{timeAgo(e.updatedAt) ?? "—"}</span> },
          ]}
        />
      </section>
      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Datasets</h2>
        <LiveTable
          caption="Datasets"
          query={datasets}
          empty="No datasets yet."
          columns={[
            { header: "Dataset", cell: (d) => <NameCell name={d.name} description={d.description} /> },
            { header: "Type", cell: (d) => <Badge variant="outline">{humanize(d.type)}</Badge> },
            { header: "Status", cell: (d) => <span className="capitalize">{humanize(d.status)}</span> },
            { header: "Updated", cell: (d) => <span className="text-muted-foreground">{timeAgo(d.updatedAt) ?? "—"}</span> },
          ]}
        />
      </section>
    </div>
  );
}
