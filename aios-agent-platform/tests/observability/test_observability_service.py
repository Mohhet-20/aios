import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.communication.communication_service import CommunicationService
from agent_platform.domain.enums import DelegationStatus, ReasoningMode
from agent_platform.models.delegation import DelegationModel
from agent_platform.models.execution import AgentExecutionModel
from agent_platform.models.reasoning import ReasoningTraceModel, ReflectionModel
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.monitoring.observability_service import ObservabilityService
from agent_platform.planner.planning_service import PlanningService


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-obs", organization_id="org1"))


async def _seed_agent(repos, ws_id, name="Agent"):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name=name, owner_id="u1")


@pytest.mark.asyncio
async def test_execution_timeline_merges_all_event_types_sorted(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do it", created_by="u1")

    execution = await repos.executions.add(AgentExecutionModel(
        agent_id=agent.id, task_id=task.id, status="completed", success=True, latency_ms=100.0, cost_usd=0.001,
    ))
    await repos.reasoning_traces.add(ReasoningTraceModel(
        execution_id=execution.id, task_id=task.id, agent_id=agent.id, mode=ReasoningMode.CHAIN_OF_THOUGHT.value, confidence=0.8,
    ))
    await repos.reflections.add(ReflectionModel(
        execution_id=execution.id, task_id=task.id, reflecting_agent_id=agent.id, critique="fine", passed_verification=True,
    ))
    comms = CommunicationService(repos)
    await comms.send_status_update(task.id, agent.id, "started working")

    svc = ObservabilityService(repos)
    timeline = await svc.execution_timeline(task.id)

    types = {ev["type"] for ev in timeline}
    assert types == {"execution", "message", "reasoning", "reflection"}
    assert len(timeline) == 4
    timestamps = [ev["timestamp"] for ev in timeline]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_delegation_chain_returns_ordered_delegations(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    coordinator = await _seed_agent(repos, ws.id, "Coordinator")
    worker = await _seed_agent(repos, ws.id, "Worker")
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do it", created_by="u1")

    await repos.delegations.add(DelegationModel(
        task_id=task.id, from_agent_id=coordinator.id, to_agent_id=worker.id, status=DelegationStatus.ACCEPTED.value,
    ))

    svc = ObservabilityService(repos)
    chain = await svc.delegation_chain(task.id)
    assert len(chain) == 1
    assert chain[0]["from_agent_id"] == coordinator.id
    assert chain[0]["to_agent_id"] == worker.id


@pytest.mark.asyncio
async def test_agent_health_summary_aggregates_executions(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="completed", success=True, latency_ms=100.0, cost_usd=0.01, input_tokens=10, output_tokens=5))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="failed", success=False, latency_ms=50.0, cost_usd=0.0))

    svc = ObservabilityService(repos)
    summary = await svc.agent_health_summary(agent.id)

    assert summary["execution_count"] == 2
    assert summary["success_rate"] == 50.0
    assert summary["total_cost_usd"] == pytest.approx(0.01)
    assert summary["total_tokens"] == 15
    assert summary["avg_latency_ms"] == pytest.approx(75.0)
