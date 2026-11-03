"use client";

import * as React from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { NAV_SECTIONS } from "@/lib/constants";
import { ICON_MAP } from "@/lib/icon-map";
import { useUIStore } from "@/stores/ui-store";
import { useHotkey } from "@/hooks/use-hotkeys";
import { Plus, Moon, Sun, Search } from "lucide-react";
import { useTheme } from "next-themes";

/**
 * Global command palette (Cmd/Ctrl+K) — the fast path for navigation and
 * quick actions in a platform with dozens of pages. This is the single
 * biggest discoverability lever in an app this large: users shouldn't need
 * to remember which sidebar section a page lives in.
 */
export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, setCommandPaletteOpen } = useUIStore();
  const { setTheme, resolvedTheme } = useTheme();

  useHotkey("mod+k", (e) => {
    e.preventDefault();
    setCommandPaletteOpen(!commandPaletteOpen);
  });

  const go = (href: string) => {
    router.push(href);
    setCommandPaletteOpen(false);
  };

  return (
    <Dialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <DialogContent className="max-w-xl overflow-hidden p-0">
        <Command className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground">
          <div className="flex items-center gap-2 border-b border-border px-3">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Command.Input
              autoFocus
              placeholder="Search pages, agents, prompts, actions..."
              className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          <Command.List className="max-h-96 overflow-y-auto p-2 scrollbar-thin">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">No results found.</Command.Empty>

            <Command.Group heading="Quick actions">
              <Command.Item
                onSelect={() => go("/prompts/studio")}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-accent"
              >
                <Plus className="h-4 w-4" /> New prompt
              </Command.Item>
              <Command.Item
                onSelect={() => go("/workflows/builder")}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-accent"
              >
                <Plus className="h-4 w-4" /> New workflow
              </Command.Item>
              <Command.Item
                onSelect={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-accent"
              >
                {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                Toggle theme
              </Command.Item>
            </Command.Group>

            {NAV_SECTIONS.map((section) => (
              <Command.Group key={section.label} heading={section.label}>
                {section.items.map((item) => {
                  const Icon = ICON_MAP[item.icon];
                  return (
                    <Command.Item
                      key={item.href}
                      value={item.label}
                      onSelect={() => go(item.href)}
                      className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm aria-selected:bg-accent"
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Command.Item>
                  );
                })}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
