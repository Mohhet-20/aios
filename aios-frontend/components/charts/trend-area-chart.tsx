"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber } from "@/lib/utils";

type ValueFormatKind = "number" | "currency" | "ms" | "percent";

// Note: "currency" intentionally replicates the original inline `$${v}`
// callers used (a plain prefix, no grouping/decimals) rather than switching
// to `formatCurrency` — preserving exact prior chart-label behavior.
const FORMATTERS: Record<ValueFormatKind, (v: number) => string> = {
  number: (v) => formatNumber(v),
  currency: (v) => `$${v}`,
  ms: (v) => `${Math.round(v)}ms`,
  percent: (v) => `${v}%`,
};

interface TrendAreaChartProps {
  data: { date: string; value: number }[];
  color?: "chart-1" | "chart-2" | "chart-3" | "chart-4" | "chart-5";
  /**
   * A serializable formatter *kind* rather than a function prop: this
   * component is a Client Component, but several of its callers (e.g.
   * `app/(shell)/dashboard/page.tsx`) are Server Components, and functions
   * cannot cross the Server -> Client Component boundary as props. Passing
   * `(v) => formatNumber(v)` directly used to break the production build
   * (dev mode didn't catch it) — this enum keeps the actual formatting
   * logic inside the Client Component instead.
   */
  valueFormatter?: ValueFormatKind;
  height?: number;
}

/**
 * Shared time-series area chart used for token usage, cost, latency, and
 * error-rate trends across the Dashboard, Monitoring, and Analytics pages.
 * One implementation means one place to fix tooltip/axis/theming behavior.
 */
export function TrendAreaChart({ data, color = "chart-1", valueFormatter = "number", height = 220 }: TrendAreaChartProps) {
  const format = FORMATTERS[valueFormatter];
  const varColor = `hsl(var(--${color}))`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`fill-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={varColor} stopOpacity={0.35} />
            <stop offset="95%" stopColor={varColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={format}
          width={48}
        />
        <Tooltip
          contentStyle={{
            background: "hsl(var(--popover))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value: number) => [format(value), "Value"]}
        />
        <Area type="monotone" dataKey="value" stroke={varColor} strokeWidth={2} fill={`url(#fill-${color})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
