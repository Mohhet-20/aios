from __future__ import annotations

import pytest

from gateway_platform.api_management.api_key_service import ApiKeyService
from gateway_platform.api_management.quota_service import QuotaService
from gateway_platform.core.exceptions import QuotaExceededError
from gateway_platform.models.api_management import ApiUsageRecordModel

TENANT = "am-quota-tenant"


@pytest.mark.asyncio
async def test_quota_tracks_remaining(repos):
    key_service = ApiKeyService(repos)
    result = await key_service.issue_key(TENANT, name="quota-key", quota_per_day=3)
    quota = QuotaService(repos)
    assert await quota.remaining(result.api_key) == 3

    await repos.api_usage_records.add(
        ApiUsageRecordModel(tenant_id=TENANT, api_key_id=result.api_key.id, endpoint="/x", method="GET")
    )
    assert await quota.remaining(result.api_key) == 2


@pytest.mark.asyncio
async def test_quota_exceeded_raises(repos):
    key_service = ApiKeyService(repos)
    result = await key_service.issue_key(TENANT, name="quota-key-2", quota_per_day=1)
    quota = QuotaService(repos)
    await repos.api_usage_records.add(
        ApiUsageRecordModel(tenant_id=TENANT, api_key_id=result.api_key.id, endpoint="/x", method="GET")
    )
    with pytest.raises(QuotaExceededError):
        await quota.enforce(result.api_key)
