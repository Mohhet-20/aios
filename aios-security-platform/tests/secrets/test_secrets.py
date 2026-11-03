"""Tests for the Credential Vault: creation, access-policy-gated
reads with audit logging, rotation (old version deactivated, new
version created), lifecycle transitions (revoke/expire/renew), and
environment secret injection."""
from __future__ import annotations

import pytest

from security_platform.core.exceptions import InvalidTransitionError, SecretAccessDeniedError, SecretExpiredError
from security_platform.secrets.access_service import SecretAccessService
from security_platform.secrets.secret_service import SecretService

TENANT = "tenant-secrets"


@pytest.mark.asyncio
async def test_create_secret_and_denied_read_without_access_policy(repos):
    service = SecretService(repos)
    secret = await service.create_secret(TENANT, name="db-password", secret_type="password", plaintext_value="hunter2")
    with pytest.raises(SecretAccessDeniedError):
        await service.get_secret_value(TENANT, secret.id, "user-1")
    logs = await repos.secret_access_log.list_for_secret(TENANT, secret.id)
    assert len(logs) == 1
    assert logs[0].success is False


@pytest.mark.asyncio
async def test_granted_access_can_read_correct_plaintext(repos):
    secret_service = SecretService(repos)
    access_service = SecretAccessService(repos)
    secret = await secret_service.create_secret(TENANT, name="api-key", secret_type="api_key", plaintext_value="sk-abc123")
    await access_service.grant_access(TENANT, secret.id, "user-1", can_read=True)

    value = await secret_service.get_secret_value(TENANT, secret.id, "user-1")
    assert value == "sk-abc123"
    logs = await repos.secret_access_log.list_for_secret(TENANT, secret.id)
    assert logs[0].success is True


@pytest.mark.asyncio
async def test_rotate_secret_creates_new_version_and_deactivates_old(repos):
    secret_service = SecretService(repos)
    access_service = SecretAccessService(repos)
    secret = await secret_service.create_secret(TENANT, name="rotating-token", secret_type="token", plaintext_value="v1-token")
    await access_service.grant_access(TENANT, secret.id, "user-1")

    rotated = await secret_service.rotate_secret(TENANT, secret.id, "v2-token", rotated_by="admin-1")
    assert rotated.current_version_number == 2
    assert rotated.status == "active"

    value = await secret_service.get_secret_value(TENANT, secret.id, "user-1")
    assert value == "v2-token"

    versions = await repos.secret_versions.list_for_secret(TENANT, secret.id)
    active_versions = [v for v in versions if v.is_active]
    assert len(active_versions) == 1
    assert active_versions[0].version_number == 2


@pytest.mark.asyncio
async def test_revoked_secret_cannot_be_read(repos):
    secret_service = SecretService(repos)
    access_service = SecretAccessService(repos)
    secret = await secret_service.create_secret(TENANT, name="to-revoke", secret_type="token", plaintext_value="v1")
    await access_service.grant_access(TENANT, secret.id, "user-1")

    await secret_service.revoke_secret(TENANT, secret.id)
    with pytest.raises(SecretAccessDeniedError):
        await secret_service.get_secret_value(TENANT, secret.id, "user-1")


@pytest.mark.asyncio
async def test_expired_secret_cannot_be_read_then_renew_restores_access(repos):
    secret_service = SecretService(repos)
    access_service = SecretAccessService(repos)
    secret = await secret_service.create_secret(TENANT, name="to-expire", secret_type="token", plaintext_value="v1")
    await access_service.grant_access(TENANT, secret.id, "user-1")

    await secret_service.expire_secret(TENANT, secret.id)
    with pytest.raises(SecretExpiredError):
        await secret_service.get_secret_value(TENANT, secret.id, "user-1")

    await secret_service.renew_secret(TENANT, secret.id)
    value = await secret_service.get_secret_value(TENANT, secret.id, "user-1")
    assert value == "v1"


@pytest.mark.asyncio
async def test_revoked_secret_cannot_be_rotated_or_renewed(repos):
    secret_service = SecretService(repos)
    secret = await secret_service.create_secret(TENANT, name="dead-secret", secret_type="token", plaintext_value="v1")
    await secret_service.revoke_secret(TENANT, secret.id)
    with pytest.raises(InvalidTransitionError):
        await secret_service.rotate_secret(TENANT, secret.id, "v2")
    with pytest.raises(InvalidTransitionError):
        await secret_service.renew_secret(TENANT, secret.id)


@pytest.mark.asyncio
async def test_revoke_access_removes_read_permission(repos):
    secret_service = SecretService(repos)
    access_service = SecretAccessService(repos)
    secret = await secret_service.create_secret(TENANT, name="revocable-access", secret_type="token", plaintext_value="v1")
    await access_service.grant_access(TENANT, secret.id, "user-1")
    assert await secret_service.get_secret_value(TENANT, secret.id, "user-1") == "v1"

    await access_service.revoke_access(TENANT, secret.id, "user-1")
    with pytest.raises(SecretAccessDeniedError):
        await secret_service.get_secret_value(TENANT, secret.id, "user-1")


@pytest.mark.asyncio
async def test_inject_for_environment_resolves_multiple_secrets(repos):
    secret_service = SecretService(repos)
    access_service = SecretAccessService(repos)
    s1 = await secret_service.create_secret(TENANT, name="ENV_A", secret_type="custom", plaintext_value="value-a")
    s2 = await secret_service.create_secret(TENANT, name="ENV_B", secret_type="custom", plaintext_value="value-b")
    await access_service.grant_access(TENANT, s1.id, "ci-bot")
    await access_service.grant_access(TENANT, s2.id, "ci-bot")

    env = await secret_service.inject_for_environment(TENANT, ["ENV_A", "ENV_B"], "ci-bot")
    assert env == {"ENV_A": "value-a", "ENV_B": "value-b"}
