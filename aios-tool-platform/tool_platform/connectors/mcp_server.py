"""McpServerHandler: a real, working reference implementation of "call a
tool on a remote MCP-shaped server over HTTP" — a plain JSON-RPC-style
POST (`{"method": ..., "params": ...}` -> the server's JSON response).
Real Model Context Protocol servers typically speak stdio or SSE
transports rather than a single HTTP POST; this connector is deliberately
the simplest transport that's genuinely implementable and testable
without an actual MCP server dependency, kept behind the same
`connector_key="mcp_server"` seam so swapping in a real MCP client
library later (stdio/SSE transport, capability negotiation, etc.) only
touches this one file — the tool/version data model, execution engine,
and every other connector are already agnostic to how MCP compatibility
gets implemented underneath."""
from __future__ import annotations

from typing import Any

import httpx

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class McpServerHandler(ConnectorHandler):
    def __init__(self, *, client: httpx.AsyncClient | None = None):
        self._client = client

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        server_url = ctx.config.get("server_url")
        method = ctx.input_data.get("method") or ctx.config.get("method")
        if not server_url:
            raise ToolExecutionError("mcp_server tool call requires a 'server_url' in config")
        if not method:
            raise ToolExecutionError("mcp_server tool call requires a 'method'")

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": ctx.input_data.get("params", {})}
        if self._client is not None:
            response = await self._client.post(server_url, json=payload)
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(server_url, json=payload)

        body = response.json()
        if "error" in body:
            raise ToolExecutionError(f"MCP server returned an error: {body['error']}")
        return {"result": body.get("result")}
