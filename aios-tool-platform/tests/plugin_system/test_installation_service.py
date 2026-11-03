import pytest

from tool_platform.core.exceptions import PluginDependencyError, PluginIsolationError, PluginSignatureError, ValidationError
from tool_platform.domain.enums import PluginInstallationStatus


@pytest.mark.asyncio
async def test_install_signed_plugin_succeeds(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Slack Connector", author="Acme", category="slack", manifest={"capabilities": ["network_access"]})
    installation = await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    assert installation.status == PluginInstallationStatus.INSTALLED.value
    assert installation.installed_version == plugin.latest_version


@pytest.mark.asyncio
async def test_install_increments_install_count(registry_service, installation_service, workspace, repos):
    plugin = await registry_service.publish_plugin(name="Slack Connector", author="Acme", category="slack")
    await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    refreshed = await repos.plugins.get_or_404(plugin.id)
    assert refreshed.install_count == 1


@pytest.mark.asyncio
async def test_install_rejects_unpublished_plugin(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Draft Plugin", author="Acme", category="custom")
    await registry_service.suspend_plugin(plugin.id, reason="wip")
    with pytest.raises(ValidationError):
        await installation_service.install(workspace.id, plugin.id, installed_by="u1")


@pytest.mark.asyncio
async def test_install_rejects_tampered_manifest(registry_service, installation_service, workspace, repos):
    plugin = await registry_service.publish_plugin(name="Tampered Plugin", author="Acme", category="custom", manifest={"capabilities": []})
    # Simulate tampering: manifest changed without re-signing.
    plugin.manifest = {"capabilities": ["network_access"]}
    await repos.plugins.update(plugin)
    with pytest.raises(PluginSignatureError):
        await installation_service.install(workspace.id, plugin.id, installed_by="u1")


@pytest.mark.asyncio
async def test_install_requires_signature_when_configured(installation_service, workspace, repos):
    from tool_platform.models.plugin import PluginModel
    unsigned = await repos.plugins.add(PluginModel(name="Unsigned", slug="unsigned", author="Acme", category="custom", status="published", is_signed=False))
    with pytest.raises(PluginSignatureError):
        await installation_service.install(workspace.id, unsigned.id, installed_by="u1")


@pytest.mark.asyncio
async def test_install_allows_unsigned_when_signature_not_required(installation_service_unsigned_ok, workspace, repos):
    from tool_platform.models.plugin import PluginModel
    unsigned = await repos.plugins.add(PluginModel(name="Unsigned OK", slug="unsigned-ok", author="Acme", category="custom", status="published", is_signed=False))
    installation = await installation_service_unsigned_ok.install(workspace.id, unsigned.id, installed_by="u1")
    assert installation.status == "installed"


@pytest.mark.asyncio
async def test_install_twice_in_same_workspace_rejected(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Once Only", author="Acme", category="custom")
    await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    with pytest.raises(ValidationError):
        await installation_service.install(workspace.id, plugin.id, installed_by="u1")


@pytest.mark.asyncio
async def test_install_missing_dependency_rejected(registry_service, installation_service, workspace):
    base = await registry_service.publish_plugin(name="Base Plugin", author="Acme", category="custom")
    dependent = await registry_service.publish_plugin(name="Dependent Plugin", author="Acme", category="custom")
    await registry_service.add_dependency(dependent.id, depends_on_plugin_id=base.id, version_constraint=">=1.0.0")

    with pytest.raises(PluginDependencyError):
        await installation_service.install(workspace.id, dependent.id, installed_by="u1")


@pytest.mark.asyncio
async def test_install_satisfied_dependency_succeeds(registry_service, installation_service, workspace):
    base = await registry_service.publish_plugin(name="Base Plugin 2", author="Acme", category="custom", version="1.5.0")
    dependent = await registry_service.publish_plugin(name="Dependent Plugin 2", author="Acme", category="custom")
    await registry_service.add_dependency(dependent.id, depends_on_plugin_id=base.id, version_constraint=">=1.0.0")

    await installation_service.install(workspace.id, base.id, installed_by="u1")
    installation = await installation_service.install(workspace.id, dependent.id, installed_by="u1")
    assert installation.status == "installed"


@pytest.mark.asyncio
async def test_install_unsatisfied_version_constraint_rejected(registry_service, installation_service, workspace):
    base = await registry_service.publish_plugin(name="Base Plugin 3", author="Acme", category="custom", version="1.0.0")
    dependent = await registry_service.publish_plugin(name="Dependent Plugin 3", author="Acme", category="custom")
    await registry_service.add_dependency(dependent.id, depends_on_plugin_id=base.id, version_constraint=">=2.0.0")

    await installation_service.install(workspace.id, base.id, installed_by="u1")
    with pytest.raises(PluginDependencyError):
        await installation_service.install(workspace.id, dependent.id, installed_by="u1")


@pytest.mark.asyncio
async def test_install_rejects_disallowed_capability(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(
        name="Sneaky Plugin", author="Acme", category="custom", manifest={"capabilities": ["code_execution"]},
    )
    with pytest.raises(PluginIsolationError):
        await installation_service.install(
            workspace.id, plugin.id, installed_by="u1", workspace_allowed_capabilities=["network_access"],
        )


@pytest.mark.asyncio
async def test_enable_disable_cycle(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Toggle Plugin", author="Acme", category="custom")
    installation = await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    enabled = await installation_service.enable(installation.id)
    assert enabled.status == "enabled"
    disabled = await installation_service.disable(enabled.id)
    assert disabled.status == "disabled"


@pytest.mark.asyncio
async def test_update_cycle_preserves_enabled_state(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Updatable Plugin", author="Acme", category="custom", version="1.0.0")
    installation = await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    installation = await installation_service.enable(installation.id)

    await registry_service.publish_new_version(plugin.id, version="2.0.0")
    installation = await installation_service.begin_update(installation.id)
    assert installation.status == "updating"
    installation = await installation_service.complete_update(installation.id, new_version="2.0.0")
    assert installation.status == "enabled"
    assert installation.installed_version == "2.0.0"


@pytest.mark.asyncio
async def test_update_cycle_preserves_disabled_state(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Updatable Plugin 2", author="Acme", category="custom", version="1.0.0")
    installation = await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    # freshly installed = INSTALLED, not ENABLED or DISABLED — disable it first
    installation = await installation_service.enable(installation.id)
    installation = await installation_service.disable(installation.id)

    installation = await installation_service.begin_update(installation.id)
    installation = await installation_service.complete_update(installation.id, new_version="2.0.0")
    assert installation.status == "disabled"


@pytest.mark.asyncio
async def test_failed_update_preserves_old_version(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Flaky Plugin", author="Acme", category="custom", version="1.0.0")
    installation = await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    installation = await installation_service.begin_update(installation.id)
    installation = await installation_service.fail_update(installation.id, error_message="checksum mismatch")
    assert installation.status == "failed"
    assert installation.installed_version == "1.0.0"


@pytest.mark.asyncio
async def test_uninstall(registry_service, installation_service, workspace):
    plugin = await registry_service.publish_plugin(name="Removable Plugin", author="Acme", category="custom")
    installation = await installation_service.install(workspace.id, plugin.id, installed_by="u1")
    uninstalled = await installation_service.uninstall(installation.id)
    assert uninstalled.status == "uninstalled"
