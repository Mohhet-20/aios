import pytest

from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.domain.enums import Permission, Role
from agent_platform.models.workspace import WorkspaceModel
from agent_platform.permissions.rbac_service import RBACService


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-rbac", organization_id="org1"))


async def _seed_agent(repos, ws_id, *, owner_id="owner-1"):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("coding")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name="Coder", owner_id=owner_id)


@pytest.mark.asyncio
async def test_owner_has_implicit_owner_role(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, owner_id="owner-1")

    rbac = RBACService(repos)
    role = await rbac.effective_role_for_agent("owner-1", agent)
    assert role == Role.OWNER
    assert await rbac.has_permission("owner-1", Permission.AGENT_DELETE, agent=agent) is True


@pytest.mark.asyncio
async def test_no_grant_means_no_permission(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    rbac = RBACService(repos)
    assert await rbac.effective_role_for_agent("stranger", agent) is None
    assert await rbac.has_permission("stranger", Permission.AGENT_READ, agent=agent) is False


@pytest.mark.asyncio
async def test_agent_scoped_grant_beats_workspace_scoped_grant(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    rbac = RBACService(repos)
    await rbac.grant("u2", "workspace", ws.id, Role.VIEWER, granted_by="owner-1")
    await rbac.grant("u2", "agent", agent.id, Role.OPERATOR, granted_by="owner-1")

    role = await rbac.effective_role_for_agent("u2", agent)
    assert role == Role.OPERATOR  # the more specific agent-level grant wins
    assert await rbac.has_permission("u2", Permission.AGENT_EXECUTE, agent=agent) is True


@pytest.mark.asyncio
async def test_workspace_grant_applies_when_no_agent_specific_grant(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    rbac = RBACService(repos)
    await rbac.grant("u3", "workspace", ws.id, Role.VIEWER, granted_by="owner-1")

    role = await rbac.effective_role_for_agent("u3", agent)
    assert role == Role.VIEWER
    assert await rbac.has_permission("u3", Permission.AGENT_READ, agent=agent) is True
    assert await rbac.has_permission("u3", Permission.AGENT_DELETE, agent=agent) is False


@pytest.mark.asyncio
async def test_revoke_removes_grant(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id)

    rbac = RBACService(repos)
    grant = await rbac.grant("u4", "workspace", ws.id, Role.OPERATOR, granted_by="owner-1")
    assert await rbac.effective_role_for_agent("u4", agent) == Role.OPERATOR

    await rbac.revoke(grant.id)
    assert await rbac.effective_role_for_agent("u4", agent) is None
