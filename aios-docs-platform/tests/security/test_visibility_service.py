import pytest

from docs_platform.config.settings import Settings
from docs_platform.core.exceptions import PermissionDeniedError
from docs_platform.security.role_assignment_service import RoleAssignmentService
from docs_platform.security.visibility_service import VisibilityService

pytestmark = pytest.mark.asyncio

TENANT = "t-security"


async def test_public_visible_to_anonymous(repos):
    role_svc = RoleAssignmentService(repos, Settings())
    vis_svc = VisibilityService(role_svc)
    assert await vis_svc.can_view(TENANT, visibility="public", user_id=None) is True


async def test_internal_hidden_from_anonymous(repos):
    role_svc = RoleAssignmentService(repos, Settings())
    vis_svc = VisibilityService(role_svc)
    assert await vis_svc.can_view(TENANT, visibility="internal", user_id=None) is False


async def test_internal_visible_to_role_holder(repos):
    role_svc = RoleAssignmentService(repos, Settings())
    vis_svc = VisibilityService(role_svc)
    await role_svc.assign_role(TENANT, user_id="viewer-user", role="viewer")
    assert await vis_svc.can_view(TENANT, visibility="internal", user_id="viewer-user") is True


async def test_internal_hidden_from_user_without_role(repos):
    role_svc = RoleAssignmentService(repos, Settings())
    vis_svc = VisibilityService(role_svc)
    assert await vis_svc.can_view(TENANT, visibility="internal", user_id="no-role-user") is False


async def test_assert_can_view_raises_permission_denied(repos):
    role_svc = RoleAssignmentService(repos, Settings())
    vis_svc = VisibilityService(role_svc)
    with pytest.raises(PermissionDeniedError):
        await vis_svc.assert_can_view(TENANT, visibility="internal", user_id=None)
