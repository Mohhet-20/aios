"use client";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Braces } from "lucide-react";

interface VariablesPanelProps {
  variables: string[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
}

/** Extracts {{variable}} placeholders from a prompt template and renders a
 *  live input for each — used to preview a rendered prompt without leaving
 *  the studio. Mirrors the Prompt Engine's `render(vars, targetModel)`
 *  contract from the Phase 1 architecture blueprint. */
export function VariablesPanel({ variables, values, onChange }: VariablesPanelProps) {
  if (variables.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
        <Braces className="h-4 w-4" /> No <code>{"{{variables}}"}</code> detected in this template.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {variables.map((v) => (
        <div key={v} className="space-y-1.5">
          <Label htmlFor={`var-${v}`} className="flex items-center gap-1.5 text-xs">
            <Badge variant="outline" className="font-mono text-[10px]">
              {"{{" + v + "}}"}
            </Badge>
          </Label>
          <Input id={`var-${v}`} value={values[v] ?? ""} onChange={(e) => onChange(v, e.target.value)} placeholder={`Value for ${v}`} />
        </div>
      ))}
    </div>
  );
}
