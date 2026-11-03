import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.communication.communication_service import CommunicationService
from agent_platform.domain.enums import ReasoningMode, TaskStatus
from agent_platform.evaluation.evaluation_service import EvaluationService
from agent_platform.models.execution import AgentExecutionModel
from agent_platform.models.reasoning import ReasoningTraceModel
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService

from tests.conftest import make_response
import json


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-eval", organization_id="org1"))


async def _seed_agent(repos, ws_id, name="Agent"):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name=name, owner_id="u1")


def _decomposition_response(subtasks):
    return json.dumps({"rationale": "test", "subtasks": subtasks})


@pytest.mark.asyncio
async def test_task_success_rate(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await planner.decompose(root.id)
    a.status = TaskStatus.COMPLETED.value
    await repos.tasks.update(a)
    b.status = TaskStatus.FAILED.value
    await repos.tasks.update(b)

    svc = EvaluationService(repos)
    result = await svc.task_success_rate(root.id)
    assert result["total"] == 2
    assert result["completed"] == 1
    assert result["failed"] == 1
    assert result["success_rate"] == 50.0


@pytest.mark.asyncio
async def test_planning_quality_penalizes_cancellations(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "C", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "D", "goal": "g", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b, c, d = await planner.decompose(root.id)
    b.status = TaskStatus.CANCELLED.value
    await repos.tasks.update(b)

    svc = EvaluationService(repos)
    result = await svc.planning_quality(root.id)
    assert result["subtask_count"] == 4
    assert result["cancelled_ratio"] == 0.25
    assert result["quality_score"] == 0.75


@pytest.mark.asyncio
async def test_reasoning_quality_proxy_averages_confidence(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do it", created_by="u1")

    await repos.reasoning_traces.add(ReasoningTraceModel(task_id=task.id, agent_id=agent.id, mode=ReasoningMode.CHAIN_OF_THOUGHT.value, confidence=0.6))
    await repos.reasoning_traces.add(ReasoningTraceModel(task_id=task.id, agent_id=agent.id, mode=ReasoningMode.CHAIN_OF_THOUGHT.value, confidence=1.0))

    svc = EvaluationService(repos)
    result = await svc.reasoning_quality_proxy(task.id)
    assert result["trace_count"] == 2
    assert result["avg_confidence"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_tool_effectiveness(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="completed", success=True, tool_calls_count=2))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="failed", success=False, tool_calls_count=1))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="completed", success=True, tool_calls_count=0))  # no tools used

    svc = EvaluationService(repos)
    result = await svc.tool_effectiveness(agent.id)
    assert result["executions_using_tools"] == 2
    assert result["tool_success_rate"] == 50.0


@pytest.mark.asyncio
async def test_reliability_tracks_retries(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="completed", success=True, retry_count=0))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="completed", success=True, retry_count=2))

    svc = EvaluationService(repos)
    result = await svc.reliability(agent.id)
    assert result["execution_count"] == 2
    assert result["success_rate"] == 100.0
    assert result["avg_retries"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_collaboration_quality_counts_participants(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent_a = await _seed_agent(repos, ws.id, "A")
    agent_b = await _seed_agent(repos, ws.id, "B")
    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Task", goal="Do it", created_by="u1")

    comms = CommunicationService(repos)
    await comms.send_direct(task.id, agent_a.id, agent_b.id, "hello")
    await comms.send_direct(task.id, agent_b.id, agent_a.id, "hi back")

    svc = EvaluationService(repos)
    result = await svc.collaboration_quality(task.id)
    assert result["message_count"] == 2
    assert result["distinct_agents"] == 2


@pytest.mark.asyncio
async def test_failure_recovery_rate(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    # task-1: failed then recovered
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, task_id="task-1", status="failed", success=False))
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, task_id="task-1", status="completed", success=True))
    # task-2: failed, never recovered
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, task_id="task-2", status="failed", success=False))
    # task-3: succeeded cleanly, no failure at all
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, task_id="task-3", status="completed", success=True))

    svc = EvaluationService(repos)
    result = await svc.failure_recovery_rate(agent.id)
    assert result["tasks_with_failure"] == 2
    assert result["recovered"] == 1
    assert result["failure_recovery_rate"] == 50.0
