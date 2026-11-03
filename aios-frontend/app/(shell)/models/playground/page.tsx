"use client";

import { useState } from "react";
import { Loader2, Play, Info } from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useGenerate, useModels } from "@/services/console";
import { formatLatency } from "@/lib/utils";

const AUTO = "auto";

export default function ModelPlaygroundPage() {
  const models = useModels();
  const generate = useGenerate();
  const [prompt, setPrompt] = useState(
    "A customer wants a refund on an item bought 20 days ago. Our policy allows refunds within 30 days. Draft a two-sentence reply.",
  );
  const [choice, setChoice] = useState(AUTO);
  const result = generate.data;

  function run() {
    const [provider, model] = choice === AUTO ? [undefined, undefined] : choice.split("::");
    generate.mutate({ prompt, provider, model });
  }

  return (
    <div>
      <PageHeader
        title="Model Playground"
        description="Send a prompt through the AI Core gateway. Routing, retries and cost tracking happen there; latency is measured on each call."
      />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Request</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="model">Model</Label>
              <Select value={choice} onValueChange={setChoice}>
                <SelectTrigger id="model" aria-label="Model">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={AUTO}>Let the router choose</SelectItem>
                  {models.data?.map((m) => (
                    <SelectItem key={`${m.provider}::${m.name}`} value={`${m.provider}::${m.name}`}>
                      {m.provider} · {m.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="prompt">Prompt</Label>
              <textarea
                id="prompt"
                className="min-h-[160px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                maxLength={8000}
              />
            </div>
            <Button onClick={run} disabled={generate.isPending || !prompt.trim()}>
              {generate.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {generate.isPending ? "Running…" : "Run"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Response</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm" aria-live="polite">
            {!result && !generate.error && <p className="text-muted-foreground">Run a prompt to see the gateway&apos;s response here.</p>}
            {generate.error && <p role="alert" className="text-destructive">{generate.error.message}</p>}
            {result?.ok && (
              <>
                <p className="whitespace-pre-wrap leading-relaxed">{result.content}</p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
                  <span>{[result.provider, result.model].filter(Boolean).join(" · ")}</span>
                  <span>{formatLatency(result.latencyMs)} measured</span>
                  {result.outputTokens !== undefined && <span>{result.inputTokens ?? 0} in / {result.outputTokens} out tokens</span>}
                </div>
              </>
            )}
            {result && !result.ok && (
              <div role="alert" className="flex gap-3 rounded-md border border-border bg-muted/40 p-3">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="space-y-1">
                  <p className="font-medium">No model provider could serve this request.</p>
                  <p className="text-muted-foreground">{result.error}</p>
                  <p className="text-muted-foreground">
                    Configure one for AI Core (for example <code>ANTHROPIC_API_KEY</code>, <code>OPENAI_API_KEY</code>, or a local
                    Ollama endpoint) and run again. Nothing is simulated here.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
