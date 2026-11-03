from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.forecasting.forecast_job_service import ForecastJobService
from analytics_platform.observability.forecast_accuracy_service import ForecastAccuracyService, compute_error_pct
from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService
from datetime import datetime, timedelta, timezone

TENANT = "accuracy-tenant"


def test_compute_error_pct_basic():
    assert compute_error_pct(predicted_value=100.0, actual_value=100.0) == 0.0
    assert compute_error_pct(predicted_value=90.0, actual_value=100.0) == 10.0


def test_compute_error_pct_zero_actual():
    assert compute_error_pct(predicted_value=0.0, actual_value=0.0) == 0.0
    assert compute_error_pct(predicted_value=5.0, actual_value=0.0) == 100.0


@pytest.mark.asyncio
async def test_record_accuracy_and_average(repos):
    service = ForecastAccuracyService(repos)
    await service.record_accuracy(TENANT, forecast_job_id="job-1", predicted_value=100.0, actual_value=110.0)
    await service.record_accuracy(TENANT, forecast_job_id="job-1", predicted_value=100.0, actual_value=90.0)

    entries = await service.list_for_job(TENANT, "job-1")
    assert len(entries) == 2
    avg = await service.average_error(TENANT, "job-1")
    assert avg == pytest.approx((10 / 110 * 100 + 10 / 90 * 100) / 2)


@pytest.mark.asyncio
async def test_average_error_no_entries_is_zero(repos):
    service = ForecastAccuracyService(repos)
    assert await service.average_error(TENANT, "no-such-job") == 0.0


@pytest.mark.asyncio
async def test_record_from_job_pulls_predicted_value(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="orders.count", name="Orders", data_source="workflows")
    ingestion = EventIngestionService(repos, registry=registry)
    engine = AggregationEngine(repos)
    base = datetime.now(timezone.utc) - timedelta(days=5)
    for day_offset, value in enumerate([10.0, 20.0, 30.0]):
        period_start = base + timedelta(days=day_offset)
        period_end = period_start + timedelta(days=1)
        await ingestion.ingest_event(TENANT, metric_key="orders.count", data_source="workflows", value=value, occurred_at=period_start + timedelta(hours=1))
        await engine.compute_rollup(TENANT, "orders.count", domain="business", period="daily", period_start=period_start, period_end=period_end, aggregation_type="sum")

    forecasts = ForecastJobService(repos)
    job = await forecasts.request_job(TENANT, forecast_type="usage", metric_key="orders.count", method="linear_regression", horizon_days=2)
    completed = await forecasts.run(TENANT, job.id)
    assert completed.status == "completed"

    accuracy = ForecastAccuracyService(repos)
    recorded = await accuracy.record_from_job(TENANT, completed, step=1, actual_value=41.0)
    assert recorded.predicted_value == completed.result["predictions"][0]["value"]
    assert recorded.actual_value == 41.0


@pytest.mark.asyncio
async def test_record_from_job_missing_step_raises(repos):
    from analytics_platform.models.forecasts import ForecastJobModel
    job = ForecastJobModel(tenant_id=TENANT, forecast_type="usage", metric_key="x", status="completed", result={"predictions": []})
    service = ForecastAccuracyService(repos)
    with pytest.raises(ValidationError):
        await service.record_from_job(TENANT, job, step=1, actual_value=1.0)
