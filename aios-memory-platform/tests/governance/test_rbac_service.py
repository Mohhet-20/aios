import pytest

from memory_platform.core.exceptions import AuthorizationError
from memory_platform.domain.enums import Permission, Role
from memory_platform.governance.rbac_service import RBACService
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_no_grant_means_no_role(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    role = await rbac.resolve_role(principal_id="user-1", workspace_id="ws-1")
    assert role is None


@pytest.mark.asyncio
async def test_workspace_level_grant_resolves(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.OPERATOR, granted_by="admin-1")
    role = await rbac.resolve_role(principal_id="user-1", workspace_id="ws-1")
    assert role == Role.OPERATOR


@pytest.mark.asyncio
async def test_resource_specific_grant_takes_precedence_over_workspace(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.VIEWER, granted_by="admin-1")
    await rbac.grant_role(principal_id="user-1", resource_type="knowledge_base", resource_id="kb-1", role=Role.ADMIN, granted_by="admin-1")
    role = await rbac.resolve_role(principal_id="user-1", workspace_id="ws-1", resource_type="knowledge_base", resource_id="kb-1")
    assert role == Role.ADMIN


@pytest.mark.asyncio
async def test_implicit_owner_role(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    role = await rbac.resolve_role(principal_id="user-1", workspace_id="ws-1", resource_type="knowledge_base", resource_id="kb-1", owner_id="user-1")
    assert role == Role.OWNER


@pytest.mark.asyncio
async def test_has_permission_respects_role_permission_set(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.VIEWER, granted_by="admin-1")
    assert await rbac.has_permission(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_READ) is True
    assert await rbac.has_permission(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_DELETE) is False


@pytest.mark.asyncio
async def test_require_permission_raises_when_missing(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.VIEWER, granted_by="admin-1")
    with pytest.raises(AuthorizationError):
        await rbac.require_permission(principal_id="user-1", workspace_id="ws-1", permission=Permission.WORKSPACE_MANAGE)


@pytest.mark.asyncio
async def test_revoke_role_removes_grant(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    grant = await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.ADMIN, granted_by="admin-1")
    await rbac.revoke_role(grant.id)
    role = await rbac.resolve_role(principal_id="user-1", workspace_id="ws-1")
    assert role is None


@pytest.mark.asyncio
async def test_highest_role_wins_with_multiple_grants(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.VIEWER, granted_by="admin-1")
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.ADMIN, granted_by="admin-1")
    role = await rbac.resolve_role(principal_id="user-1", workspace_id="ws-1")
    assert role == Role.ADMIN
