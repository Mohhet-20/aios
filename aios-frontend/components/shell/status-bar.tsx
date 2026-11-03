"use client";

import { StatusDot } from "@/components/shared/status-dot";
import { Activity, History } from "lucide-react";
import { useUIStore } from "@/stores/ui-store";
import { usePlatformStatus } from "@/services/console";

/** Persistent footer: live platform readiness on every page, from the same probe as the dashboard's health card
 *  (every service's /health/ready, latency measured by the edge). */
export function StatusBar() {
  const toggleActivityFeed = useUIStore((s) => s.toggleActivityFeed);
  const status = usePlatformStatus();
  const services = status.data ?? [];
  const ready = services.filter((s) => s.ready).length;
  const slowest = Math.max(0, ...services.map((s) => s.latencyMs ?? 0));
  const state = status.error ? "down" : !status.data ? "idle" : ready === services.length ? "healthy" : "degraded";
  return (
    <div className="flex h-7 items-center justify-between border-t border-border bg-card px-4 text-[11px] text-muted-foreground">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <StatusDot status={state} />
          {status.error ? "Platform status unavailable" : !status.data ? "Checking services…" : `${ready}/${services.length} services ready`}
        </span>
        {status.data && (
          <span className="flex items-center gap-1.5">
            <Activity className="h-3 w-3" /> slowest readiness probe {slowest} ms
          </span>
        )}
      </div>
      <button onClick={toggleActivityFeed} className="flex items-center gap-1.5 hover:text-foreground">
        <History className="h-3 w-3" /> Activity
      </button>
    </div>
  );
}
