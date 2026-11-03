from __future__ import annotations

import pytest

from gateway_platform.api_management.api_key_service import ApiKeyService
from gateway_platform.core.exceptions import ApiKeyExpiredError, ApiKeyRevokedError

TENANT = "am-tenant"


@pytest.mark.asyncio
async def test_issue_and_verify_key(repos):
    service = ApiKeyService(repos)
    result = await service.issue_key(TENANT, name="k1", scopes=["read"])
    assert result.raw_key.startswith("gwk_")
    verified = await service.verify_key(result.raw_key)
    assert verified.id == result.api_key.id
    assert verified.last_used_at is not None


@pytest.mark.asyncio
async def test_verify_invalid_key_raises(repos):
    service = ApiKeyService(repos)
    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key("gwk_does-not-exist")


@pytest.mark.asyncio
async def test_revoke_then_verify_raises(repos):
    service = ApiKeyService(repos)
    result = await service.issue_key(TENANT, name="k2")
    await service.revoke_key(result.api_key.id)
    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key(result.raw_key)


@pytest.mark.asyncio
async def test_expired_key_raises_and_marks_expired(repos):
    service = ApiKeyService(repos)
    result = await service.issue_key(TENANT, name="k3", ttl_days=-1)
    with pytest.raises(ApiKeyExpiredError):
        await service.verify_key(result.raw_key)
    refreshed = await repos.api_keys.get(result.api_key.id)
    assert refreshed.status == "expired"


@pytest.mark.asyncio
async def test_rotate_key_issues_new_and_revokes_old(repos):
    service = ApiKeyService(repos)
    original = await service.issue_key(TENANT, name="k4", scopes=["read", "write"])
    rotated = await service.rotate_key(original.api_key.id)
    assert rotated.raw_key != original.raw_key
    with pytest.raises(ApiKeyRevokedError):
        await service.verify_key(original.raw_key)
    verified = await service.verify_key(rotated.raw_key)
    assert verified.scopes == ["read", "write"]
