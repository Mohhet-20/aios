from __future__ import annotations

from perf_platform.optimization.recommendation_rules import (
    budget_near_exhaustion_recommendation,
    high_latency_recommendation,
    low_cache_hit_rate_recommendation,
    model_tier_overprovisioning_recommendation,
)


def test_low_cache_hit_rate_flags_below_threshold():
    rec = low_cache_hit_rate_recommendation(layer="response", hit_rate_pct=20.0, threshold_pct=40.0)
    assert rec is not None
    assert rec["category"] == "caching"


def test_low_cache_hit_rate_no_flag_above_threshold():
    assert low_cache_hit_rate_recommendation(layer="response", hit_rate_pct=90.0, threshold_pct=40.0) is None


def test_high_latency_flags_over_threshold():
    rec = high_latency_recommendation(operation="db_query_users", p99_ms=3000, threshold_ms=1500)
    assert rec is not None
    assert rec["category"] == "database"


def test_high_latency_no_flag_under_threshold():
    assert high_latency_recommendation(operation="op", p99_ms=100, threshold_ms=1500) is None


def test_model_tier_overprovisioning_requires_repeated_occurrences():
    assert model_tier_overprovisioning_recommendation(
        task_complexity="trivial", chosen_tier="reasoning", occurrences=2, cost_delta_usd_per_request=0.05,
    ) is None
    rec = model_tier_overprovisioning_recommendation(
        task_complexity="trivial", chosen_tier="reasoning", occurrences=20, cost_delta_usd_per_request=0.05,
    )
    assert rec is not None
    assert rec["category"] == "model_downgrade"
    assert rec["estimated_savings_usd"] == 1.0


def test_model_tier_overprovisioning_no_flag_when_tier_matches_baseline():
    assert model_tier_overprovisioning_recommendation(
        task_complexity="expert", chosen_tier="reasoning", occurrences=50, cost_delta_usd_per_request=0.1,
    ) is None


def test_budget_near_exhaustion_flags_at_90_pct():
    rec = budget_near_exhaustion_recommendation(entity_type="workflow", entity_id="wf-1", utilization_pct=95.0)
    assert rec is not None
    assert rec["category"] == "scaling"


def test_budget_near_exhaustion_no_flag_below_90_pct():
    assert budget_near_exhaustion_recommendation(entity_type="user", entity_id="u1", utilization_pct=50.0) is None
