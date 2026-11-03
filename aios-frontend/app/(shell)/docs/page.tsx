import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Search, Rocket, Bot, Workflow, ShieldCheck, Wrench, BarChart3 } from "lucide-react";

const categories = [
  { icon: Rocket, title: "Getting started", desc: "Set up your first workspace, agent, and prompt.", articles: 12 },
  { icon: Bot, title: "Agents", desc: "Define roles, tools, and memory scopes for agents.", articles: 18 },
  { icon: Workflow, title: "Workflows", desc: "Compose multi-step automations with branching.", articles: 14 },
  { icon: BarChart3, title: "Evaluation", desc: "Build golden sets and gate promotions on quality.", articles: 9 },
  { icon: Wrench, title: "Tools & integrations", desc: "Register internal tools and connect SaaS apps.", articles: 21 },
  { icon: ShieldCheck, title: "Security & governance", desc: "RBAC, audit logs, and data residency controls.", articles: 11 },
];

export default function DocumentationPage() {
  return (
    <div>
      <PageHeader title="Documentation" description="Guides and API reference for building on AIOS." />
      <div className="relative mb-6 max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search documentation..." className="h-12 pl-9 text-base" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {categories.map((c) => (
          <Card key={c.title} className="cursor-pointer transition-shadow hover:shadow-md">
            <CardContent className="p-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <c.icon className="h-4.5 w-4.5 text-primary" />
              </div>
              <p className="mt-3 text-sm font-medium">{c.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{c.desc}</p>
              <p className="mt-2 text-[11px] text-muted-foreground/70">{c.articles} articles</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
