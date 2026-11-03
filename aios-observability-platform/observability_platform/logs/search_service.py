"""Log search/filtering. Lexical `LIKE`-based text search over the
message field plus exact-match filters on level/service/correlation
id/trace id/user id/time range — the same honestly-scoped lexical
approach the Collaboration Platform's search took for the same reason:
a real inverted index (Elasticsearch/OpenSearch-backed) is the
production answer at real log volumes, and swapping one in behind this
service's interface is a one-file change, not a redesign."""
from __future__ import annotations

from datetime import datetime

from observability_platform.config.settings import Settings, get_settings
from observability_platform.models.logs import LogEntryModel
from observability_platform.repositories.registry import RepositoryRegistry


class LogSearchService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def search(
        self,
        tenant_id: str,
        *,
        level: str | None = None,
        service_name: str | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        user_id: str | None = None,
        text_query: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[LogEntryModel]:
        return await self.repos.log_entries.search(
            tenant_id,
            level=level,
            service_name=service_name,
            correlation_id=correlation_id,
            trace_id=trace_id,
            user_id=user_id,
            text_query=text_query,
            start_time=start_time,
            end_time=end_time,
            limit=limit or self.settings.log_search_default_limit,
        )

    async def by_correlation_id(self, tenant_id: str, correlation_id: str) -> list[LogEntryModel]:
        """Pulls every log line stitched to one request/operation across
        every service that touched it — the log-side counterpart to a
        distributed trace, useful when a caller only has a correlation
        id and no trace id (not every log line is guaranteed to carry
        one)."""
        return await self.repos.log_entries.search(tenant_id, correlation_id=correlation_id, limit=5000)

    async def by_trace_id(self, tenant_id: str, trace_id: str) -> list[LogEntryModel]:
        return await self.repos.log_entries.search(tenant_id, trace_id=trace_id, limit=5000)

    async def level_counts(
        self, tenant_id: str, *, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> dict[str, int]:
        return await self.repos.log_entries.count_by_level(tenant_id, start_time=start_time, end_time=end_time)

    async def total_count(
        self, tenant_id: str, *, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> int:
        return await self.repos.log_entries.count_total(tenant_id, start_time=start_time, end_time=end_time)
