"use client";
import { useCallback, useRef, useState } from "react";

/**
 * Simulates a token-streaming LLM response (what a real implementation would
 * receive over SSE/WebSocket from the AI Core gateway defined in the original architecture).
 * Consumed by Inference Studio / Model Playground so the streaming UX,
 * cancellation, and incremental-render behavior is real even though the
 * tokens themselves are generated client-side in this frontend-only mode.
 */
export function useStreamingCompletion() {
  const [output, setOutput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const cancelRef = useRef(false);

  const start = useCallback(async (fullText: string, tokensPerTick = 3, tickMs = 28) => {
    cancelRef.current = false;
    setOutput("");
    setIsStreaming(true);
    const words = fullText.split(" ");
    for (let i = 0; i < words.length; i += tokensPerTick) {
      if (cancelRef.current) break;
      await new Promise((r) => setTimeout(r, tickMs));
      setOutput((prev) => (prev ? prev + " " : "") + words.slice(i, i + tokensPerTick).join(" "));
    }
    setIsStreaming(false);
  }, []);

  const stop = useCallback(() => {
    cancelRef.current = true;
    setIsStreaming(false);
  }, []);

  return { output, isStreaming, start, stop };
}
