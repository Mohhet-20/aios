"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck } from "lucide-react";

const policies = [
  { id: "p1", label: "Require SSO for all members", description: "Disable email/password login org-wide.", enabled: true },
  { id: "p2", label: "Enforce evaluation gating before prompt promotion", description: "Block production promotion below 90% eval score.", enabled: true },
  { id: "p3", label: "Require approval for mutating tool calls", description: "Human-in-the-loop for any tool marked side-effect: mutating.", enabled: true },
  { id: "p4", label: "Allow local/self-hosted models", description: "Permit agents to route requests to on-prem inference.", enabled: false },
  { id: "p5", label: "Data residency: EU only", description: "Restrict provider routing to EU-hosted endpoints.", enabled: false },
];

export default function AdministrationPage() {
  const [state, setState] = useState(policies);
  return (
    <div>
      <PageHeader title="Administration" description="Organization-wide security and governance policies." />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4" /> Governance policies
          </CardTitle>
          <CardDescription>Enforced across every workspace in this organization.</CardDescription>
        </CardHeader>
        <CardContent className="divide-y divide-border">
          {state.map((p) => (
            <div key={p.id} className="flex items-center justify-between py-3">
              <div className="pr-4">
                <p className="text-sm font-medium">{p.label}</p>
                <p className="text-xs text-muted-foreground">{p.description}</p>
              </div>
              <Switch
                checked={p.enabled}
                onCheckedChange={(v) => setState((prev) => prev.map((x) => (x.id === p.id ? { ...x, enabled: v } : x)))}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Role permissions</CardTitle>
          <CardDescription>What each role can do by default.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[
            { role: "Owner", perms: ["Manage billing", "Manage roles", "All resource access"] },
            { role: "Admin", perms: ["Manage agents/prompts/workflows", "Manage tools", "View audit logs"] },
            { role: "Member", perms: ["Create/edit own prompts", "Run agents", "View dashboards"] },
            { role: "Viewer", perms: ["Read-only access to dashboards"] },
          ].map((r) => (
            <div key={r.role} className="rounded-lg border border-border p-3">
              <p className="mb-2 text-sm font-medium">{r.role}</p>
              <div className="flex flex-wrap gap-1.5">
                {r.perms.map((p) => (
                  <Badge key={p} variant="secondary" className="text-[10px]">{p}</Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
