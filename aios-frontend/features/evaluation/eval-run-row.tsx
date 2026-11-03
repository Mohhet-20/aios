"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { EvalRun } from "@/types";
import { ArrowDownRight, ArrowUpRight, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export function EvalRunRow({ run }: { run: EvalRun }) {
  const delta = run.previousScore != null ? +(run.score - run.previousScore).toFixed(1) : null;
  return (
    <div className="grid grid-cols-12 items-center gap-3 rounded-lg border border-border px-4 py-3 text-sm">
      <div className="col-span-4">
        <p className="font-medium">{run.target}</p>
        <p className="text-xs text-muted-foreground">{run.suiteName}</p>
      </div>
      <div className="col-span-3">
        <div className="flex items-center gap-2">
          <Progress value={run.total ? (run.passed / run.total) * 100 : 0} className="h-1.5" />
          <span className="w-14 shrink-0 font-mono text-xs text-muted-foreground">
            {run.passed}/{run.total}
          </span>
        </div>
      </div>
      <div className="col-span-2 font-mono text-sm">
        {run.status === "running" ? (
          <span className="flex items-center gap-1 text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" /> running
          </span>
        ) : (
          <span className="font-semibold">{run.score}%</span>
        )}
      </div>
      <div className="col-span-1">
        {delta != null && (
          <span className={`flex items-center gap-0.5 text-xs ${delta >= 0 ? "text-success" : "text-destructive"}`}>
            {delta >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta)}
          </span>
        )}
      </div>
      <div className="col-span-2 text-right text-xs text-muted-foreground">{formatDistanceToNow(new Date(run.createdAt), { addSuffix: true })}</div>
    </div>
  );
}
