"use client";
import { useEffect } from "react";

type Handler = (e: KeyboardEvent) => void;

/**
 * Registers a global keyboard shortcut. Used for the command palette (Cmd/
 * Ctrl+K), quick-create (C), and search focus (/) — the "Keyboard Shortcuts"
 * requirement of the Enterprise UX section.
 */
export function useHotkey(combo: string, handler: Handler, enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    const keys = combo.toLowerCase().split("+");
    const needsMeta = keys.includes("mod");
    const key = keys[keys.length - 1];

    const listener = (e: KeyboardEvent) => {
      const metaOk = needsMeta ? e.metaKey || e.ctrlKey : true;
      if (metaOk && e.key.toLowerCase() === key) {
        handler(e);
      }
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [combo, handler, enabled]);
}
