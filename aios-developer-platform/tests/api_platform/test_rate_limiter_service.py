import uuid

import pytest

from developer_platform.api_platform.api_key_service import ApiKeyService
from developer_platform.api_platform.rate_limit_service import RateLimiterService
from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import RateLimitExceededError

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_rate_limiter_allows_under_limit_and_blocks_over(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, api_rate_limit_burst_multiplier=1.0)
    key_service = ApiKeyService(repos, settings=settings)
    limiter = RateLimiterService(repos, settings=settings)

    issued = await key_service.issue_key(tenant_id, name="limited", rate_limit_per_minute=3)
    await db_session.commit()
    api_key = issued.api_key

    for _ in range(3):
        await limiter.check_and_record(api_key, endpoint="/v1/ping", method="GET")
        await db_session.commit()

    with pytest.raises(RateLimitExceededError):
        await limiter.check_and_record(api_key, endpoint="/v1/ping", method="GET")


async def test_rate_limiter_records_usage(repos, db_session):
    tenant_id = _tid()
    key_service = ApiKeyService(repos)
    limiter = RateLimiterService(repos)
    issued = await key_service.issue_key(tenant_id, name="logged", rate_limit_per_minute=60)
    await db_session.commit()

    await limiter.record(tenant_id, api_key_id=issued.api_key.id, endpoint="/v1/things", method="POST", status_code=201)
    await db_session.commit()

    recent = await repos.api_usage_records.list_recent(tenant_id, api_key_id=issued.api_key.id)
    assert len(recent) == 1
    assert recent[0].status_code == 201
