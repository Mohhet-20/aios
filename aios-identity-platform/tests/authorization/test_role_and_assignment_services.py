import pytest

from identity_platform.authorization.assignment_service import RoleAssignmentService
from identity_platform.authorization.bootstrap import seed_builtin_roles
from identity_platform.authorization.role_service import RoleService
from identity_platform.core.exceptions import ConflictError, RoleError, UnknownPermissionError
from identity_platform.domain.enums import OrganizationStatus, PrincipalType, RoleScopeType
from identity_platform.models.organization import OrganizationModel

pytestmark = pytest.mark.asyncio


async def _make_org(repos, db_session, slug: str) -> OrganizationModel:
    org = OrganizationModel(name=slug, slug=slug, status=OrganizationStatus.ACTIVE.value)
    await repos.organizations.add(org)
    await db_session.commit()
    return org


async def test_create_custom_role_and_list_available(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "custom-role-org")

    role_service = RoleService(repos)
    role = await role_service.create_custom_role(
        org.id, name="Support Agent", slug="support_agent", scope_type=RoleScopeType.ORGANIZATION,
        permissions=["user:read"],
    )
    await db_session.commit()
    assert role.is_custom is True

    available = await role_service.list_available_for_organization(org.id)
    slugs = {r.slug for r in available}
    assert "support_agent" in slugs
    assert "org_admin" in slugs  # built-in roles are visible too


async def test_create_custom_role_rejects_unknown_permission(repos, db_session):
    org = await _make_org(repos, db_session, "bad-perm-org")
    role_service = RoleService(repos)
    with pytest.raises(UnknownPermissionError):
        await role_service.create_custom_role(
            org.id, name="Bad", slug="bad", scope_type=RoleScopeType.ORGANIZATION, permissions=["not:a-real-permission"],
        )


async def test_create_custom_role_rejects_duplicate_slug(repos, db_session):
    org = await _make_org(repos, db_session, "dupe-slug-org")
    role_service = RoleService(repos)
    await role_service.create_custom_role(org.id, name="A", slug="dupe", scope_type=RoleScopeType.ORGANIZATION, permissions=[])
    await db_session.commit()
    with pytest.raises(ConflictError):
        await role_service.create_custom_role(org.id, name="B", slug="dupe", scope_type=RoleScopeType.ORGANIZATION, permissions=[])


async def test_cannot_modify_or_delete_builtin_role(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    role_service = RoleService(repos)
    builtin = await repos.roles.get_by_slug(None, "org_member")

    with pytest.raises(RoleError):
        await role_service.update_permissions(builtin.id, ["user:read"])
    with pytest.raises(RoleError):
        await role_service.delete_custom_role(builtin.id)


async def test_assign_and_revoke_role(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "assign-org")
    org_admin_role = await repos.roles.get_by_slug(None, "org_admin")

    assignment_service = RoleAssignmentService(repos)
    assignment = await assignment_service.assign_role(
        principal_type=PrincipalType.USER.value, principal_id="user-1", role_id=org_admin_role.id,
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by="user-0",
    )
    await db_session.commit()
    assert assignment.revoked_at is None

    assignments = await assignment_service.list_for_principal(PrincipalType.USER.value, "user-1")
    assert len(assignments) == 1

    await assignment_service.revoke_assignment(assignment.id)
    await db_session.commit()

    active = await repos.role_assignments.get_active_for_scope(PrincipalType.USER.value, "user-1", RoleScopeType.ORGANIZATION.value, org.id)
    assert active is None


async def test_assign_role_rejects_scope_mismatch(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org = await _make_org(repos, db_session, "scope-mismatch-org")
    workspace_role = await repos.roles.get_by_slug(None, "workspace_admin")

    assignment_service = RoleAssignmentService(repos)
    with pytest.raises(RoleError):
        await assignment_service.assign_role(
            principal_type=PrincipalType.USER.value, principal_id="user-1", role_id=workspace_role.id,
            scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id, granted_by="user-0",
        )
