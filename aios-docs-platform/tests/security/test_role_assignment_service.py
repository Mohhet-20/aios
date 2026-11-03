import pytest

from docs_platform.config.settings import Settings
from docs_platform.core.exceptions import ValidationError
from docs_platform.security.role_assignment_service import RoleAssignmentService

pytestmark = pytest.mark.asyncio

TENANT = "t-security"


async def test_assign_role_rejects_unknown_role(repos):
    svc = RoleAssignmentService(repos, Settings())
    with pytest.raises(ValidationError):
        await svc.assign_role(TENANT, user_id="u1", role="superuser")


async def test_assign_and_get_role_tenant_wide(repos):
    svc = RoleAssignmentService(repos, Settings())
    await svc.assign_role(TENANT, user_id="u2", role="editor")
    role = await svc.get_role(TENANT, "u2")
    assert role == "editor"


async def test_reassign_role_overwrites(repos):
    svc = RoleAssignmentService(repos, Settings())
    await svc.assign_role(TENANT, user_id="u3", role="viewer")
    await svc.assign_role(TENANT, user_id="u3", role="admin")
    role = await svc.get_role(TENANT, "u3")
    assert role == "admin"


async def test_get_role_falls_back_to_tenant_wide(repos):
    svc = RoleAssignmentService(repos, Settings())
    await svc.assign_role(TENANT, user_id="u4", role="owner")
    role = await svc.get_role(TENANT, "u4", scope_ref="space:1")
    assert role == "owner"


async def test_scoped_role_takes_precedence_over_tenant_wide(repos):
    svc = RoleAssignmentService(repos, Settings())
    await svc.assign_role(TENANT, user_id="u5", role="viewer")
    await svc.assign_role(TENANT, user_id="u5", role="admin", scope_ref="space:2")
    scoped_role = await svc.get_role(TENANT, "u5", scope_ref="space:2")
    other_scope_role = await svc.get_role(TENANT, "u5", scope_ref="space:other")
    assert scoped_role == "admin"
    assert other_scope_role == "viewer"


async def test_has_at_least_respects_hierarchy(repos):
    svc = RoleAssignmentService(repos, Settings())
    await svc.assign_role(TENANT, user_id="u6", role="contributor")
    assert await svc.has_at_least(TENANT, "u6", "viewer") is True
    assert await svc.has_at_least(TENANT, "u6", "contributor") is True
    assert await svc.has_at_least(TENANT, "u6", "editor") is False


async def test_has_at_least_no_assignment_is_false(repos):
    svc = RoleAssignmentService(repos, Settings())
    assert await svc.has_at_least(TENANT, "ghost-user", "viewer") is False


async def test_list_for_user(repos):
    svc = RoleAssignmentService(repos, Settings())
    await svc.assign_role(TENANT, user_id="u7", role="viewer")
    await svc.assign_role(TENANT, user_id="u7", role="editor", scope_ref="space:3")
    assignments = await svc.list_for_user(TENANT, "u7")
    assert len(assignments) == 2
