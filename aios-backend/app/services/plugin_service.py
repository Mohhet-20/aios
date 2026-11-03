"""PluginService — bridges the in-process `PluginRegistry` (what plugins
*could* be installed) with `PluginModel` (what's actually installed/enabled
per organization). Installing a plugin materializes its `provides_tools`
into `ToolModel` rows so agents can be granted access to them through the
normal `Agent.allowed_tool_ids` mechanism.
"""

from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.models.plugin import PluginModel, ToolModel
from app.plugins.registry import PluginRegistry
from app.repositories.plugin_repository import PluginRepository, ToolRepository


class PluginService:
    def __init__(self, repository: PluginRepository, tools: ToolRepository, registry: PluginRegistry):
        self.repository = repository
        self.tools = tools
        self.registry = registry

    def list_available(self):
        return self.registry.all()

    async def install(self, organization_id: str, plugin_manifest_id: str) -> PluginModel:
        manifest = self.registry.get(plugin_manifest_id)
        if manifest is None:
            raise NotFoundError(f"No plugin manifest registered with id '{plugin_manifest_id}'")

        plugin_row = PluginModel(
            organization_id=organization_id,
            name=manifest.name,
            category=manifest.category,
            version=manifest.version,
            enabled=True,
        )
        plugin_row = await self.repository.add(plugin_row)

        for tool_name in manifest.provides_tools:
            await self.tools.add(
                ToolModel(
                    organization_id=organization_id,
                    name=tool_name,
                    category=manifest.category,
                    side_effect="read_only",
                    verified=True,
                )
            )
        return plugin_row

    async def toggle(self, plugin_id: str, enabled: bool) -> PluginModel:
        plugin_row = await self.repository.get_or_404(plugin_id)
        plugin_row.enabled = enabled
        return await self.repository.update(plugin_row)

    async def list_installed(self, organization_id: str) -> list[PluginModel]:
        return await self.repository.list(organization_id=organization_id)
