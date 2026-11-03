"""MCP transport abstraction. This platform is a control plane that
tracks MCP servers, sessions, and discovered capabilities — it does
not itself speak the wire protocol over a real stdio/HTTP/SSE
transport. `McpTransportAdapter` is the seam a real transport
implementation plugs into: given a server's `endpoint_ref`, discover
what resources/tools/prompts it exposes. `StaticTransportAdapter` is
the reference implementation used by tests and by admin-declared
servers (an operator who already knows a server's capabilities can
register them directly without a live connection).

`negotiate_protocol_version` exists for "future protocol evolution":
new MCP protocol versions can be added to `SUPPORTED_PROTOCOL_VERSIONS`
without touching any other module — every caller negotiates through
this one function."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from developer_platform.core.exceptions import McpError

SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26")


@dataclass
class McpDiscoveryResult:
    resources: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    prompts: list[dict] = field(default_factory=list)


class McpTransportAdapter(Protocol):
    async def discover(self) -> McpDiscoveryResult: ...


class StaticTransportAdapter:
    """Reference adapter returning a pre-supplied discovery payload —
    stands in for a live stdio/HTTP/SSE connection in tests and for
    servers whose capabilities are declared by an operator up front."""

    def __init__(self, discovery: McpDiscoveryResult):
        self._discovery = discovery

    async def discover(self) -> McpDiscoveryResult:
        return self._discovery


def negotiate_protocol_version(requested: str) -> str:
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    raise McpError(
        f"protocol version '{requested}' is not supported; supported versions: {list(SUPPORTED_PROTOCOL_VERSIONS)}"
    )
