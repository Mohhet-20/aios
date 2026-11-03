import pytest

from memory_platform.core.exceptions import AuthorizationError
from memory_platform.domain.enums import Permission, Role, SensitivityLevel
from memory_platform.governance.access_policy_service import AccessPolicyService
from memory_platform.governance.rbac_service import RBACService
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_viewer_can_read_public_content(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.VIEWER, granted_by="admin-1")
    policy = AccessPolicyService(rbac)
    role = await policy.enforce_access(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_READ, sensitivity_level=SensitivityLevel.PUBLIC)
    assert role == Role.VIEWER


@pytest.mark.asyncio
async def test_viewer_cannot_read_restricted_content(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.VIEWER, granted_by="admin-1")
    policy = AccessPolicyService(rbac)
    with pytest.raises(AuthorizationError):
        await policy.enforce_access(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_READ, sensitivity_level=SensitivityLevel.RESTRICTED)


@pytest.mark.asyncio
async def test_admin_can_read_restricted_content(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.ADMIN, granted_by="admin-1")
    policy = AccessPolicyService(rbac)
    role = await policy.enforce_access(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_READ, sensitivity_level=SensitivityLevel.RESTRICTED)
    assert role == Role.ADMIN


@pytest.mark.asyncio
async def test_no_role_raises(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    policy = AccessPolicyService(rbac)
    with pytest.raises(AuthorizationError):
        await policy.enforce_access(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_READ, sensitivity_level=SensitivityLevel.PUBLIC)


@pytest.mark.asyncio
async def test_permission_still_checked_even_with_sufficient_sensitivity_role(repos):
    await _workspace(repos)
    rbac = RBACService(repos)
    await rbac.grant_role(principal_id="user-1", resource_type="workspace", resource_id="ws-1", role=Role.OPERATOR, granted_by="admin-1")
    policy = AccessPolicyService(rbac)
    # OPERATOR passes the CONFIDENTIAL sensitivity bar but lacks MEMORY_DELETE
    with pytest.raises(AuthorizationError):
        await policy.enforce_access(principal_id="user-1", workspace_id="ws-1", permission=Permission.MEMORY_DELETE, sensitivity_level=SensitivityLevel.CONFIDENTIAL)
