from __future__ import annotations

import pytest

from analytics_platform.kpis.kpi_service import KpiService
from analytics_platform.kpis.snapshot_service import KpiSnapshotService

TENANT = "kpi-snapshot-tenant"


@pytest.mark.asyncio
async def test_record_snapshot_computes_health(repos):
    kpis = KpiService(repos)
    kpi = await kpis.register_kpi(
        TENANT, name="Task Completion", scope="business", metric_key="tasks.completed", target_value=0.9,
        higher_is_better=True, threshold_warning=0.7, threshold_critical=0.5,
    )
    snapshots = KpiSnapshotService(repos, kpi_service=kpis)
    snapshot = await snapshots.record_snapshot(TENANT, kpi.id, value=0.4)
    assert snapshot.health == "breached"


@pytest.mark.asyncio
async def test_history_and_trend_up(repos):
    kpis = KpiService(repos)
    kpi = await kpis.register_kpi(TENANT, name="Throughput", scope="engineering", metric_key="sys.throughput", target_value=1000)
    snapshots = KpiSnapshotService(repos, kpi_service=kpis)
    await snapshots.record_snapshot(TENANT, kpi.id, value=100.0)
    await snapshots.record_snapshot(TENANT, kpi.id, value=200.0)

    history = await snapshots.history(TENANT, kpi.id)
    assert len(history) == 2

    trend = await snapshots.trend(TENANT, kpi.id)
    assert trend == "up"


@pytest.mark.asyncio
async def test_trend_with_insufficient_data_is_flat(repos):
    kpis = KpiService(repos)
    kpi = await kpis.register_kpi(TENANT, name="New KPI", scope="custom", metric_key="new.metric", target_value=1)
    snapshots = KpiSnapshotService(repos, kpi_service=kpis)
    trend = await snapshots.trend(TENANT, kpi.id)
    assert trend == "flat"
