"""OAuth-ready client registration: registers a client_id/secret pair
(secret hashed at rest, never stored raw) with a redirect URI
allowlist and granted scopes. This is client registration and secret
verification, not a full OAuth2 authorization server — the actual
authorization-code/token-exchange endpoints are out of scope for this
control plane, the same disclosed boundary the Developer Platform's
own OAuth readiness module drew."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import OAuthClientNotFoundError
from gateway_platform.domain.enums import OAuthClientStatus
from gateway_platform.models.api_management import OAuthClientModel
from gateway_platform.repositories.registry import RepositoryRegistry
from gateway_platform.security.tokens import generate_raw_token, hash_token


class OAuthClientService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def register_client(
        self, tenant_id: str, *, name: str, redirect_uris: list[str] | None = None, scopes: list[str] | None = None,
    ) -> tuple[OAuthClientModel, str]:
        client_id = f"gwc_{generate_raw_token(num_bytes=12)}"
        client_secret = generate_raw_token()
        client = OAuthClientModel(
            tenant_id=tenant_id, client_id=client_id, client_secret_hash=hash_token(client_secret), name=name,
            redirect_uris=redirect_uris or [], scopes=scopes or [], status=OAuthClientStatus.ACTIVE.value,
        )
        client = await self.repos.oauth_clients.add(client)
        return client, client_secret

    async def verify_client(self, client_id: str, client_secret: str) -> OAuthClientModel:
        client = await self.repos.oauth_clients.get_by_client_id(client_id)
        if client is None or client.client_secret_hash != hash_token(client_secret):
            raise OAuthClientNotFoundError("OAuth client credentials are invalid")
        if client.status != OAuthClientStatus.ACTIVE.value:
            raise OAuthClientNotFoundError(f"OAuth client '{client_id}' is not active")
        return client

    async def suspend_client(self, client_id: str) -> OAuthClientModel:
        client = await self._get_or_404(client_id)
        client.status = OAuthClientStatus.SUSPENDED.value
        return await self.repos.oauth_clients.update(client)

    async def revoke_client(self, client_id: str) -> OAuthClientModel:
        client = await self._get_or_404(client_id)
        client.status = OAuthClientStatus.REVOKED.value
        return await self.repos.oauth_clients.update(client)

    async def list_for_tenant(self, tenant_id: str) -> list[OAuthClientModel]:
        return await self.repos.oauth_clients.list_for_tenant(tenant_id)

    async def _get_or_404(self, client_id: str) -> OAuthClientModel:
        client = await self.repos.oauth_clients.get_by_client_id(client_id)
        if client is None:
            raise OAuthClientNotFoundError(f"OAuth client '{client_id}' not found")
        return client
