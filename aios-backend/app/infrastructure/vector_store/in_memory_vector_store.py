"""In-memory cosine-similarity vector store. O(n) per query — fine for
local dev and tests (hundreds to low thousands of vectors); a production
deployment must swap to an indexed store (pgvector/Qdrant/Pinecone) as
noted in `base.py`.
"""

from __future__ import annotations

import math

from app.infrastructure.vector_store.base import ScoredVectorRecord, VectorRecord, VectorStore


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, record: VectorRecord) -> None:
        self._records[record.id] = record

    async def query(
        self, vector: list[float], top_k: int = 5, filters: dict | None = None
    ) -> list[ScoredVectorRecord]:
        candidates = self._records.values()
        if filters:
            candidates = [r for r in candidates if all(r.metadata.get(k) == v for k, v in filters.items())]
        scored = [
            ScoredVectorRecord(
                id=r.id, vector=r.vector, metadata=r.metadata, score=_cosine_similarity(vector, r.vector)
            )
            for r in candidates
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    async def delete(self, id: str) -> None:
        self._records.pop(id, None)


in_memory_vector_store = InMemoryVectorStore()
