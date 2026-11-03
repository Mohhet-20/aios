"""Vector store abstraction + in-memory reference implementation, so
`SimilaritySearchService` (and anything else that needs nearest-neighbor
lookup) has somewhere to write/query vectors today. Production deployments
swap this for pgvector/Qdrant/Pinecone/Weaviate behind the same three-
method interface — this is the "future vector databases" integration
point the embedding engine is required to leave open.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimilarityMatch:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    async def query(self, vector: list[float], *, top_k: int = 5, filter_metadata: dict[str, Any] | None = None) -> list[SimilarityMatch]: ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None: ...


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class InMemoryVectorStore(VectorStore):
    """O(n) cosine similarity over an in-memory dict. Fine for dev/test and
    small deployments; a real vector DB is required past a few thousand
    records for query latency — that's exactly the swap this interface
    exists to make painless."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    async def upsert(self, records: list[VectorRecord]) -> None:
        for r in records:
            self._records[r.id] = r

    async def query(self, vector: list[float], *, top_k: int = 5, filter_metadata: dict[str, Any] | None = None) -> list[SimilarityMatch]:
        candidates = self._records.values()
        if filter_metadata:
            candidates = [r for r in candidates if all(r.metadata.get(k) == v for k, v in filter_metadata.items())]
        scored = [SimilarityMatch(id=r.id, score=_cosine_similarity(vector, r.vector), metadata=r.metadata) for r in candidates]
        return sorted(scored, key=lambda m: m.score, reverse=True)[:top_k]

    async def delete(self, ids: list[str]) -> None:
        for i in ids:
            self._records.pop(i, None)
