import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.analytics.analytics_service import AnalyticsService
from agent_platform.models.execution import AgentExecutionModel
from agent_platform.models.workspace import WorkspaceModel


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-analytics", organization_id="org1"))


async def _seed_agent(repos, ws_id):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name="Coder", owner_id="u1")


@pytest.mark.asyncio
async def test_cost_rollup_by_agent_computes_totals_and_percentiles(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    latencies = [10.0, 20.0, 30.0, 40.0, 100.0]
    for lat in latencies:
        await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="completed", success=True, latency_ms=lat, cost_usd=0.001, input_tokens=10, output_tokens=5))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="failed", success=False, latency_ms=200.0, cost_usd=0.0))

    svc = AnalyticsService(repos)
    rollup = await svc.cost_rollup(agent_id=agent.id)

    assert rollup["count"] == 6
    assert rollup["success_count"] == 5
    assert rollup["failure_count"] == 1
    assert rollup["total_cost_usd"] == pytest.approx(0.005)
    assert rollup["total_input_tokens"] == 50
    assert rollup["latency_p50_ms"] > 0
    assert rollup["latency_p99_ms"] >= rollup["latency_p50_ms"]


@pytest.mark.asyncio
async def test_cost_rollup_by_task(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    task_id = "task-fixed-1"

    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, task_id=task_id, status="completed", success=True, latency_ms=15.0, cost_usd=0.002))

    svc = AnalyticsService(repos)
    rollup = await svc.cost_rollup(task_id=task_id)
    assert rollup["count"] == 1
    assert rollup["total_cost_usd"] == pytest.approx(0.002)


@pytest.mark.asyncio
async def test_cost_rollup_requires_agent_or_task(repos, scripted_ai_core):
    svc = AnalyticsService(repos)
    with pytest.raises(ValueError):
        await svc.cost_rollup()
