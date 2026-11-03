import pytest

from identity_platform.authorization.assignment_service import RoleAssignmentService
from identity_platform.authorization.authorization_service import AuthorizationService
from identity_platform.authorization.bootstrap import seed_builtin_roles
from identity_platform.authorization.role_service import RoleService
from identity_platform.domain.enums import OrganizationStatus, PrincipalType, RoleScopeType
from identity_platform.models.organization import OrganizationModel

pytestmark = pytest.mark.asyncio


async def _make_org(repos, db_session, slug: str) -> OrganizationModel:
    org = OrganizationModel(name=slug, slug=slug, status=OrganizationStatus.ACTIVE.value)
    await repos.organizations.add(org)
    await db_session.commit()
    return org


async def test_org_admin_has_manage_permission_via_manage_key(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "authz-admin-org")
    org_admin_role = await repos.roles.get_by_slug(None, "org_admin")

    assignment_service = RoleAssignmentService(repos)
    await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="admin-user", role_id=org_admin_role.id,
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by="root",
    )
    await db_session.commit()

    authz = AuthorizationService(repos)
    assert await authz.has_permission(
        principal_type=PrincipalType.USER.value, principal_id="admin-user", permission_key="workspace:create",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
    ) is True


async def test_member_lacks_manage_permission(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "authz-member-org")
    member_role = await repos.roles.get_by_slug(None, "org_member")

    assignment_service = RoleAssignmentService(repos)
    await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="member-user", role_id=member_role.id,
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by="root",
    )
    await db_session.commit()

    authz = AuthorizationService(repos)
    assert await authz.has_permission(
        principal_type=PrincipalType.USER.value, principal_id="member-user", permission_key="workspace:delete",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
    ) is False
    assert await authz.has_permission(
        principal_type=PrincipalType.USER.value, principal_id="member-user", permission_key="organization:read",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
    ) is True


async def test_system_admin_wildcard_applies_everywhere(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "authz-system-org")
    system_admin_role = await repos.roles.get_by_slug(None, "system_admin")

    assignment_service = RoleAssignmentService(repos)
    await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="root-user", role_id=system_admin_role.id,
        scope_type=RoleScopeType.SYSTEM, scope_id="system", granted_by="root",
    )
    await db_session.commit()

    authz = AuthorizationService(repos)
    assert await authz.has_permission(
        principal_type=PrincipalType.USER.value, principal_id="root-user", permission_key="anything:whatsoever",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
    ) is True


async def test_permission_denied_at_wrong_scope(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org_a = await _make_org(repos, db_session, "authz-scope-a")
    org_b = await _make_org(repos, db_session, "authz-scope-b")
    org_admin_role = await repos.roles.get_by_slug(None, "org_admin")

    assignment_service = RoleAssignmentService(repos)
    await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="scoped-user", role_id=org_admin_role.id,
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org_a.id, granted_by="root",
    )
    await db_session.commit()

    authz = AuthorizationService(repos)
    assert await authz.has_permission(
        principal_type=PrincipalType.USER.value, principal_id="scoped-user", permission_key="workspace:create",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org_b.id,
    ) is False


async def test_require_permission_raises(repos, db_session):
    from identity_platform.core.exceptions import PermissionDeniedError

    org = await _make_org(repos, db_session, "authz-require-org")
    authz = AuthorizationService(repos)
    with pytest.raises(PermissionDeniedError):
        await authz.require_permission(
            principal_type=PrincipalType.USER.value, principal_id="nobody", permission_key="workspace:create",
            scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
        )


async def test_effective_permissions_union(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "authz-effective-org")
    member_role = await repos.roles.get_by_slug(None, "org_member")

    role_service = RoleService(repos)
    custom_role = await role_service.create_custom_role(
        org.id, name="Extra", slug="extra_reader", scope_type=RoleScopeType.ORGANIZATION, permissions=["audit:read"],
    )
    await db_session.commit()

    assignment_service = RoleAssignmentService(repos)
    await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="union-user", role_id=member_role.id,
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by="root",
    )
    await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="union-user", role_id=custom_role.id,
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by="root",
    )
    await db_session.commit()

    authz = AuthorizationService(repos)
    effective = await authz.effective_permissions(
        principal_type=PrincipalType.USER.value, principal_id="union-user",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
    )
    assert "audit:read" in effective
    assert "organization:read" in effective
