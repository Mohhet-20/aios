"""Provider abstraction. Every LLM/embedding backend the AI Core talks to —
OpenAI, Anthropic, Gemini, Azure OpenAI, HuggingFace, Ollama, vLLM, LM
Studio, local Transformers, and anything added later — implements this one
ABC. The execution engine, router, and every business service only ever
see this interface; nothing above this layer imports a provider SDK or
knows a provider-specific wire format.

Adding a new provider = one new file implementing `generate`/`stream`/
`embed`/`health_check` (embed/stream can raise NotImplementedError if the
provider doesn't support them) and one line registering it in
`providers/registry_bootstrap.py`. Nothing else in the codebase changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

import httpx

from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.responses import EmbeddingResponse, GenerationResponse, StreamChunk


class ModelProviderAdapter(ABC):
    """One instance per provider (not per model — a single OpenAI adapter
    instance serves gpt-4o, gpt-4o-mini, etc.)."""

    provider_name: str

    def __init__(self, *, http_client: httpx.AsyncClient | None = None, timeout_seconds: float = 60.0):
        # A caller-supplied client is how tests inject httpx.MockTransport
        # without any network access; production code lets this default.
        self._owns_client = http_client is None
        # trust_env=False: don't silently pick up ambient HTTP_PROXY/
        # ALL_PROXY env vars. Provider base_urls are explicit config here
        # (including intentionally-local ones like Ollama/vLLM), so an
        # inherited proxy is far more likely to be a surprising footgun
        # than a desired behavior. Callers who do need a proxy can inject
        # their own configured httpx.AsyncClient via `http_client=`.
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds, trust_env=False)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @abstractmethod
    async def generate(self, request: GenerationRequest, *, model: str) -> GenerationResponse:
        """Non-streaming completion."""

    @abstractmethod
    def stream(self, request: GenerationRequest, *, model: str) -> AsyncIterator[StreamChunk]:
        """Streaming completion. Returns an async generator (not a
        coroutine) so callers do `async for chunk in provider.stream(...)`."""

    async def embed(self, request: EmbeddingRequest, *, model: str) -> EmbeddingResponse:
        raise NotImplementedError(f"{self.provider_name} does not support embeddings")

    async def health_check(self) -> bool:
        """Cheap liveness probe used by the registry to mark models
        degraded/unavailable. Default implementation is a no-op success;
        providers with a real health endpoint should override this."""
        return True
