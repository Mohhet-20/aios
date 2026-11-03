import pytest


@pytest.mark.asyncio
async def test_timeline_is_chronologically_sorted(ingestion_service, monitoring_service, workspace):
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", source_execution_id="exec-1", payload={"step": 1})
    await ingestion_service.ingest_event(workspace.id, event_type="model_usage", source_platform="prompt_platform", status="succeeded", source_execution_id="exec-1", payload={"step": 2})
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", source_execution_id="exec-2", payload={"step": 99})

    timeline = await monitoring_service.get_timeline(workspace.id, "exec-1")
    assert len(timeline) == 2
    assert [e.created_at for e in timeline] == sorted(e.created_at for e in timeline)
    assert [e.payload["step"] for e in timeline] == [1, 2]


@pytest.mark.asyncio
async def test_latency_stats_computed_from_reported_samples_only(ingestion_service, monitoring_service, workspace):
    for latency in [100.0, 200.0, 300.0]:
        await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", latency_ms=latency)
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded")  # no latency reported

    stats = await monitoring_service.get_latency_stats(workspace.id)
    assert stats["sample_count"] == 3
    assert stats["avg_ms"] == 200.0
    assert stats["min_ms"] == 100.0
    assert stats["max_ms"] == 300.0
    assert stats["p95_ms"] is not None


@pytest.mark.asyncio
async def test_latency_stats_empty_when_nothing_reported(monitoring_service, workspace):
    stats = await monitoring_service.get_latency_stats(workspace.id)
    assert stats == {"sample_count": 0, "avg_ms": None, "min_ms": None, "max_ms": None, "p95_ms": None}


@pytest.mark.asyncio
async def test_failure_stats_breakdown(ingestion_service, monitoring_service, workspace):
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded")
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="failed", error_type="TimeoutError", retry_count=2)
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="failed", error_type="TimeoutError", retry_count=1)
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="retried", retry_count=1)

    stats = await monitoring_service.get_failure_stats(workspace.id)
    assert stats["total_events"] == 4
    assert stats["failure_count"] == 2
    assert stats["retried_count"] == 1
    assert stats["failure_rate"] == 0.5
    assert stats["total_retries"] == 4
    assert stats["error_type_breakdown"] == {"TimeoutError": 2}


@pytest.mark.asyncio
async def test_resource_usage_stats_aggregate_only_reported_keys(ingestion_service, monitoring_service, workspace):
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", resource_usage={"cpu_seconds": 1.0, "peak_memory_mb": 50.0})
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", resource_usage={"cpu_seconds": 3.0})
    await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded")  # no resource usage

    stats = await monitoring_service.get_resource_usage_stats(workspace.id)
    assert stats["cpu_seconds"] == {"total": 4.0, "avg": 2.0, "sample_count": 2}
    assert stats["peak_memory_mb"] == {"total": 50.0, "avg": 50.0, "sample_count": 1}


@pytest.mark.asyncio
async def test_token_and_cost_stats(ingestion_service, monitoring_service, workspace):
    await ingestion_service.ingest_event(workspace.id, event_type="model_usage", source_platform="prompt_platform", status="succeeded", token_usage={"input_tokens": 10, "output_tokens": 5}, cost=0.01)
    await ingestion_service.ingest_event(workspace.id, event_type="model_usage", source_platform="prompt_platform", status="succeeded", token_usage={"input_tokens": 20, "output_tokens": 10}, cost=0.02)

    stats = await monitoring_service.get_token_and_cost_stats(workspace.id)
    assert stats["input_tokens"] == 30
    assert stats["output_tokens"] == 15
    assert stats["total_tokens"] == 45
    assert round(stats["total_cost"], 4) == 0.03
    assert stats["cost_sample_count"] == 2
