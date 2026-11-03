"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  activityFeedOpen: boolean;
  toggleSidebar: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleActivityFeed: () => void;
}

/** Shell chrome UI state — sidebar collapse, command palette, activity feed
 *  drawer. Kept separate from domain stores so shell layout re-renders don't
 *  cascade into feature state. */
export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      commandPaletteOpen: false,
      activityFeedOpen: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      toggleActivityFeed: () => set((s) => ({ activityFeedOpen: !s.activityFeedOpen })),
    }),
    { name: "aios-ui", partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed }) }
  )
);
