import pytest

from identity_platform.domain.enums import IdentityProviderKey, UserStatus
from identity_platform.federated.federated_identity_service import FederatedIdentityService
from identity_platform.federated.provider import ExternalProfile
from identity_platform.models.user import UserModel

pytestmark = pytest.mark.asyncio


async def test_provision_creates_new_active_user_for_first_time_sso(repos, db_session):
    service = FederatedIdentityService(repos)
    profile = ExternalProfile(
        provider_key=IdentityProviderKey.GOOGLE, external_user_id="g-1", email="newsso@example.com",
        display_name="New SSO User", raw_profile={"sub": "g-1"},
    )

    user = await service.provision_or_login(profile)
    await db_session.commit()

    assert user.status == "active"
    assert user.email_verified_at is not None
    assert user.display_name == "New SSO User"

    links = await service.list_linked_identities(user.id)
    assert len(links) == 1
    assert links[0].provider_key == "google"


async def test_provision_links_to_existing_user_by_email(repos, db_session):
    existing = UserModel(email="alreadyexists@example.com", status=UserStatus.ACTIVE.value)
    await repos.users.add(existing)
    await db_session.commit()

    service = FederatedIdentityService(repos)
    profile = ExternalProfile(
        provider_key=IdentityProviderKey.GITHUB, external_user_id="gh-42", email="alreadyexists@example.com",
        display_name="GitHub Name", raw_profile={},
    )
    user = await service.provision_or_login(profile)
    await db_session.commit()

    assert user.id == existing.id


async def test_second_login_with_same_provider_identity_returns_same_user(repos, db_session):
    service = FederatedIdentityService(repos)
    profile = ExternalProfile(
        provider_key=IdentityProviderKey.GOOGLE, external_user_id="g-repeat", email="repeat@example.com",
        display_name="Repeat User", raw_profile={},
    )

    first_login = await service.provision_or_login(profile)
    await db_session.commit()
    second_login = await service.provision_or_login(profile)
    await db_session.commit()

    assert first_login.id == second_login.id
    links = await service.list_linked_identities(first_login.id)
    assert len(links) == 1  # not duplicated on repeat login


async def test_unlink_identity(repos, db_session):
    service = FederatedIdentityService(repos)
    profile = ExternalProfile(
        provider_key=IdentityProviderKey.GOOGLE, external_user_id="g-unlink", email="unlink@example.com",
        display_name=None, raw_profile={},
    )
    user = await service.provision_or_login(profile)
    await db_session.commit()

    links = await service.list_linked_identities(user.id)
    assert len(links) == 1

    await service.unlink_identity(links[0].id)
    await db_session.commit()

    assert await service.list_linked_identities(user.id) == []
