from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import InvalidTransitionError
from gateway_platform.integrations.connection_service import IntegrationConnectionService
from gateway_platform.integrations.connector_service import ConnectorService

TENANT = "int-conn-tenant"


@pytest.mark.asyncio
async def test_connection_lifecycle(repos):
    connectors = ConnectorService(repos)
    connector = await connectors.register_connector(TENANT, connector_type="jira", name="Jira")
    connections = IntegrationConnectionService(repos)
    connection = await connections.create_connection(TENANT, connector.id, name="Team Jira", credentials_ref="vault://x")
    assert connection.status == "pending"

    connected = await connections.mark_connected(TENANT, connection.id)
    assert connected.status == "connected"
    assert connected.last_sync_at is not None

    errored = await connections.mark_error(TENANT, connection.id)
    assert errored.status == "error"

    recovered = await connections.mark_connected(TENANT, connection.id)
    assert recovered.status == "connected"

    disconnected = await connections.disconnect(TENANT, connection.id)
    assert disconnected.status == "disconnected"
    with pytest.raises(InvalidTransitionError):
        await connections.mark_connected(TENANT, connection.id)


@pytest.mark.asyncio
async def test_list_for_connector_and_tenant(repos):
    connectors = ConnectorService(repos)
    connector = await connectors.register_connector(TENANT, connector_type="confluence", name="Confluence")
    connections = IntegrationConnectionService(repos)
    await connections.create_connection(TENANT, connector.id, name="Docs space")
    for_connector = await connections.list_for_connector(TENANT, connector.id)
    assert len(for_connector) == 1
    for_tenant = await connections.list_for_tenant(TENANT)
    assert len(for_tenant) >= 1
