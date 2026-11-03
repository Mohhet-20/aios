"use client";

import { useState } from "react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, BookOpen } from "lucide-react";

const collections = [
  { id: "c1", name: "Support Playbooks", docCount: 84, updated: "2 days ago" },
  { id: "c2", name: "Product Documentation", docCount: 212, updated: "5 hours ago" },
  { id: "c3", name: "Engineering Runbooks", docCount: 47, updated: "1 week ago" },
  { id: "c4", name: "Legal & Compliance", docCount: 31, updated: "3 weeks ago" },
];

export default function KnowledgeBasePage() {
  const [query, setQuery] = useState("");
  return (
    <div>
      <PageHeader title="Knowledge Base" description="Semantic search over the documents your agents retrieve from." />
      <div className="relative mb-4 max-w-lg">
        <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search across all knowledge collections..."
          className="h-11 pl-9"
        />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {collections.map((c) => (
          <Card key={c.id} className="cursor-pointer transition-shadow hover:shadow-md">
            <CardContent className="p-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <BookOpen className="h-4.5 w-4.5 text-primary" />
              </div>
              <p className="mt-3 text-sm font-medium">{c.name}</p>
              <p className="text-xs text-muted-foreground">{c.docCount} documents</p>
              <Badge variant="secondary" className="mt-2 text-[10px]">Updated {c.updated}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
