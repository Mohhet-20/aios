"""VectorService — thin wrapper over the `VectorStore` port. Separate from
`EmbeddingService` (which produces vectors) and `MemoryService` (which
combines embedding + vector storage into the Memory Engine's semantic tier)
so each has one job: this one just stores/searches vectors that already
exist.
"""

from app.infrastructure.vector_store.base import ScoredVectorRecord, VectorRecord, VectorStore


class VectorService:
    def __init__(self, store: VectorStore):
        self.store = store

    async def upsert(self, id: str, vector: list[float], metadata: dict) -> None:
        await self.store.upsert(VectorRecord(id=id, vector=vector, metadata=metadata))

    async def search(
        self, vector: list[float], top_k: int = 5, filters: dict | None = None
    ) -> list[ScoredVectorRecord]:
        return await self.store.query(vector, top_k=top_k, filters=filters)

    async def delete(self, id: str) -> None:
        await self.store.delete(id)
