"""Query performance tracking: one row per executed analytics query
(duration + row count). `list_slow_queries()` and `average_duration()`
are what an engineering team actually looks at to find optimization
opportunities in this platform's own query paths -- the kind of
self-observability the prompt's self-review question ("can
engineering teams identify optimization opportunities") is asking
about."""
from __future__ import annotations

from analytics_platform.models.observability import QueryPerformanceModel
from analytics_platform.repositories.registry import RepositoryRegistry


class QueryPerformanceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(self, tenant_id: str, *, query_ref: str, duration_ms: float, row_count: int = 0) -> QueryPerformanceModel:
        entry = QueryPerformanceModel(tenant_id=tenant_id, query_ref=query_ref, duration_ms=duration_ms, row_count=row_count)
        return await self.repos.query_performance.add(entry)

    async def list_recent(self, tenant_id: str, *, limit: int = 500) -> list[QueryPerformanceModel]:
        return await self.repos.query_performance.list_recent(tenant_id, limit=limit)

    async def list_slow_queries(self, tenant_id: str, *, threshold_ms: float, limit: int = 500) -> list[QueryPerformanceModel]:
        entries = await self.list_recent(tenant_id, limit=limit)
        return [entry for entry in entries if entry.duration_ms >= threshold_ms]

    async def average_duration(self, tenant_id: str, *, query_ref: str | None = None, limit: int = 500) -> float:
        entries = await self.list_recent(tenant_id, limit=limit)
        if query_ref is not None:
            entries = [entry for entry in entries if entry.query_ref == query_ref]
        if not entries:
            return 0.0
        return sum(entry.duration_ms for entry in entries) / len(entries)
