"""EmbeddingService — thin wrapper over the AI Core's `embed()` capability.
Kept separate from `InferenceService` because embeddings have a distinct API
contract (batched texts -> vectors) and distinct callers (MemoryService,
DocumentService) even though both ultimately go through the same
`ModelProviderAdapter`.
"""

from app.infrastructure.ai_providers.base import ModelProviderAdapter


class EmbeddingService:
    def __init__(self, provider: ModelProviderAdapter):
        self.provider = provider

    async def embed_texts(self, model_id: str, texts: list[str]) -> list[list[float]]:
        return await self.provider.embed(model_id, texts)
