import json

import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.communication.communication_service import CommunicationService
from agent_platform.core.exceptions import ExecutionCancelledError, OrchestrationError
from agent_platform.coordination.orchestrator import TaskOrchestrator
from agent_platform.domain.enums import DelegationStatus, TaskStatus
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService

from tests.conftest import make_response


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-orch", organization_id="org1"))


async def _seed_agent(repos, ws_id, type_key, name, *, activate=True):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key(type_key)
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws_id, agent_type.id, name=name, owner_id="u1")
    if activate:
        agent = await agent_svc.activate(agent.id)
    return agent


def _decomposition_response(subtasks: list[dict]) -> str:
    return json.dumps({"rationale": "test", "subtasks": subtasks})


def _orchestrator(repos, context) -> TaskOrchestrator:
    comms = CommunicationService(repos)
    return TaskOrchestrator(repos, context, communication=comms)


@pytest.mark.asyncio
async def test_execute_sequential_runs_in_dependency_order(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Ship", goal="Ship feature", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "do A", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "do B", "priority": "normal", "depends_on": [0], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await planner.decompose(root.id)
    for task in (a, b):
        task.assigned_agent_id = agent.id
        await repos.tasks.update(task)

    provider.push(make_response("A done"))
    provider.push(make_response("B done"))

    orchestrator = _orchestrator(repos, context)
    results = await orchestrator.execute_sequential(root.id, [agent])

    assert results[a.id]["status"] == "completed"
    assert results[b.id]["status"] == "completed"
    refreshed_a = await repos.tasks.get_or_404(a.id)
    refreshed_b = await repos.tasks.get_or_404(b.id)
    assert refreshed_a.status == TaskStatus.COMPLETED.value
    assert refreshed_b.status == TaskStatus.COMPLETED.value
    assert refreshed_a.result["content"] == "A done"


@pytest.mark.asyncio
async def test_execute_sequential_blocks_downstream_on_failure(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Ship", goal="Ship feature", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "do A", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "do B", "priority": "normal", "depends_on": [0], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await planner.decompose(root.id)
    for task in (a, b):
        task.assigned_agent_id = agent.id
        await repos.tasks.update(task)

    provider.push(RuntimeError("boom"))
    provider.push(RuntimeError("boom"))
    provider.push(RuntimeError("boom"))

    orchestrator = _orchestrator(repos, context)
    results = await orchestrator.execute_sequential(root.id, [agent], stop_on_failure=False)

    assert results[a.id]["status"] == "failed"
    assert results[b.id]["status"] == "blocked"
    refreshed_b = await repos.tasks.get_or_404(b.id)
    assert refreshed_b.status == TaskStatus.BLOCKED.value


@pytest.mark.asyncio
async def test_execute_parallel_runs_independent_tasks_concurrently(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "research", "Researcher")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Research", goal="Research topic", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "do A", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "do B", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await planner.decompose(root.id)
    for task in (a, b):
        task.assigned_agent_id = agent.id
        await repos.tasks.update(task)

    provider.push(make_response("A done"))
    provider.push(make_response("B done"))

    orchestrator = _orchestrator(repos, context)
    results = await orchestrator.execute_parallel(root.id, [agent])

    assert results[a.id]["status"] == "completed"
    assert results[b.id]["status"] == "completed"


@pytest.mark.asyncio
async def test_delegate_reassigns_task_and_records_handoff(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    from_agent = await _seed_agent(repos, ws.id, "coordinator", "Coordinator")
    to_agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Do work", created_by="u1")

    orchestrator = _orchestrator(repos, context)
    delegation = await orchestrator.delegate(root.id, from_agent.id, to_agent.id, reason="best fit")

    assert delegation.status == DelegationStatus.ACCEPTED.value
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.assigned_agent_id == to_agent.id

    conversation = await orchestrator.communication.get_conversation(root.id)
    assert any(m.message_type == "handoff" for m in conversation)


@pytest.mark.asyncio
async def test_execute_hierarchical_delegates_each_task(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    coordinator = await _seed_agent(repos, ws.id, "coordinator", "Coordinator")
    worker = await _seed_agent(repos, ws.id, "coding", "Worker")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "do A", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    (a,) = await planner.decompose(root.id)
    provider.push(make_response("A done"))

    orchestrator = _orchestrator(repos, context)
    results = await orchestrator.execute_hierarchical(root.id, coordinator, [worker])

    assert results[a.id]["status"] == "completed"
    assert results[a.id]["delegated_to"] == worker.id
    delegations = await repos.delegations.list_for_task(a.id)
    assert len(delegations) == 1
    assert delegations[0].from_agent_id == coordinator.id


@pytest.mark.asyncio
async def test_execute_consensus_completes_on_majority_agreement(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent_a = await _seed_agent(repos, ws.id, "reasoning", "Reasoner A")
    agent_b = await _seed_agent(repos, ws.id, "reasoning", "Reasoner B")
    agent_c = await _seed_agent(repos, ws.id, "reasoning", "Reasoner C")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Answer", goal="What is the answer?", created_by="u1")

    provider.push(make_response("42"))
    provider.push(make_response("42"))
    provider.push(make_response("a different answer"))

    orchestrator = _orchestrator(repos, context)
    outcome = await orchestrator.execute_consensus(root.id, [agent_a, agent_b, agent_c])

    assert outcome["status"] == "completed"
    assert outcome["successful"] == 3
    assert outcome["agreement_ratio"] == pytest.approx(2 / 3)
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.COMPLETED.value
    assert refreshed_root.result["content"] == "42"


@pytest.mark.asyncio
async def test_execute_consensus_blocks_when_agreement_too_low(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent_a = await _seed_agent(repos, ws.id, "reasoning", "Reasoner A")
    agent_b = await _seed_agent(repos, ws.id, "reasoning", "Reasoner B")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Answer", goal="What is the answer?", created_by="u1")

    provider.push(make_response("answer one"))
    provider.push(make_response("answer two"))

    orchestrator = _orchestrator(repos, context)
    outcome = await orchestrator.execute_consensus(root.id, [agent_a, agent_b], min_agreement=0.75)

    assert outcome["status"] == "blocked"
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.BLOCKED.value


@pytest.mark.asyncio
async def test_execute_supervisor_loops_until_complete(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    supervisor = await _seed_agent(repos, ws.id, "coordinator", "Supervisor")
    worker = await _seed_agent(repos, ws.id, "coding", "Worker")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    # Round 1: supervisor decides worker should act.
    provider.push(make_response(json.dumps({
        "is_complete": False, "next_agent_id": worker.id, "instruction": "do the thing", "final_result": None,
    })))
    provider.push(make_response("worked on it"))
    # Round 2: supervisor decides the goal is complete.
    provider.push(make_response(json.dumps({
        "is_complete": True, "next_agent_id": None, "instruction": "", "final_result": "all done",
    })))

    orchestrator = _orchestrator(repos, context)
    outcome = await orchestrator.execute_supervisor(root.id, supervisor, [worker])

    assert outcome["status"] == "completed"
    assert outcome["rounds"] == 2
    assert outcome["result"] == "all done"
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_execute_collaborative_refines_shared_draft(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent_a = await _seed_agent(repos, ws.id, "documentation", "Writer A")
    agent_b = await _seed_agent(repos, ws.id, "documentation", "Writer B")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Draft", goal="Write a doc", created_by="u1")

    provider.push(make_response("draft v1"))
    provider.push(make_response("draft v2"))

    orchestrator = _orchestrator(repos, context)
    outcome = await orchestrator.execute_collaborative(root.id, [agent_a, agent_b], rounds=1)

    assert outcome["status"] == "completed"
    assert outcome["content"] == "draft v2"
    shared = await orchestrator.communication.get_shared_value(root.id, "draft")
    assert shared["content"] == "draft v2"
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_cancel_stops_sequential_execution(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    provider.push(make_response(_decomposition_response([
        {"title": "A", "goal": "do A", "priority": "normal", "depends_on": [], "estimated_tokens": 1, "estimated_duration_seconds": 1},
        {"title": "B", "goal": "do B", "priority": "normal", "depends_on": [0], "estimated_tokens": 1, "estimated_duration_seconds": 1},
    ])))
    a, b = await planner.decompose(root.id)
    for task in (a, b):
        task.assigned_agent_id = agent.id
        await repos.tasks.update(task)
    provider.push(make_response("A done"))

    orchestrator = _orchestrator(repos, context)
    await orchestrator.cancel(root.id, reason="user stopped it")

    with pytest.raises(ExecutionCancelledError):
        await orchestrator.execute_sequential(root.id, [agent])


@pytest.mark.asyncio
async def test_checkpoint_and_recover_resumes_failed_task(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    orchestrator = _orchestrator(repos, context)
    await orchestrator.checkpoint(root.id, "before_attempt", {"step": 1}, agent_id=agent.id)

    root.status = TaskStatus.PLANNING.value
    await repos.tasks.update(root)
    root_entity_status = TaskStatus.FAILED.value
    root.status = root_entity_status
    root.failure_reason = "provider outage"
    await repos.tasks.update(root)

    recovery = await orchestrator.recover(root.id)
    assert recovery["status"] == TaskStatus.IN_PROGRESS.value
    assert recovery["resumed_from_checkpoint"] == "before_attempt"
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.IN_PROGRESS.value


@pytest.mark.asyncio
async def test_route_task_prefers_least_loaded_active_agent(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent_a = await _seed_agent(repos, ws.id, "research", "A")
    agent_b = await _seed_agent(repos, ws.id, "research", "B")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    orchestrator = _orchestrator(repos, context)
    chosen = await orchestrator.route_task(root, [agent_a, agent_b])
    assert chosen.id in (agent_a.id, agent_b.id)


@pytest.mark.asyncio
async def test_resolve_agent_raises_without_assignment_or_candidates(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")

    orchestrator = _orchestrator(repos, context)
    with pytest.raises(OrchestrationError):
        await orchestrator._resolve_agent(root)


@pytest.mark.asyncio
async def test_execute_sequential_routes_non_autonomous_agent_to_approval(repos, scripted_ai_core):
    from agent_platform.config.settings import get_settings
    from agent_platform.policies.policy_engine import PolicyEngine

    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder", activate=False)
    agent.is_autonomous = False
    await repos.agents.update(agent)
    from agent_platform.agent_registry.agent_service import AgentService
    agent = await AgentService(repos).activate(agent.id)

    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    root.assigned_agent_id = agent.id
    await repos.tasks.update(root)

    comms = CommunicationService(repos)
    orchestrator = TaskOrchestrator(repos, context, communication=comms, policy_engine=PolicyEngine(repos, get_settings()))
    results = await orchestrator.execute_sequential(root.id, [agent])

    assert results[root.id]["status"] == "failed"
    assert results[root.id]["error"] == "approval_required"
    refreshed_root = await repos.tasks.get_or_404(root.id)
    assert refreshed_root.status == TaskStatus.WAITING_APPROVAL.value

    gates = await repos.approval_gates.list_for_task(root.id)
    assert len(gates) == 1


@pytest.mark.asyncio
async def test_execute_sequential_raises_on_resource_quota_exceeded(repos, scripted_ai_core):
    from agent_platform.config.settings import get_settings
    from agent_platform.core.exceptions import ResourceQuotaExceededError
    from agent_platform.models.execution import AgentExecutionModel
    from agent_platform.policies.policy_engine import PolicyEngine

    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    agent.resource_limits = {"max_concurrent_tasks": 1}
    await repos.agents.update(agent)
    await repos.executions.add(AgentExecutionModel(agent_id=agent.id, status="running"))

    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Root", goal="Root goal", created_by="u1")
    root.assigned_agent_id = agent.id
    await repos.tasks.update(root)

    comms = CommunicationService(repos)
    orchestrator = TaskOrchestrator(repos, context, communication=comms, policy_engine=PolicyEngine(repos, get_settings()))

    with pytest.raises(ResourceQuotaExceededError):
        await orchestrator.execute_sequential(root.id, [agent])
