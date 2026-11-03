import pytest

from identity_platform.authorization.authorization_service import AuthorizationService
from identity_platform.authorization.bootstrap import seed_builtin_roles
from identity_platform.core.exceptions import ConflictError, MembershipError
from identity_platform.domain.enums import PrincipalType, RoleScopeType, UserStatus
from identity_platform.models.user import UserModel
from identity_platform.organizations.membership_service import MembershipService
from identity_platform.organizations.organization_service import OrganizationService

pytestmark = pytest.mark.asyncio


async def _make_user(repos, db_session, email: str) -> UserModel:
    user = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(user)
    await db_session.commit()
    return user


async def test_create_organization_grants_owner_role(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    owner = await _make_user(repos, db_session, "org-owner@example.com")

    service = OrganizationService(repos)
    org = await service.create_organization(name="Northwind Corp", owner_user_id=owner.id)
    await db_session.commit()

    assert org.slug == "northwind-corp"
    assert org.owner_user_id == owner.id

    authz = AuthorizationService(repos)
    assert await authz.has_permission(
        principal_type=PrincipalType.USER.value, principal_id=owner.id, permission_key="workspace:create",
        scope_type=RoleScopeType.ORGANIZATION, scope_id=org.id,
    ) is True


async def test_create_organization_rejects_duplicate_slug(repos, db_session):
    owner = await _make_user(repos, db_session, "dupe-owner@example.com")
    service = OrganizationService(repos)
    await service.create_organization(name="Dupe Co", slug="dupe-co", owner_user_id=owner.id)
    await db_session.commit()

    with pytest.raises(ConflictError):
        await service.create_organization(name="Dupe Co 2", slug="dupe-co", owner_user_id=owner.id)


async def test_update_settings_merges_dict(repos, db_session):
    owner = await _make_user(repos, db_session, "settings-owner@example.com")
    service = OrganizationService(repos)
    org = await service.create_organization(name="Settings Co", owner_user_id=owner.id)
    await db_session.commit()

    await service.update_settings(org.id, settings={"theme": "dark"})
    await db_session.commit()
    updated = await service.update_settings(org.id, settings={"locale": "en-US"})
    await db_session.commit()

    assert updated.settings == {"theme": "dark", "locale": "en-US"}


async def test_transfer_ownership_requires_active_membership(repos, db_session):
    owner = await _make_user(repos, db_session, "transfer-owner@example.com")
    stranger = await _make_user(repos, db_session, "stranger@example.com")
    service = OrganizationService(repos)
    org = await service.create_organization(name="Transfer Co", owner_user_id=owner.id)
    await db_session.commit()

    with pytest.raises(MembershipError):
        await service.transfer_ownership(org.id, new_owner_user_id=stranger.id)


async def test_transfer_ownership_succeeds_for_active_member(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    owner = await _make_user(repos, db_session, "transfer-owner-2@example.com")
    new_owner = await _make_user(repos, db_session, "new-owner@example.com")
    service = OrganizationService(repos)
    org = await service.create_organization(name="Transfer Co 2", owner_user_id=owner.id)
    await db_session.commit()

    membership_service = MembershipService(repos)
    await membership_service.add_organization_member(org.id, new_owner.id)
    await db_session.commit()

    updated = await service.transfer_ownership(org.id, new_owner_user_id=new_owner.id)
    await db_session.commit()
    assert updated.owner_user_id == new_owner.id


async def test_departments(repos, db_session):
    owner = await _make_user(repos, db_session, "dept-owner@example.com")
    service = OrganizationService(repos)
    org = await service.create_organization(name="Dept Co", owner_user_id=owner.id)
    await db_session.commit()

    dept = await service.create_department(org.id, name="Engineering")
    await db_session.commit()
    assert dept.organization_id == org.id

    departments = await service.list_departments(org.id)
    assert len(departments) == 1


async def test_first_organization_becomes_the_owners_primary_one(repos, db_session):
    owner = await _make_user(repos, db_session, "primary-owner@example.com")
    service = OrganizationService(repos)
    first = await service.create_organization(name="First Co", owner_user_id=owner.id)
    second = await service.create_organization(name="Second Co", owner_user_id=owner.id)
    await db_session.commit()

    reloaded = await repos.users.get(owner.id)
    assert reloaded.primary_organization_id == first.id != second.id
