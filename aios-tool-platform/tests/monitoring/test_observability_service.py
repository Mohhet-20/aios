import pytest

from tool_platform.sandbox.subprocess_sandbox import SANDBOX_AVAILABLE

from tests.monitoring.conftest import make_published_tool


@pytest.mark.asyncio
async def test_execution_timeline_includes_created_started_completed_and_logs(
    engine, observability, tool_service, version_service, workspace
):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    execution = await engine.start_execution(tool.id, input_data={"hello": "world"})

    timeline = await observability.get_execution_timeline(execution.id)
    types = [e["type"] for e in timeline]
    assert "created" in types
    assert "started" in types
    assert "succeeded" in types
    assert any(e["type"] == "log" for e in timeline)
    # chronological order
    timestamps = [e["timestamp"] for e in timeline]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_queue_time_is_non_negative(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    execution = await engine.start_execution(tool.id, input_data={})
    queue_time = await observability.get_queue_time_ms(execution.id)
    assert queue_time is not None
    assert queue_time >= 0


@pytest.mark.asyncio
async def test_success_rate_reflects_mixed_outcomes(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    await engine.start_execution(tool.id, input_data={})
    await engine.start_execution(tool.id, input_data={})

    bad_tool, _bad_version = await make_published_tool(
        tool_service, version_service, workspace, name="Bad Tool", connector_key="does_not_exist",
    )
    with pytest.raises(Exception):
        await engine.start_execution(bad_tool.id, input_data={})

    stats = await observability.get_success_rate(tool.id)
    assert stats["total_executions"] == 2
    assert stats["succeeded"] == 2
    assert stats["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_latency_stats_computed_from_real_durations(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    for _ in range(3):
        await engine.start_execution(tool.id, input_data={})

    stats = await observability.get_latency_stats(tool.id)
    assert stats["sample_size"] == 3
    assert stats["avg_ms"] is not None
    assert stats["min_ms"] <= stats["avg_ms"] <= stats["max_ms"]


@pytest.mark.asyncio
async def test_latency_stats_empty_when_no_executions(observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    stats = await observability.get_latency_stats(tool.id)
    assert stats["sample_size"] == 0
    assert stats["avg_ms"] is None


@pytest.mark.asyncio
async def test_retry_stats_counts_only_retried_executions(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="echo", default_max_retries=0,
    )
    await engine.start_execution(tool.id, input_data={})
    stats = await observability.get_retry_stats(tool.id)
    assert stats["retried_count"] == 0
    assert stats["total_executions"] == 1


@pytest.mark.asyncio
async def test_resource_usage_stats_reports_zero_sample_for_non_sandboxed_tool(
    engine, observability, tool_service, version_service, workspace
):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    await engine.start_execution(tool.id, input_data={})
    stats = await observability.get_resource_usage_stats(tool.id)
    assert stats["cpu_seconds"]["sample_size"] == 0
    assert stats["cpu_seconds"]["avg"] is None


@pytest.mark.skipif(not SANDBOX_AVAILABLE, reason="needs POSIX rlimits (runs on Linux CI)")
@pytest.mark.asyncio
async def test_resource_usage_stats_reports_real_measurements_for_sandboxed_tool(
    engine, observability, tool_service, version_service, workspace
):
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="python_execution",
        configuration={"code": "print('hi')"},
    )
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == "succeeded"

    resource_usage = await observability.get_resource_usage(execution.id)
    assert resource_usage.get("cpu_seconds") is not None
    assert resource_usage.get("peak_memory_mb") is not None

    stats = await observability.get_resource_usage_stats(tool.id)
    assert stats["cpu_seconds"]["sample_size"] == 1
    assert stats["cpu_seconds"]["avg"] is not None
    assert stats["peak_memory_mb"]["sample_size"] == 1


@pytest.mark.asyncio
async def test_resource_usage_stats_reports_network_bytes_for_http_tool(
    engine, observability, tool_service, version_service, workspace, monkeypatch
):
    import httpx

    from tool_platform.connectors import http_client as http_client_module

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(http_client_module, "HttpClientHandler", http_client_module.HttpClientHandler)
    engine.connectors.register("http_client", http_client_module.HttpClientHandler(client=mock_client))

    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="http_client",
        configuration={"url": "https://api.example.com/data", "method": "GET"},
    )
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == "succeeded"

    stats = await observability.get_resource_usage_stats(tool.id)
    assert stats["network_bytes"]["sample_size"] == 1
    assert stats["network_bytes"]["avg"] > 0
    await mock_client.aclose()


@pytest.mark.asyncio
async def test_usage_trends_buckets_by_day(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    await engine.start_execution(tool.id, input_data={})
    await engine.start_execution(tool.id, input_data={})

    trends = await observability.get_usage_trends(tool.id)
    assert sum(trends.values()) == 2
    assert len(trends) == 1  # both calls happened "today" in this test run


@pytest.mark.asyncio
async def test_workspace_call_volume_aggregates_by_status(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(tool_service, version_service, workspace, connector_key="echo")
    await engine.start_execution(tool.id, input_data={})
    await engine.start_execution(tool.id, input_data={})

    volume = await observability.get_workspace_call_volume(workspace.id)
    assert volume["total_calls"] == 2
    assert volume["by_status"]["succeeded"] == 2


@pytest.mark.asyncio
async def test_failure_stats_collects_sample_errors(engine, observability, tool_service, version_service, workspace):
    tool, _version = await make_published_tool(
        tool_service, version_service, workspace, connector_key="python_execution",
        default_max_retries=0, configuration={},
    )
    execution = await engine.start_execution(tool.id, input_data={})
    assert execution.status == "failed"

    stats = await observability.get_failure_stats(tool.id)
    assert stats["failure_count"] == 1
    assert len(stats["sample_errors"]) == 1
