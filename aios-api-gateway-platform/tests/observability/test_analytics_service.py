from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from gateway_platform.core.exceptions import MetricNotFoundError, ValidationError
from gateway_platform.observability.analytics_service import AnalyticsSnapshotService

TENANT = "obs-analytics-tenant"


def _period():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=1)
    return start, end


@pytest.mark.asyncio
async def test_create_snapshot_rejects_unknown_type(repos):
    service = AnalyticsSnapshotService(repos)
    start, end = _period()
    with pytest.raises(ValidationError):
        await service.create_snapshot(TENANT, snapshot_type="not_a_type", period_start=start, period_end=end, data={})


@pytest.mark.asyncio
async def test_create_and_list_by_type(repos):
    service = AnalyticsSnapshotService(repos)
    start, end = _period()
    await service.create_snapshot(
        TENANT, snapshot_type="api_usage", period_start=start, period_end=end, data={"calls": 1000},
    )
    snapshots = await service.list_by_type(TENANT, "api_usage")
    assert len(snapshots) == 1
    assert snapshots[0].data == {"calls": 1000}


@pytest.mark.asyncio
async def test_latest_raises_when_none_recorded(repos):
    service = AnalyticsSnapshotService(repos)
    with pytest.raises(MetricNotFoundError):
        await service.latest(TENANT, "capacity_trends")


@pytest.mark.asyncio
async def test_latest_returns_most_recent(repos):
    service = AnalyticsSnapshotService(repos)
    start, end = _period()
    await service.create_snapshot(
        TENANT, snapshot_type="version_adoption", period_start=start, period_end=end, data={"v1": 90, "v2": 10},
    )
    latest = await service.latest(TENANT, "version_adoption")
    assert latest.data == {"v1": 90, "v2": 10}
