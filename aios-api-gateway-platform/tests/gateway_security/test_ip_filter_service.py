from __future__ import annotations

import pytest

from gateway_platform.config.settings import Settings
from gateway_platform.core.exceptions import IpBlockedError
from gateway_platform.gateway_security.ip_filter_service import IpFilterService

TENANT = "sec-ip-tenant"


@pytest.mark.asyncio
async def test_deny_rule_blocks_matching_cidr(repos):
    service = IpFilterService(repos)
    await service.add_rule(TENANT, "policy-1", cidr="10.0.0.0/8", action="deny")
    with pytest.raises(IpBlockedError):
        await service.evaluate(TENANT, "policy-1", "10.1.2.3")


@pytest.mark.asyncio
async def test_allow_rule_permits_matching_cidr(repos):
    service = IpFilterService(repos)
    await service.add_rule(TENANT, "policy-2", cidr="192.168.1.0/24", action="allow")
    assert await service.evaluate(TENANT, "policy-2", "192.168.1.42") is True


@pytest.mark.asyncio
async def test_default_mode_allow_all_when_no_rule_matches(repos):
    settings = Settings(security_ip_filter_default_mode="allow_all")
    service = IpFilterService(repos, settings=settings)
    assert await service.evaluate(TENANT, "policy-3", "8.8.8.8") is True


@pytest.mark.asyncio
async def test_default_mode_deny_all_when_no_rule_matches(repos):
    settings = Settings(security_ip_filter_default_mode="deny_all")
    service = IpFilterService(repos, settings=settings)
    with pytest.raises(IpBlockedError):
        await service.evaluate(TENANT, "policy-4", "8.8.8.8")


@pytest.mark.asyncio
async def test_list_rules(repos):
    service = IpFilterService(repos)
    await service.add_rule(TENANT, "policy-5", cidr="172.16.0.0/12", action="deny")
    rules = await service.list_rules(TENANT, "policy-5")
    assert len(rules) == 1
