import pytest

from identity_platform.core.exceptions import GeoRestrictedError, IpRestrictedError, RateLimitExceededError
from identity_platform.domain.enums import SecurityPolicyType
from identity_platform.security_platform.policy_service import SecurityPolicyService
from identity_platform.security_platform.rate_limit_service import RateLimitService
from identity_platform.security_platform.restriction_service import RestrictionService


def test_rate_limit_allows_within_limit_and_blocks_over():
    limiter = RateLimitService()
    for _ in range(3):
        assert limiter.check("test_scope", "user-1", limit=3) is True
    assert limiter.check("test_scope", "user-1", limit=3) is False


def test_rate_limit_enforce_raises():
    limiter = RateLimitService()
    limiter.enforce("test_scope", "user-2", limit=1)
    with pytest.raises(RateLimitExceededError):
        limiter.enforce("test_scope", "user-2", limit=1)


def test_rate_limit_reset_clears_state():
    limiter = RateLimitService()
    limiter.enforce("test_scope", "user-3", limit=1)
    limiter.reset("test_scope", "user-3")
    limiter.enforce("test_scope", "user-3", limit=1)  # should not raise


def test_rate_limit_scopes_are_independent():
    limiter = RateLimitService()
    limiter.enforce("scope_a", "same-id", limit=1)
    limiter.enforce("scope_b", "same-id", limit=1)  # different scope, should not raise


@pytest.mark.asyncio
async def test_ip_restriction_allow_mode(repos, db_session):
    policy_service = SecurityPolicyService(repos)
    await policy_service.set_policy("org-ip", SecurityPolicyType.IP_RESTRICTION, config={"mode": "allow", "values": ["10.0.0.0/8"]})
    await db_session.commit()

    restriction_service = RestrictionService(repos)
    assert await restriction_service.is_ip_allowed("org-ip", "10.1.2.3") is True
    assert await restriction_service.is_ip_allowed("org-ip", "192.168.1.1") is False

    with pytest.raises(IpRestrictedError):
        await restriction_service.enforce_ip("org-ip", "192.168.1.1")


@pytest.mark.asyncio
async def test_ip_restriction_deny_mode(repos, db_session):
    policy_service = SecurityPolicyService(repos)
    await policy_service.set_policy("org-ip-deny", SecurityPolicyType.IP_RESTRICTION, config={"mode": "deny", "values": ["1.2.3.4/32"]})
    await db_session.commit()

    restriction_service = RestrictionService(repos)
    assert await restriction_service.is_ip_allowed("org-ip-deny", "1.2.3.4") is False
    assert await restriction_service.is_ip_allowed("org-ip-deny", "8.8.8.8") is True


@pytest.mark.asyncio
async def test_no_ip_policy_means_unrestricted(repos, db_session):
    restriction_service = RestrictionService(repos)
    assert await restriction_service.is_ip_allowed("org-no-policy", "1.2.3.4") is True


@pytest.mark.asyncio
async def test_geo_restriction_deny_mode(repos, db_session):
    policy_service = SecurityPolicyService(repos)
    await policy_service.set_policy("org-geo", SecurityPolicyType.GEO_RESTRICTION, config={"mode": "deny", "values": ["KP"]})
    await db_session.commit()

    restriction_service = RestrictionService(repos)
    assert await restriction_service.is_country_allowed("org-geo", "US") is True
    assert await restriction_service.is_country_allowed("org-geo", "kp") is False

    with pytest.raises(GeoRestrictedError):
        await restriction_service.enforce_country("org-geo", "KP")
