"use client";

import { PageHeader } from "@/components/shared/page-header";
import { LiveTable } from "@/components/shared/live-table";
import { Badge } from "@/components/ui/badge";
import { useModels } from "@/services/console";
import { humanize } from "@/lib/utils";

export default function ModelRegistryPage() {
  const models = useModels();
  return (
    <div>
      <PageHeader
        title="Model Registry"
        description="Models the AI Core gateway can route to, with capabilities and list pricing (configurable, not fetched from a billing API)."
      />
      <LiveTable
        caption="Models"
        query={models}
        rowKey={(m) => `${m.provider}:${m.name}`}
        empty="AI Core has no models registered."
        columns={[
          { header: "Model", cell: (m) => <span className="font-medium">{m.name}</span> },
          { header: "Provider", cell: (m) => <Badge variant="outline">{humanize(m.provider)}</Badge> },
          { header: "Context", cell: (m) => <span className="font-mono">{m.contextWindow.toLocaleString()}</span>, className: "text-right" },
          {
            header: "Price / 1M tokens",
            cell: (m) => (
              <span className="font-mono text-xs">
                ${m.inputCostPer1M.toFixed(2)} in · ${m.outputCostPer1M.toFixed(2)} out
              </span>
            ),
          },
          {
            header: "Capabilities",
            cell: (m) => (
              <div className="flex flex-wrap gap-1">
                {m.capabilities.map((c) => (
                  <Badge key={c} variant="secondary" className="text-[10px]">
                    {humanize(c)}
                  </Badge>
                ))}
              </div>
            ),
          },
          {
            header: "Status",
            cell: (m) => (
              <Badge variant={m.status === "available" ? "success" : "secondary"} className="capitalize">
                {m.status}
              </Badge>
            ),
          },
        ]}
      />
    </div>
  );
}
