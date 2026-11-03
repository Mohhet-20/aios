"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusDot } from "@/components/shared/status-dot";
import type { ServiceStatus } from "@/types/live";

/** Readiness of every service as probed by the edge just now (GET /health/ready, latency measured). */
export function PlatformHealth({ services }: { services: ServiceStatus[] }) {
  const ready = services.filter((s) => s.ready).length;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Platform health</CardTitle>
        <CardDescription>
          {ready}/{services.length} services ready, probed live by the console edge every 15 seconds.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2 xl:grid-cols-4" aria-label="Service readiness">
          {services.map((s) => (
            <li key={s.name} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-2">
                <StatusDot status={s.ready ? "healthy" : "down"} />
                <span className="truncate">{s.label}</span>
              </span>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {s.ready && s.latencyMs !== null ? `${s.latencyMs} ms` : "down"}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
