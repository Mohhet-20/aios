import uuid

import pytest

from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import PluginDependencyError
from developer_platform.plugin_sdk.dependency_service import PluginDependencyService
from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.plugin_sdk.manifest import scaffold_manifest

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def _published_plugin(lifecycle: PluginLifecycleService, tenant_id: str, name: str, db_session):
    plugin = await lifecycle.register_plugin(tenant_id, name=name, category="tool")
    await db_session.commit()
    manifest = scaffold_manifest(name=name, category="tool")
    version = await lifecycle.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await lifecycle.validate_version(tenant_id, version.id)
    await lifecycle.sign_version(tenant_id, version.id, signed_by="dev-1")
    await lifecycle.publish_version(tenant_id, version.id)
    await db_session.commit()
    return plugin, version


async def test_resolve_chain_simple(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    dependency = PluginDependencyService(repos)

    plugin_a, version_a = await _published_plugin(lifecycle, tenant_id, "dep-a", db_session)
    plugin_b, version_b = await _published_plugin(lifecycle, tenant_id, "dep-b", db_session)

    await dependency.add_dependency(tenant_id, version_b.id, depends_on_plugin_id=plugin_a.id)
    await db_session.commit()

    chain = await dependency.resolve_chain(tenant_id, version_b.id)
    assert chain == [version_a.id]


async def test_self_dependency_raises(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    dependency = PluginDependencyService(repos)
    plugin_a, version_a = await _published_plugin(lifecycle, tenant_id, "self-dep", db_session)

    with pytest.raises(PluginDependencyError):
        await dependency.add_dependency(tenant_id, version_a.id, depends_on_plugin_id=plugin_a.id)


async def test_cycle_detected(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    dependency = PluginDependencyService(repos)

    plugin_a, version_a = await _published_plugin(lifecycle, tenant_id, "cycle-a", db_session)
    plugin_b, version_b = await _published_plugin(lifecycle, tenant_id, "cycle-b", db_session)

    await dependency.add_dependency(tenant_id, version_a.id, depends_on_plugin_id=plugin_b.id)
    await dependency.add_dependency(tenant_id, version_b.id, depends_on_plugin_id=plugin_a.id)
    await db_session.commit()

    with pytest.raises(PluginDependencyError):
        await dependency.resolve_chain(tenant_id, version_a.id)


async def test_depth_limit_enforced(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, plugin_max_dependency_depth=2)
    lifecycle = PluginLifecycleService(repos)
    dependency = PluginDependencyService(repos, settings=settings)

    plugins = []
    versions = []
    for i in range(4):
        plugin, version = await _published_plugin(lifecycle, tenant_id, f"chain-{i}", db_session)
        plugins.append(plugin)
        versions.append(version)

    # chain-0 -> chain-1 -> chain-2 -> chain-3 (depth 3 > limit 2)
    for i in range(3):
        await dependency.add_dependency(tenant_id, versions[i].id, depends_on_plugin_id=plugins[i + 1].id)
    await db_session.commit()

    with pytest.raises(PluginDependencyError):
        await dependency.resolve_chain(tenant_id, versions[0].id)


async def test_dependency_on_unpublished_plugin_raises(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    dependency = PluginDependencyService(repos)

    plugin_a, version_a = await _published_plugin(lifecycle, tenant_id, "needs-unpublished", db_session)
    unpublished_plugin = await lifecycle.register_plugin(tenant_id, name="never-published", category="tool")
    await db_session.commit()

    await dependency.add_dependency(tenant_id, version_a.id, depends_on_plugin_id=unpublished_plugin.id)
    await db_session.commit()

    with pytest.raises(PluginDependencyError):
        await dependency.resolve_chain(tenant_id, version_a.id)
