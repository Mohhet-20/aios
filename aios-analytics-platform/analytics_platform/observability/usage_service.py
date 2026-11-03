"""Usage tracking for the analytics platform itself: every dashboard
view, report generation, query execution, visualization render,
forecast run, and recommendation action gets a row here across the
six usage-event types the prompt specifies. `summarize()` gives the
"how is this platform actually being used" rollup that a self-review
of adoption depends on; `sweep_retention()` mirrors the same
retention-sweep pattern the Data Warehouse (Task #263) already
established for raw metric events."""
from __future__ import annotations

from datetime import timedelta

from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.core.exceptions import ValidationError
from analytics_platform.domain.enums import UsageEventType
from analytics_platform.models.observability import UsageEventModel
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.clock import utc_now


class UsageEventService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid_event_type(self, event_type: str) -> None:
        if event_type not in {e.value for e in UsageEventType}:
            raise ValidationError(f"'{event_type}' is not a recognized usage event type")

    async def record(
        self, tenant_id: str, *, event_type: str, resource_type: str | None = None, resource_id: str | None = None,
        actor_id: str | None = None, duration_ms: float = 0.0,
    ) -> UsageEventModel:
        self._assert_valid_event_type(event_type)
        event = UsageEventModel(
            tenant_id=tenant_id, event_type=event_type, resource_type=resource_type, resource_id=resource_id,
            actor_id=actor_id, duration_ms=duration_ms,
        )
        return await self.repos.usage_events.add(event)

    async def list_recent(self, tenant_id: str, *, event_type: str | None = None, limit: int = 500) -> list[UsageEventModel]:
        return await self.repos.usage_events.list_recent(tenant_id, event_type=event_type, limit=limit)

    async def summarize(self, tenant_id: str, *, limit: int = 500) -> dict[str, int]:
        events = await self.list_recent(tenant_id, limit=limit)
        summary: dict[str, int] = {}
        for event in events:
            summary[event.event_type] = summary.get(event.event_type, 0) + 1
        return summary

    async def sweep_retention(self, tenant_id: str) -> int:
        cutoff = utc_now() - timedelta(days=self.settings.observability_usage_retention_days)
        return await self.repos.usage_events.delete_older_than(tenant_id, cutoff)
