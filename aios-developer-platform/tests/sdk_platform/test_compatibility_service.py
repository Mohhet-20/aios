import uuid

import pytest

from developer_platform.core.exceptions import SdkVersionIncompatibleError, UnsupportedLanguageError, ValidationError
from developer_platform.sdk_platform.compatibility_service import SdkCompatibilityService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_register_and_check_compatible(repos, db_session):
    tenant_id = _tid()
    service = SdkCompatibilityService(repos)

    await service.register_entry(tenant_id, language="python", sdk_major_version=2, min_api_version="v1", max_api_version="v2")
    await db_session.commit()

    assert await service.check_compatible(tenant_id, language="python", sdk_major_version=2, api_version="v1") is True
    assert await service.check_compatible(tenant_id, language="python", sdk_major_version=2, api_version="v2") is True

    with pytest.raises(SdkVersionIncompatibleError):
        await service.check_compatible(tenant_id, language="python", sdk_major_version=2, api_version="v3")


async def test_register_duplicate_raises(repos, db_session):
    tenant_id = _tid()
    service = SdkCompatibilityService(repos)
    await service.register_entry(tenant_id, language="typescript", sdk_major_version=1, min_api_version="v1")
    await db_session.commit()

    with pytest.raises(ValidationError):
        await service.register_entry(tenant_id, language="typescript", sdk_major_version=1, min_api_version="v1")


async def test_unsupported_language_raises(repos, db_session):
    service = SdkCompatibilityService(repos)
    with pytest.raises(UnsupportedLanguageError):
        await service.register_entry(_tid(), language="cobol", sdk_major_version=1, min_api_version="v1")


async def test_mark_unsupported_then_check_raises(repos, db_session):
    tenant_id = _tid()
    service = SdkCompatibilityService(repos)
    await service.register_entry(tenant_id, language="go", sdk_major_version=1, min_api_version="v1")
    await db_session.commit()

    await service.mark_unsupported(tenant_id, language="go", sdk_major_version=1)
    await db_session.commit()

    with pytest.raises(SdkVersionIncompatibleError):
        await service.check_compatible(tenant_id, language="go", sdk_major_version=1, api_version="v1")


async def test_check_unknown_entry_raises(repos, db_session):
    service = SdkCompatibilityService(repos)
    with pytest.raises(SdkVersionIncompatibleError):
        await service.check_compatible(_tid(), language="java", sdk_major_version=9, api_version="v1")
