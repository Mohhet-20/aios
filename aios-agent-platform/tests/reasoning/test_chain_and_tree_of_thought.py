import json

import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.domain.enums import ReasoningMode
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService
from agent_platform.reasoning.reasoning_service import ReasoningService

from tests.conftest import make_response


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-reason", organization_id="org1"))


async def _seed_agent(repos, ws_id, type_key, name):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key(type_key)
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws_id, agent_type.id, name=name, owner_id="u1")
    return await agent_svc.activate(agent.id)


def _cot_response(final_answer: str, confidence: float, *, steps: int = 2) -> str:
    return json.dumps({
        "steps": [{"step": i + 1, "thought": f"thinking step {i + 1}", "action": None, "observation": None} for i in range(steps)],
        "final_answer": final_answer,
        "confidence": confidence,
    })


@pytest.mark.asyncio
async def test_chain_of_thought_persists_trace(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "reasoning", "Reasoner")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Solve", goal="Solve the puzzle", created_by="u1")

    provider.push(make_response(_cot_response("the answer is 7", 0.9)))

    svc = ReasoningService(repos, context)
    trace = await svc.think(agent, root, mode=ReasoningMode.CHAIN_OF_THOUGHT)

    assert trace.mode == ReasoningMode.CHAIN_OF_THOUGHT.value
    assert trace.branches_explored == 1
    assert trace.final_answer == "the answer is 7"
    assert trace.confidence == pytest.approx(0.9)
    assert len(trace.steps) == 2

    fetched = await svc.list_for_task(root.id)
    assert len(fetched) == 1
    assert fetched[0].id == trace.id


@pytest.mark.asyncio
async def test_tree_of_thought_selects_highest_confidence_branch(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "reasoning", "Reasoner")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Solve", goal="Solve the puzzle", created_by="u1")

    provider.push(make_response(_cot_response("branch A answer", 0.4)))
    provider.push(make_response(_cot_response("branch B answer", 0.95)))
    provider.push(make_response(_cot_response("branch C answer", 0.6)))

    svc = ReasoningService(repos, context)
    trace = await svc.think(agent, root, mode=ReasoningMode.TREE_OF_THOUGHT, branches=3)

    assert trace.mode == ReasoningMode.TREE_OF_THOUGHT.value
    assert trace.branches_explored == 3
    assert trace.final_answer == "branch B answer"
    assert trace.confidence == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_chain_of_thought_confidence_is_min_of_self_reported_and_attempt(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "reasoning", "Reasoner")
    planner = PlanningService(repos, context)
    root = await planner.create_root_task(ws.id, title="Solve", goal="Solve the puzzle", created_by="u1")

    # First attempt is malformed JSON -> triggers a repair round -> attempt-based confidence drops to 0.7,
    # even though the eventual valid response claims 0.99 self-reported confidence.
    provider.push(make_response("not json at all"))
    provider.push(make_response(_cot_response("the real answer", 0.99)))

    svc = ReasoningService(repos, context)
    trace = await svc.think(agent, root, mode=ReasoningMode.CHAIN_OF_THOUGHT)

    assert trace.final_answer == "the real answer"
    assert trace.confidence == pytest.approx(0.7)
