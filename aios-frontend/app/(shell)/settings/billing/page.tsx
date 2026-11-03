"use client";

import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CreditCard, DollarSign, Zap } from "lucide-react";

const invoices = [
  { id: "in_1", period: "June 2026", amount: "$4,218.40", status: "paid" },
  { id: "in_2", period: "May 2026", amount: "$3,904.10", status: "paid" },
  { id: "in_3", period: "April 2026", amount: "$3,512.85", status: "paid" },
];

export default function BillingPage() {
  return (
    <div>
      <PageHeader title="Billing" description="Plan, usage-based charges, and invoice history." />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Current plan" value="Enterprise" icon={CreditCard} />
        <StatCard label="Month-to-date spend" value="$3,140.22" delta={8.1} icon={DollarSign} />
        <StatCard label="Included credits used" value="72%" icon={Zap} />
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Usage against plan limits</CardTitle>
          <CardDescription>Resets on the 1st of each month.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { label: "Tokens processed", value: 72, detail: "14.4M / 20M" },
            { label: "Agent executions", value: 58, detail: "58,200 / 100,000" },
            { label: "Workflow runs", value: 34, detail: "3,400 / 10,000" },
            { label: "Seats", value: 80, detail: "16 / 20" },
          ].map((u) => (
            <div key={u.label}>
              <div className="mb-1 flex justify-between text-xs">
                <span className="text-muted-foreground">{u.label}</span>
                <span className="font-mono">{u.detail}</span>
              </div>
              <Progress value={u.value} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Invoice history</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {invoices.map((i) => (
            <div key={i.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5 text-sm">
              <span>{i.period}</span>
              <div className="flex items-center gap-3">
                <span className="font-mono">{i.amount}</span>
                <Badge variant="success" className="capitalize">{i.status}</Badge>
                <Button size="sm" variant="outline">Download</Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
