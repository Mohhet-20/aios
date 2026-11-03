"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useNotificationStore } from "@/stores/notification-store";
import { CheckCheck } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";

const DOT_COLOR = { info: "bg-primary", success: "bg-success", warning: "bg-warning", error: "bg-destructive" } as const;

export default function NotificationsPage() {
  const { items, markAllRead, markRead } = useNotificationStore();

  return (
    <div>
      <PageHeader
        title="Notifications"
        description="System alerts, evaluation results, and platform events."
        actions={
          <Button size="sm" variant="outline" onClick={markAllRead}>
            <CheckCheck className="h-4 w-4" /> Mark all read
          </Button>
        }
      />
      <div className="space-y-2">
        {items.map((n) => (
          <Card key={n.id} className={cn(!n.read && "border-primary/40")}>
            <CardContent className="flex items-start gap-3 p-4">
              <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", DOT_COLOR[n.type])} />
              <button onClick={() => markRead(n.id)} className="min-w-0 flex-1 text-left">
                <p className="text-sm font-medium">{n.title}</p>
                <p className="text-sm text-muted-foreground">{n.description}</p>
                <p className="mt-1 text-xs text-muted-foreground/70">{formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}</p>
              </button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
