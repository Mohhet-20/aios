"""Forward compatibility with the Model Context Protocol (MCP) tool
format. MCP tool specs look like `{"name": ..., "description": ...,
"inputSchema": {...}}` — structurally almost identical to our
ToolDefinition (`parameters` vs `inputSchema`), so bridging is a field
rename, not a redesign. When the platform adds a real MCP client, it
registers each MCP server's tools through `from_mcp_tool_spec` and routes
`ToolExecutor` calls to the MCP server instead of a local handler — the
tool-calling contract the model sees (ToolCall/ToolResult) never changes.
"""
from __future__ import annotations

from typing import Any

from ai_core.schemas.enums import ToolSideEffect
from ai_core.schemas.tools import ToolDefinition


def from_mcp_tool_spec(spec: dict[str, Any]) -> ToolDefinition:
    return ToolDefinition(
        name=spec["name"],
        description=spec.get("description", ""),
        parameters=spec.get("inputSchema", {"type": "object", "properties": {}, "required": []}),
        side_effect=ToolSideEffect.EXTERNAL,
    )


def to_mcp_tool_spec(tool: ToolDefinition) -> dict[str, Any]:
    return {"name": tool.name, "description": tool.description, "inputSchema": tool.parameters}
