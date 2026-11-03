import pytest

from ai_core.schemas.tools import ToolCall, ToolDefinition

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.domain.enums import ToolPermissionLevel
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.tool_bridge.tool_bridge_service import ToolBridgeService


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-tool", organization_id="org1"))


async def _seed_agent(repos, ws_id, type_key, name):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key(type_key)
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws_id, agent_type.id, name=name, owner_id="u1")
    return await agent_svc.activate(agent.id)


async def _adder(**kwargs):
    return kwargs["a"] + kwargs["b"]


def _register_calculator(context):
    definition = ToolDefinition(
        name="calculator", description="adds two numbers",
        parameters={"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
    )
    context.tool_registry.register(definition, _adder)
    return definition


@pytest.mark.asyncio
async def test_available_tools_filters_by_permission(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    _register_calculator(context)
    context.tool_registry.register(
        ToolDefinition(name="not_granted", description="unused"), _adder,
    )

    agent_svc = AgentService(repos)
    await agent_svc.grant_tool_permission(agent.id, "calculator", ToolPermissionLevel.EXECUTE, granted_by="u1")

    bridge = ToolBridgeService(repos, context)
    tools = await bridge.available_tools(agent.id)
    names = {t.name for t in tools}
    assert names == {"calculator"}


@pytest.mark.asyncio
async def test_invoke_denied_without_permission(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    _register_calculator(context)

    bridge = ToolBridgeService(repos, context)
    result = await bridge.invoke(agent.id, ToolCall(id="tc1", name="calculator", arguments={"a": 2, "b": 3}))

    assert result.is_error is True
    assert "permission" in result.error


@pytest.mark.asyncio
async def test_invoke_succeeds_with_permission(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    _register_calculator(context)

    agent_svc = AgentService(repos)
    await agent_svc.grant_tool_permission(agent.id, "calculator", ToolPermissionLevel.EXECUTE, granted_by="u1")

    bridge = ToolBridgeService(repos, context)
    result = await bridge.invoke(agent.id, ToolCall(id="tc1", name="calculator", arguments={"a": 2, "b": 3}))

    assert result.is_error is False
    assert result.content == 5


@pytest.mark.asyncio
async def test_invoke_many_is_sequential_and_preserves_order(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")
    _register_calculator(context)
    agent_svc = AgentService(repos)
    await agent_svc.grant_tool_permission(agent.id, "calculator", ToolPermissionLevel.EXECUTE, granted_by="u1")

    bridge = ToolBridgeService(repos, context)
    calls = [ToolCall(id="tc1", name="calculator", arguments={"a": 1, "b": 1}), ToolCall(id="tc2", name="calculator", arguments={"a": 5, "b": 5})]
    results = await bridge.invoke_many(agent.id, calls)

    assert [r.content for r in results] == [2, 10]


@pytest.mark.asyncio
async def test_register_mcp_tool_bridges_input_schema(repos, scripted_ai_core):
    context, _ = scripted_ai_core
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, "coding", "Coder")

    bridge = ToolBridgeService(repos, context)
    mcp_spec = {"name": "mcp_tool", "description": "an MCP-sourced tool", "inputSchema": {"type": "object", "properties": {}, "required": []}}
    definition = bridge.register_mcp_tool(mcp_spec, _adder)
    assert definition.name == "mcp_tool"
    assert "mcp_tool" in context.tool_registry

    agent_svc = AgentService(repos)
    await agent_svc.grant_tool_permission(agent.id, "mcp_tool", ToolPermissionLevel.EXECUTE, granted_by="u1")
    tools = await bridge.available_tools(agent.id)
    assert any(t.name == "mcp_tool" for t in tools)
