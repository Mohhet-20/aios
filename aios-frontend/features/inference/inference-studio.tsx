"use client";

import { useRef, useState } from "react";
import { MessageBubble } from "./message-bubble";
import { sampleConversation, models, memoryItems } from "@/lib/mock-data";
import type { ChatMessage } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Send, Square, BrainCircuit, Settings2 } from "lucide-react";
import { useStreamingCompletion } from "@/hooks/use-streaming-completion";
import { ModelProviderBadge } from "@/components/shared/model-badge";

const CANNED_RESPONSE =
  "I've reviewed the account history and the transaction in question. Based on our refund policy and the fact that this purchase falls within the 30-day window, I'm approving a full refund to the original payment method. I'll also flag this case as resolved in the ticketing system and notify the customer.";

export function InferenceStudio() {
  const [messages, setMessages] = useState<ChatMessage[]>(sampleConversation);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(models[1].id);
  const [temperature, setTemperature] = useState(0.4);
  const { output, isStreaming, start, stop } = useStreamingCompletion();
  const bottomRef = useRef<HTMLDivElement>(null);

  async function send() {
    if (!input.trim() || isStreaming) return;
    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: input, createdAt: new Date().toISOString() };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    await start(CANNED_RESPONSE);
  }

  // Once streaming finishes, commit the streamed output as a real message.
  const displayMessages = isStreaming || output
    ? [
        ...messages,
        ...(isStreaming || output
          ? [{ id: "streaming", role: "assistant" as const, content: output, createdAt: new Date().toISOString(), streaming: isStreaming }]
          : []),
      ]
    : messages;

  return (
    <div className="grid h-[calc(100vh-9.5rem)] grid-cols-1 gap-4 lg:grid-cols-[1fr_300px]">
      <Card className="flex flex-col overflow-hidden">
        <CardHeader className="flex-row items-center justify-between space-y-0 border-b border-border py-3">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm">Inference Studio</CardTitle>
            <ModelProviderBadge provider={models.find((m) => m.id === model)!.provider} />
          </div>
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger className="h-8 w-56 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {models.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent className="flex-1 space-y-4 overflow-y-auto scrollbar-thin p-4">
          {displayMessages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          <div ref={bottomRef} />
        </CardContent>
        <div className="flex items-center gap-2 border-t border-border p-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Send a message to test this agent..."
            className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          {isStreaming ? (
            <Button variant="outline" onClick={stop}>
              <Square className="h-4 w-4" /> Stop
            </Button>
          ) : (
            <Button onClick={send}>
              <Send className="h-4 w-4" /> Send
            </Button>
          )}
        </div>
      </Card>

      <div className="space-y-4 overflow-y-auto scrollbar-thin">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
              <Settings2 className="h-3.5 w-3.5" /> Generation params
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                <span>Temperature</span>
                <span className="font-mono">{temperature.toFixed(1)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-primary"
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Max tokens</span>
              <span className="font-mono">4096</span>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Context window</span>
              <span className="font-mono">{models.find((m) => m.id === model)?.contextWindow.toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
              <BrainCircuit className="h-3.5 w-3.5" /> Memory context used
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {memoryItems.slice(0, 2).map((m) => (
              <div key={m.id} className="rounded-md border border-border px-2.5 py-2 text-xs">
                <div className="mb-1 flex items-center justify-between">
                  <Badge variant="outline" className="text-[10px] capitalize">
                    {m.type}
                  </Badge>
                  {m.relevance && <span className="font-mono text-muted-foreground">{Math.round(m.relevance * 100)}%</span>}
                </div>
                <p className="text-muted-foreground">{m.content}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
