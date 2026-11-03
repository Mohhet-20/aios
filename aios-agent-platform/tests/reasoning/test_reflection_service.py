import json

import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.execution.agent_executor import AgentExecutor
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService
from agent_platform.reflection.reflection_service import ReflectionService

from tests.conftest import make_response


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-reflect", organization_id="org1"))


async def _seed_agent(repos, ws_id, type_key, name):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key(type_key)
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws_id, agent_type.id, name=name, owner_id="u1")
    return await agent_svc.activate(agent.id)


def _critique_response(passed: bool, *, critique: str = "looks fine", correction: str | None = None, confidence: float = 0.85) -> str:
    return json.dumps({
        "critique": critique, "passed": passed, "issues": [] if passed else ["missing detail"],
        "suggested_correction": correction, "confidence": confidence,
    })


@pytest.mark.asyncio
async def test_critique_persists_reflection(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    await _seed_agent(repos, ws.id, "coding", "Worker")
    critic = await _seed_agent(repos, ws.id, "critic", "Critic")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Build", goal="Build the thing", created_by="u1")

    provider.push(make_response(_critique_response(True, critique="solid work")))

    svc = ReflectionService(repos, context)
    reflection = await svc.critique(response_content="here is my work", task=root, reflecting_agent=critic, execution_id="exec-1")

    assert reflection.passed_verification is True
    assert reflection.critique == "solid work"
    assert reflection.reflecting_agent_id == critic.id

    fetched = await svc.list_for_task(root.id)
    assert len(fetched) == 1


@pytest.mark.asyncio
async def test_verify_output_is_a_critique_alias(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    verifier = await _seed_agent(repos, ws.id, "verifier", "Verifier")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Ship", goal="Ship it", created_by="u1")

    provider.push(make_response(_critique_response(False, critique="numbers don't add up", correction="recompute the total")))

    svc = ReflectionService(repos, context)
    reflection = await svc.verify_output(response_content="total is 42", task=root, verifier_agent=verifier, execution_id="exec-2")

    assert reflection.passed_verification is False
    assert reflection.self_correction == "recompute the total"


@pytest.mark.asyncio
async def test_reflection_loop_passes_on_first_iteration(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    worker = await _seed_agent(repos, ws.id, "coding", "Worker")
    critic = await _seed_agent(repos, ws.id, "critic", "Critic")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Build", goal="Build the thing", created_by="u1")

    provider.push(make_response("my first attempt"))
    provider.push(make_response(_critique_response(True)))

    executor = AgentExecutor(repos, context)
    svc = ReflectionService(repos, context)
    outcome = await svc.run_reflection_loop(executor, worker, root, critic_agent=critic, max_iterations=3)

    assert outcome["status"] == "passed"
    assert outcome["iterations"] == 1
    assert len(outcome["reflections"]) == 1


@pytest.mark.asyncio
async def test_reflection_loop_retries_and_eventually_passes(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    worker = await _seed_agent(repos, ws.id, "coding", "Worker")
    critic = await _seed_agent(repos, ws.id, "critic", "Critic")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Build", goal="Build the thing", created_by="u1")

    provider.push(make_response("attempt one"))
    provider.push(make_response(_critique_response(False, critique="incomplete", correction="add more detail")))
    provider.push(make_response("attempt two, revised"))
    provider.push(make_response(_critique_response(True, critique="now it's complete")))

    executor = AgentExecutor(repos, context)
    svc = ReflectionService(repos, context)
    outcome = await svc.run_reflection_loop(executor, worker, root, critic_agent=critic, max_iterations=3)

    assert outcome["status"] == "passed"
    assert outcome["iterations"] == 2
    assert len(outcome["reflections"]) == 2
    assert outcome["reflections"][0].passed_verification is False
    assert outcome["reflections"][1].passed_verification is True


@pytest.mark.asyncio
async def test_reflection_loop_fails_after_max_iterations(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    worker = await _seed_agent(repos, ws.id, "coding", "Worker")
    critic = await _seed_agent(repos, ws.id, "critic", "Critic")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Build", goal="Build the thing", created_by="u1")

    for _ in range(2):
        provider.push(make_response("attempt"))
        provider.push(make_response(_critique_response(False, critique="still not right")))

    executor = AgentExecutor(repos, context)
    svc = ReflectionService(repos, context)
    outcome = await svc.run_reflection_loop(executor, worker, root, critic_agent=critic, max_iterations=2)

    assert outcome["status"] == "failed_verification"
    assert outcome["iterations"] == 2
    assert len(outcome["reflections"]) == 2
