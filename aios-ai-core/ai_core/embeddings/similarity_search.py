"""Convenience service wiring EmbeddingEngine + VectorStore together: embed
a query, search the store, return ranked matches. Downstream memory/
knowledge-base subsystems (Phase 5+) are expected to build on this rather
than re-plumbing embed-then-query themselves.
"""
from __future__ import annotations

from typing import Any

from ai_core.embeddings.embedding_engine import EmbeddingEngine
from ai_core.embeddings.vector_store import SimilarityMatch, VectorRecord, VectorStore
from ai_core.schemas.requests import EmbeddingRequest


class SimilaritySearchService:
    def __init__(self, embedding_engine: EmbeddingEngine, vector_store: VectorStore):
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store

    async def index(self, items: list[tuple[str, str, dict[str, Any]]]) -> None:
        """items: list of (id, text, metadata) to embed and upsert."""
        if not items:
            return
        texts = [text for _, text, _ in items]
        response = await self.embedding_engine.embed(EmbeddingRequest(input=texts))
        records = [
            VectorRecord(id=item_id, vector=vector, metadata=metadata)
            for (item_id, _, metadata), vector in zip(items, response.embeddings)
        ]
        await self.vector_store.upsert(records)

    async def search(self, query: str, *, top_k: int = 5, filter_metadata: dict[str, Any] | None = None) -> list[SimilarityMatch]:
        response = await self.embedding_engine.embed(EmbeddingRequest(input=query))
        return await self.vector_store.query(response.embeddings[0], top_k=top_k, filter_metadata=filter_metadata)
