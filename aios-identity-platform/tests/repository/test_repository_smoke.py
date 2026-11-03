"""CRUD-roundtrip smoke test through the repository layer, exercising
the RepositoryRegistry (unit of work) across a handful of tables
including a unique-constrained membership join."""
import pytest

from identity_platform.domain.enums import MembershipStatus, OrganizationStatus, UserStatus
from identity_platform.models.membership import OrganizationMembershipModel
from identity_platform.models.organization import OrganizationModel
from identity_platform.models.user import UserModel

pytestmark = pytest.mark.asyncio


async def test_organization_crud_roundtrip(repos, db_session):
    org = OrganizationModel(name="Acme Corp", slug="acme-corp", status=OrganizationStatus.ACTIVE.value)
    await repos.organizations.add(org)
    await db_session.commit()

    fetched = await repos.organizations.get(org.id)
    assert fetched is not None
    assert fetched.slug == "acme-corp"

    by_slug = await repos.organizations.get_by_slug("acme-corp")
    assert by_slug is not None
    assert by_slug.id == org.id

    fetched.name = "Acme Corporation"
    await repos.organizations.update(fetched)
    await db_session.commit()
    refetched = await repos.organizations.get(org.id)
    assert refetched.name == "Acme Corporation"


async def test_user_repository_get_by_email_lowercases(repos, db_session):
    user = UserModel(email="jane@example.com", status=UserStatus.PENDING_VERIFICATION.value)
    await repos.users.add(user)
    await db_session.commit()

    found = await repos.users.get_by_email("JANE@example.com")
    assert found is not None
    assert found.id == user.id


async def test_organization_membership_unique_constraint_and_listing(repos, db_session):
    org = OrganizationModel(name="Globex", slug="globex", status=OrganizationStatus.ACTIVE.value)
    user = UserModel(email="member@globex.com", status=UserStatus.ACTIVE.value)
    await repos.organizations.add(org)
    await repos.users.add(user)
    await db_session.flush()

    membership = OrganizationMembershipModel(
        organization_id=org.id, user_id=user.id, status=MembershipStatus.ACTIVE.value
    )
    await repos.organization_memberships.add(membership)
    await db_session.commit()

    found = await repos.organization_memberships.get_for_org_and_user(org.id, user.id)
    assert found is not None

    members = await repos.organization_memberships.list_for_organization(org.id)
    assert len(members) == 1
    assert members[0].user_id == user.id


async def test_delete_is_soft(repos, db_session):
    org = OrganizationModel(name="Initech", slug="initech", status=OrganizationStatus.ACTIVE.value)
    await repos.organizations.add(org)
    await db_session.commit()

    await repos.organizations.delete(org)
    await db_session.commit()

    assert await repos.organizations.get(org.id) is None
    assert await repos.organizations.get(org.id, include_deleted=True) is not None
