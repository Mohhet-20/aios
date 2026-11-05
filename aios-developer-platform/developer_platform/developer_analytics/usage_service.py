"""Developer Analytics: one append-only event log
(`dev_usage_events`) covering all eight tracked event types — SDK
calls, API calls, CLI commands, plugin installs, webhook deliveries,
developer activity, package downloads, and API errors — via an
`event_type` discriminator rather than eight separate tables, mirroring
the generic time-series pattern used by every other AIOS platform's
observability module. `developer_analytics_sample_rate` controls what
fraction of events actually get persisted; the sampling decision is
injectable (`rand=`) so tests never depend on real randomness."""
from __future__ import annotations

import random
from datetime import timedelta
from typing import Callable

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import AnalyticsError
from developer_platform.database.base import utcnow
from developer_platform.domain.enums import UsageEventType
from developer_platform.models.analytics import UsageEventModel
from developer_platform.repositories.registry import RepositoryRegistry


class UsageAnalyticsService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, rand: Callable[[], float] = random.random):
        self.repos = repos
        self.settings = settings or get_settings()
        self._rand = rand

    async def record_event(
        self, tenant_id: str, event_type: str, *, resource_type: str | None = None, resource_id: str | None = None,
        developer_id: str | None = None, metadata: dict | None = None,
    ) -> UsageEventModel | None:
        if event_type not in {t.value for t in UsageEventType}:
            raise AnalyticsError(f"'{event_type}' is not a recognized usage event type")
        if self._rand() >= self.settings.developer_analytics_sample_rate:
            return None

        event = UsageEventModel(
            tenant_id=tenant_id, event_type=event_type, resource_type=resource_type, resource_id=resource_id,
            developer_id=developer_id, event_metadata=metadata or {},
        )
        return await self.repos.usage_events.add(event)

    async def record_sdk_call(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.SDK_CALL.value, developer_id=developer_id, **kwargs)

    async def record_api_call(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.API_CALL.value, developer_id=developer_id, **kwargs)

    async def record_cli_command(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.CLI_COMMAND.value, developer_id=developer_id, **kwargs)

    async def record_plugin_install(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.PLUGIN_INSTALL.value, developer_id=developer_id, **kwargs)

    async def record_webhook_delivery(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.WEBHOOK_DELIVERY.value, developer_id=developer_id, **kwargs)

    async def record_developer_activity(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.DEVELOPER_ACTIVITY.value, developer_id=developer_id, **kwargs)

    async def record_package_download(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.PACKAGE_DOWNLOAD.value, developer_id=developer_id, **kwargs)

    async def record_api_error(self, tenant_id: str, *, developer_id: str | None = None, **kwargs) -> UsageEventModel | None:
        return await self.record_event(tenant_id, UsageEventType.API_ERROR.value, developer_id=developer_id, **kwargs)

    async def get_summary(self, tenant_id: str) -> dict[str, int]:
        return await self.repos.usage_events.count_by_type(tenant_id)

    async def list_recent(self, tenant_id: str, *, event_type: str | None = None, limit: int = 200) -> list[UsageEventModel]:
        return await self.repos.usage_events.list_recent(tenant_id, event_type=event_type, limit=limit)

    async def purge_old_events(self, tenant_id: str) -> int:
        cutoff = utcnow() - timedelta(days=self.settings.analytics_retention_days)
        return await self.repos.usage_events.delete_older_than(tenant_id, cutoff)
