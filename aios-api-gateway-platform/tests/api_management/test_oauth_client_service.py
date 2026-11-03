from __future__ import annotations

import pytest

from gateway_platform.api_management.oauth_client_service import OAuthClientService
from gateway_platform.core.exceptions import OAuthClientNotFoundError

TENANT = "am-oauth-tenant"


@pytest.mark.asyncio
async def test_register_and_verify_client(repos):
    service = OAuthClientService(repos)
    client, secret = await service.register_client(TENANT, name="partner-app", scopes=["read"])
    assert client.client_id.startswith("gwc_")
    verified = await service.verify_client(client.client_id, secret)
    assert verified.id == client.id


@pytest.mark.asyncio
async def test_verify_wrong_secret_rejected(repos):
    service = OAuthClientService(repos)
    client, _secret = await service.register_client(TENANT, name="partner-app-2")
    with pytest.raises(OAuthClientNotFoundError):
        await service.verify_client(client.client_id, "wrong-secret")


@pytest.mark.asyncio
async def test_suspend_and_revoke(repos):
    service = OAuthClientService(repos)
    client, secret = await service.register_client(TENANT, name="partner-app-3")
    await service.suspend_client(client.client_id)
    with pytest.raises(OAuthClientNotFoundError):
        await service.verify_client(client.client_id, secret)

    await service.revoke_client(client.client_id)
    fetched = await service._get_or_404(client.client_id)
    assert fetched.status == "revoked"


@pytest.mark.asyncio
async def test_list_for_tenant(repos):
    service = OAuthClientService(repos)
    await service.register_client(TENANT, name="partner-app-4")
    clients = await service.list_for_tenant(TENANT)
    assert len(clients) >= 1
