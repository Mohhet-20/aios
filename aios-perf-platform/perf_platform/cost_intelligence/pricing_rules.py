"""Pure pricing functions — zero DB/service imports, unit-testable in
isolation. Rates come from Settings (illustrative, deployment-
configurable defaults — see README disclosed scope boundaries), never
hardcoded here, so a deployment can point this at real negotiated
rates without touching this module."""
from __future__ import annotations

from perf_platform.config.settings import Settings
from perf_platform.core.exceptions import UnsupportedModelTierError


def token_cost_usd(settings: Settings, *, model_tier: str, input_tokens: int, output_tokens: int) -> float:
    pricing = settings.model_tier_pricing_per_1k.get(model_tier)
    if pricing is None:
        raise UnsupportedModelTierError(f"Unsupported model tier '{model_tier}'")
    return round((input_tokens / 1000.0) * pricing["input"] + (output_tokens / 1000.0) * pricing["output"], 6)


def gpu_cost_usd(settings: Settings, *, gpu_hours: float) -> float:
    return round(gpu_hours * settings.gpu_cost_per_hour_usd, 6)


def cpu_cost_usd(settings: Settings, *, core_hours: float) -> float:
    return round(core_hours * settings.cpu_cost_per_core_hour_usd, 6)


def memory_cost_usd(settings: Settings, *, gb_hours: float) -> float:
    return round(gb_hours * settings.memory_cost_per_gb_hour_usd, 6)


def storage_cost_usd(settings: Settings, *, gb_months: float) -> float:
    return round(gb_months * settings.storage_cost_per_gb_month_usd, 6)


def bandwidth_cost_usd(settings: Settings, *, gb: float) -> float:
    return round(gb * settings.bandwidth_cost_per_gb_usd, 6)


def budget_utilization_pct(*, spent_usd: float, limit_usd: float) -> float:
    if limit_usd <= 0:
        return 0.0
    return round(100.0 * spent_usd / limit_usd, 2)


def crossed_thresholds(*, utilization_pct: float, thresholds_pct: list[float], already_alerted_pct: list[float]) -> list[float]:
    """Which of the configured alert thresholds does this utilization
    newly cross (i.e. is at/above but hasn't already been alerted on)?
    Pure function so the alerting decision is independently testable
    from the DB read/write around it."""
    return sorted(t for t in thresholds_pct if utilization_pct >= t and t not in already_alerted_pct)
