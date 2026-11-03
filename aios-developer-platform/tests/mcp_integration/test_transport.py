import pytest

from developer_platform.core.exceptions import McpError
from developer_platform.mcp_integration.transport import (
    McpDiscoveryResult,
    StaticTransportAdapter,
    negotiate_protocol_version,
)

@pytest.mark.asyncio
async def test_static_adapter_returns_supplied_discovery():
    discovery = McpDiscoveryResult(resources=[{"uri": "file:///a"}], tools=[], prompts=[])
    adapter = StaticTransportAdapter(discovery)
    result = await adapter.discover()
    assert result.resources == [{"uri": "file:///a"}]


def test_negotiate_known_version():
    assert negotiate_protocol_version("2024-11-05") == "2024-11-05"


def test_negotiate_unknown_version_raises():
    with pytest.raises(McpError):
        negotiate_protocol_version("1999-01-01")
