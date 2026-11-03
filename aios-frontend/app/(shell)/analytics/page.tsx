"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { TrendAreaChart } from "@/components/charts/trend-area-chart";
import { ComparisonBarChart } from "@/components/charts/comparison-bar-chart";
import { DonutChart } from "@/components/charts/donut-chart";
import { tokenUsageSeries, costSeries, workspaces } from "@/lib/mock-data";

const byWorkspace = workspaces.map((w, i) => ({ name: w.name.split(" ")[0], Requests: 1200 + i * 640, Cost: 220 + i * 95 }));
const byProvider = [
  { name: "Anthropic", value: 62, color: "chart-1" },
  { name: "OpenAI", value: 24, color: "chart-2" },
  { name: "Google", value: 9, color: "chart-3" },
  { name: "Local", value: 5, color: "chart-4" },
];

export default function AnalyticsPage() {
  return (
    <div>
      <PageHeader title="Analytics" description="Usage patterns across workspaces, providers, and time." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Requests by workspace</CardTitle>
            <CardDescription>Last 30 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <ComparisonBarChart
              data={byWorkspace}
              xKey="name"
              bars={[{ key: "Requests", color: "chart-1", label: "Requests" }]}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Spend by provider</CardTitle>
            <CardDescription>Share of total monthly spend.</CardDescription>
          </CardHeader>
          <CardContent>
            <DonutChart data={byProvider} />
            <div className="mt-2 space-y-1">
              {byProvider.map((p) => (
                <div key={p.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: `hsl(var(--${p.color}))` }} /> {p.name}
                  </span>
                  <span className="font-mono">{p.value}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Token usage trend</CardTitle>
            <CardDescription>Organization-wide, last 14 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendAreaChart data={tokenUsageSeries} color="chart-1" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Cost trend</CardTitle>
            <CardDescription>Organization-wide, last 14 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendAreaChart data={costSeries} color="chart-4" valueFormatter="currency" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
