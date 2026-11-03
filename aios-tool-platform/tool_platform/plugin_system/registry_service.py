"""PluginRegistryService: publish/list/version a marketplace listing
(`PluginModel`) and its declared dependency edges. This is the "list
your extension on the marketplace" side; `installation_service.py` is
the "a workspace actually installs it" side — same Tool/ToolVersion-style
split, so a workspace's installed copy doesn't shift under it if the
publisher ships an update."""
from __future__ import annotations

from slugify import slugify

from tool_platform.core.exceptions import ValidationError
from tool_platform.models.plugin import PluginDependencyModel, PluginModel
from tool_platform.plugin_system.signing import sign_manifest
from tool_platform.plugin_system.versioning import satisfies
from tool_platform.repositories.registry import RepositoryRegistry


class PluginRegistryService:
    def __init__(self, repos: RepositoryRegistry, *, secret_key: str):
        self.repos = repos
        self._secret_key = secret_key

    async def publish_plugin(
        self, *, name: str, author: str, category: str, slug: str | None = None, description: str | None = None,
        tags: list[str] | None = None, organization_id: str | None = None, manifest: dict | None = None,
        version: str = "0.1.0",
    ) -> PluginModel:
        resolved_slug = slug or slugify(name)
        existing = await self.repos.plugins.get_by_slug(resolved_slug)
        if existing is not None:
            raise ValidationError(f"a plugin with slug '{resolved_slug}' already exists")

        manifest = manifest or {}
        checksum, signature = sign_manifest(manifest, secret_key=self._secret_key)
        return await self.repos.plugins.add(PluginModel(
            name=name, slug=resolved_slug, description=description, author=author, organization_id=organization_id,
            category=category, tags=tags or [], latest_version=version, status="published", manifest=manifest,
            is_signed=True, checksum=checksum, signature=signature,
        ))

    async def publish_new_version(self, plugin_id: str, *, version: str, manifest: dict | None = None) -> PluginModel:
        plugin = await self.repos.plugins.get_or_404(plugin_id)
        if manifest is not None:
            plugin.manifest = manifest
            plugin.checksum, plugin.signature = sign_manifest(manifest, secret_key=self._secret_key)
            plugin.is_signed = True
        plugin.latest_version = version
        return await self.repos.plugins.update(plugin)

    async def add_dependency(self, plugin_id: str, *, depends_on_plugin_id: str, version_constraint: str = "*") -> PluginDependencyModel:
        await self.repos.plugins.get_or_404(plugin_id)
        await self.repos.plugins.get_or_404(depends_on_plugin_id)
        if plugin_id == depends_on_plugin_id:
            raise ValidationError("a plugin cannot depend on itself")
        return await self.repos.plugin_dependencies.add(PluginDependencyModel(
            plugin_id=plugin_id, depends_on_plugin_id=depends_on_plugin_id, version_constraint=version_constraint,
        ))

    async def get_plugin(self, plugin_id: str) -> PluginModel:
        return await self.repos.plugins.get_or_404(plugin_id)

    async def deprecate_plugin(self, plugin_id: str) -> PluginModel:
        plugin = await self.repos.plugins.get_or_404(plugin_id)
        plugin.status = "deprecated"
        return await self.repos.plugins.update(plugin)

    async def suspend_plugin(self, plugin_id: str, *, reason: str) -> PluginModel:
        """A marketplace-operator action (e.g. a security issue was
        found) — suspended plugins drop out of marketplace search and
        cannot be newly installed, but existing installations are left
        alone (an operator uninstalling those is a separate, deliberate
        action, not an automatic side effect)."""
        plugin = await self.repos.plugins.get_or_404(plugin_id)
        plugin.status = "suspended"
        plugin.manifest = {**plugin.manifest, "suspension_reason": reason}
        return await self.repos.plugins.update(plugin)

    def check_version_dependency(self, installed_version: str, constraint: str) -> bool:
        return satisfies(installed_version, constraint)
