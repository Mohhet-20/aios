"use client";

import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { Bot, User, Wrench, Terminal } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { format } from "date-fns";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";

  if (isTool) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-dashed border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        <Terminal className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span className="font-mono">{message.content}</span>
      </div>
    );
  }

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-accent text-accent-foreground"
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div className={cn("max-w-[75%] space-y-1.5", isUser && "items-end text-right")}>
        {message.toolCalls?.map((tc, i) => (
          <div key={i} className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/50 px-2 py-1 text-[11px] text-muted-foreground">
            <Wrench className="h-3 w-3" /> called <span className="font-mono">{tc.name}</span>
          </div>
        ))}
        <div
          className={cn(
            "rounded-xl px-3.5 py-2.5 text-sm leading-relaxed",
            isUser ? "bg-primary text-primary-foreground" : "bg-muted"
          )}
        >
          <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-0">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
          {message.streaming && <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-current align-middle" />}
        </div>
        <p className="text-[10px] text-muted-foreground">{format(new Date(message.createdAt), "h:mm a")}</p>
      </div>
    </div>
  );
}
