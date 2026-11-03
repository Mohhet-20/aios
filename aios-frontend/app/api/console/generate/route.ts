import { NextResponse } from "next/server";
import { withSession } from "@/lib/server/route";
import { callService, ServiceError } from "@/lib/server/services";
import type { GenerationResult } from "@/types/live";

interface GenerationResponse {
  content: string;
  usage?: { input_tokens?: number; output_tokens?: number };
  execution?: { provider?: string; model?: string };
}

/**
 * One real completion through the AI Core gateway (routing, retries and cost tracking happen there). The latency
 * shown in the playground is this call's measured wall-clock time. With no provider configured, AI Core's own
 * error comes back unchanged so the UI can say so, instead of inventing output.
 */
export const POST = withSession(async (session, req): Promise<GenerationResult | Response> => {
  const body = (await req.json().catch(() => null)) as { prompt?: unknown; provider?: unknown; model?: unknown } | null;
  const prompt = typeof body?.prompt === "string" ? body.prompt.trim() : "";
  if (!prompt || prompt.length > 8_000) {
    return NextResponse.json({ error: "invalid_request", detail: "prompt must be 1-8000 characters" }, { status: 400 });
  }
  const started = performance.now();
  try {
    const res = await callService<GenerationResponse>("ai-core", "/v1/generate", {
      method: "POST",
      userId: session.userId,
      timeoutMs: 60_000,
      body: {
        messages: [{ role: "user", content: prompt }],
        provider: typeof body?.provider === "string" ? body.provider : undefined,
        model: typeof body?.model === "string" ? body.model : undefined,
        max_tokens: 512,
        metadata: { source: "console-playground" },
      },
    });
    return {
      ok: true,
      content: res.content,
      provider: res.execution?.provider,
      model: res.execution?.model,
      inputTokens: res.usage?.input_tokens,
      outputTokens: res.usage?.output_tokens,
      latencyMs: Math.round(performance.now() - started),
    };
  } catch (err) {
    // A request the gateway rejected, or one no configured provider could serve, is a result to show the user.
    if (err instanceof ServiceError && (err.status < 500 || err.type === "AllProvidersFailedError")) {
      return { ok: false, error: err.message, latencyMs: Math.round(performance.now() - started) };
    }
    throw err;
  }
});
