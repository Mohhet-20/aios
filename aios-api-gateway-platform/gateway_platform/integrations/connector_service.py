"""Connector catalog: one row per enterprise system type this
platform knows how to integrate with (the sixteen types the prompt
specifies — CRM through custom enterprise systems). `register_connector`
is a get-or-create by type, since the catalog entry for e.g. "slack"
only needs to exist once per tenant regardless of how many connections
a tenant later creates against it. This is a connector *catalog*, not
a live third-party API client — actually calling out to Slack/GitHub/
Salesforce/etc. is out of scope for this control plane, the same
disclosed boundary the Developer Platform's MCP integration module
drew around real wire-protocol implementations."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import ConnectorNotFoundError, UnsupportedConnectorTypeError
from gateway_platform.models.integrations import ConnectorModel
from gateway_platform.repositories.registry import RepositoryRegistry


class ConnectorService:
    """`register_connector` is a get-or-create keyed on `(tenant_id,
    connector_type)` — guarded with an in-process `asyncio.Lock` per
    key, the same commit-spanning-lock pattern used across every prior
    AIOS platform's own "upsert by identity" methods, since two
    concurrent callers registering the same connector type for the
    first time would otherwise both observe no existing row and both
    insert, producing a duplicate catalog entry."""

    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_supported(self, connector_type: str) -> None:
        if connector_type not in self.settings.integration_supported_connectors:
            raise UnsupportedConnectorTypeError(f"'{connector_type}' is not a supported connector type")

    async def register_connector(
        self, tenant_id: str, *, connector_type: str, name: str, config_schema: dict | None = None,
        sync_interval_minutes: int | None = None,
    ) -> ConnectorModel:
        self._assert_supported(connector_type)
        lock_key = f"{tenant_id}:{connector_type}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.connectors.get_by_type(tenant_id, connector_type)
            if existing is not None:
                return existing
            connector = ConnectorModel(
                tenant_id=tenant_id, connector_type=connector_type, name=name, config_schema=config_schema or {},
                sync_interval_minutes=sync_interval_minutes or self.settings.integration_sync_default_interval_minutes,
            )
            connector = await self.repos.connectors.add(connector)
            # Commit while still holding the lock — releasing it before the
            # row is durably committed would reopen the exact race the lock
            # exists to close, since a waiting caller's `get_by_type` would
            # run against a connection that can't yet see this insert.
            await self.repos.session.commit()
            return connector

    async def list_for_tenant(self, tenant_id: str) -> list[ConnectorModel]:
        return await self.repos.connectors.list_for_tenant(tenant_id)

    async def get_by_type(self, tenant_id: str, connector_type: str) -> ConnectorModel:
        connector = await self.repos.connectors.get_by_type(tenant_id, connector_type)
        if connector is None:
            raise ConnectorNotFoundError(f"no '{connector_type}' connector registered for tenant '{tenant_id}'")
        return connector
