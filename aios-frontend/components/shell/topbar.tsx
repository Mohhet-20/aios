"use client";

import { Search } from "lucide-react";
import { Breadcrumbs } from "./breadcrumbs";
import { NotificationCenter } from "./notification-center";
import { UserMenu } from "./user-menu";
import { useUIStore } from "@/stores/ui-store";

/**
 * Top chrome bar. Deliberately thin (56px) and shared across every route —
 * it hosts wayfinding (breadcrumbs) and global affordances (search,
 * notifications, profile), while page-specific actions live in each page's
 * PageHeader instead of crowding this bar.
 */
export function Topbar() {
  const setCommandPaletteOpen = useUIStore((s) => s.setCommandPaletteOpen);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-border bg-background/80 px-4 backdrop-blur">
      <Breadcrumbs />

      <div className="flex flex-1 items-center justify-end gap-2">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex w-64 items-center gap-2 rounded-md border border-input bg-muted/50 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="flex-1 text-left">Search AIOS...</span>
          <kbd className="rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium">⌘K</kbd>
        </button>
        <NotificationCenter />
        <UserMenu />
      </div>
    </header>
  );
}
