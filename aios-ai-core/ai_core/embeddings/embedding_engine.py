"""Unified Embedding Engine: routes an embedding request to a candidate
model (via the same ModelRouter used for generation), checks the cache for
each input text, only calls the execution engine for cache misses, and
returns a single EmbeddingResponse with per-item cache-hit flags and a
version tag — this is what every other embedding consumer (memory,
knowledge base, similarity search) should call instead of touching
ExecutionEngine.embed() or a provider directly.
"""
from __future__ import annotations

import hashlib

from ai_core.config.settings import AICoreSettings
from ai_core.embeddings.cache import EmbeddingCache, InMemoryEmbeddingCache
from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.router.model_router import ModelRouter
from ai_core.schemas.requests import EmbeddingRequest
from ai_core.schemas.responses import EmbeddingResponse
from ai_core.schemas.usage import TokenUsage

_CACHE_VERSION = "v1"


class EmbeddingEngine:
    def __init__(
        self,
        execution_engine: ExecutionEngine,
        router: ModelRouter,
        *,
        cache: EmbeddingCache | None = None,
        cache_version: str = _CACHE_VERSION,
        settings: AICoreSettings | None = None,
    ):
        self.execution_engine = execution_engine
        self.router = router
        self.cache = cache or InMemoryEmbeddingCache()
        self.cache_version = cache_version
        self.settings = settings or AICoreSettings()

    def _cache_key(self, provider: str, model: str, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
        return f"{provider}:{model}:{self.cache_version}:{digest}"

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        texts = request.as_list()
        candidates = self.router.route_embedding(request)
        chosen = candidates[0]

        use_cache = request.use_cache and self.settings.enable_embedding_cache

        resolved: dict[int, list[float]] = {}
        miss_indices: list[int] = []
        if use_cache:
            for i, text in enumerate(texts):
                vector = self.cache.get(self._cache_key(chosen.provider, chosen.name, text))
                if vector is not None:
                    resolved[i] = vector
                else:
                    miss_indices.append(i)
        else:
            miss_indices = list(range(len(texts)))

        usage = TokenUsage()
        final_provider, final_model = chosen.provider, chosen.name

        if miss_indices:
            sub_request = request.model_copy(
                update={"input": [texts[i] for i in miss_indices], "provider": chosen.provider, "model": chosen.name}
            )
            fresh = await self.execution_engine.embed(sub_request)
            usage = fresh.usage
            final_provider, final_model = fresh.provider, fresh.model
            for local_idx, global_idx in enumerate(miss_indices):
                vector = fresh.embeddings[local_idx]
                resolved[global_idx] = vector
                if use_cache:
                    self.cache.set(self._cache_key(chosen.provider, chosen.name, texts[global_idx]), vector)

        embeddings = [resolved[i] for i in range(len(texts))]
        cached_flags = [i not in miss_indices for i in range(len(texts))]
        return EmbeddingResponse(
            request_id=request.request_id,
            embeddings=embeddings,
            model=final_model,
            provider=final_provider,
            dimensions=len(embeddings[0]) if embeddings else 0,
            usage=usage,
            cached=cached_flags,
            version=self.cache_version,
        )
