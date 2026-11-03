import asyncio

import pytest

from tests.execution.conftest import make_engine, publish_graph
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.monitoring.observability_service import ObservabilityService
from workflow_platform.node_library.registry import seed_node_definitions
from workflow_platform.workflow_core.version_service import WorkflowVersionService
from workflow_platform.workflow_core.workflow_service import WorkflowService


@pytest.fixture(autouse=True)
async def _seed(repos):
    await seed_node_definitions(repos)


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Obs Co", organization_id="org-1", slug="obs-co"))


@pytest.fixture
def workflow_service(repos):
    return WorkflowService(repos)


@pytest.fixture
def version_service(repos):
    return WorkflowVersionService(repos)


async def _linear_workflow(workflow_service, version_service, workspace, *, name="Obs WF"):
    wf = await workflow_service.create_workflow(workspace.id, name=name, owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "delay", "node_type": "delay", "name": "Delay", "config": {"seconds": 0}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "delay"},
            {"source_node_key": "delay", "target_node_key": "end"},
        ],
    )
    return wf


@pytest.mark.asyncio
async def test_execution_timeline_is_chronologically_ordered(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    timeline = await obs.get_execution_timeline(execution.id)
    assert len(timeline) > 0
    timestamps = [e["timestamp"] for e in timeline]
    assert timestamps == sorted(timestamps)
    assert any(e["type"] == "node_succeeded" for e in timeline)


@pytest.mark.asyncio
async def test_execution_graph_annotates_node_status(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    graph = await obs.get_execution_graph(execution.id)
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2
    node_by_key = {n["node_key"]: n for n in graph["nodes"]}
    assert node_by_key["delay"]["status"] == "succeeded"
    assert node_by_key["delay"]["duration_ms"] is not None


@pytest.mark.asyncio
async def test_execution_logs_capture_success(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    logs = await obs.list_execution_logs(execution.id)
    assert len(logs) >= 3  # one success log per node
    assert any("delay" in log.message for log in logs)


@pytest.mark.asyncio
async def test_queue_time_is_measured(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    execution = await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    queue_time = await obs.get_queue_time_ms(execution.id)
    assert queue_time is not None
    assert queue_time >= 0


@pytest.mark.asyncio
async def test_success_rate_across_multiple_executions(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    for _ in range(3):
        await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    stats = await obs.get_success_rate(wf.id)
    assert stats["total_executions"] == 3
    assert stats["completed"] == 3
    assert stats["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_latency_stats_computed_from_real_durations(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    await engine.start_execution(wf.id, triggered_by="u1")
    await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    stats = await obs.get_latency_stats(wf.id)
    assert stats["sample_size"] == 2
    assert stats["avg_ms"] >= 0
    assert stats["min_ms"] <= stats["max_ms"]


@pytest.mark.asyncio
async def test_node_duration_stats_per_node_key(repos, workspace, workflow_service, version_service):
    wf = await _linear_workflow(workflow_service, version_service, workspace)
    engine = make_engine(repos)
    await engine.start_execution(wf.id, triggered_by="u1")
    await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    stats = await obs.get_node_duration_stats(wf.id)
    assert "delay" in stats
    assert stats["delay"]["sample_size"] == 2


@pytest.mark.asyncio
async def test_failure_and_retry_stats_reflect_real_failures(repos, workspace, workflow_service, version_service):
    calls = {"n": 0}

    async def flaky(ctx):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return {}

    async def always_fails(ctx):
        raise RuntimeError("permanent boom")

    wf = await workflow_service.create_workflow(workspace.id, name="Flaky Obs WF", owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "flaky", "node_type": "custom", "name": "Flaky", "config": {"handler_key": "flaky"}, "max_retries": 2},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "flaky"},
            {"source_node_key": "flaky", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, sleep_fn=lambda s: asyncio.sleep(0), custom_handlers={"flaky": flaky, "always_fails": always_fails})
    execution = await engine.start_execution(wf.id, triggered_by="u1")
    assert execution.status == "completed"

    obs = ObservabilityService(repos)
    retry_stats = await obs.get_retry_stats(wf.id)
    assert retry_stats.get("flaky") == 1

    # a second workflow whose node always fails, to populate failure stats
    # without disturbing the first workflow's clean retry-then-succeed history
    wf2 = await workflow_service.create_workflow(workspace.id, name="Always Fails Obs WF", owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf2.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "flaky", "node_type": "custom", "name": "Flaky", "config": {"handler_key": "always_fails"}, "max_retries": 0},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "flaky"},
            {"source_node_key": "flaky", "target_node_key": "end"},
        ],
    )
    execution2 = await engine.start_execution(wf2.id, triggered_by="u1")
    assert execution2.status in ("failed", "compensated")
    failure_stats = await obs.get_failure_stats(wf2.id)
    assert failure_stats["flaky"]["failure_count"] >= 1


@pytest.mark.asyncio
async def test_token_usage_aggregates_real_llm_call_output(repos, workspace, workflow_service, version_service, scripted_ai_core):
    from tests.conftest import make_response

    ai_core, provider = scripted_ai_core
    provider.push(make_response("first"))
    provider.push(make_response("second"))

    wf = await workflow_service.create_workflow(workspace.id, name="Token WF", owner_id="u1", category="automation")
    await publish_graph(
        version_service, wf.id,
        nodes=[
            {"node_key": "start", "node_type": "start", "name": "Start"},
            {"node_key": "call_llm", "node_type": "llm_call", "name": "Call LLM", "config": {"prompt": "hi"}},
            {"node_key": "end", "node_type": "end", "name": "End"},
        ],
        edges=[
            {"source_node_key": "start", "target_node_key": "call_llm"},
            {"source_node_key": "call_llm", "target_node_key": "end"},
        ],
    )
    engine = make_engine(repos, ai_core=ai_core)
    await engine.start_execution(wf.id, triggered_by="u1")
    await engine.start_execution(wf.id, triggered_by="u1")

    obs = ObservabilityService(repos)
    usage = await obs.get_token_usage(wf.id)
    assert usage["llm_call_count"] == 2
    assert usage["total_input_tokens"] == 40  # 20 tokens per call, per make_response's default TokenUsage
    assert usage["total_output_tokens"] == 20
    assert usage["total_tokens"] == 60
