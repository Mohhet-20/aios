from __future__ import annotations

import pytest

from gateway_platform.config.settings import Settings
from gateway_platform.core.exceptions import GeoBlockedError
from gateway_platform.gateway_security.geo_filter_service import GeoFilterService

TENANT = "sec-geo-tenant"


@pytest.mark.asyncio
async def test_deny_rule_blocks_matching_country(repos):
    service = GeoFilterService(repos)
    await service.add_rule(TENANT, "policy-1", country_code="kp", action="deny")
    with pytest.raises(GeoBlockedError):
        await service.evaluate(TENANT, "policy-1", "KP")


@pytest.mark.asyncio
async def test_allow_rule_permits_matching_country(repos):
    service = GeoFilterService(repos)
    await service.add_rule(TENANT, "policy-2", country_code="US", action="allow")
    assert await service.evaluate(TENANT, "policy-2", "us") is True


@pytest.mark.asyncio
async def test_default_mode_deny_all(repos):
    settings = Settings(security_geo_restriction_default_mode="deny_all")
    service = GeoFilterService(repos, settings=settings)
    with pytest.raises(GeoBlockedError):
        await service.evaluate(TENANT, "policy-3", "FR")


@pytest.mark.asyncio
async def test_default_mode_allow_all(repos):
    settings = Settings(security_geo_restriction_default_mode="allow_all")
    service = GeoFilterService(repos, settings=settings)
    assert await service.evaluate(TENANT, "policy-4", "FR") is True
