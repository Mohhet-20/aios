"""Daily quota enforcement — a coarser, longer-window sibling to the
rate limiter: counts committed usage records since midnight UTC
against the key's `quota_per_day`. Deliberately a separate check from
`RateLimiterService.enforce()` so quota and per-minute rate limiting
can be reasoned about (and tested) independently, even though both
read the same `gw_api_usage_records` table."""
from __future__ import annotations

from datetime import datetime

from gateway_platform.core.exceptions import QuotaExceededError
from gateway_platform.models.api_management import ApiKeyModel
from gateway_platform.repositories.registry import RepositoryRegistry
from gateway_platform.clock import utc_now


def _start_of_day_utc() -> datetime:
    now = utc_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class QuotaService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def enforce(self, api_key: ApiKeyModel) -> None:
        count = await self.repos.api_usage_records.count_since(api_key.tenant_id, api_key.id, _start_of_day_utc())
        if count >= api_key.quota_per_day:
            raise QuotaExceededError(f"API key '{api_key.id}' exceeded its daily quota of {api_key.quota_per_day} requests")

    async def remaining(self, api_key: ApiKeyModel) -> int:
        count = await self.repos.api_usage_records.count_since(api_key.tenant_id, api_key.id, _start_of_day_utc())
        return max(0, api_key.quota_per_day - count)
