"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every prior AIOS
platform. This platform has three commit-spanning-lock check-then-act
sequences (see each service's module docstring):
`PluginLifecycleService.register_plugin` (get-or-create by plugin
name), `PackageRegistryService.register_package` /
`.publish_version` (get-or-create by package identity, check-then-
insert by version), and `DeveloperRbacService.grant_role` (upsert by
principal/scope). Each test below proves the per-key `asyncio.Lock`
actually prevents the race a naive "check then write" sequence would
produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from developer_platform.core.exceptions import PackageVersionExistsError
from developer_platform.database.session import session_scope
from developer_platform.dev_security.rbac_service import DeveloperRbacService
from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.registry_platform.package_service import PackageRegistryService
from developer_platform.repositories.registry import RepositoryRegistry

TENANT = "stress-tenant"


async def _register_plugin_once() -> str:
    plugin_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = PluginLifecycleService(repos)
        plugin = await service.register_plugin(TENANT, name="stress-plugin", category="tool")
        plugin_id = plugin.id
    return plugin_id


@pytest.mark.asyncio
async def test_concurrent_register_plugin_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_plugin_once() for _ in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # plugin row (same id) rather than each creating its own — this is
    # exactly the bug an unlocked "check existing, then insert"
    # sequence would produce under real concurrency.
    assert len(set(results)) == 1

    plugins = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        plugins = await repos.plugins.list_for_tenant(TENANT)
    assert sum(1 for p in plugins if p.name == "stress-plugin") == 1


async def _register_package_once() -> str:
    package_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = PackageRegistryService(repos)
        package = await service.register_package(TENANT, name="stress-pkg", package_type="sdk")
        package_id = package.id
    return package_id


@pytest.mark.asyncio
async def test_concurrent_register_package_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_package_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    packages = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        packages = await repos.registry_packages.list_by_type(TENANT, "sdk")
    assert sum(1 for p in packages if p.name == "stress-pkg") == 1


async def _publish_version_once(package_id: str) -> object:
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = PackageRegistryService(repos)
        return await service.publish_version(TENANT, package_id, version="1.0.0", language="python")
    return None


@pytest.mark.asyncio
async def test_concurrent_publish_same_version_rejects_all_but_one():
    package_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = PackageRegistryService(repos)
        package = await service.register_package(TENANT, name="stress-pkg-versioned", package_type="sdk")
        package_id = package.id

    n_callers = 8
    results = await asyncio.gather(*[_publish_version_once(package_id) for _ in range(n_callers)], return_exceptions=True)

    succeeded = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]

    # Only the first publish to acquire the lock should have gone
    # through; every other concurrent caller must observe the
    # now-committed version row and be rejected — proving the lock
    # closed the window a naive "check then insert" sequence would
    # otherwise leave open (which would raise a raw IntegrityError
    # from a DB-level unique constraint instead of the friendly
    # `PackageVersionExistsError`, or worse, silently duplicate rows
    # on a backend without one).
    assert len(succeeded) == 1
    assert len(failed) == n_callers - 1
    assert all(isinstance(exc, PackageVersionExistsError) for exc in failed)

    versions = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        versions = await repos.registry_package_versions.list_for_package(TENANT, package_id)
    assert len(versions) == 1


async def _grant_role_once(role: str) -> str:
    binding_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = DeveloperRbacService(repos)
        binding = await service.grant_role(TENANT, principal_id="stress-dev", role=role)
        binding_id = binding.id
    return binding_id


@pytest.mark.asyncio
async def test_concurrent_grant_role_upserts_a_single_binding():
    n_callers = 10
    results = await asyncio.gather(*[_grant_role_once("operator") for _ in range(n_callers)])

    # Every concurrent grant should have been serialized onto the SAME
    # binding row (same id) — an unlocked "check existing, then
    # insert-or-update" sequence would let two callers both see no
    # existing binding and both insert, leaving two competing rows for
    # the same principal/scope.
    assert len(set(results)) == 1

    bindings = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        bindings = await repos.developer_role_bindings.list_for_principal(TENANT, "stress-dev")
    assert len(bindings) == 1
    assert bindings[0].role == "operator"
