"""Token/cost usage aggregation and rate/cost-limit enforcement. Tracks
input/output/cached tokens and cost per organization/user/project, rolled
up by day and by month, plus a per-scope sliding-window request-rate
limiter. In-memory by design (dev/single-instance); the aggregation keys
(scope, period, period_key) are exactly what a Postgres/Redis-backed
implementation would use as a composite key, so swapping storage is a
drop-in replacement of this one class.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from ai_core.config.settings import AICoreSettings
from ai_core.registry.model_registry import ModelRegistry
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest, UsageContext
from ai_core.schemas.responses import EmbeddingResponse, GenerationResponse
from ai_core.schemas.usage import TokenUsage
from ai_core.utils.exceptions import CostLimitExceededError, ModelNotFoundError, RateLimitExceededError


@dataclass
class UsageSummary:
    scope: str
    period: str
    period_key: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_cost_usd: float = 0.0
    request_count: int = 0


def _scopes_for(ctx: UsageContext) -> list[str]:
    scopes = ["global"]
    if ctx.organization_id:
        scopes.append(f"org:{ctx.organization_id}")
    if ctx.user_id:
        scopes.append(f"user:{ctx.user_id}")
    if ctx.project_id:
        scopes.append(f"project:{ctx.project_id}")
    return scopes


class UsageTracker:
    def __init__(self, *, settings: AICoreSettings | None = None, registry: ModelRegistry | None = None, cost_calculator=None):
        self.settings = settings or AICoreSettings()
        self.registry = registry
        self.cost_calculator = cost_calculator
        self._usage: dict[tuple[str, str, str], UsageSummary] = {}
        self._request_timestamps: dict[str, list[float]] = defaultdict(list)

    def _record(self, ctx: UsageContext, usage: TokenUsage, cost_usd: float) -> None:
        now = datetime.now(timezone.utc)
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")
        for scope in _scopes_for(ctx):
            for period, key in (("day", day_key), ("month", month_key)):
                summary = self._usage.setdefault((scope, period, key), UsageSummary(scope=scope, period=period, period_key=key))
                summary.input_tokens += usage.input_tokens
                summary.output_tokens += usage.output_tokens
                summary.cached_tokens += usage.cached_tokens
                summary.total_cost_usd += cost_usd
                summary.request_count += 1

    def record_generation(self, request: GenerationRequest, response: GenerationResponse) -> None:
        self._record(request.usage_context, response.usage, response.cost.total_cost_usd)

    def record_embedding(self, request: EmbeddingRequest, response: EmbeddingResponse) -> None:
        cost_usd = 0.0
        if self.registry is not None and self.cost_calculator is not None:
            try:
                model = self.registry.get(response.provider, response.model)
                cost_usd = self.cost_calculator.calculate(model, response.usage).total_cost_usd
            except ModelNotFoundError:
                pass  # unknown/dynamically-served model — token counts still tracked, cost reported as 0.0
        self._record(request.usage_context, response.usage, cost_usd)

    def check_limits(self, request: GenerationRequest) -> None:
        now = datetime.now(timezone.utc)
        day = self._usage.get(("global", "day", now.strftime("%Y-%m-%d")))
        if day is not None and day.total_cost_usd >= self.settings.daily_cost_limit_usd:
            raise CostLimitExceededError(
                f"daily cost limit of ${self.settings.daily_cost_limit_usd:.2f} reached (${day.total_cost_usd:.2f} spent)",
                limit_usd=self.settings.daily_cost_limit_usd, current_usd=day.total_cost_usd,
            )
        month = self._usage.get(("global", "month", now.strftime("%Y-%m")))
        if month is not None and month.total_cost_usd >= self.settings.monthly_cost_limit_usd:
            raise CostLimitExceededError(
                f"monthly cost limit of ${self.settings.monthly_cost_limit_usd:.2f} reached (${month.total_cost_usd:.2f} spent)",
                limit_usd=self.settings.monthly_cost_limit_usd, current_usd=month.total_cost_usd,
            )

        scope_key = request.usage_context.user_id or request.usage_context.organization_id or "global"
        timestamps = self._request_timestamps[scope_key]
        cutoff = time.time() - 60
        del timestamps[: sum(1 for t in timestamps if t <= cutoff)]
        if len(timestamps) >= self.settings.rate_limit_requests_per_minute:
            raise RateLimitExceededError(
                f"rate limit of {self.settings.rate_limit_requests_per_minute} requests/minute exceeded for '{scope_key}'"
            )
        timestamps.append(time.time())

    def get_usage(self, *, scope: str, period: str, period_key: str | None = None) -> UsageSummary | None:
        if period_key is None:
            now = datetime.now(timezone.utc)
            period_key = now.strftime("%Y-%m-%d") if period == "day" else now.strftime("%Y-%m")
        return self._usage.get((scope, period, period_key))
