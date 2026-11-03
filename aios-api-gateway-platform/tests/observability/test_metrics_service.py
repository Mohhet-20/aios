from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import ValidationError
from gateway_platform.observability.metrics_service import GatewayMetricsService

TENANT = "obs-metrics-tenant"


@pytest.mark.asyncio
async def test_record_metric_rejects_unknown_type(repos):
    service = GatewayMetricsService(repos)
    with pytest.raises(ValidationError):
        await service.record_metric(TENANT, metric_type="not_a_metric", value=1.0)


@pytest.mark.asyncio
async def test_record_and_list_recent(repos):
    service = GatewayMetricsService(repos)
    await service.record_metric(TENANT, metric_type="latency", value=120.0)
    await service.record_metric(TENANT, metric_type="latency", value=80.0)
    samples = await service.list_recent(TENANT, metric_type="latency")
    assert len(samples) == 2


@pytest.mark.asyncio
async def test_average_and_total(repos):
    service = GatewayMetricsService(repos)
    await service.record_metric(TENANT, metric_type="throughput", value=10.0)
    await service.record_metric(TENANT, metric_type="throughput", value=20.0)
    assert await service.average(TENANT, "throughput") == 15.0
    assert await service.total(TENANT, "throughput") == 30.0


@pytest.mark.asyncio
async def test_average_with_no_samples_is_zero(repos):
    service = GatewayMetricsService(repos)
    assert await service.average(TENANT, "error_rate") == 0.0


@pytest.mark.asyncio
async def test_error_rate_computation(repos):
    service = GatewayMetricsService(repos)
    await service.record_metric(TENANT, metric_type="api_calls", value=100.0)
    await service.record_metric(TENANT, metric_type="failures", value=5.0)
    assert await service.error_rate(TENANT) == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_error_rate_with_no_calls_is_zero(repos):
    service = GatewayMetricsService(repos)
    assert await service.error_rate(TENANT) == 0.0
