"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface DraftState {
  drafts: Record<string, string>;
  saveDraft: (key: string, content: string) => void;
  clearDraft: (key: string) => void;
}

/**
 * Generic autosave/draft-recovery store used by Prompt Studio, Workflow
 * Builder, and any other editor surface: `key` is a stable id (e.g.
 * `prompt:pr_1`) and `content` is a JSON-serialized editor value. Persisted
 * so an accidental tab close doesn't lose unsaved work — this is the backing
 * store for the "Session Recovery" requirement.
 */
export const useDraftStore = create<DraftState>()(
  persist(
    (set) => ({
      drafts: {},
      saveDraft: (key, content) => set((s) => ({ drafts: { ...s.drafts, [key]: content } })),
      clearDraft: (key) =>
        set((s) => {
          const next = { ...s.drafts };
          delete next[key];
          return { drafts: next };
        }),
    }),
    { name: "aios-drafts" }
  )
);
