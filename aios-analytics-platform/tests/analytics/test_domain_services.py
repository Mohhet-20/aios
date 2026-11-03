from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from analytics_platform.analytics.ai_analytics_service import AiAnalyticsService
from analytics_platform.analytics.business_analytics_service import BusinessAnalyticsService
from analytics_platform.analytics.financial_analytics_service import FinancialAnalyticsService
from analytics_platform.analytics.performance_analytics_service import PerformanceAnalyticsService
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "domain-svc-tenant"


def _window():
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)
    return start, end


@pytest.mark.asyncio
async def test_business_analytics_rollup_is_domain_locked(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="users.active", name="Active Users", data_source="users")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    await ingestion.ingest_event(TENANT, metric_key="users.active", data_source="users", value=1.0, occurred_at=start + timedelta(minutes=1))

    service = BusinessAnalyticsService(repos)
    rollup = await service.compute_rollup(TENANT, "users.active", period="hourly", period_start=start, period_end=end, aggregation_type="sum")
    assert rollup.domain == "business"

    rollups = await service.list_rollups(TENANT, "users.active")
    assert all(r.domain == "business" for r in rollups)


@pytest.mark.asyncio
async def test_ai_analytics_rollup(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="prompt.success_rate", name="Prompt Success Rate", data_source="prompts", unit="percentage")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    for v in (1.0, 0.0, 1.0):
        await ingestion.ingest_event(TENANT, metric_key="prompt.success_rate", data_source="prompts", value=v, occurred_at=start + timedelta(minutes=1))

    service = AiAnalyticsService(repos)
    rollup = await service.compute_rollup(TENANT, "prompt.success_rate", period="hourly", period_start=start, period_end=end)
    assert rollup.domain == "ai"
    assert rollup.value == pytest.approx(2 / 3)


@pytest.mark.asyncio
async def test_financial_analytics_rollup_and_roi(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="infra.cost", name="Infra Cost", data_source="infrastructure", unit="currency_usd")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    await ingestion.ingest_event(TENANT, metric_key="infra.cost", data_source="infrastructure", value=500.0, occurred_at=start + timedelta(minutes=1))

    service = FinancialAnalyticsService(repos)
    rollup = await service.compute_rollup(TENANT, "infra.cost", period="hourly", period_start=start, period_end=end)
    assert rollup.domain == "financial"
    assert rollup.value == 500.0

    roi = FinancialAnalyticsService.compute_roi(value_generated=1500.0, cost_incurred=500.0)
    assert roi == 2.0
    assert FinancialAnalyticsService.compute_roi(value_generated=100.0, cost_incurred=0.0) == 0.0


@pytest.mark.asyncio
async def test_performance_analytics_rollup_and_availability(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="api.error_rate", name="Error Rate", data_source="api_gateway", unit="percentage")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    for v in (0.01, 0.02, 0.05):
        await ingestion.ingest_event(TENANT, metric_key="api.error_rate", data_source="api_gateway", value=v, occurred_at=start + timedelta(minutes=1))

    service = PerformanceAnalyticsService(repos)
    rollup = await service.compute_rollup(TENANT, "api.error_rate", period="hourly", period_start=start, period_end=end)
    assert rollup.domain == "performance"

    availability = PerformanceAnalyticsService.compute_availability(uptime_seconds=3595, total_seconds=3600)
    assert availability == pytest.approx(0.99861, rel=1e-3)
    assert PerformanceAnalyticsService.compute_availability(uptime_seconds=10, total_seconds=0) == 0.0
