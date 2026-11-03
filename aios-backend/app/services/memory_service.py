"""MemoryService — the Memory Engine's three-tier interface (session /
semantic / episodic) from Phase 1, Section 3.4. Semantic writes generate an
embedding and store it in the vector store; queries embed the query text and
rank stored items by similarity. Session/episodic writes skip the embedding
step (queried by scope/recency, not similarity) — mirroring the real design
distinction between the tiers rather than treating them identically.
"""

from __future__ import annotations

from app.core.exceptions import ValidationError
from app.models.memory import MemoryItemModel
from app.repositories.memory_repository import MemoryRepository
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService

_DEFAULT_EMBEDDING_MODEL = "text-embed-3"


class MemoryService:
    def __init__(self, repository: MemoryRepository, embeddings: EmbeddingService, vectors: VectorService):
        self.repository = repository
        self.embeddings = embeddings
        self.vectors = vectors

    async def write(self, workspace_id: str, memory_type: str, scope: str, content: str) -> MemoryItemModel:
        if not content.strip():
            raise ValidationError("Memory content must not be empty")

        item = MemoryItemModel(
            workspace_id=workspace_id, memory_type=memory_type, scope=scope, content=content
        )
        item = await self.repository.add(item)

        if memory_type == "semantic":
            [vector] = await self.embeddings.embed_texts(_DEFAULT_EMBEDDING_MODEL, [content])
            await self.vectors.upsert(item.id, vector, {"workspace_id": workspace_id, "scope": scope})
            item.embedding_id = item.id
            await self.repository.update(item)

        return item

    async def query(
        self, workspace_id: str, query_text: str, memory_type: str | None = None, top_k: int = 5
    ) -> list[MemoryItemModel]:
        if memory_type and memory_type != "semantic":
            return await self.repository.list_by_type(workspace_id, memory_type)

        [query_vector] = await self.embeddings.embed_texts(_DEFAULT_EMBEDDING_MODEL, [query_text])
        scored = await self.vectors.search(query_vector, top_k=top_k, filters={"workspace_id": workspace_id})

        items = []
        for result in scored:
            item = await self.repository.get(result.id)
            if item:
                item.relevance = round(result.score, 4)
                items.append(item)
        return items
