from __future__ import annotations

import pytest

from perf_platform.core.exceptions import NoEligibleModelTierError
from perf_platform.routing.routing_rules import select_tier


def test_trivial_task_routes_small():
    tier, reasoning = select_tier(task_complexity="trivial")
    assert tier == "small"
    assert "trivial" in reasoning


def test_expert_task_routes_reasoning_for_enterprise():
    tier, _ = select_tier(task_complexity="expert", user_tier="enterprise")
    assert tier == "reasoning"


def test_free_tier_capped_below_reasoning():
    tier, reasoning = select_tier(task_complexity="expert", user_tier="free")
    assert tier == "medium"
    assert "ceiling" in reasoning


def test_vision_task_always_routes_vision_tier():
    tier, _ = select_tier(task_complexity="expert", requires_vision=True)
    assert tier == "vision"


def test_code_task_always_routes_code_tier():
    tier, _ = select_tier(task_complexity="trivial", requires_code=True)
    assert tier == "code"


def test_tight_latency_budget_downgrades_one_rung():
    tier, reasoning = select_tier(task_complexity="expert", user_tier="enterprise", latency_budget_ms=200)
    assert tier == "large"
    assert "tight" in reasoning


def test_generous_latency_budget_does_not_downgrade():
    tier, _ = select_tier(task_complexity="expert", user_tier="enterprise", latency_budget_ms=5000)
    assert tier == "reasoning"


def test_policy_allowed_tiers_falls_back_gracefully():
    tier, reasoning = select_tier(task_complexity="expert", user_tier="enterprise", allowed_tiers=["small", "medium"])
    assert tier == "medium"
    assert "fell back" in reasoning


def test_policy_allowed_tiers_raises_when_nothing_eligible():
    with pytest.raises(NoEligibleModelTierError):
        select_tier(task_complexity="trivial", allowed_tiers=["reasoning"])


def test_policy_allows_exact_match_no_fallback_note():
    tier, reasoning = select_tier(task_complexity="moderate", allowed_tiers=["small", "medium", "large"])
    assert tier == "medium"
    assert "policy allows" in reasoning
