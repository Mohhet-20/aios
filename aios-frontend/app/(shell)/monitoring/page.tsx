import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { TrendAreaChart } from "@/components/charts/trend-area-chart";
import { StatusDot } from "@/components/shared/status-dot";
import { latencyP95Series, errorRateSeries, models } from "@/lib/mock-data";
import { Gauge, Timer, AlertTriangle, Server } from "lucide-react";
import { formatLatency } from "@/lib/utils";

const services = [
  { name: "API Gateway", status: "healthy" as const, uptime: "99.99%" },
  { name: "Agent Engine", status: "healthy" as const, uptime: "99.97%" },
  { name: "Workflow Engine", status: "healthy" as const, uptime: "99.95%" },
  { name: "Memory Engine (vector store)", status: "degraded" as const, uptime: "99.42%" },
  { name: "Evaluation Engine", status: "healthy" as const, uptime: "100%" },
  { name: "Anthropic provider", status: "healthy" as const, uptime: "99.98%" },
  { name: "OpenAI provider", status: "healthy" as const, uptime: "99.91%" },
  { name: "Local inference cluster", status: "down" as const, uptime: "94.10%" },
];

export default function MonitoringPage() {
  return (
    <div>
      <PageHeader title="Monitoring" description="Real-time platform health across every engine and model provider." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="p95 latency" value={formatLatency(820)} delta={-6.1} icon={Timer} />
        <StatCard label="Error rate (24h)" value="1.2%" delta={0.4} deltaLabel="vs yesterday" icon={AlertTriangle} />
        <StatCard label="Requests / min" value="4,812" delta={11.3} icon={Gauge} />
        <StatCard label="Services degraded" value="1 of 8" icon={Server} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>p95 latency</CardTitle>
            <CardDescription>Across all model providers, last 14 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendAreaChart data={latencyP95Series} color="chart-2" valueFormatter="ms" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Error rate</CardTitle>
            <CardDescription>Percentage of failed requests, last 14 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <TrendAreaChart data={errorRateSeries} color="chart-5" valueFormatter="percent" />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Service health</CardTitle>
          <CardDescription>Every engine and provider AIOS depends on.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {services.map((s) => (
            <div key={s.name} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm">
              <div className="flex items-center gap-2">
                <StatusDot status={s.status} pulse={s.status !== "healthy"} />
                {s.name}
              </div>
              <span className="font-mono text-xs text-muted-foreground">{s.uptime}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
