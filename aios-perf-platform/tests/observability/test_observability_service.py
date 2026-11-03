from __future__ import annotations

import pytest

from perf_platform.domain.enums import JobStatus
from perf_platform.observability.observability_service import (
    BenchmarkService,
    LatencyTrackingService,
    ThroughputTrackingService,
)

TENANT = "t-obs"


@pytest.mark.asyncio
async def test_latency_percentiles_and_slo(repos):
    svc = LatencyTrackingService(repos)
    for ms in [50, 100, 150, 200, 3000]:
        await svc.record(TENANT, "GET /widgets", ms)
    stats = await svc.percentiles(TENANT, "GET /widgets")
    assert stats["sample_count"] == 5
    assert stats["p99"] == 3000

    slo = await svc.slo_status(TENANT, "GET /widgets")
    assert slo["p99_within_slo"] is False  # 3000ms exceeds the 1500ms default SLO


@pytest.mark.asyncio
async def test_throughput_tracking(repos):
    svc = ThroughputTrackingService(repos)
    await svc.record(TENANT, "POST /jobs", request_count=300, window_seconds=60)
    rate = await svc.current_rate(TENANT, "POST /jobs")
    assert rate == 5.0


@pytest.mark.asyncio
async def test_benchmark_lifecycle_completed(repos):
    svc = BenchmarkService(repos)
    run = await svc.start(TENANT, name="cache-vs-nocache", target_ref="response-cache")
    assert run.status == JobStatus.RUNNING.value

    completed = await svc.complete(TENANT, run.id, baseline_ms=500.0, optimized_ms=50.0)
    assert completed.status == JobStatus.COMPLETED.value
    assert completed.improvement_pct == 90.0


@pytest.mark.asyncio
async def test_benchmark_lifecycle_failed(repos):
    svc = BenchmarkService(repos)
    run = await svc.start(TENANT, name="failing-benchmark")
    failed = await svc.fail(TENANT, run.id)
    assert failed.status == JobStatus.FAILED.value
    with pytest.raises(Exception):
        await svc.complete(TENANT, run.id, baseline_ms=1, optimized_ms=1)
