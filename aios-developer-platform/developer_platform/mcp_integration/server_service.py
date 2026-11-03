"""MCP server registry: register a server (stdio/http/sse transport,
opaque `endpoint_ref`), then track its connection state through a
simple field-based transition guarded directly here — the same
"guarded in-service" precedent used for CLI sessions and extension
registrations elsewhere in this platform, since there's no dedicated
domain entity for what is fundamentally a status field with a few
legal moves."""
from __future__ import annotations

from developer_platform.core.exceptions import McpError, NotFoundError
from developer_platform.domain.enums import McpServerStatus, McpTransport
from developer_platform.mcp_integration.transport import negotiate_protocol_version
from developer_platform.models.mcp import McpServerModel
from developer_platform.repositories.registry import RepositoryRegistry

_TRANSITIONS: dict[McpServerStatus, set[McpServerStatus]] = {
    McpServerStatus.REGISTERED: {McpServerStatus.CONNECTED, McpServerStatus.ERROR},
    McpServerStatus.CONNECTED: {McpServerStatus.DISCONNECTED, McpServerStatus.ERROR},
    McpServerStatus.DISCONNECTED: {McpServerStatus.CONNECTED, McpServerStatus.ERROR},
    McpServerStatus.ERROR: {McpServerStatus.CONNECTED, McpServerStatus.DISCONNECTED},
}


def _transition(server: McpServerModel, target: McpServerStatus) -> None:
    current = McpServerStatus(server.status)
    if target not in _TRANSITIONS.get(current, set()):
        raise McpError(f"MCP server '{server.id}' cannot move from {current.value} to {target.value}")
    server.status = target.value


class McpServerService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_server(
        self, tenant_id: str, *, name: str, transport: str = McpTransport.STDIO.value,
        endpoint_ref: str, protocol_version: str = "2024-11-05",
    ) -> McpServerModel:
        negotiate_protocol_version(protocol_version)
        existing = await self.repos.mcp_servers.get_by_name(tenant_id, name)
        if existing is not None:
            return existing
        server = McpServerModel(
            tenant_id=tenant_id, name=name, transport=transport, endpoint_ref=endpoint_ref,
            status=McpServerStatus.REGISTERED.value, protocol_version=protocol_version,
        )
        return await self.repos.mcp_servers.add(server)

    async def connect(self, tenant_id: str, server_id: str) -> McpServerModel:
        server = await self._get_or_404(tenant_id, server_id)
        _transition(server, McpServerStatus.CONNECTED)
        return await self.repos.mcp_servers.update(server)

    async def disconnect(self, tenant_id: str, server_id: str) -> McpServerModel:
        server = await self._get_or_404(tenant_id, server_id)
        _transition(server, McpServerStatus.DISCONNECTED)
        return await self.repos.mcp_servers.update(server)

    async def mark_error(self, tenant_id: str, server_id: str) -> McpServerModel:
        server = await self._get_or_404(tenant_id, server_id)
        _transition(server, McpServerStatus.ERROR)
        return await self.repos.mcp_servers.update(server)

    async def list_for_tenant(self, tenant_id: str) -> list[McpServerModel]:
        return await self.repos.mcp_servers.list_for_tenant(tenant_id)

    async def _get_or_404(self, tenant_id: str, server_id: str) -> McpServerModel:
        try:
            server = await self.repos.mcp_servers.get_or_404(server_id)
        except NotFoundError as exc:
            raise McpError(f"MCP server '{server_id}' not found") from exc
        if server.tenant_id != tenant_id:
            raise McpError(f"MCP server '{server_id}' not found for tenant '{tenant_id}'")
        return server
