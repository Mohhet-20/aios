"use client";

import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useNotificationStore } from "@/stores/notification-store";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

const DOT_COLOR = { info: "bg-primary", success: "bg-success", warning: "bg-warning", error: "bg-destructive" } as const;

export function NotificationCenter() {
  const { items, unreadCount, markAllRead, markRead } = useNotificationStore();
  const unread = unreadCount();

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
              {unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          <Button variant="ghost" size="sm" onClick={markAllRead} className="h-7 gap-1 text-xs">
            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
          </Button>
        </div>
        <ScrollArea className="h-80">
          {items.length === 0 && <p className="px-4 py-10 text-center text-sm text-muted-foreground">You&apos;re all caught up.</p>}
          <ul>
            {items.map((n) => (
              <li key={n.id}>
                <button
                  onClick={() => markRead(n.id)}
                  className={cn("flex w-full gap-3 px-4 py-3 text-left hover:bg-accent", !n.read && "bg-accent/40")}
                >
                  <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", DOT_COLOR[n.type])} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{n.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{n.description}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground/70">
                      {formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}
                    </p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  );
}
