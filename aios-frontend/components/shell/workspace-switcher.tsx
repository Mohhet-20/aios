"use client";

import { useSession } from "@/services/console";
import { cn } from "@/lib/utils";

/**
 * The signed-in organisation, from the identity service. The console works in one workspace per organisation
 * (each domain service resolves the organisation to its own workspace), so there is nothing to switch between yet;
 * this shows where the user is rather than offering choices that don't exist.
 */
export function WorkspaceSwitcher({ collapsed }: { collapsed: boolean }) {
  const { data } = useSession();
  const name = data?.organization?.name ?? (data ? "No organisation" : "…");
  const initials = name.split(/\s+/).filter((w) => /^[A-Za-z]/.test(w)).map((w) => w[0]).join("").slice(0, 2).toUpperCase() || "–";

  return (
    <div
      className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5", collapsed && "justify-center px-0")}
      aria-label={`Organisation: ${name}`}
    >
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-primary/15 text-[10px] font-bold text-primary">
        {initials}
      </div>
      {!collapsed && (
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-sidebar-foreground">{name}</p>
          <p className="truncate text-[11px] text-sidebar-foreground/50">{data?.user.email ?? "Organisation"}</p>
        </div>
      )}
    </div>
  );
}
