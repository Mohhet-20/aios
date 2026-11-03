import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  delta?: number;
  deltaLabel?: string;
  icon?: LucideIcon;
  className?: string;
}

/** KPI tile used across the Executive Dashboard, Analytics, and Cost views. */
export function StatCard({ label, value, delta, deltaLabel, icon: Icon, className }: StatCardProps) {
  const positive = (delta ?? 0) >= 0;
  return (
    <Card className={cn(className)}>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground">{label}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
        {typeof delta === "number" && (
          <p className={cn("mt-1 flex items-center gap-1 text-xs", positive ? "text-success" : "text-destructive")}>
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta)}% {deltaLabel ?? "vs last period"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
