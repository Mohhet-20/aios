"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { organizations, workspaces } from "@/lib/mock-data";

interface WorkspaceState {
  organizationId: string;
  workspaceId: string;
  setOrganization: (id: string) => void;
  setWorkspace: (id: string) => void;
}

/**
 * Current org/workspace selection. Persisted to localStorage so a refresh
 * doesn't drop the user back to a default context — the same pattern every
 * multi-tenant enterprise console (Vercel, Linear, Datadog) uses.
 */
export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      organizationId: organizations[0].id,
      workspaceId: workspaces[0].id,
      setOrganization: (id) => set({ organizationId: id, workspaceId: workspaces.find((w) => w.organizationId === id)?.id ?? "" }),
      setWorkspace: (id) => set({ workspaceId: id }),
    }),
    { name: "aios-workspace" }
  )
);
