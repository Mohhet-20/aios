import pytest

from workflow_platform.core.exceptions import AuthorizationError
from workflow_platform.domain.enums import Permission, Role
from workflow_platform.models.workspace import WorkspaceModel
from workflow_platform.security.rbac_service import RBACService


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="RBAC Co", organization_id="org-1", slug="rbac-co"))


@pytest.mark.asyncio
async def test_grant_and_check_workspace_level_permission(repos, workspace):
    rbac = RBACService(repos)
    await rbac.grant("user-1", "workspace", workspace.id, Role.OPERATOR, granted_by="admin")

    assert await rbac.has_permission("user-1", Permission.WORKFLOW_EXECUTE, workspace_id=workspace.id) is True
    assert await rbac.has_permission("user-1", Permission.WORKSPACE_MANAGE, workspace_id=workspace.id) is False


@pytest.mark.asyncio
async def test_no_grant_means_no_permissions(repos, workspace):
    rbac = RBACService(repos)
    assert await rbac.has_permission("stranger", Permission.WORKFLOW_READ, workspace_id=workspace.id) is False


@pytest.mark.asyncio
async def test_require_permission_raises_when_missing(repos, workspace):
    rbac = RBACService(repos)
    with pytest.raises(AuthorizationError):
        await rbac.require_permission("stranger", Permission.WORKFLOW_EXECUTE, workspace_id=workspace.id)


@pytest.mark.asyncio
async def test_workflow_level_grant_overrides_workspace_level(repos, workspace):
    rbac = RBACService(repos)
    await rbac.grant("user-1", "workspace", workspace.id, Role.VIEWER, granted_by="admin")
    await rbac.grant("user-1", "workflow", "wf-special", Role.ADMIN, granted_by="admin")

    # workspace-wide, this user is only a VIEWER
    assert await rbac.has_permission("user-1", Permission.WORKFLOW_WRITE, workspace_id=workspace.id) is False
    # but on this one specific workflow, they're an ADMIN
    assert await rbac.has_permission("user-1", Permission.WORKFLOW_WRITE, workspace_id=workspace.id, workflow_id="wf-special") is True
    assert await rbac.has_permission("user-1", Permission.WORKFLOW_DELETE, workspace_id=workspace.id, workflow_id="wf-special") is True


@pytest.mark.asyncio
async def test_owner_role_has_every_permission(repos, workspace):
    rbac = RBACService(repos)
    await rbac.grant("owner-1", "workspace", workspace.id, Role.OWNER, granted_by="system")
    for permission in Permission:
        assert await rbac.has_permission("owner-1", permission, workspace_id=workspace.id) is True


@pytest.mark.asyncio
async def test_revoke_removes_access(repos, workspace):
    rbac = RBACService(repos)
    grant = await rbac.grant("user-1", "workspace", workspace.id, Role.ADMIN, granted_by="admin")
    assert await rbac.has_permission("user-1", Permission.WORKFLOW_WRITE, workspace_id=workspace.id) is True

    await rbac.revoke(grant.id, revoked_by="admin")
    assert await rbac.has_permission("user-1", Permission.WORKFLOW_WRITE, workspace_id=workspace.id) is False


@pytest.mark.asyncio
async def test_grant_and_revoke_are_audited(repos, workspace):
    rbac = RBACService(repos)
    grant = await rbac.grant("user-1", "workspace", workspace.id, Role.OPERATOR, granted_by="admin")
    await rbac.revoke(grant.id, revoked_by="admin")

    entries = await repos.audit_log.list_for_resource("workspace", workspace.id)
    actions = [e.action for e in entries]
    assert "rbac_grant" in actions
    assert "rbac_revoke" in actions


@pytest.mark.asyncio
async def test_viewer_role_is_read_only(repos, workspace):
    rbac = RBACService(repos)
    await rbac.grant("viewer-1", "workspace", workspace.id, Role.VIEWER, granted_by="admin")
    assert await rbac.has_permission("viewer-1", Permission.WORKFLOW_READ, workspace_id=workspace.id) is True
    assert await rbac.has_permission("viewer-1", Permission.EXECUTION_READ, workspace_id=workspace.id) is True
    assert await rbac.has_permission("viewer-1", Permission.WORKFLOW_WRITE, workspace_id=workspace.id) is False
    assert await rbac.has_permission("viewer-1", Permission.EXECUTION_CONTROL, workspace_id=workspace.id) is False
