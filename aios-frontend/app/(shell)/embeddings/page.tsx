"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Cell } from "recharts";

const CLUSTERS = [
  { name: "Refunds & billing", color: "chart-1" },
  { name: "Technical issues", color: "chart-2" },
  { name: "Account access", color: "chart-3" },
  { name: "Fraud & risk", color: "chart-4" },
];

function generatePoints() {
  const points: { x: number; y: number; cluster: number; label: string }[] = [];
  CLUSTERS.forEach((c, ci) => {
    const cx = Math.cos((ci / CLUSTERS.length) * Math.PI * 2) * 40 + 50;
    const cy = Math.sin((ci / CLUSTERS.length) * Math.PI * 2) * 40 + 50;
    for (let i = 0; i < 18; i++) {
      const angle = (i * 37) % 360;
      const r = 4 + ((i * 13) % 10);
      points.push({
        x: Math.round((cx + Math.cos((angle * Math.PI) / 180) * r) * 10) / 10,
        y: Math.round((cy + Math.sin((angle * Math.PI) / 180) * r) * 10) / 10,
        cluster: ci,
        label: `${c.name} #${i + 1}`,
      });
    }
  });
  return points;
}

export default function EmbeddingsExplorerPage() {
  const points = useMemo(() => generatePoints(), []);
  const [selected, setSelected] = useState(points[0]);

  return (
    <div>
      <PageHeader title="Embeddings Explorer" description="2D projection (UMAP-style) of semantic memory embeddings, clustered by topic." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_300px]">
        <Card>
          <CardHeader>
            <CardTitle>Vector space projection</CardTitle>
            <CardDescription>{points.length} embeddings across {CLUSTERS.length} clusters</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={420}>
              <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" dataKey="x" hide />
                <YAxis type="number" dataKey="y" hide />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  formatter={((_: unknown, __: unknown, item: { payload: { label: string } }) => [item.payload.label, ""]) as never}
                />
                <Scatter
                  data={points}
                  onClick={(d: any) => setSelected(d)}
                  cursor="pointer"
                >
                  {points.map((p, i) => (
                    <Cell key={i} fill={`hsl(var(--${CLUSTERS[p.cluster].color}))`} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-3 flex flex-wrap gap-3">
              {CLUSTERS.map((c) => (
                <span key={c.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: `hsl(var(--${c.color}))` }} /> {c.name}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">Selected point</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="font-medium">{selected.label}</p>
            <Badge variant="outline">{CLUSTERS[selected.cluster].name}</Badge>
            <div className="space-y-1 pt-2 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>x</span><span className="font-mono">{selected.x}</span></div>
              <div className="flex justify-between"><span>y</span><span className="font-mono">{selected.y}</span></div>
              <div className="flex justify-between"><span>Embedding model</span><span className="font-mono">text-embed-3</span></div>
              <div className="flex justify-between"><span>Dimensions</span><span className="font-mono">1536</span></div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
