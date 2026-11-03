"""Lightweight in-process aggregation over the usage event log for the
Developer Analytics Dashboard: event-type counts (delegated to the
repository's SQL `GROUP BY`) plus a "most-used resources" ranking
computed in Python over a bounded recent window — simple enough not to
need its own materialized rollup table at this platform's scale."""
from __future__ import annotations

from collections import Counter

from developer_platform.repositories.registry import RepositoryRegistry


class DeveloperActivityDashboardService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def build_summary(self, tenant_id: str) -> dict[str, int]:
        return await self.repos.usage_events.count_by_type(tenant_id)

    async def top_resources(
        self, tenant_id: str, *, event_type: str | None = None, limit: int = 10, window: int = 1000,
    ) -> list[tuple[str, int]]:
        events = await self.repos.usage_events.list_recent(tenant_id, event_type=event_type, limit=window)
        counts = Counter(e.resource_id for e in events if e.resource_id is not None)
        return counts.most_common(limit)

    async def most_active_developers(
        self, tenant_id: str, *, event_type: str | None = None, limit: int = 10, window: int = 1000,
    ) -> list[tuple[str, int]]:
        events = await self.repos.usage_events.list_recent(tenant_id, event_type=event_type, limit=window)
        counts = Counter(e.developer_id for e in events if e.developer_id is not None)
        return counts.most_common(limit)
