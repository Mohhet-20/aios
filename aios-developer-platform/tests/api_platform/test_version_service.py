import pytest

from developer_platform.api_platform.version_service import ApiVersionService
from developer_platform.core.exceptions import UnsupportedApiVersionError, ValidationError

pytestmark = pytest.mark.asyncio


async def test_register_deprecate_sunset_lifecycle(repos, db_session):
    service = ApiVersionService(repos)
    version = f"v-{id(service)}"

    registered = await service.register_version(version, notes="initial")
    await db_session.commit()
    assert registered.status == "active"

    with pytest.raises(ValidationError):
        await service.register_version(version)

    deprecated = await service.deprecate_version(version)
    await db_session.commit()
    assert deprecated.status == "deprecated"
    assert deprecated.sunset_at is not None

    usable = await service.assert_usable(version)
    assert usable.status == "deprecated"

    sunset = await service.sunset_version(version)
    await db_session.commit()
    assert sunset.status == "sunset"

    with pytest.raises(UnsupportedApiVersionError):
        await service.assert_usable(version)


async def test_assert_usable_unknown_version_raises(repos, db_session):
    service = ApiVersionService(repos)
    with pytest.raises(UnsupportedApiVersionError):
        await service.assert_usable("v-does-not-exist")
