import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.core.exceptions import InvalidTransitionError, ValidationError
from agent_platform.domain.enums import AgentHealthStatus, AgentLifecycleStatus, ToolPermissionLevel
from agent_platform.models.workspace import WorkspaceModel


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-reg", organization_id="org1"))


@pytest.mark.asyncio
async def test_seed_builtin_types_creates_seventeen_and_is_idempotent(repos):
    svc = AgentTypeService(repos)
    created = await svc.seed_builtin_types()
    assert len(created) == 17
    keys = {t.key for t in created}
    assert {"planner", "research", "critic", "verifier", "coordinator", "human_approval", "system"} <= keys

    again = await svc.seed_builtin_types()
    assert len(again) == 17
    all_types = await svc.list_types()
    assert len(all_types) == 17  # no duplicates from the second seed call


@pytest.mark.asyncio
async def test_create_custom_type_and_duplicate_key_rejected(repos):
    svc = AgentTypeService(repos)
    custom = await svc.create_type(key="translator", name="Translator Agent", default_instructions="Translate text accurately.")
    assert custom.is_builtin is False
    with pytest.raises(ValidationError):
        await svc.create_type(key="translator", name="Dup", default_instructions="x")


@pytest.mark.asyncio
async def test_create_agent_inherits_type_defaults(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    planner_type = await type_svc.get_by_key("planner")

    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws.id, planner_type.id, name="Planner One", owner_id="u1")
    assert agent.role == planner_type.name
    assert agent.instructions == planner_type.default_instructions
    assert agent.capabilities == planner_type.default_capabilities
    assert agent.status == AgentLifecycleStatus.DRAFT.value


@pytest.mark.asyncio
async def test_create_agent_overrides_type_defaults(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    planner_type = await type_svc.get_by_key("planner")

    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(
        ws.id, planner_type.id, name="Planner Two", owner_id="u1", role="Chief Planner", instructions="Custom instructions.",
    )
    assert agent.role == "Chief Planner"
    assert agent.instructions == "Custom instructions."


@pytest.mark.asyncio
async def test_create_agent_grants_default_tool_permissions(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    research_type = await type_svc.get_by_key("research")

    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws.id, research_type.id, name="Researcher", owner_id="u1")
    grants = await agent_svc.list_tool_permissions(agent.id)
    tool_names = {g.tool_name for g in grants}
    assert tool_names == set(research_type.default_tool_names)


@pytest.mark.asyncio
async def test_duplicate_slug_in_same_workspace_rejected(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    t = await type_svc.get_by_key("system")
    agent_svc = AgentService(repos)
    await agent_svc.create_agent(ws.id, t.id, name="Sys Agent", owner_id="u1", slug="sysagent")
    with pytest.raises(ValidationError):
        await agent_svc.create_agent(ws.id, t.id, name="Sys Agent Two", owner_id="u1", slug="sysagent")


@pytest.mark.asyncio
async def test_agent_lifecycle_transitions_through_service(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    t = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws.id, t.id, name="Coder", owner_id="u1")

    activated = await agent_svc.activate(agent.id)
    assert activated.status == AgentLifecycleStatus.ACTIVE.value
    paused = await agent_svc.pause(agent.id)
    assert paused.status == AgentLifecycleStatus.PAUSED.value
    resumed = await agent_svc.resume(agent.id)
    assert resumed.status == AgentLifecycleStatus.ACTIVE.value
    deprecated = await agent_svc.deprecate(agent.id)
    assert deprecated.status == AgentLifecycleStatus.DEPRECATED.value
    archived = await agent_svc.archive(agent.id)
    assert archived.status == AgentLifecycleStatus.ARCHIVED.value

    with pytest.raises(InvalidTransitionError):
        await agent_svc.activate(agent.id)


@pytest.mark.asyncio
async def test_update_health(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    t = await type_svc.get_by_key("system")
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws.id, t.id, name="Sys", owner_id="u1")

    updated = await agent_svc.update_health(agent.id, AgentHealthStatus.DEGRADED)
    assert updated.health_status == AgentHealthStatus.DEGRADED.value


@pytest.mark.asyncio
async def test_tool_permission_grant_revoke_and_level_check(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    t = await type_svc.get_by_key("system")  # no default tools
    agent_svc = AgentService(repos)
    agent = await agent_svc.create_agent(ws.id, t.id, name="Sys2", owner_id="u1")

    assert await agent_svc.has_tool_permission(agent.id, "python_execution") is False

    await agent_svc.grant_tool_permission(agent.id, "python_execution", ToolPermissionLevel.READ_ONLY, granted_by="u1")
    assert await agent_svc.has_tool_permission(agent.id, "python_execution", minimum=ToolPermissionLevel.EXECUTE) is False
    assert await agent_svc.has_tool_permission(agent.id, "python_execution", minimum=ToolPermissionLevel.READ_ONLY) is True

    await agent_svc.grant_tool_permission(agent.id, "python_execution", ToolPermissionLevel.FULL, granted_by="u1")
    assert await agent_svc.has_tool_permission(agent.id, "python_execution", minimum=ToolPermissionLevel.EXECUTE) is True

    await agent_svc.revoke_tool_permission(agent.id, "python_execution")
    assert await agent_svc.has_tool_permission(agent.id, "python_execution") is False


@pytest.mark.asyncio
async def test_list_and_search_agents(repos):
    ws = await _seed_workspace(repos)
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    t = await type_svc.get_by_key("planner")
    agent_svc = AgentService(repos)
    await agent_svc.create_agent(ws.id, t.id, name="Alpha Planner", owner_id="u1")
    await agent_svc.create_agent(ws.id, t.id, name="Beta Planner", owner_id="u1")

    page = await agent_svc.list_agents(ws.id)
    assert page.total == 2

    results = await agent_svc.search_agents(ws.id, "alpha")
    assert len(results) == 1
    assert results[0].name == "Alpha Planner"
