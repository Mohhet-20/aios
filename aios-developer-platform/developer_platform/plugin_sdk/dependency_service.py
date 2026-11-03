"""Plugin dependency tracking: a dependency edge points from a plugin
*version* to a depended-upon *plugin* (its currently published
version is what actually gets resolved, matching how a package
manager resolves a named dependency to a concrete version at install
time). `resolve_chain` walks the graph depth-first, rejecting cycles
and chains deeper than `plugin_max_dependency_depth` — a real
correctness concern once plugins can depend on plugins that depend on
other plugins."""
from __future__ import annotations

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import PluginDependencyError, PluginNotFoundError
from developer_platform.domain.enums import PluginVersionStatus
from developer_platform.models.plugins import PluginDependencyModel
from developer_platform.repositories.registry import RepositoryRegistry


class PluginDependencyService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def add_dependency(
        self, tenant_id: str, plugin_version_id: str, *, depends_on_plugin_id: str, version_constraint: str = "*",
    ) -> PluginDependencyModel:
        if depends_on_plugin_id == (await self._plugin_id_for_version(tenant_id, plugin_version_id)):
            raise PluginDependencyError("a plugin cannot depend on itself")
        record = PluginDependencyModel(
            tenant_id=tenant_id, plugin_version_id=plugin_version_id,
            depends_on_plugin_id=depends_on_plugin_id, version_constraint=version_constraint,
        )
        return await self.repos.plugin_dependencies.add(record)

    async def list_for_version(self, tenant_id: str, plugin_version_id: str) -> list[PluginDependencyModel]:
        return await self.repos.plugin_dependencies.list_for_version(tenant_id, plugin_version_id)

    async def resolve_chain(self, tenant_id: str, plugin_version_id: str) -> list[str]:
        """Returns the ordered list of plugin-version ids in the
        resolved dependency chain (excluding the root). Raises
        `PluginDependencyError` on a cycle or a chain deeper than
        `plugin_max_dependency_depth`."""
        resolved: list[str] = []
        visiting: set[str] = set()

        async def _walk(version_id: str, depth: int) -> None:
            if depth > self.settings.plugin_max_dependency_depth:
                raise PluginDependencyError(
                    f"dependency chain exceeds max depth of {self.settings.plugin_max_dependency_depth}"
                )
            if version_id in visiting:
                raise PluginDependencyError(f"circular dependency detected at plugin version '{version_id}'")
            visiting.add(version_id)

            for dep in await self.repos.plugin_dependencies.list_for_version(tenant_id, version_id):
                target_version = await self._latest_published_version(tenant_id, dep.depends_on_plugin_id)
                if target_version is None:
                    raise PluginDependencyError(
                        f"dependency '{dep.depends_on_plugin_id}' has no published version to resolve"
                    )
                resolved.append(target_version.id)
                await _walk(target_version.id, depth + 1)

            visiting.discard(version_id)

        await _walk(plugin_version_id, 1)
        return resolved

    async def _plugin_id_for_version(self, tenant_id: str, plugin_version_id: str) -> str:
        record = await self.repos.plugin_versions.get_or_404(plugin_version_id)
        if record.tenant_id != tenant_id:
            raise PluginNotFoundError(f"Plugin version '{plugin_version_id}' not found for tenant '{tenant_id}'")
        return record.plugin_id

    async def _latest_published_version(self, tenant_id: str, plugin_id: str):
        versions = await self.repos.plugin_versions.list_for_plugin(tenant_id, plugin_id)
        published = [v for v in versions if v.status == PluginVersionStatus.PUBLISHED.value]
        if not published:
            return None
        return max(published, key=lambda v: v.created_at)
