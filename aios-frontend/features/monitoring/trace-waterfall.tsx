"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface Span {
  id: string;
  name: string;
  start: number; // ms offset
  duration: number; // ms
  layer: "gateway" | "agent" | "prompt" | "memory" | "ai-core" | "tool";
}

const LAYER_COLOR: Record<Span["layer"], string> = {
  gateway: "bg-chart-5",
  agent: "bg-chart-1",
  prompt: "bg-chart-2",
  memory: "bg-chart-3",
  "ai-core": "bg-primary",
  tool: "bg-chart-4",
};

const SPANS: Span[] = [
  { id: "s1", name: "API Gateway — auth + route", start: 0, duration: 12, layer: "gateway" },
  { id: "s2", name: "Agent Engine — Support Triage", start: 12, duration: 420, layer: "agent" },
  { id: "s3", name: "Prompt Engine — render template", start: 14, duration: 8, layer: "prompt" },
  { id: "s4", name: "Memory Engine — semantic query", start: 24, duration: 68, layer: "memory" },
  { id: "s5", name: "AI Core — claude-haiku-4.5 generation", start: 95, duration: 290, layer: "ai-core" },
  { id: "s6", name: "Tool Engine — kb_search", start: 130, duration: 140, layer: "tool" },
  { id: "s7", name: "API Gateway — stream response", start: 432, duration: 6, layer: "gateway" },
];

const TOTAL = 460;

/**
 * Waterfall / execution timeline for a single request trace — the
 * Observability engine's per-span tracing concept made visual. Clicking a
 * span shows its detail, mirroring how a real distributed trace explorer
 * (Honeycomb, Jaeger) would render a request through AIOS's engines.
 */
export function TraceWaterfall() {
  const [selected, setSelected] = useState<string>(SPANS[4].id);
  const span = SPANS.find((s) => s.id === selected)!;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_280px]">
      <div className="space-y-1.5 rounded-xl border border-border p-4">
        {SPANS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSelected(s.id)}
            className="group flex w-full items-center gap-3 rounded-md px-1 py-1.5 text-left hover:bg-muted/50"
          >
            <span className="w-56 shrink-0 truncate text-xs text-muted-foreground group-hover:text-foreground">{s.name}</span>
            <div className="relative h-4 flex-1 rounded bg-muted/40">
              <div
                className={cn("absolute h-4 rounded transition-all", LAYER_COLOR[s.layer], selected === s.id && "ring-2 ring-ring")}
                style={{ left: `${(s.start / TOTAL) * 100}%`, width: `${Math.max((s.duration / TOTAL) * 100, 1)}%` }}
              />
            </div>
            <span className="w-14 shrink-0 text-right font-mono text-xs text-muted-foreground">{s.duration}ms</span>
          </button>
        ))}
      </div>

      <div className="space-y-3 rounded-xl border border-border p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Span detail</p>
        <div>
          <p className="text-sm font-medium">{span.name}</p>
          <p className="mt-1 text-xs text-muted-foreground">layer: {span.layer}</p>
        </div>
        <div className="space-y-1.5 text-xs">
          <div className="flex justify-between"><span className="text-muted-foreground">Start offset</span><span className="font-mono">{span.start}ms</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Duration</span><span className="font-mono">{span.duration}ms</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Trace ID</span><span className="font-mono">tr_88a2f1</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Tenant</span><span className="font-mono">org_1 / ws_1</span></div>
        </div>
      </div>
    </div>
  );
}
