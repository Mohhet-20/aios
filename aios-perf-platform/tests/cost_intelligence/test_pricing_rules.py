from __future__ import annotations

import pytest

from perf_platform.config.settings import Settings
from perf_platform.core.exceptions import UnsupportedModelTierError
from perf_platform.cost_intelligence.pricing_rules import (
    bandwidth_cost_usd,
    budget_utilization_pct,
    cpu_cost_usd,
    crossed_thresholds,
    gpu_cost_usd,
    memory_cost_usd,
    storage_cost_usd,
    token_cost_usd,
)

SETTINGS = Settings()


def test_token_cost_small_vs_large_tier():
    small = token_cost_usd(SETTINGS, model_tier="small", input_tokens=1000, output_tokens=1000)
    large = token_cost_usd(SETTINGS, model_tier="large", input_tokens=1000, output_tokens=1000)
    assert small < large


def test_token_cost_unsupported_tier():
    with pytest.raises(UnsupportedModelTierError):
        token_cost_usd(SETTINGS, model_tier="ultra", input_tokens=1, output_tokens=1)


def test_infra_cost_helpers_are_linear():
    assert gpu_cost_usd(SETTINGS, gpu_hours=2) == round(2 * SETTINGS.gpu_cost_per_hour_usd, 6)
    assert cpu_cost_usd(SETTINGS, core_hours=4) == round(4 * SETTINGS.cpu_cost_per_core_hour_usd, 6)
    assert memory_cost_usd(SETTINGS, gb_hours=8) == round(8 * SETTINGS.memory_cost_per_gb_hour_usd, 6)
    assert storage_cost_usd(SETTINGS, gb_months=100) == round(100 * SETTINGS.storage_cost_per_gb_month_usd, 6)
    assert bandwidth_cost_usd(SETTINGS, gb=50) == round(50 * SETTINGS.bandwidth_cost_per_gb_usd, 6)


def test_budget_utilization_pct():
    assert budget_utilization_pct(spent_usd=50, limit_usd=100) == 50.0
    assert budget_utilization_pct(spent_usd=0, limit_usd=0) == 0.0


def test_crossed_thresholds_only_new_ones():
    result = crossed_thresholds(utilization_pct=85.0, thresholds_pct=[50.0, 80.0, 100.0], already_alerted_pct=[50.0])
    assert result == [80.0]


def test_crossed_thresholds_none_when_under():
    assert crossed_thresholds(utilization_pct=10.0, thresholds_pct=[50.0, 80.0], already_alerted_pct=[]) == []
