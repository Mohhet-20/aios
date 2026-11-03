from __future__ import annotations

import pytest

from gateway_platform.api_management.api_key_service import ApiKeyService
from gateway_platform.api_management.rate_limit_service import RateLimiterService
from gateway_platform.config.settings import Settings
from gateway_platform.core.exceptions import RateLimitExceededError

TENANT = "am-rl-tenant"


@pytest.mark.asyncio
async def test_enforce_allows_under_limit(repos):
    key_service = ApiKeyService(repos)
    result = await key_service.issue_key(TENANT, name="rl-key", rate_limit_per_minute=5)
    settings = Settings(security_rate_limit_burst_multiplier=1.0)
    limiter = RateLimiterService(repos, settings=settings)
    for _ in range(5):
        await limiter.check_and_record(result.api_key, endpoint="/x", method="GET")


@pytest.mark.asyncio
async def test_enforce_rejects_over_limit(repos):
    key_service = ApiKeyService(repos)
    result = await key_service.issue_key(TENANT, name="rl-key-2", rate_limit_per_minute=2)
    settings = Settings(security_rate_limit_burst_multiplier=1.0)
    limiter = RateLimiterService(repos, settings=settings)
    await limiter.check_and_record(result.api_key, endpoint="/x", method="GET")
    await limiter.check_and_record(result.api_key, endpoint="/x", method="GET")
    with pytest.raises(RateLimitExceededError):
        await limiter.check_and_record(result.api_key, endpoint="/x", method="GET")
