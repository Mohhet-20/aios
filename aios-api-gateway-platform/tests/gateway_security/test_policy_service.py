from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import SecurityPolicyNotFoundError, ValidationError
from gateway_platform.gateway_security.policy_service import SecurityPolicyService

TENANT = "sec-policy-tenant"


@pytest.mark.asyncio
async def test_register_policy_idempotent_by_name_and_type(repos):
    service = SecurityPolicyService(repos)
    a = await service.register_policy(TENANT, name="default-ip-filter", policy_type="ip_filter")
    b = await service.register_policy(TENANT, name="default-ip-filter", policy_type="ip_filter", rules={"strict": True})
    assert a.id == b.id
    assert b.rules == {"strict": True}


@pytest.mark.asyncio
async def test_invalid_policy_type_rejected(repos):
    service = SecurityPolicyService(repos)
    with pytest.raises(ValidationError):
        await service.register_policy(TENANT, name="bad", policy_type="not_a_real_type")


@pytest.mark.asyncio
async def test_activate_deactivate(repos):
    service = SecurityPolicyService(repos)
    policy = await service.register_policy(TENANT, name="threat-policy", policy_type="threat_detection")
    deactivated = await service.deactivate_policy(TENANT, policy.id)
    assert deactivated.status == "inactive"
    reactivated = await service.activate_policy(TENANT, policy.id)
    assert reactivated.status == "active"


@pytest.mark.asyncio
async def test_list_for_tenant_filters_by_type(repos):
    service = SecurityPolicyService(repos)
    await service.register_policy(TENANT, name="geo-1", policy_type="geo_restriction")
    await service.register_policy(TENANT, name="bot-1", policy_type="bot_detection")
    geo_only = await service.list_for_tenant(TENANT, policy_type="geo_restriction")
    assert all(p.policy_type == "geo_restriction" for p in geo_only)
    assert len(geo_only) == 1


@pytest.mark.asyncio
async def test_not_found_for_other_tenant(repos):
    service = SecurityPolicyService(repos)
    policy = await service.register_policy(TENANT, name="rl-1", policy_type="rate_limit")
    with pytest.raises(SecurityPolicyNotFoundError):
        await service.deactivate_policy("other-tenant", policy.id)
