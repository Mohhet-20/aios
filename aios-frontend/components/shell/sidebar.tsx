"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronsLeft, ChevronsRight } from "lucide-react";
import { NAV_SECTIONS } from "@/lib/constants";
import { ICON_MAP } from "@/lib/icon-map";
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";
import { WorkspaceSwitcher } from "./workspace-switcher";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * Primary left navigation. Collapses to an icon rail (persisted via
 * useUIStore) rather than disappearing entirely — enterprise users keep
 * this open all day, so collapse is a density choice, not a hide toggle.
 */
export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200",
        sidebarCollapsed ? "w-sidebar-collapsed" : "w-sidebar"
      )}
    >
      <div className={cn("flex h-14 items-center gap-2 border-b border-sidebar-border px-3", sidebarCollapsed && "justify-center px-0")}>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-bold text-primary-foreground">
          AI
        </div>
        {!sidebarCollapsed && <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">AIOS</span>}
      </div>

      <div className="border-b border-sidebar-border p-2">
        <WorkspaceSwitcher collapsed={sidebarCollapsed} />
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-2 py-3">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-4">
            {!sidebarCollapsed && (
              <p className="mb-1 px-2 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50">
                {section.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = ICON_MAP[item.icon];
                const active = pathname === item.href || pathname?.startsWith(item.href + "/");
                const linkEl = (
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-sidebar-accent font-medium text-primary"
                        : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                      sidebarCollapsed && "justify-center px-0"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );
                return (
                  <li key={item.href}>
                    {sidebarCollapsed ? (
                      <Tooltip>
                        <TooltipTrigger asChild>{linkEl}</TooltipTrigger>
                        <TooltipContent side="right">{item.label}</TooltipContent>
                      </Tooltip>
                    ) : (
                      linkEl
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <button
        onClick={toggleSidebar}
        className="flex h-10 items-center justify-center gap-2 border-t border-sidebar-border text-xs text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground"
      >
        {sidebarCollapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        {!sidebarCollapsed && "Collapse"}
      </button>
    </aside>
  );
}
