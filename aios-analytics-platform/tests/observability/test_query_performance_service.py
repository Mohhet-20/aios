from __future__ import annotations

import pytest

from analytics_platform.observability.query_performance_service import QueryPerformanceService

TENANT = "query-perf-tenant"


@pytest.mark.asyncio
async def test_record_and_list_recent(repos):
    service = QueryPerformanceService(repos)
    await service.record(TENANT, query_ref="dashboard.revenue_widget", duration_ms=50.0, row_count=100)
    await service.record(TENANT, query_ref="dashboard.revenue_widget", duration_ms=5000.0, row_count=100000)

    entries = await service.list_recent(TENANT)
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_list_slow_queries_filters_by_threshold(repos):
    service = QueryPerformanceService(repos)
    await service.record(TENANT, query_ref="fast", duration_ms=10.0)
    await service.record(TENANT, query_ref="slow", duration_ms=2000.0)

    slow = await service.list_slow_queries(TENANT, threshold_ms=1000.0)
    assert len(slow) == 1
    assert slow[0].query_ref == "slow"


@pytest.mark.asyncio
async def test_average_duration_overall_and_filtered(repos):
    service = QueryPerformanceService(repos)
    await service.record(TENANT, query_ref="a", duration_ms=100.0)
    await service.record(TENANT, query_ref="a", duration_ms=300.0)
    await service.record(TENANT, query_ref="b", duration_ms=1000.0)

    assert await service.average_duration(TENANT, query_ref="a") == 200.0
    assert await service.average_duration(TENANT) == pytest.approx(1400.0 / 3)


@pytest.mark.asyncio
async def test_average_duration_no_entries_is_zero(repos):
    service = QueryPerformanceService(repos)
    assert await service.average_duration(TENANT) == 0.0
