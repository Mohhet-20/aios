from __future__ import annotations

import pytest

from observability_platform.core.exceptions import HighCardinalityError, ValidationError
from observability_platform.metrics.aggregation_service import aggregate
from observability_platform.metrics.ingest_service import MetricIngestService
from observability_platform.metrics.query_service import MetricQueryService


@pytest.mark.asyncio
async def test_ingest_registers_definition_once(repos):
    svc = MetricIngestService(repos)
    await svc.ingest("t1", name="cpu_usage", metric_type="gauge", value=10.0, unit="percent")
    await svc.ingest("t1", name="cpu_usage", metric_type="gauge", value=20.0, unit="percent")

    definition = await repos.metric_definitions.get_by_name("t1", "cpu_usage")
    assert definition is not None
    points = await repos.metric_points.query_range("t1", "cpu_usage")
    assert len(points) == 2


@pytest.mark.asyncio
async def test_ingest_rejects_unknown_metric_type(repos):
    svc = MetricIngestService(repos)
    with pytest.raises(ValidationError):
        await svc.ingest("t1", name="x", metric_type="not-a-type", value=1.0)


@pytest.mark.asyncio
async def test_ingest_rejects_high_cardinality_labels(repos):
    svc = MetricIngestService(repos)
    svc.settings.metric_high_cardinality_label_limit = 2
    with pytest.raises(HighCardinalityError):
        await svc.ingest("t1", name="x", metric_type="counter", value=1.0, labels={"a": 1, "b": 2, "c": 3})


@pytest.mark.asyncio
async def test_query_latest_and_aggregate(repos):
    svc = MetricIngestService(repos)
    for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
        await svc.ingest("t1", name="latency_ms", metric_type="gauge", value=v)

    query = MetricQueryService(repos)
    latest = await query.latest("t1", "latency_ms")
    assert latest is not None and latest.value == 50.0

    agg = await query.aggregate_range("t1", "latency_ms")
    assert agg.count == 5
    assert agg.avg == 30.0
    assert agg.min == 10.0
    assert agg.max == 50.0
    assert agg.p50 > 0


def test_aggregate_empty_is_safe():
    result = aggregate([])
    assert result.count == 0
    assert result.avg == 0.0


def test_aggregate_percentiles_nearest_rank():
    values = list(range(1, 101))  # 1..100
    result = aggregate([float(v) for v in values])
    assert result.p50 == 50.0
    assert result.p95 == 95.0
    assert result.p99 == 99.0


@pytest.mark.asyncio
async def test_component_scoped_queries_are_isolated(repos):
    svc = MetricIngestService(repos)
    await svc.ingest("t1", name="req_count", metric_type="counter", value=1.0, component_id="comp-a")
    await svc.ingest("t1", name="req_count", metric_type="counter", value=2.0, component_id="comp-b")

    query = MetricQueryService(repos)
    comp_a_points = await query.query_range("t1", "req_count", component_id="comp-a")
    assert len(comp_a_points) == 1
    assert comp_a_points[0].value == 1.0
