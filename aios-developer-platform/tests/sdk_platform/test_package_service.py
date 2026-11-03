import uuid

import pytest

from developer_platform.core.exceptions import PackageVersionExistsError, UnsupportedLanguageError
from developer_platform.sdk_platform.package_service import SdkPackageService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_publish_version_creates_package_and_publishes(repos, db_session):
    tenant_id = _tid()
    service = SdkPackageService(repos)

    version = await service.publish_version(tenant_id, language="python", version="1.0.0", storage_uri="s3://sdks/python/1.0.0")
    await db_session.commit()

    assert version.status == "published"
    assert version.published_at is not None
    assert version.language == "python"

    versions = await service.list_versions(tenant_id, "python")
    assert len(versions) == 1


async def test_publish_duplicate_version_raises(repos, db_session):
    tenant_id = _tid()
    service = SdkPackageService(repos)
    await service.publish_version(tenant_id, language="typescript", version="2.0.0")
    await db_session.commit()

    with pytest.raises(PackageVersionExistsError):
        await service.publish_version(tenant_id, language="typescript", version="2.0.0")


async def test_deprecate_version(repos, db_session):
    tenant_id = _tid()
    service = SdkPackageService(repos)
    await service.publish_version(tenant_id, language="go", version="1.0.0")
    await db_session.commit()

    deprecated = await service.deprecate_version(tenant_id, language="go", version="1.0.0")
    await db_session.commit()

    assert deprecated.status == "deprecated"
    assert deprecated.deprecated_at is not None


async def test_unsupported_language_raises(repos, db_session):
    service = SdkPackageService(repos)
    with pytest.raises(UnsupportedLanguageError):
        await service.publish_version(_tid(), language="rust", version="1.0.0")
