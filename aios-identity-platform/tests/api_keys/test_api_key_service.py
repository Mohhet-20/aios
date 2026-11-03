import pytest

from datetime import timedelta

from identity_platform.api_keys.api_key_service import ApiKeyService
from identity_platform.api_keys.service_account_service import ServiceAccountService
from identity_platform.config.settings import Settings
from identity_platform.core.exceptions import ApiKeyExpiredError, ApiKeyRevokedError, UnknownPermissionError
from identity_platform.domain.enums import UserStatus
from identity_platform.models.user import UserModel
from identity_platform.organizations.organization_service import OrganizationService

pytestmark = pytest.mark.asyncio


async def _make_org(repos, db_session, name: str, email: str):
    owner = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(owner)
    await db_session.commit()
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


async def test_issue_and_verify_key(repos, db_session):
    org, owner = await _make_org(repos, db_session, "ApiKey Co", "apikey-owner@example.com")
    service = ApiKeyService(repos)

    result = await service.issue_key(
        org.id, owner_type="user", owner_id=owner.id, name="CI Key", created_by=owner.id, scopes=["workflow:execute"],
    )
    await db_session.commit()
    assert result.raw_key
    assert result.api_key.key_prefix == result.raw_key[:8]

    verified = await service.verify_key(result.raw_key)
    await db_session.commit()
    assert verified.id == result.api_key.id
    assert verified.last_used_at is not None


async def test_verify_key_rejects_unknown_key(repos, db_session):
    service = ApiKeyService(repos)
    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key("not-a-real-key")


async def test_issue_key_rejects_unknown_scope(repos, db_session):
    org, owner = await _make_org(repos, db_session, "BadScope Co", "badscope-owner@example.com")
    service = ApiKeyService(repos)
    with pytest.raises(UnknownPermissionError):
        await service.issue_key(org.id, owner_type="user", owner_id=owner.id, name="Bad", created_by=owner.id, scopes=["not:real"])


async def test_revoke_key_prevents_verification(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Revoke Co", "revoke-owner@example.com")
    service = ApiKeyService(repos)
    result = await service.issue_key(org.id, owner_type="user", owner_id=owner.id, name="Key", created_by=owner.id)
    await db_session.commit()

    await service.revoke_key(result.api_key.id)
    await db_session.commit()

    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key(result.raw_key)


async def test_rotate_key_invalidates_old_and_issues_new(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Rotate Co", "rotate-owner@example.com")
    service = ApiKeyService(repos)
    result = await service.issue_key(org.id, owner_type="user", owner_id=owner.id, name="Key", created_by=owner.id, scopes=["workflow:execute"])
    await db_session.commit()

    rotated = await service.rotate_key(result.api_key.id)
    await db_session.commit()

    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key(result.raw_key)

    verified = await service.verify_key(rotated.raw_key)
    assert verified.scopes == ["workflow:execute"]


async def test_expired_key_rejected(repos, db_session):
    from identity_platform.database.base import utcnow

    org, owner = await _make_org(repos, db_session, "Expire Co", "expire-owner@example.com")
    service = ApiKeyService(repos)
    result = await service.issue_key(
        org.id, owner_type="user", owner_id=owner.id, name="Key", created_by=owner.id,
        expires_at=utcnow() - timedelta(seconds=1),
    )
    await db_session.commit()

    with pytest.raises(ApiKeyExpiredError):
        await service.verify_key(result.raw_key)


async def test_default_ttl_applied_when_configured(repos, db_session):
    org, owner = await _make_org(repos, db_session, "DefaultTTL Co", "ttl-owner@example.com")
    settings = Settings(secret_key="x" * 32, api_key_default_ttl_days=30)
    service = ApiKeyService(repos, settings=settings)

    result = await service.issue_key(org.id, owner_type="user", owner_id=owner.id, name="Key", created_by=owner.id)
    await db_session.commit()
    assert result.api_key.expires_at is not None


async def test_service_account_lifecycle_and_key_ownership(repos, db_session):
    org, owner = await _make_org(repos, db_session, "SvcAcct Co", "svcacct-owner@example.com")
    sa_service = ServiceAccountService(repos)
    account = await sa_service.create(org.id, name="CI Bot")
    await db_session.commit()
    assert account.status == "active"

    api_key_service = ApiKeyService(repos)
    result = await api_key_service.issue_key(org.id, owner_type="service_account", owner_id=account.id, name="Bot Key", created_by=owner.id)
    await db_session.commit()

    keys = await api_key_service.list_for_owner("service_account", account.id)
    assert len(keys) == 1
    assert keys[0].id == result.api_key.id

    disabled = await sa_service.disable(account.id)
    await db_session.commit()
    assert disabled.status == "disabled"

    accounts = await sa_service.list_for_organization(org.id)
    assert len(accounts) == 1
