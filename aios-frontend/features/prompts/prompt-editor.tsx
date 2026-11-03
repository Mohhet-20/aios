"use client";

import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { Skeleton } from "@/components/ui/skeleton";

const MonacoEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.default), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

const MonacoDiffEditor = dynamic(() => import("@monaco-editor/react").then((m) => m.DiffEditor), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

/** Code-editor-grade prompt authoring surface. Using Monaco (the VS Code
 *  editor) rather than a <textarea> gives prompt engineers syntax
 *  highlighting for {{variables}}, multi-cursor editing, and — critically —
 *  a real diff view for comparing prompt versions before promotion. */
export function PromptEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { resolvedTheme } = useTheme();
  return (
    <MonacoEditor
      height="100%"
      language="markdown"
      theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
      value={value}
      onChange={(v) => onChange(v ?? "")}
      options={{
        minimap: { enabled: false },
        fontSize: 13,
        fontFamily: "var(--font-mono)",
        wordWrap: "on",
        padding: { top: 16 },
        scrollBeyondLastLine: false,
      }}
    />
  );
}

export function PromptDiffViewer({ original, modified }: { original: string; modified: string }) {
  const { resolvedTheme } = useTheme();
  return (
    <MonacoDiffEditor
      height="100%"
      language="markdown"
      theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
      original={original}
      modified={modified}
      options={{ minimap: { enabled: false }, fontSize: 13, renderSideBySide: true, readOnly: true }}
    />
  );
}
