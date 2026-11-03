"""Vector store interface — the Memory Engine's semantic-tier persistence
seam. `InMemoryVectorStore` is the dev/test implementation; a production
deployment binds this same interface to pgvector/Qdrant/Pinecone (per the
Phase 1 tech-stack decision) with zero changes to `MemoryService` or
`VectorService`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict


@dataclass
class ScoredVectorRecord(VectorRecord):
    score: float = 0.0


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, record: VectorRecord) -> None: ...

    @abstractmethod
    async def query(
        self, vector: list[float], top_k: int = 5, filters: dict | None = None
    ) -> list[ScoredVectorRecord]: ...

    @abstractmethod
    async def delete(self, id: str) -> None: ...
