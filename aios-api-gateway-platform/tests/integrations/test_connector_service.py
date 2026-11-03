from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import ConnectorNotFoundError, UnsupportedConnectorTypeError
from gateway_platform.integrations.connector_service import ConnectorService

TENANT = "int-tenant"


@pytest.mark.asyncio
async def test_register_connector_idempotent_by_type(repos):
    service = ConnectorService(repos)
    a = await service.register_connector(TENANT, connector_type="slack", name="Slack")
    b = await service.register_connector(TENANT, connector_type="slack", name="Slack (dup)")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_unsupported_connector_type_rejected(repos):
    service = ConnectorService(repos)
    with pytest.raises(UnsupportedConnectorTypeError):
        await service.register_connector(TENANT, connector_type="carrier_pigeon", name="Pigeon Post")


@pytest.mark.asyncio
async def test_get_by_type_not_found_raises(repos):
    service = ConnectorService(repos)
    with pytest.raises(ConnectorNotFoundError):
        await service.get_by_type(TENANT, "jira")


@pytest.mark.asyncio
async def test_list_for_tenant(repos):
    service = ConnectorService(repos)
    await service.register_connector(TENANT, connector_type="github", name="GitHub")
    connectors = await service.list_for_tenant(TENANT)
    assert any(c.connector_type == "github" for c in connectors)
