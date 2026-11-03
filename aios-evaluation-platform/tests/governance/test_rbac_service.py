import pytest

from eval_platform.core.exceptions import AuthorizationError, ValidationError
from eval_platform.domain.enums import Permission, Role


@pytest.mark.asyncio
async def test_grant_and_check_permission(rbac_service):
    await rbac_service.grant_role("user-1", resource_type="workspace", resource_id="ws-1", role="analyst", granted_by="owner-1")
    role = await rbac_service.get_effective_role("user-1", resource_type="workspace", resource_id="ws-1")
    assert role == Role.ANALYST
    assert await rbac_service.has_permission("user-1", resource_type="workspace", resource_id="ws-1", permission=Permission.EVALUATION_WRITE)
    assert not await rbac_service.has_permission("user-1", resource_type="workspace", resource_id="ws-1", permission=Permission.GOVERNANCE_ADMIN)


@pytest.mark.asyncio
async def test_grant_rejects_unknown_role(rbac_service):
    with pytest.raises(ValidationError):
        await rbac_service.grant_role("user-1", resource_type="workspace", resource_id="ws-1", role="superuser", granted_by="owner-1")


@pytest.mark.asyncio
async def test_regranting_revokes_previous_grant(rbac_service):
    await rbac_service.grant_role("user-1", resource_type="workspace", resource_id="ws-1", role="viewer", granted_by="owner-1")
    await rbac_service.grant_role("user-1", resource_type="workspace", resource_id="ws-1", role="admin", granted_by="owner-1")

    grants = await rbac_service.list_grants_for_principal("user-1")
    assert len(grants) == 2
    active = [g for g in grants if g.revoked_at is None]
    assert len(active) == 1
    assert active[0].role == "admin"


@pytest.mark.asyncio
async def test_revoke_role(rbac_service):
    await rbac_service.grant_role("user-1", resource_type="workspace", resource_id="ws-1", role="admin", granted_by="owner-1")
    await rbac_service.revoke_role("user-1", resource_type="workspace", resource_id="ws-1")
    role = await rbac_service.get_effective_role("user-1", resource_type="workspace", resource_id="ws-1")
    assert role is None


@pytest.mark.asyncio
async def test_no_grant_means_no_permission(rbac_service):
    assert await rbac_service.has_permission("stranger", resource_type="workspace", resource_id="ws-1", permission=Permission.EVALUATION_READ) is False


@pytest.mark.asyncio
async def test_require_permission_raises_when_missing(rbac_service):
    await rbac_service.grant_role("user-1", resource_type="workspace", resource_id="ws-1", role="viewer", granted_by="owner-1")
    with pytest.raises(AuthorizationError):
        await rbac_service.require_permission("user-1", resource_type="workspace", resource_id="ws-1", permission=Permission.EVALUATION_WRITE)


@pytest.mark.asyncio
async def test_owner_has_every_permission(rbac_service):
    await rbac_service.grant_role("owner-1", resource_type="workspace", resource_id="ws-1", role="owner", granted_by="owner-1")
    for permission in Permission:
        assert await rbac_service.has_permission("owner-1", resource_type="workspace", resource_id="ws-1", permission=permission)
