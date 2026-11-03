import uuid

import pytest

from developer_platform.api_platform.api_key_service import ApiKeyService
from developer_platform.core.exceptions import ApiKeyExpiredError, ApiKeyRevokedError

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_issue_and_verify_key(repos, db_session):
    tenant_id = _tid()
    service = ApiKeyService(repos)

    result = await service.issue_key(tenant_id, name="ci key", scopes=["read"])
    await db_session.commit()
    assert result.raw_key.startswith("dpk_")
    assert result.api_key.key_prefix == result.raw_key[:12]

    verified = await service.verify_key(result.raw_key)
    assert verified.id == result.api_key.id
    assert verified.last_used_at is not None


async def test_verify_unknown_key_raises(repos, db_session):
    service = ApiKeyService(repos)
    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key("dpk_not-a-real-key")


async def test_revoke_then_verify_raises(repos, db_session):
    tenant_id = _tid()
    service = ApiKeyService(repos)
    result = await service.issue_key(tenant_id, name="to revoke")
    await db_session.commit()

    await service.revoke_key(result.api_key.id)
    await db_session.commit()

    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key(result.raw_key)


async def test_expired_key_raises_and_transitions(repos, db_session):
    tenant_id = _tid()
    service = ApiKeyService(repos)
    result = await service.issue_key(tenant_id, name="short-lived", ttl_days=-1)
    await db_session.commit()

    with pytest.raises(ApiKeyExpiredError):
        await service.verify_key(result.raw_key)
    await db_session.commit()

    listed = await service.list_for_tenant(tenant_id)
    assert listed[0].status == "expired"


async def test_rotate_key_revokes_old_and_issues_new(repos, db_session):
    tenant_id = _tid()
    service = ApiKeyService(repos)
    original = await service.issue_key(tenant_id, name="rotating", scopes=["read", "write"])
    await db_session.commit()

    rotated = await service.rotate_key(original.api_key.id)
    await db_session.commit()

    assert rotated.api_key.id != original.api_key.id
    assert rotated.api_key.scopes == ["read", "write"]
    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key(original.raw_key)
    verified_new = await service.verify_key(rotated.raw_key)
    assert verified_new.id == rotated.api_key.id
