"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/shared/status-dot";
import type { Agent } from "@/types";
import { formatNumber } from "@/lib/utils";
import { Bot, ChevronRight } from "lucide-react";
import Link from "next/link";
import { motion } from "framer-motion";

const STATUS_MAP = { active: "healthy", idle: "idle", error: "down", training: "pending" } as const;

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>
      <Card className="group h-full transition-shadow hover:shadow-md">
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-lg"
              style={{ backgroundColor: `hsl(var(--${agent.avatarColor}) / 0.15)` }}
            >
              <Bot className="h-5 w-5" style={{ color: `hsl(var(--${agent.avatarColor}))` }} />
            </div>
            <div>
              <p className="text-sm font-semibold">{agent.name}</p>
              <p className="text-xs text-muted-foreground">{agent.role}</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <StatusDot status={STATUS_MAP[agent.status]} pulse={agent.status === "active"} />
            <span className="text-xs capitalize text-muted-foreground">{agent.status}</span>
          </div>
        </CardHeader>
        <CardContent>
          <p className="line-clamp-2 text-sm text-muted-foreground">{agent.description}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {agent.tools.map((t) => (
              <Badge key={t} variant="secondary" className="text-[11px]">
                {t}
              </Badge>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
            <span>{agent.model}</span>
            <span>{formatNumber(agent.runsToday)} runs today</span>
          </div>
          <Link
            href={`/agents/${agent.id}`}
            className="mt-3 flex items-center justify-center gap-1 rounded-md border border-border py-1.5 text-xs font-medium opacity-0 transition-opacity group-hover:opacity-100"
          >
            Open agent <ChevronRight className="h-3 w-3" />
          </Link>
        </CardContent>
      </Card>
    </motion.div>
  );
}
