"""VectorPlatformService — the abstraction layer every memory/knowledge/
document subsystem indexes through, so a future real vector database
(pgvector/Qdrant/Pinecone/Weaviate) swaps in behind this one seam
without touching callers. Wraps the AI Core's `EmbeddingEngine` +
`VectorStore` + `SimilaritySearchService` (explicitly documented in the
AI Core as the intended integration point for downstream subsystems)
rather than re-plumbing embed-then-query.

Provides what a raw `VectorStore` doesn't: durable embedding metadata
and versioning (`EmbeddingRecordModel` — the vector float array itself
still lives only in the in-memory `VectorStore` today), batch indexing,
incremental single-item updates, logical multi-index support (tagged via
`vector_store_index`, since the underlying store is physically flat),
and index health reporting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_core.bootstrap import AICoreContext
from ai_core.embeddings.similarity_search import SimilaritySearchService
from ai_core.embeddings.vector_store import SimilarityMatch, VectorRecord
from ai_core.schemas.requests import EmbeddingRequest

from memory_platform.database.base import new_uuid
from memory_platform.models.embedding_record import EmbeddingRecordModel
from memory_platform.repositories.registry import RepositoryRegistry


@dataclass
class IndexHealth:
    vector_store_index: str
    record_count: int
    distinct_dimensions: list[int]
    healthy: bool
    issues: list[str]


class VectorPlatformService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core
        self.similarity_search = SimilaritySearchService(ai_core.embedding_engine, ai_core.vector_store)

    # -- embedding storage / batch indexing -----------------------------------------

    async def embed_and_index(
        self, *, workspace_id: str, source_type: str, items: list[tuple[str, str, dict[str, Any]]], vector_store_index: str = "default", batch_size: int = 100,
    ) -> list[EmbeddingRecordModel]:
        """items: list of (source_id, text, metadata). Embeds in batches
        (real batch indexing, not one-call-per-item) and upserts into the
        vector store, then persists our own durable metadata row per item."""
        records: list[EmbeddingRecordModel] = []
        for start in range(0, len(items), batch_size):
            batch = items[start:start + batch_size]
            texts = [text for _, text, _ in batch]
            response = await self.ai_core.embedding_engine.embed(EmbeddingRequest(input=texts))
            vector_records = []
            for (source_id, _, metadata), vector in zip(batch, response.embeddings):
                enriched_metadata = {**(metadata or {}), "source_type": source_type, "index": vector_store_index}
                vector_records.append(VectorRecord(id=source_id, vector=vector, metadata=enriched_metadata))
                records.append(await self.repos.embedding_records.add(EmbeddingRecordModel(
                    id=new_uuid(), workspace_id=workspace_id, source_type=source_type, source_id=source_id,
                    vector_store_index=vector_store_index, model=response.model, provider=response.provider, dimensions=len(vector),
                )))
            await self.ai_core.vector_store.upsert(vector_records)
        return records

    async def incremental_update(self, *, workspace_id: str, source_type: str, source_id: str, text: str, metadata: dict | None = None, vector_store_index: str = "default") -> EmbeddingRecordModel:
        """Re-embeds and re-upserts a single item without touching the rest
        of the index — the common case when one document/memory changes."""
        records = await self.embed_and_index(workspace_id=workspace_id, source_type=source_type, items=[(source_id, text, metadata or {})], vector_store_index=vector_store_index)
        return records[0]

    # -- embedding versioning ---------------------------------------------------------

    async def reindex_with_version_bump(self, *, workspace_id: str, source_type: str, source_id: str, text: str, metadata: dict | None = None, vector_store_index: str = "default") -> EmbeddingRecordModel:
        """Unlike `incremental_update`, this keeps the prior `EmbeddingRecordModel`
        row intact (never overwritten) and records a new row with an
        incremented `embedding_version` — full embedding history, not just
        the latest vector."""
        existing = await self.repos.embedding_records.get_for_source(source_type, source_id)
        next_version = 1
        if existing is not None:
            try:
                next_version = int(existing.embedding_version.lstrip("v")) + 1
            except ValueError:
                next_version = 2
        response = await self.ai_core.embedding_engine.embed(EmbeddingRequest(input=[text]))
        vector = response.embeddings[0]
        await self.ai_core.vector_store.upsert([VectorRecord(id=source_id, vector=vector, metadata={**(metadata or {}), "source_type": source_type, "index": vector_store_index})])
        return await self.repos.embedding_records.add(EmbeddingRecordModel(
            id=new_uuid(), workspace_id=workspace_id, source_type=source_type, source_id=source_id, vector_store_index=vector_store_index,
            model=response.model, provider=response.provider, dimensions=len(vector), embedding_version=f"v{next_version}",
        ))

    # -- similarity / ANN search --------------------------------------------------------

    async def similarity_search_query(self, query: str, *, top_k: int = 10, filter_metadata: dict[str, Any] | None = None) -> list[SimilarityMatch]:
        return await self.similarity_search.search(query, top_k=top_k, filter_metadata=filter_metadata)

    # -- deletion ------------------------------------------------------------------------

    async def delete_from_index(self, source_type: str, source_ids: list[str]) -> int:
        if not source_ids:
            return 0
        await self.ai_core.vector_store.delete(source_ids)
        return await self.repos.embedding_records.delete_for_sources(source_type, source_ids)

    # -- multi-index support / index health -----------------------------------------------

    async def list_indexes(self, workspace_id: str) -> list[str]:
        return await self.repos.embedding_records.list_distinct_indexes(workspace_id)

    async def index_health(self, vector_store_index: str = "default") -> IndexHealth:
        count = await self.repos.embedding_records.count_for_index(vector_store_index)
        dims = await self.repos.embedding_records.distinct_dimensions_for_index(vector_store_index)
        issues: list[str] = []
        if len(dims) > 1:
            issues.append(f"inconsistent embedding dimensions in one logical index: {dims}")
        if count == 0:
            issues.append("index is empty")
        return IndexHealth(vector_store_index=vector_store_index, record_count=count, distinct_dimensions=dims, healthy=not issues, issues=issues)
