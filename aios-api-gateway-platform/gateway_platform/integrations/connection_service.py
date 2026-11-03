"""Integration connections: an actual per-tenant instance of a
connector (e.g. "our team's Slack workspace"), guarded through
pending -> connected/error -> connected/disconnected. Consistent with
this platform's "own the pointer, not the data" posture,
`credentials_ref` is always an opaque reference — this service never
accepts or stores a raw credential."""
from __future__ import annotations

from gateway_platform.core.exceptions import ConnectionNotFoundError
from gateway_platform.database.base import utcnow
from gateway_platform.domain.enums import ConnectionStatus
from gateway_platform.integrations.mappers import apply_connection_domain_to_model, connection_to_domain
from gateway_platform.models.integrations import IntegrationConnectionModel
from gateway_platform.repositories.registry import RepositoryRegistry


class IntegrationConnectionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_connection(
        self, tenant_id: str, connector_id: str, *, name: str, credentials_ref: str | None = None, config: dict | None = None,
    ) -> IntegrationConnectionModel:
        connection = IntegrationConnectionModel(
            tenant_id=tenant_id, connector_id=connector_id, name=name, status=ConnectionStatus.PENDING.value,
            credentials_ref=credentials_ref, config=config or {},
        )
        return await self.repos.integration_connections.add(connection)

    async def mark_connected(self, tenant_id: str, connection_id: str) -> IntegrationConnectionModel:
        connection = await self._get_or_404(tenant_id, connection_id)
        entity = connection_to_domain(connection)
        entity.connect()
        apply_connection_domain_to_model(entity, connection)
        connection.last_sync_at = utcnow()
        return await self.repos.integration_connections.update(connection)

    async def mark_error(self, tenant_id: str, connection_id: str) -> IntegrationConnectionModel:
        connection = await self._get_or_404(tenant_id, connection_id)
        entity = connection_to_domain(connection)
        entity.error()
        apply_connection_domain_to_model(entity, connection)
        return await self.repos.integration_connections.update(connection)

    async def disconnect(self, tenant_id: str, connection_id: str) -> IntegrationConnectionModel:
        connection = await self._get_or_404(tenant_id, connection_id)
        entity = connection_to_domain(connection)
        entity.disconnect()
        apply_connection_domain_to_model(entity, connection)
        return await self.repos.integration_connections.update(connection)

    async def record_sync(self, tenant_id: str, connection_id: str) -> IntegrationConnectionModel:
        connection = await self._get_or_404(tenant_id, connection_id)
        connection.last_sync_at = utcnow()
        return await self.repos.integration_connections.update(connection)

    async def list_for_connector(self, tenant_id: str, connector_id: str) -> list[IntegrationConnectionModel]:
        return await self.repos.integration_connections.list_for_connector(tenant_id, connector_id)

    async def list_for_tenant(self, tenant_id: str) -> list[IntegrationConnectionModel]:
        return await self.repos.integration_connections.list_for_tenant(tenant_id)

    async def _get_or_404(self, tenant_id: str, connection_id: str) -> IntegrationConnectionModel:
        connection = await self.repos.integration_connections.get_or_404(connection_id)
        if connection.tenant_id != tenant_id:
            raise ConnectionNotFoundError(f"connection '{connection_id}' not found for tenant '{tenant_id}'")
        return connection
