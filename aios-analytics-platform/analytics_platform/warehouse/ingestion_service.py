"""Event ingestion: the single entry point every collector for the
sixteen data sources the prompt specifies (authentication through
developer platform) writes through. Ingestion requires the metric to
already be registered in the Metrics Registry — this keeps the fact
table honest (`an_metric_events.metric_key` always resolves to a real
definition) rather than silently accepting typos as new metrics."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.core.exceptions import EventIngestionError, UnsupportedDataSourceError
from analytics_platform.database.base import utcnow
from analytics_platform.domain.enums import DataSourceType
from analytics_platform.models.warehouse import MetricEventModel
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService


class EventIngestionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, registry: MetricRegistryService | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.registry = registry or MetricRegistryService(repos)

    def _assert_supported_source(self, data_source: str) -> None:
        if data_source not in self.settings.warehouse_supported_sources:
            raise UnsupportedDataSourceError(f"'{data_source}' is not a supported data source")
        DataSourceType(data_source)  # defensive: enum/settings lists must stay in sync

    async def ingest_event(
        self, tenant_id: str, *, metric_key: str, data_source: str, value: float,
        dimensions: dict[str, Any] | None = None, occurred_at: datetime | None = None,
    ) -> MetricEventModel:
        self._assert_supported_source(data_source)
        await self.registry.get_by_key(tenant_id, metric_key)  # raises MetricDefinitionNotFoundError if unregistered
        event = MetricEventModel(
            tenant_id=tenant_id, metric_key=metric_key, data_source=data_source, value=value,
            dimensions=dimensions or {}, occurred_at=occurred_at or utcnow(),
        )
        return await self.repos.metric_events.add(event)

    async def ingest_batch(self, tenant_id: str, events: list[dict[str, Any]]) -> list[MetricEventModel]:
        if len(events) > self.settings.warehouse_batch_ingest_max_size:
            raise EventIngestionError(
                f"batch of {len(events)} events exceeds max batch size {self.settings.warehouse_batch_ingest_max_size}"
            )
        recorded: list[MetricEventModel] = []
        for event in events:
            recorded.append(await self.ingest_event(tenant_id, **event))
        return recorded

    async def list_for_metric(
        self, tenant_id: str, metric_key: str, *, since: datetime | None = None, limit: int = 1000,
    ) -> list[MetricEventModel]:
        return await self.repos.metric_events.list_for_metric(tenant_id, metric_key, since=since, limit=limit)

    async def sweep_retention(self, tenant_id: str) -> int:
        cutoff = utcnow() - timedelta(days=self.settings.warehouse_event_retention_days)
        return await self.repos.metric_events.delete_older_than(tenant_id, cutoff)
