from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.security.rbac_service import AnalyticsRbacService, role_satisfies

TENANT = "rbac-tenant"


def test_role_satisfies_hierarchy():
    assert role_satisfies("admin", "viewer") is True
    assert role_satisfies("viewer", "admin") is False
    assert role_satisfies("editor", "editor") is True


def test_role_satisfies_unknown_role_fails_closed():
    assert role_satisfies("not_a_role", "viewer") is False


@pytest.mark.asyncio
async def test_grant_role_rejects_bad_role(repos):
    service = AnalyticsRbacService(repos)
    with pytest.raises(ValidationError):
        await service.grant_role(TENANT, "user-1", role_level="superuser")


@pytest.mark.asyncio
async def test_grant_role_is_upsert(repos):
    service = AnalyticsRbacService(repos)
    a = await service.grant_role(TENANT, "user-1", role_level="viewer")
    b = await service.grant_role(TENANT, "user-1", role_level="admin")
    assert a.id == b.id
    assert await service.get_role(TENANT, "user-1") == "admin"


@pytest.mark.asyncio
async def test_check_permission_true_and_false(repos):
    service = AnalyticsRbacService(repos)
    await service.grant_role(TENANT, "user-1", role_level="analyst")
    assert await service.check_permission(TENANT, "user-1", required_role="viewer") is True
    assert await service.check_permission(TENANT, "user-1", required_role="admin") is False


@pytest.mark.asyncio
async def test_check_permission_no_grant_is_false(repos):
    service = AnalyticsRbacService(repos)
    assert await service.check_permission(TENANT, "ghost-user", required_role="viewer") is False


@pytest.mark.asyncio
async def test_scoped_grants_are_independent(repos):
    service = AnalyticsRbacService(repos)
    await service.grant_role(TENANT, "user-1", role_level="admin", scope="workspace-a")
    await service.grant_role(TENANT, "user-1", role_level="viewer", scope="workspace-b")
    assert await service.get_role(TENANT, "user-1", scope="workspace-a") == "admin"
    assert await service.get_role(TENANT, "user-1", scope="workspace-b") == "viewer"


@pytest.mark.asyncio
async def test_revoke_role(repos):
    service = AnalyticsRbacService(repos)
    await service.grant_role(TENANT, "user-1", role_level="editor")
    await service.revoke_role(TENANT, "user-1")
    assert await service.get_role(TENANT, "user-1") is None
