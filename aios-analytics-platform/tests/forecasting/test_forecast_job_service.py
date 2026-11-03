from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.core.exceptions import ForecastGenerationFailedError, UnsupportedForecastTypeError, ValidationError
from analytics_platform.forecasting.forecast_job_service import ForecastJobService
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "forecast-tenant"


async def _seed_daily_rollups(repos, *, metric_key: str, domain: str, values: list[float]) -> None:
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key=metric_key, name=metric_key, data_source="workflows")
    ingestion = EventIngestionService(repos, registry=registry)
    engine = AggregationEngine(repos)
    base = datetime.now(timezone.utc) - timedelta(days=len(values) + 1)
    for day_offset, value in enumerate(values):
        period_start = base + timedelta(days=day_offset)
        period_end = period_start + timedelta(days=1)
        await ingestion.ingest_event(TENANT, metric_key=metric_key, data_source="workflows", value=value, occurred_at=period_start + timedelta(hours=1))
        await engine.compute_rollup(
            TENANT, metric_key, domain=domain, period="daily", period_start=period_start, period_end=period_end, aggregation_type="sum",
        )


@pytest.mark.asyncio
async def test_request_job_rejects_bad_forecast_type(repos):
    service = ForecastJobService(repos)
    with pytest.raises(UnsupportedForecastTypeError):
        await service.request_job(TENANT, forecast_type="not_a_type", metric_key="x")


@pytest.mark.asyncio
async def test_request_job_rejects_bad_method(repos):
    service = ForecastJobService(repos)
    with pytest.raises(ValidationError):
        await service.request_job(TENANT, forecast_type="usage", metric_key="x", method="astrology")


@pytest.mark.asyncio
async def test_request_job_rejects_non_positive_horizon(repos):
    service = ForecastJobService(repos)
    with pytest.raises(ValidationError):
        await service.request_job(TENANT, forecast_type="usage", metric_key="x", horizon_days=0)


@pytest.mark.asyncio
async def test_run_fails_with_insufficient_history(repos):
    service = ForecastJobService(repos)
    job = await service.request_job(TENANT, forecast_type="usage", metric_key="orders.count", horizon_days=7)
    completed = await service.run(TENANT, job.id)
    assert completed.status == "failed"
    assert "rollup points" in completed.error.lower()


@pytest.mark.asyncio
async def test_run_produces_linear_regression_predictions(repos):
    await _seed_daily_rollups(repos, metric_key="orders.count", domain="business", values=[10.0, 20.0, 30.0, 40.0, 50.0])
    service = ForecastJobService(repos)
    job = await service.request_job(TENANT, forecast_type="usage", metric_key="orders.count", method="linear_regression", horizon_days=3)

    completed = await service.run(TENANT, job.id)
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.result["history_points"] == 5
    assert len(completed.result["predictions"]) == 3
    assert completed.result["predictions"][0]["value"] == pytest.approx(60.0)
    assert completed.result["domain"] == "business"
    assert completed.result["period"] == "daily"


@pytest.mark.asyncio
async def test_run_moving_average_method(repos):
    await _seed_daily_rollups(repos, metric_key="latency.ms", domain="performance", values=[100.0, 200.0, 300.0])
    service = ForecastJobService(repos)
    job = await service.request_job(TENANT, forecast_type="performance_trend", metric_key="latency.ms", method="moving_average", horizon_days=2)

    completed = await service.run(TENANT, job.id)
    assert completed.status == "completed"
    assert completed.result["method"] == "moving_average"
    assert completed.result["predictions"][0]["value"] == pytest.approx(200.0)


@pytest.mark.asyncio
async def test_run_detects_anomalies_in_history(repos):
    await _seed_daily_rollups(repos, metric_key="cost.spend", domain="financial", values=[10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 500.0])
    service = ForecastJobService(repos)
    job = await service.request_job(TENANT, forecast_type="cost", metric_key="cost.spend", method="exponential_smoothing", horizon_days=1)

    completed = await service.run(TENANT, job.id)
    assert completed.status == "completed"
    assert any(a["value"] == 500.0 for a in completed.result["anomalies_in_history"])


@pytest.mark.asyncio
async def test_list_for_tenant_filters_by_forecast_type(repos):
    service = ForecastJobService(repos)
    await service.request_job(TENANT, forecast_type="usage", metric_key="a")
    await service.request_job(TENANT, forecast_type="cost", metric_key="b")

    usage_jobs = await service.list_for_tenant(TENANT, forecast_type="usage")
    assert len(usage_jobs) == 1
    assert usage_jobs[0].forecast_type == "usage"


@pytest.mark.asyncio
async def test_fail_before_start_raises(repos):
    service = ForecastJobService(repos)
    job = await service.request_job(TENANT, forecast_type="usage", metric_key="x")
    with pytest.raises(ForecastGenerationFailedError):
        await service.fail(TENANT, job.id, error="too early")
