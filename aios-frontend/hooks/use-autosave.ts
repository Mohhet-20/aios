"use client";
import { useEffect, useRef } from "react";
import { useDraftStore } from "@/stores/draft-store";

/**
 * Debounced autosave into the draft store. Editor surfaces (Prompt Studio,
 * Workflow Builder) call this with their current content; on unmount or
 * remount, the last saved draft is available via useDraftStore for recovery.
 */
export function useAutosave(key: string, content: string, delayMs = 800) {
  const saveDraft = useDraftStore((s) => s.saveDraft);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => saveDraft(key, content), delayMs);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [key, content, delayMs, saveDraft]);
}
