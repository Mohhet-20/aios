from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.core.exceptions import UnsupportedAnalyticsDomainError, UnsupportedRollupPeriodError
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "agg-tenant"


def _window():
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)
    return start, end


@pytest.mark.asyncio
async def test_compute_rollup_sum(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="orders.created", name="Orders Created", data_source="workflows")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    for v in (1.0, 2.0, 3.0):
        await ingestion.ingest_event(TENANT, metric_key="orders.created", data_source="workflows", value=v, occurred_at=start + timedelta(minutes=1))

    engine = AggregationEngine(repos)
    rollup = await engine.compute_rollup(
        TENANT, "orders.created", domain="business", period="hourly", period_start=start, period_end=end, aggregation_type="sum",
    )
    assert rollup.value == 6.0
    assert rollup.sample_count == 3


@pytest.mark.asyncio
async def test_compute_rollup_percentiles(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="api.latency", name="API Latency", data_source="api_gateway", unit="milliseconds")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    for v in (10.0, 20.0, 30.0, 40.0, 50.0):
        await ingestion.ingest_event(TENANT, metric_key="api.latency", data_source="api_gateway", value=v, occurred_at=start + timedelta(minutes=1))

    engine = AggregationEngine(repos)
    p50 = await engine.compute_rollup(
        TENANT, "api.latency", domain="performance", period="hourly", period_start=start, period_end=end, aggregation_type="p50",
    )
    assert p50.value == 30.0


@pytest.mark.asyncio
async def test_compute_rollup_is_upsert(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="tokens.used", name="Tokens Used", data_source="models", unit="tokens")
    ingestion = EventIngestionService(repos, registry=registry)
    start, end = _window()
    await ingestion.ingest_event(TENANT, metric_key="tokens.used", data_source="models", value=100.0, occurred_at=start + timedelta(minutes=1))

    engine = AggregationEngine(repos)
    first = await engine.compute_rollup(
        TENANT, "tokens.used", domain="ai", period="hourly", period_start=start, period_end=end, aggregation_type="sum",
    )
    await ingestion.ingest_event(TENANT, metric_key="tokens.used", data_source="models", value=50.0, occurred_at=start + timedelta(minutes=2))
    second = await engine.compute_rollup(
        TENANT, "tokens.used", domain="ai", period="hourly", period_start=start, period_end=end, aggregation_type="sum",
    )
    assert first.id == second.id
    assert second.value == 150.0
    assert second.sample_count == 2


@pytest.mark.asyncio
async def test_compute_rollup_rejects_bad_domain_and_period(repos):
    engine = AggregationEngine(repos)
    start, end = _window()
    with pytest.raises(UnsupportedAnalyticsDomainError):
        await engine.compute_rollup(TENANT, "x", domain="not_a_domain", period="hourly", period_start=start, period_end=end)
    with pytest.raises(UnsupportedRollupPeriodError):
        await engine.compute_rollup(TENANT, "x", domain="business", period="not_a_period", period_start=start, period_end=end)
