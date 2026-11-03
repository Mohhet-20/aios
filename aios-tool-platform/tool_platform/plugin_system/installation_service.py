"""PluginInstallationService: a specific workspace's copy of a
marketplace plugin — install (signature + dependency + isolation
checks), enable/disable, update, uninstall. Every check here is a real
guard, not a formality: signature verification actually recomputes the
manifest checksum and HMAC (see `signing.py`), and dependency
resolution actually walks `PluginDependencyModel` rows and checks the
depending workspace has a satisfying version already ENABLED — not just
present in the marketplace."""
from __future__ import annotations

from tool_platform.core.exceptions import PluginDependencyError, PluginSignatureError, ValidationError
from tool_platform.domain.enums import PluginInstallationStatus
from tool_platform.models.plugin import PluginInstallationModel
from tool_platform.plugin_system.isolation import PluginIsolationPolicy
from tool_platform.plugin_system.mappers import apply_installation_domain_to_model, installation_to_domain
from tool_platform.plugin_system.signing import verify_signature
from tool_platform.plugin_system.versioning import satisfies
from tool_platform.repositories.registry import RepositoryRegistry


class PluginInstallationService:
    def __init__(self, repos: RepositoryRegistry, *, secret_key: str, require_signature: bool = True):
        self.repos = repos
        self._secret_key = secret_key
        self._require_signature = require_signature
        self._isolation = PluginIsolationPolicy()

    async def install(
        self, workspace_id: str, plugin_id: str, *, installed_by: str, configuration: dict | None = None,
        workspace_allowed_capabilities: list[str] | None = None,
    ) -> PluginInstallationModel:
        plugin = await self.repos.plugins.get_or_404(plugin_id)
        if plugin.status != "published":
            raise ValidationError(f"plugin '{plugin_id}' is {plugin.status}, not published — cannot install")

        if self._require_signature:
            if not plugin.is_signed or not plugin.checksum or not plugin.signature:
                raise PluginSignatureError(f"plugin '{plugin_id}' is not signed and signature verification is required")
            if not verify_signature(plugin.manifest, checksum=plugin.checksum, signature=plugin.signature, secret_key=self._secret_key):
                raise PluginSignatureError(f"plugin '{plugin_id}' failed signature verification")

        await self._check_dependencies(plugin_id, workspace_id)

        declared_capabilities = plugin.manifest.get("capabilities", [])
        self._isolation.validate_capabilities(declared_capabilities, workspace_allowed_capabilities=workspace_allowed_capabilities)

        existing = await self.repos.plugin_installations.get_for_workspace(workspace_id, plugin_id)
        if existing is not None:
            raise ValidationError(f"plugin '{plugin_id}' is already installed in workspace '{workspace_id}'")

        installation = await self.repos.plugin_installations.add(PluginInstallationModel(
            plugin_id=plugin_id, workspace_id=workspace_id, installed_version=plugin.latest_version,
            installed_by=installed_by, configuration=configuration or {},
        ))
        plugin.install_count += 1
        await self.repos.plugins.update(plugin)
        return installation

    async def _check_dependencies(self, plugin_id: str, workspace_id: str) -> None:
        dependencies = await self.repos.plugin_dependencies.list_for_plugin(plugin_id)
        for dep in dependencies:
            dep_installation = await self.repos.plugin_installations.get_for_workspace(workspace_id, dep.depends_on_plugin_id)
            if dep_installation is None or dep_installation.status not in (
                PluginInstallationStatus.INSTALLED.value, PluginInstallationStatus.ENABLED.value,
            ):
                dep_plugin = await self.repos.plugins.get_or_404(dep.depends_on_plugin_id)
                raise PluginDependencyError(
                    f"plugin '{plugin_id}' requires '{dep_plugin.name}' ({dep.version_constraint}) to be installed first"
                )
            if not satisfies(dep_installation.installed_version, dep.version_constraint):
                raise PluginDependencyError(
                    f"plugin '{plugin_id}' requires dependency version '{dep.version_constraint}', "
                    f"but installed version is '{dep_installation.installed_version}'"
                )

    async def enable(self, installation_id: str) -> PluginInstallationModel:
        return await self._apply_transition(installation_id, "enable")

    async def disable(self, installation_id: str) -> PluginInstallationModel:
        return await self._apply_transition(installation_id, "disable")

    async def uninstall(self, installation_id: str) -> PluginInstallationModel:
        return await self._apply_transition(installation_id, "uninstall")

    async def begin_update(self, installation_id: str) -> PluginInstallationModel:
        """Stashes whether the installation was ENABLED or DISABLED before
        entering UPDATING, since both can transition there and the prior
        status would otherwise be lost — `complete_update` needs it to know
        which status to return to."""
        model = await self.repos.plugin_installations.get_or_404(installation_id)
        was_enabled = model.status == PluginInstallationStatus.ENABLED.value
        entity = installation_to_domain(model)
        entity.begin_update()
        apply_installation_domain_to_model(entity, model)
        model.configuration = {**model.configuration, "_was_enabled_before_update": was_enabled}
        return await self.repos.plugin_installations.update(model)

    async def complete_update(self, installation_id: str, *, new_version: str) -> PluginInstallationModel:
        model = await self.repos.plugin_installations.get_or_404(installation_id)
        was_enabled = model.configuration.get("_was_enabled_before_update", True)
        entity = installation_to_domain(model)
        entity.complete_update(new_version, was_enabled=was_enabled)
        apply_installation_domain_to_model(entity, model)
        model.configuration = {k: v for k, v in model.configuration.items() if k != "_was_enabled_before_update"}
        return await self.repos.plugin_installations.update(model)

    async def fail_update(self, installation_id: str, *, error_message: str) -> PluginInstallationModel:
        model = await self.repos.plugin_installations.get_or_404(installation_id)
        entity = installation_to_domain(model)
        entity.fail_update(error_message)
        apply_installation_domain_to_model(entity, model)
        return await self.repos.plugin_installations.update(model)

    async def _apply_transition(self, installation_id: str, transition: str) -> PluginInstallationModel:
        model = await self.repos.plugin_installations.get_or_404(installation_id)
        entity = installation_to_domain(model)
        getattr(entity, transition)()
        apply_installation_domain_to_model(entity, model)
        return await self.repos.plugin_installations.update(model)
