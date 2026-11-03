from __future__ import annotations

import pytest

from gateway_platform.api_management.version_service import ApiVersionService
from gateway_platform.core.exceptions import ApiVersionNotFoundError, ApiVersionRetiredError, ValidationError


@pytest.mark.asyncio
async def test_register_deprecate_retire_lifecycle(repos):
    service = ApiVersionService(repos)
    version = await service.register_version("2026-01-01", notes="initial")
    assert version.status == "active"

    deprecated = await service.deprecate_version("2026-01-01")
    assert deprecated.status == "deprecated"
    assert deprecated.sunset_at is not None

    usable = await service.assert_usable("2026-01-01")
    assert usable.status == "deprecated"

    retired = await service.retire_version("2026-01-01")
    assert retired.status == "retired"
    with pytest.raises(ApiVersionRetiredError):
        await service.assert_usable("2026-01-01")


@pytest.mark.asyncio
async def test_duplicate_registration_rejected(repos):
    service = ApiVersionService(repos)
    await service.register_version("2026-02-01")
    with pytest.raises(ValidationError):
        await service.register_version("2026-02-01")


@pytest.mark.asyncio
async def test_unknown_version_raises_not_found(repos):
    service = ApiVersionService(repos)
    with pytest.raises(ApiVersionNotFoundError):
        await service.assert_usable("does-not-exist")


@pytest.mark.asyncio
async def test_list_versions(repos):
    service = ApiVersionService(repos)
    await service.register_version("2026-03-01")
    versions = await service.list_versions()
    assert any(v.version == "2026-03-01" for v in versions)
