"""AnalyticsService — the observability rollups every dashboard in the
spec (Memory Analytics, Retrieval Performance) reads from: real
percentile math over logged retrieval latency (not an approximation),
failure rates, a search-quality proxy, embedding growth/health, document
storage usage, knowledge growth, and per-agent memory usage. Built
entirely from data this platform already writes as a side effect of
normal operation (`RetrievalLogModel`/`ContextAssemblyLogModel` via the
Retrieval Engine and Context Assembly Engine's shared logging, plus the
memory/knowledge/document/embedding tables themselves) — nothing here is
a separate, unverified metrics pipeline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _percentile(sorted_values: list[float], p: float) -> float:
    """Real percentile via linear interpolation between closest ranks —
    not a bucket-based approximation."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = p / 100 * (len(sorted_values) - 1)
    lower, upper = math.floor(rank), math.ceil(rank)
    if lower == upper:
        return sorted_values[int(rank)]
    weight = rank - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


@dataclass
class RetrievalPerformance:
    total_queries: int
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    failure_rate: float
    non_empty_result_rate: float
    avg_result_count: float


@dataclass
class ContextAssemblyPerformance:
    total_assemblies: int
    avg_tokens_used: float
    avg_latency_ms: float
    compression_rate: float


@dataclass
class EmbeddingPerformance:
    indexes: dict[str, dict] = field(default_factory=dict)  # index_name -> {record_count, distinct_dimensions, healthy}


@dataclass
class MemoryAnalytics:
    total_reads: int
    entries_created_in_window: int
    entries_updated_in_window: int
    window_days: int


@dataclass
class KnowledgeGrowth:
    total_items: int
    items_created_in_window: int
    window_days: int


@dataclass
class StorageUsage:
    total_document_bytes: int
    document_count: int
    memory_entry_count: int
    knowledge_item_count: int


@dataclass
class AgentMemoryUsage:
    agent_id: str
    entry_count: int
    total_access_count: int


class AnalyticsService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- retrieval latency / quality / failure rate ---------------------------------

    async def retrieval_performance(self, workspace_id: str, *, since: datetime | None = None) -> RetrievalPerformance:
        logs = await self.repos.retrieval_logs.list_for_workspace(workspace_id, since=since, limit=10_000)
        if not logs:
            return RetrievalPerformance(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        latencies = sorted(log.latency_ms for log in logs)
        failures = sum(1 for log in logs if not log.success)
        non_empty = sum(1 for log in logs if log.result_count > 0)
        return RetrievalPerformance(
            total_queries=len(logs),
            p50_latency_ms=_percentile(latencies, 50),
            p95_latency_ms=_percentile(latencies, 95),
            p99_latency_ms=_percentile(latencies, 99),
            avg_latency_ms=sum(latencies) / len(latencies),
            failure_rate=failures / len(logs),
            non_empty_result_rate=non_empty / len(logs),
            avg_result_count=sum(log.result_count for log in logs) / len(logs),
        )

    # -- context assembly performance ------------------------------------------------

    async def context_assembly_performance(self, workspace_id: str) -> ContextAssemblyPerformance:
        logs = await self.repos.context_assembly_logs.list_for_workspace(workspace_id, limit=10_000)
        if not logs:
            return ContextAssemblyPerformance(0, 0.0, 0.0, 0.0)
        compressed = sum(1 for log in logs if log.compression_applied)
        return ContextAssemblyPerformance(
            total_assemblies=len(logs),
            avg_tokens_used=sum(log.tokens_used for log in logs) / len(logs),
            avg_latency_ms=sum(log.latency_ms for log in logs) / len(logs),
            compression_rate=compressed / len(logs),
        )

    # -- embedding performance / index health -----------------------------------------

    async def embedding_performance(self, workspace_id: str) -> EmbeddingPerformance:
        indexes = await self.repos.embedding_records.list_distinct_indexes(workspace_id)
        result: dict[str, dict] = {}
        for index_name in indexes:
            count = await self.repos.embedding_records.count_for_index(index_name)
            dims = await self.repos.embedding_records.distinct_dimensions_for_index(index_name)
            result[index_name] = {"record_count": count, "distinct_dimensions": dims, "healthy": len(dims) <= 1}
        return EmbeddingPerformance(indexes=result)

    # -- memory reads / writes ---------------------------------------------------------

    async def memory_analytics(self, workspace_id: str, *, window_days: int = 30) -> MemoryAnalytics:
        since = _now() - timedelta(days=window_days)
        total_reads = await self.repos.memory_entries.sum_access_count_for_workspace(workspace_id)
        created = await self.repos.memory_entries.count_created_since(workspace_id, since)
        updated = await self.repos.memory_entries.count_updated_since(workspace_id, since)
        return MemoryAnalytics(total_reads=total_reads, entries_created_in_window=created, entries_updated_in_window=updated, window_days=window_days)

    # -- knowledge growth ----------------------------------------------------------------

    async def knowledge_growth(self, workspace_id: str, *, window_days: int = 30) -> KnowledgeGrowth:
        since = _now() - timedelta(days=window_days)
        total = await self.repos.knowledge_items.count_for_workspace(workspace_id)
        created = await self.repos.knowledge_items.count_created_since(workspace_id, since)
        return KnowledgeGrowth(total_items=total, items_created_in_window=created, window_days=window_days)

    # -- storage usage ---------------------------------------------------------------------

    async def storage_usage(self, workspace_id: str) -> StorageUsage:
        document_bytes = await self.repos.documents.sum_size_bytes(workspace_id)
        document_count = await self.repos.documents.count_total(workspace_id)
        memory_count = await self.repos.memory_entries.count_for_workspace(workspace_id)
        knowledge_count = await self.repos.knowledge_items.count_for_workspace(workspace_id)
        return StorageUsage(total_document_bytes=document_bytes, document_count=document_count, memory_entry_count=memory_count, knowledge_item_count=knowledge_count)

    # -- per-agent memory usage --------------------------------------------------------------

    async def agent_memory_usage(self, workspace_id: str) -> list[AgentMemoryUsage]:
        grouped = await self.repos.memory_entries.group_count_by_scope(workspace_id, "agent")
        return [AgentMemoryUsage(agent_id=agent_id, entry_count=data["entry_count"], total_access_count=data["total_access_count"]) for agent_id, data in grouped.items()]
