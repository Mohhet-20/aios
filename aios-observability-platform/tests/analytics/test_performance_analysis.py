from __future__ import annotations

import pytest

from observability_platform.analytics.performance_service import PerformanceAnalysisService
from observability_platform.core.exceptions import PerformanceAnalysisError
from observability_platform.metrics.ingest_service import MetricIngestService
from observability_platform.tracing.span_service import SpanService
from observability_platform.tracing.trace_service import TraceService


@pytest.mark.asyncio
async def test_latency_analysis_uses_metric_aggregation(repos):
    metric_svc = MetricIngestService(repos)
    for v in [100.0, 200.0, 300.0]:
        await metric_svc.ingest("t1", name="perf_api_latency_ms", metric_type="gauge", value=v)

    perf_svc = PerformanceAnalysisService(repos)
    result = await perf_svc.latency_analysis("t1", "perf_api_latency_ms")
    assert result.count == 3
    assert result.avg == 200.0


@pytest.mark.asyncio
async def test_detect_bottleneck_identifies_slowest_span(repos):
    span_svc = SpanService(repos)
    trace_svc = TraceService(repos)

    root = await span_svc.start_span("t1", trace_id="perf-trace-1", span_id="root", service_name="api", operation_name="handle_request")
    slow = await span_svc.start_span(
        "t1", trace_id="perf-trace-1", span_id="slow-child", parent_span_id="root",
        service_name="db", operation_name="big_query", span_kind="database_query",
    )
    fast = await span_svc.start_span(
        "t1", trace_id="perf-trace-1", span_id="fast-child", parent_span_id="root",
        service_name="cache", operation_name="lookup",
    )
    from datetime import timedelta
    await span_svc.end_span("t1", slow, status="ok", end_time=slow.start_time + timedelta(milliseconds=500))
    await span_svc.end_span("t1", fast, status="ok", end_time=fast.start_time + timedelta(milliseconds=5))
    await span_svc.end_span("t1", root, status="ok", end_time=root.start_time + timedelta(milliseconds=520))
    await trace_svc.finalize_trace("t1", "perf-trace-1")

    perf_svc = PerformanceAnalysisService(repos)
    bottleneck = await perf_svc.detect_bottleneck("t1", "perf-trace-1")
    assert bottleneck["span_id"] == "slow-child"
    assert bottleneck["share_of_trace_pct"] > 50


@pytest.mark.asyncio
async def test_detect_bottleneck_raises_when_no_completed_spans(repos):
    span_svc = SpanService(repos)
    await span_svc.start_span("t1", trace_id="perf-trace-2", span_id="root", service_name="api", operation_name="op")

    perf_svc = PerformanceAnalysisService(repos)
    with pytest.raises(PerformanceAnalysisError):
        await perf_svc.detect_bottleneck("t1", "perf-trace-2")


@pytest.mark.asyncio
async def test_slow_query_analysis_groups_by_operation(repos):
    span_svc = SpanService(repos)
    from datetime import timedelta

    for i, dur in enumerate([50, 150, 300]):
        span = await span_svc.start_span(
            "t1", trace_id=f"perf-trace-q{i}", span_id=f"q{i}", service_name="db",
            operation_name="SELECT users", span_kind="database_query",
        )
        await span_svc.end_span("t1", span, status="ok", end_time=span.start_time + timedelta(milliseconds=dur))

    perf_svc = PerformanceAnalysisService(repos)
    slow = await perf_svc.slow_query_analysis("t1", threshold_ms=100.0)
    assert len(slow) == 1
    assert slow[0]["operation_name"] == "SELECT users"
    assert slow[0]["count"] == 2  # only the 150ms and 300ms queries clear the threshold


@pytest.mark.asyncio
async def test_performance_by_span_kind_groups_tool_calls(repos):
    span_svc = SpanService(repos)
    from datetime import timedelta

    span = await span_svc.start_span(
        "t1", trace_id="perf-trace-tool", span_id="tool1", service_name="tool-platform",
        operation_name="web_search", span_kind="tool_call",
    )
    await span_svc.end_span("t1", span, status="ok", end_time=span.start_time + timedelta(milliseconds=250))

    perf_svc = PerformanceAnalysisService(repos)
    results = await perf_svc.performance_by_span_kind("t1", "tool_call")
    assert len(results) == 1
    assert results[0]["operation_name"] == "web_search"
    assert results[0]["avg"] == 250.0
