from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from analytics_platform.config.settings import Settings
from analytics_platform.core.exceptions import ValidationError
from analytics_platform.observability.usage_service import UsageEventService

TENANT = "usage-tenant"


@pytest.mark.asyncio
async def test_record_rejects_bad_event_type(repos):
    service = UsageEventService(repos)
    with pytest.raises(ValidationError):
        await service.record(TENANT, event_type="teleport")


@pytest.mark.asyncio
async def test_record_and_list_recent(repos):
    service = UsageEventService(repos)
    await service.record(TENANT, event_type="dashboard_view", resource_id="dash-1", actor_id="user-1")
    await service.record(TENANT, event_type="report_generate", resource_id="rep-1", actor_id="user-1")

    all_events = await service.list_recent(TENANT)
    assert len(all_events) == 2

    dashboard_only = await service.list_recent(TENANT, event_type="dashboard_view")
    assert len(dashboard_only) == 1


@pytest.mark.asyncio
async def test_summarize_counts_by_event_type(repos):
    service = UsageEventService(repos)
    await service.record(TENANT, event_type="query_execute")
    await service.record(TENANT, event_type="query_execute")
    await service.record(TENANT, event_type="forecast_run")

    summary = await service.summarize(TENANT)
    assert summary == {"query_execute": 2, "forecast_run": 1}


@pytest.mark.asyncio
async def test_sweep_retention_removes_old_events(repos):
    settings = Settings(observability_usage_retention_days=1)
    service = UsageEventService(repos, settings=settings)
    from analytics_platform.models.observability import UsageEventModel

    old_event = UsageEventModel(
        tenant_id=TENANT, event_type="dashboard_view", occurred_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    await repos.usage_events.add(old_event)
    await service.record(TENANT, event_type="dashboard_view")

    deleted = await service.sweep_retention(TENANT)
    assert deleted == 1
    remaining = await service.list_recent(TENANT)
    assert len(remaining) == 1
