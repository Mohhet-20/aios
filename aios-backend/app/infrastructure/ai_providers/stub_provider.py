"""Deterministic placeholder implementation of `ModelProviderAdapter`.

This is a seam, not a mock-for-tests: it's what `InferenceService` actually
calls today so `/api/v1/inference` is a real, runnable endpoint rather than
a `501 Not Implemented`. Output is clearly marked as stubbed so no one
mistakes it for a real model response. Token counts are approximated by
word count (`* 1.3`) purely so downstream cost/usage accounting has
plausible-looking numbers to work with.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import AsyncIterator

from app.infrastructure.ai_providers.base import (
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ModelProviderAdapter,
)

_STUB_NOTICE = (
    "[stubbed response — no AI model logic is wired up yet; this is Phase 3's "
    "backend platform, not Phase 4's AI Core] "
)


class StubModelProvider(ModelProviderAdapter):
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        start = time.perf_counter()
        last_user_message = next(
            (m["content"] for m in reversed(request.messages) if m["role"] == "user"), ""
        )
        content = f"{_STUB_NOTICE}Echoing your request to {request.model_id}: {last_user_message[:200]}"
        await asyncio.sleep(0.05)  # simulate network latency for realistic timing behavior
        latency_ms = (time.perf_counter() - start) * 1000
        prompt_tokens = sum(len(m["content"].split()) for m in request.messages)
        completion_tokens = len(content.split())
        return GenerationResponse(
            content=content,
            model_id=request.model_id,
            prompt_tokens=int(prompt_tokens * 1.3),
            completion_tokens=int(completion_tokens * 1.3),
            latency_ms=round(latency_ms, 2),
        )

    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]:
        response = await self.generate(request)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            await asyncio.sleep(0.02)
            yield GenerationChunk(delta=word + " ", is_final=(i == len(words) - 1))
        yield GenerationChunk(delta="", is_final=True, finish_reason="stop")

    async def embed(self, model_id: str, texts: list[str]) -> list[list[float]]:
        """Deterministic pseudo-embedding: hash each text into a fixed-length
        float vector. Not semantically meaningful — it exists so
        `EmbeddingService`/`VectorService` have real vectors to store and
        search over (cosine similarity between hash-based vectors is
        meaningless, but the *pipeline* — embed, store, query, rank — is
        fully exercised end-to-end)."""
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [b / 255.0 for b in digest[:32]]
            vectors.append(vector)
        return vectors


stub_provider = StubModelProvider()
