import { Badge } from "@/components/ui/badge";
import type { ModelProvider } from "@/types";
import { cn } from "@/lib/utils";

const PROVIDER_COLOR: Record<ModelProvider, string> = {
  anthropic: "bg-chart-1/15 text-chart-1",
  openai: "bg-chart-2/15 text-chart-2",
  google: "bg-chart-3/15 text-chart-3",
  local: "bg-chart-4/15 text-chart-4",
  azure: "bg-chart-5/15 text-chart-5",
};

/** Consistent per-provider color used in Model Registry, Playground, and
 *  Cost dashboards so a provider is instantly recognizable everywhere. */
export function ModelProviderBadge({ provider }: { provider: ModelProvider }) {
  return (
    <Badge variant="outline" className={cn("border-transparent capitalize", PROVIDER_COLOR[provider])}>
      {provider}
    </Badge>
  );
}
