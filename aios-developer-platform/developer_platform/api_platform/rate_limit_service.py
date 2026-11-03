"""Sliding-window rate limiting + raw API usage logging. Enforcement
counts committed `dev_api_usage_records` rows for the key inside the
trailing 60-second window against `rate_limit_per_minute * burst
multiplier` — a real, DB-backed sliding window rather than an
in-process counter, so it stays correct across multiple app workers
sharing the same database."""
from __future__ import annotations

from datetime import timedelta

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import RateLimitExceededError
from developer_platform.database.base import utcnow
from developer_platform.models.api_platform import ApiKeyModel, ApiUsageRecordModel
from developer_platform.repositories.registry import RepositoryRegistry


class RateLimiterService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def enforce(self, api_key: ApiKeyModel) -> None:
        window_start = utcnow() - timedelta(seconds=60)
        count = await self.repos.api_usage_records.count_since(api_key.tenant_id, api_key.id, window_start)
        limit = int(api_key.rate_limit_per_minute * self.settings.api_rate_limit_burst_multiplier)
        if count >= limit:
            raise RateLimitExceededError(
                f"API key '{api_key.id}' exceeded {limit} requests/minute (burst-adjusted)"
            )

    async def record(
        self, tenant_id: str, *, api_key_id: str | None, endpoint: str, method: str,
        status_code: int, latency_ms: float = 0.0,
    ) -> ApiUsageRecordModel:
        record = ApiUsageRecordModel(
            tenant_id=tenant_id, api_key_id=api_key_id, endpoint=endpoint, method=method,
            status_code=status_code, latency_ms=latency_ms,
        )
        return await self.repos.api_usage_records.add(record)

    async def check_and_record(
        self, api_key: ApiKeyModel, *, endpoint: str, method: str, status_code: int = 200, latency_ms: float = 0.0,
    ) -> ApiUsageRecordModel:
        """Enforces the limit first, then logs the request — a caller
        that gets past `enforce()` without raising is the one whose
        request counts toward the next caller's window."""
        await self.enforce(api_key)
        return await self.record(
            api_key.tenant_id, api_key_id=api_key.id, endpoint=endpoint, method=method,
            status_code=status_code, latency_ms=latency_ms,
        )
