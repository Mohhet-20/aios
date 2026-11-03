import pytest

from ai_core.schemas.responses import GenerationResponse
from ai_core.schemas.tools import ToolCall, ToolDefinition

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.domain.enums import ToolPermissionLevel
from agent_platform.execution.agent_executor import AgentExecutor
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.planner.planning_service import PlanningService
from agent_platform.tool_bridge.tool_bridge_service import ToolBridgeService

from tests.conftest import make_response


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-toolexec", organization_id="org1"))


async def _seed_agent(repos, ws_id, *, resource_limits: dict | None = None):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws_id, agent_type.id, name="Coder", owner_id="u1", resource_limits=resource_limits)
    return await agent_svc.activate(agent.id)


async def _adder(**kwargs):
    return kwargs["a"] + kwargs["b"]


def _register_calculator(context):
    definition = ToolDefinition(
        name="calculator", description="adds two numbers",
        parameters={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
    )
    context.tool_registry.register(definition, _adder)


def _response_with_tool_call() -> GenerationResponse:
    base = make_response(content="")
    return base.model_copy(update={"tool_calls": [ToolCall(id="tc1", name="calculator", arguments={"a": 2, "b": 3})]})


@pytest.mark.asyncio
async def test_run_executes_tool_call_and_returns_final_response(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    _register_calculator(context)
    agent_svc = AgentService(repos)
    await agent_svc.grant_tool_permission(agent.id, "calculator", ToolPermissionLevel.EXECUTE, granted_by="u1")

    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Compute", goal="Add 2 and 3", created_by="u1")

    provider.push(_response_with_tool_call())
    provider.push(make_response("the answer is 5"))

    bridge = ToolBridgeService(repos, context)
    executor = AgentExecutor(repos, context, tool_bridge=bridge)
    outcome = await executor.run(agent, task)

    assert outcome.success is True
    assert outcome.response.content == "the answer is 5"
    assert outcome.execution.tool_calls_count == 1


@pytest.mark.asyncio
async def test_run_without_tool_bridge_ignores_tool_calls(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    _register_calculator(context)

    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Compute", goal="Add 2 and 3", created_by="u1")

    provider.push(_response_with_tool_call())

    executor = AgentExecutor(repos, context)  # no tool_bridge configured
    outcome = await executor.run(agent, task)

    assert outcome.success is True
    assert outcome.execution.tool_calls_count == 0
    assert len(outcome.response.tool_calls) == 1  # unresolved — caller chose not to wire a bridge


@pytest.mark.asyncio
async def test_run_stops_tool_looping_at_max_tool_rounds(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, resource_limits={"max_tool_rounds": 0})
    _register_calculator(context)
    agent_svc = AgentService(repos)
    await agent_svc.grant_tool_permission(agent.id, "calculator", ToolPermissionLevel.EXECUTE, granted_by="u1")

    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Compute", goal="Add 2 and 3", created_by="u1")

    provider.push(_response_with_tool_call())

    bridge = ToolBridgeService(repos, context)
    executor = AgentExecutor(repos, context, tool_bridge=bridge)
    outcome = await executor.run(agent, task)

    assert outcome.success is True
    assert outcome.execution.tool_calls_count == 0  # never got a round of capacity to execute it
    assert len(outcome.response.tool_calls) == 1  # returned as-is, unresolved


@pytest.mark.asyncio
async def test_run_reports_denied_tool_call_but_still_completes(repos, scripted_ai_core):
    context, provider = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)
    _register_calculator(context)
    # deliberately no permission grant

    planner = PlanningService(repos, context)
    task = await planner.create_root_task(ws.id, title="Compute", goal="Add 2 and 3", created_by="u1")

    provider.push(_response_with_tool_call())
    provider.push(make_response("I couldn't use the calculator, so here's my estimate: 5"))

    bridge = ToolBridgeService(repos, context)
    executor = AgentExecutor(repos, context, tool_bridge=bridge)
    outcome = await executor.run(agent, task)

    assert outcome.success is True
    assert outcome.response.content == "I couldn't use the calculator, so here's my estimate: 5"
    assert outcome.execution.tool_calls_count == 1
