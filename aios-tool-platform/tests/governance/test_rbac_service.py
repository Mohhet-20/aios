import pytest

from tool_platform.core.exceptions import AuthorizationError
from tool_platform.domain.enums import Permission


@pytest.mark.asyncio
async def test_workspace_wide_grant_satisfies_resource_specific_check(rbac, workspace):
    await rbac.grant("user-1", "workspace", workspace.id, "operator", granted_by="admin-1")

    allowed = await rbac.has_permission(
        "user-1", Permission.TOOL_EXECUTE, resource_type="tool", resource_id="tool-123", workspace_id=workspace.id,
    )
    assert allowed is True


@pytest.mark.asyncio
async def test_viewer_role_cannot_execute_tools(rbac, workspace):
    await rbac.grant("user-2", "workspace", workspace.id, "viewer", granted_by="admin-1")

    allowed = await rbac.has_permission(
        "user-2", Permission.TOOL_EXECUTE, resource_type="tool", resource_id="tool-123", workspace_id=workspace.id,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_no_grant_at_all_denies_permission(rbac, workspace):
    allowed = await rbac.has_permission(
        "stranger", Permission.TOOL_READ, resource_type="tool", resource_id="tool-123", workspace_id=workspace.id,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_enforce_permission_raises_for_denied_principal(rbac, workspace):
    with pytest.raises(AuthorizationError):
        await rbac.enforce_permission(
            "stranger", Permission.TOOL_WRITE, resource_type="tool", resource_id="tool-123", workspace_id=workspace.id,
        )


@pytest.mark.asyncio
async def test_revoked_grant_no_longer_satisfies_permission(rbac, workspace):
    grant = await rbac.grant("user-3", "workspace", workspace.id, "admin", granted_by="admin-1")
    await rbac.revoke(grant.id)

    allowed = await rbac.has_permission(
        "user-3", Permission.TOOL_WRITE, resource_type="tool", resource_id="tool-123", workspace_id=workspace.id,
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_resource_specific_grant_overrides_lack_of_workspace_grant(rbac, workspace):
    await rbac.grant("user-4", "tool", "tool-999", "admin", granted_by="admin-1")

    allowed_on_that_tool = await rbac.has_permission(
        "user-4", Permission.TOOL_DELETE, resource_type="tool", resource_id="tool-999", workspace_id=workspace.id,
    )
    allowed_on_other_tool = await rbac.has_permission(
        "user-4", Permission.TOOL_DELETE, resource_type="tool", resource_id="tool-other", workspace_id=workspace.id,
    )
    assert allowed_on_that_tool is True
    assert allowed_on_other_tool is False


def test_enforce_workspace_isolation_raises_on_mismatch(rbac):
    with pytest.raises(AuthorizationError):
        rbac.enforce_workspace_isolation("ws-a", "ws-b")
    rbac.enforce_workspace_isolation("ws-a", "ws-a")  # no raise


def test_enforce_organization_isolation_raises_on_mismatch(rbac):
    with pytest.raises(AuthorizationError):
        rbac.enforce_organization_isolation("org-a", "org-b")
    rbac.enforce_organization_isolation("org-a", "org-a")  # no raise


@pytest.mark.asyncio
async def test_list_for_principal_returns_all_grants(rbac, workspace):
    await rbac.grant("user-5", "workspace", workspace.id, "viewer", granted_by="admin-1")
    await rbac.grant("user-5", "tool", "tool-1", "admin", granted_by="admin-1")

    grants = await rbac.list_for_principal("user-5")
    assert len(grants) == 2
