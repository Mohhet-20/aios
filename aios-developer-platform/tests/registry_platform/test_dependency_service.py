import uuid

import pytest

from developer_platform.core.exceptions import PackageDeprecatedError, PackageNotFoundError
from developer_platform.registry_platform.dependency_service import PackageDependencyService
from developer_platform.registry_platform.package_service import PackageRegistryService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def _published(service: PackageRegistryService, tenant_id: str, name: str, package_type: str, db_session):
    package = await service.register_package(tenant_id, name=name, package_type=package_type)
    await db_session.commit()
    version = await service.publish_version(tenant_id, package.id, version="1.0.0")
    await db_session.commit()
    return package, version


async def test_resolve_dependencies_simple_chain(repos, db_session):
    tenant_id = _tid()
    packages = PackageRegistryService(repos)
    dependencies = PackageDependencyService(repos)

    base_pkg, base_version = await _published(packages, tenant_id, "base-tool", "sdk", db_session)
    top_pkg, top_version = await _published(packages, tenant_id, "top-agent", "agent_template", db_session)

    await dependencies.add_dependency(
        tenant_id, top_pkg.id, version=top_version.version, depends_on_name="base-tool", depends_on_type="sdk",
    )
    await db_session.commit()

    resolved = await dependencies.resolve_dependencies(tenant_id, top_pkg.id, version=top_version.version)
    assert len(resolved) == 1
    assert resolved[0].id == base_version.id


async def test_missing_dependency_package_raises(repos, db_session):
    tenant_id = _tid()
    packages = PackageRegistryService(repos)
    dependencies = PackageDependencyService(repos)
    pkg, version = await _published(packages, tenant_id, "lonely-agent", "agent_template", db_session)

    await dependencies.add_dependency(
        tenant_id, pkg.id, version=version.version, depends_on_name="does-not-exist", depends_on_type="sdk",
    )
    await db_session.commit()

    with pytest.raises(PackageNotFoundError):
        await dependencies.resolve_dependencies(tenant_id, pkg.id, version=version.version)


async def test_cycle_detected(repos, db_session):
    tenant_id = _tid()
    packages = PackageRegistryService(repos)
    dependencies = PackageDependencyService(repos)

    pkg_a, version_a = await _published(packages, tenant_id, "cycle-a", "workflow_template", db_session)
    pkg_b, version_b = await _published(packages, tenant_id, "cycle-b", "workflow_template", db_session)

    await dependencies.add_dependency(tenant_id, pkg_a.id, version=version_a.version, depends_on_name="cycle-b", depends_on_type="workflow_template")
    await dependencies.add_dependency(tenant_id, pkg_b.id, version=version_b.version, depends_on_name="cycle-a", depends_on_type="workflow_template")
    await db_session.commit()

    with pytest.raises(PackageDeprecatedError):
        await dependencies.resolve_dependencies(tenant_id, pkg_a.id, version=version_a.version)
