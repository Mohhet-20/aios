import uuid

import pytest

from developer_platform.core.exceptions import PackageNotFoundError, PackageVersionExistsError, ValidationError
from developer_platform.registry_platform.package_service import PackageRegistryService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_register_package_is_idempotent(repos, db_session):
    tenant_id = _tid()
    service = PackageRegistryService(repos)
    first = await service.register_package(tenant_id, name="starter-agent", package_type="agent_template")
    await db_session.commit()
    second = await service.register_package(tenant_id, name="starter-agent", package_type="agent_template")
    await db_session.commit()
    assert first.id == second.id


async def test_invalid_package_type_raises(repos, db_session):
    service = PackageRegistryService(repos)
    with pytest.raises(ValidationError):
        await service.register_package(_tid(), name="x", package_type="not-a-type")


async def test_publish_version_transitions_to_published(repos, db_session):
    tenant_id = _tid()
    service = PackageRegistryService(repos)
    package = await service.register_package(tenant_id, name="rag-workflow", package_type="workflow_template")
    await db_session.commit()

    version = await service.publish_version(tenant_id, package.id, version="1.0.0", storage_uri="pkg://rag/1.0.0")
    await db_session.commit()
    assert version.status == "published"
    assert version.published_at is not None


async def test_publish_duplicate_version_raises(repos, db_session):
    tenant_id = _tid()
    service = PackageRegistryService(repos)
    package = await service.register_package(tenant_id, name="support-prompt", package_type="prompt_template")
    await db_session.commit()
    await service.publish_version(tenant_id, package.id, version="1.0.0")
    await db_session.commit()

    with pytest.raises(PackageVersionExistsError):
        await service.publish_version(tenant_id, package.id, version="1.0.0")


async def test_deprecate_version_returns_removal_recommendation(repos, db_session):
    tenant_id = _tid()
    service = PackageRegistryService(repos)
    package = await service.register_package(tenant_id, name="legacy-plugin-pkg", package_type="plugin")
    await db_session.commit()
    await service.publish_version(tenant_id, package.id, version="1.0.0")
    await db_session.commit()

    result = await service.deprecate_version(tenant_id, package.id, version="1.0.0")
    await db_session.commit()
    assert result.version.status == "deprecated"
    assert result.version.deprecated_at is not None
    assert result.recommended_removal_at > result.version.deprecated_at


async def test_get_version_not_found_raises(repos, db_session):
    tenant_id = _tid()
    service = PackageRegistryService(repos)
    package = await service.register_package(tenant_id, name="empty-pkg", package_type="sdk")
    await db_session.commit()
    with pytest.raises(PackageNotFoundError):
        await service.get_version(tenant_id, package.id, "9.9.9")


async def test_list_versions_and_by_type(repos, db_session):
    tenant_id = _tid()
    service = PackageRegistryService(repos)
    package = await service.register_package(tenant_id, name="multi-version-pkg", package_type="workflow_template")
    await db_session.commit()
    await service.publish_version(tenant_id, package.id, version="1.0.0")
    await service.publish_version(tenant_id, package.id, version="2.0.0")
    await db_session.commit()

    versions = await service.list_versions(tenant_id, package.id)
    assert {v.version for v in versions} == {"1.0.0", "2.0.0"}

    by_type = await service.list_by_type(tenant_id, "workflow_template")
    assert package.id in [p.id for p in by_type]
