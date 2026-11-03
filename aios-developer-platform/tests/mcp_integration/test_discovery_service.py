import uuid

import pytest

from developer_platform.mcp_integration.discovery_service import McpDiscoveryService
from developer_platform.mcp_integration.server_service import McpServerService
from developer_platform.mcp_integration.transport import McpDiscoveryResult, StaticTransportAdapter

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_discover_and_sync_creates_capabilities(repos, db_session):
    tenant_id = _tid()
    servers = McpServerService(repos)
    discovery = McpDiscoveryService(repos)

    server = await servers.register_server(tenant_id, name="rich-mcp", endpoint_ref="stdio://rich")
    await db_session.commit()

    payload = McpDiscoveryResult(
        resources=[{"uri": "file:///readme.md", "name": "readme", "mime_type": "text/markdown"}],
        tools=[{"name": "search", "description": "full text search", "input_schema": {"type": "object"}}],
        prompts=[{"name": "summarize", "arguments_schema": {"type": "object"}}],
    )
    adapter = StaticTransportAdapter(payload)

    result = await discovery.discover_and_sync(tenant_id, server.id, adapter)
    await db_session.commit()

    assert len(result.resources) == 1
    assert len(result.tools) == 1
    assert len(result.prompts) == 1
    assert result.tools[0].name == "search"


async def test_discover_and_sync_updates_existing_by_name(repos, db_session):
    tenant_id = _tid()
    servers = McpServerService(repos)
    discovery = McpDiscoveryService(repos)
    server = await servers.register_server(tenant_id, name="update-mcp", endpoint_ref="stdio://update")
    await db_session.commit()

    first_payload = McpDiscoveryResult(tools=[{"name": "search", "description": "v1"}])
    await discovery.discover_and_sync(tenant_id, server.id, StaticTransportAdapter(first_payload))
    await db_session.commit()

    second_payload = McpDiscoveryResult(tools=[{"name": "search", "description": "v2"}])
    result = await discovery.discover_and_sync(tenant_id, server.id, StaticTransportAdapter(second_payload))
    await db_session.commit()

    assert len(result.tools) == 1
    assert result.tools[0].description == "v2"

    all_tools = await discovery.list_tools(tenant_id, server.id)
    assert len(all_tools) == 1
