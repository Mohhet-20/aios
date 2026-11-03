import { cn } from "@/lib/utils";

export type Status = "healthy" | "degraded" | "down" | "idle" | "running" | "success" | "failed" | "pending";

const STATUS_COLOR: Record<Status, string> = {
  healthy: "bg-success",
  success: "bg-success",
  running: "bg-primary",
  idle: "bg-muted-foreground",
  pending: "bg-warning",
  degraded: "bg-warning",
  down: "bg-destructive",
  failed: "bg-destructive",
};

export function StatusDot({ status, pulse = false }: { status: Status; pulse?: boolean }) {
  return (
    <span className="relative flex h-2 w-2">
      {pulse && <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", STATUS_COLOR[status])} />}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", STATUS_COLOR[status])} />
    </span>
  );
}
