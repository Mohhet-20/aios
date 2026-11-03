"use client";

import { cn } from "@/lib/utils";
import type { Prompt } from "@/types";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";

export function PromptListPanel({
  prompts,
  selectedId,
  onSelect,
}: {
  prompts: Prompt[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex h-full flex-col overflow-y-auto scrollbar-thin">
      {prompts.map((p) => {
        const latest = p.versions[0];
        return (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={cn(
              "flex flex-col gap-1 border-b border-border px-3 py-3 text-left text-sm transition-colors hover:bg-muted/50",
              selectedId === p.id && "bg-accent"
            )}
          >
            <div className="flex items-center justify-between">
              <p className="font-medium">{p.name}</p>
              <Badge variant={latest.status === "production" ? "success" : latest.status === "staged" ? "warning" : "secondary"} className="text-[10px]">
                {latest.status}
              </Badge>
            </div>
            <p className="line-clamp-1 text-xs text-muted-foreground">{p.description}</p>
            <p className="text-[11px] text-muted-foreground/70">
              v{latest.version} · {formatDistanceToNow(new Date(p.updatedAt), { addSuffix: true })}
            </p>
          </button>
        );
      })}
    </div>
  );
}
