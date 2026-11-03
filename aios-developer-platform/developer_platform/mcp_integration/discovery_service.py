"""Capability discovery: runs a transport adapter's `discover()` and
upserts the resulting resources/tools/prompts against what this
platform already knows about a server, matched by name. This is a
best-effort sync — an item that disappears from a later discovery
response is left in place rather than deleted, so a server's capability
history stays inspectable even if a discovery run is incomplete or a
server goes temporarily degraded."""
from __future__ import annotations

from dataclasses import dataclass

from developer_platform.mcp_integration.transport import McpDiscoveryResult, McpTransportAdapter
from developer_platform.models.mcp import McpPromptModel, McpResourceModel, McpToolModel
from developer_platform.repositories.registry import RepositoryRegistry


@dataclass
class DiscoverySyncResult:
    resources: list[McpResourceModel]
    tools: list[McpToolModel]
    prompts: list[McpPromptModel]


class McpDiscoveryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def discover_and_sync(self, tenant_id: str, server_id: str, adapter: McpTransportAdapter) -> DiscoverySyncResult:
        discovery: McpDiscoveryResult = await adapter.discover()

        existing_resources = {r.uri: r for r in await self.repos.mcp_resources.list_for_server(tenant_id, server_id)}
        resources: list[McpResourceModel] = []
        for item in discovery.resources:
            row = existing_resources.get(item["uri"])
            if row is None:
                row = McpResourceModel(
                    tenant_id=tenant_id, mcp_server_id=server_id, uri=item["uri"],
                    name=item.get("name", item["uri"]), mime_type=item.get("mime_type"),
                )
                row = await self.repos.mcp_resources.add(row)
            else:
                row.name = item.get("name", row.name)
                row.mime_type = item.get("mime_type", row.mime_type)
                row = await self.repos.mcp_resources.update(row)
            resources.append(row)

        existing_tools = {t.name: t for t in await self.repos.mcp_tools.list_for_server(tenant_id, server_id)}
        tools: list[McpToolModel] = []
        for item in discovery.tools:
            row = existing_tools.get(item["name"])
            if row is None:
                row = McpToolModel(
                    tenant_id=tenant_id, mcp_server_id=server_id, name=item["name"],
                    description=item.get("description", ""), input_schema=item.get("input_schema", {}),
                )
                row = await self.repos.mcp_tools.add(row)
            else:
                row.description = item.get("description", row.description)
                row.input_schema = item.get("input_schema", row.input_schema)
                row = await self.repos.mcp_tools.update(row)
            tools.append(row)

        existing_prompts = {p.name: p for p in await self.repos.mcp_prompts.list_for_server(tenant_id, server_id)}
        prompts: list[McpPromptModel] = []
        for item in discovery.prompts:
            row = existing_prompts.get(item["name"])
            if row is None:
                row = McpPromptModel(
                    tenant_id=tenant_id, mcp_server_id=server_id, name=item["name"],
                    arguments_schema=item.get("arguments_schema", {}),
                )
                row = await self.repos.mcp_prompts.add(row)
            else:
                row.arguments_schema = item.get("arguments_schema", row.arguments_schema)
                row = await self.repos.mcp_prompts.update(row)
            prompts.append(row)

        return DiscoverySyncResult(resources=resources, tools=tools, prompts=prompts)

    async def list_resources(self, tenant_id: str, server_id: str) -> list[McpResourceModel]:
        return await self.repos.mcp_resources.list_for_server(tenant_id, server_id)

    async def list_tools(self, tenant_id: str, server_id: str) -> list[McpToolModel]:
        return await self.repos.mcp_tools.list_for_server(tenant_id, server_id)

    async def list_prompts(self, tenant_id: str, server_id: str) -> list[McpPromptModel]:
        return await self.repos.mcp_prompts.list_for_server(tenant_id, server_id)
