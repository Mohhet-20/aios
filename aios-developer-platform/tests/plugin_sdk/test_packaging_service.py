import uuid


from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.plugin_sdk.manifest import scaffold_manifest
from developer_platform.plugin_sdk.packaging_service import PluginPackagingService, compute_package_checksum

def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_package_version_computes_checksum_and_flags_missing_entrypoint(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    packaging = PluginPackagingService(repos)

    plugin = await lifecycle.register_plugin(tenant_id, name="pkg-plugin", category="tool")
    await db_session.commit()
    manifest = scaffold_manifest(name="pkg-plugin", category="tool", entrypoint="main.py")
    version = await lifecycle.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await db_session.commit()

    packaged = await packaging.package_version(tenant_id, version.id, files={"README.md": b"hello"})
    await db_session.commit()
    assert "entrypoint 'main.py' not present in packaged files" in packaged.validation_errors
    assert "package" in packaged.manifest


async def test_package_version_with_entrypoint_present(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    packaging = PluginPackagingService(repos)

    plugin = await lifecycle.register_plugin(tenant_id, name="pkg-plugin-2", category="tool")
    await db_session.commit()
    manifest = scaffold_manifest(name="pkg-plugin-2", category="tool", entrypoint="main.py")
    version = await lifecycle.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await db_session.commit()

    files = {"main.py": b"print('hi')", "README.md": b"docs"}
    packaged = await packaging.package_version(tenant_id, version.id, files=files)
    await db_session.commit()

    assert packaged.manifest["package"]["checksum"] == compute_package_checksum(files)
    assert packaged.manifest["package"]["file_count"] == 2
    assert packaged.manifest["package"]["storage_uri"].startswith("pkg://")


def test_checksum_is_deterministic_and_order_independent():
    files_a = {"a.py": b"1", "b.py": b"2"}
    files_b = {"b.py": b"2", "a.py": b"1"}
    assert compute_package_checksum(files_a) == compute_package_checksum(files_b)
