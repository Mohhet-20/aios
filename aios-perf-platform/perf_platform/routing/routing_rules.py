"""Pure model-tier selection logic — zero DB/service imports, fully
deterministic and unit-testable. `ModelRoutingService` (routing_service.py)
is a thin orchestration shell around this: fetch a policy row, call
`select_tier`, persist the decision.

Escalation ladder (increasing capability and cost): small < medium <
large < reasoning. `vision` and `code` are specialty tiers picked
directly when the task requires that modality, orthogonal to the
ladder — a vision task doesn't get "upgraded" to reasoning just
because it's hard, it goes to the model actually built for images.
"""
from __future__ import annotations

from perf_platform.core.exceptions import NoEligibleModelTierError

_LADDER = ["small", "medium", "large", "reasoning"]

_COMPLEXITY_BASELINE_TIER = {
    "trivial": "small",
    "simple": "small",
    "moderate": "medium",
    "complex": "large",
    "expert": "reasoning",
}

# Highest ladder rung each user tier may reach without an explicit
# policy override — a cost-control default, not a hard platform limit
# (an org's own RoutingPolicy can raise or lower this via allowed_tiers).
_USER_TIER_CEILING = {
    "free": "medium",
    "pro": "large",
    "team": "reasoning",
    "enterprise": "reasoning",
}

# Below this latency budget, prefer one rung down the ladder over the
# complexity-indicated tier — a documented accuracy/latency tradeoff,
# not a bug: a slow "correct" answer is often worse than a fast "good
# enough" one for interactive use cases. Callers that need max accuracy
# regardless of latency should not pass a tight latency_budget_ms.
_TIGHT_LATENCY_BUDGET_MS = 800.0


def _rank(tier: str) -> int:
    return _LADDER.index(tier)


def select_tier(
    *,
    task_complexity: str,
    user_tier: str = "enterprise",
    latency_budget_ms: float | None = None,
    requires_vision: bool = False,
    requires_code: bool = False,
    allowed_tiers: list[str] | None = None,
) -> tuple[str, str]:
    """Returns (chosen_tier, human-readable reasoning). Raises
    `NoEligibleModelTierError` if a policy's `allowed_tiers` excludes
    every ladder rung at or below what would otherwise be chosen."""
    reasons: list[str] = []

    if requires_vision:
        return "vision", "task requires vision input; routed directly to the vision-specialty tier"
    if requires_code:
        return "code", "task requires code generation; routed directly to the code-specialty tier"

    baseline = _COMPLEXITY_BASELINE_TIER.get(task_complexity)
    if baseline is None:
        baseline = "medium"
        reasons.append(f"unrecognized complexity '{task_complexity}', defaulted to medium")
    else:
        reasons.append(f"complexity '{task_complexity}' baseline tier is '{baseline}'")

    tier = baseline
    ceiling = _USER_TIER_CEILING.get(user_tier, "medium")
    if _rank(tier) > _rank(ceiling):
        reasons.append(f"capped from '{tier}' to user tier '{user_tier}' ceiling '{ceiling}'")
        tier = ceiling

    if latency_budget_ms is not None and latency_budget_ms < _TIGHT_LATENCY_BUDGET_MS and _rank(tier) > 0:
        downgraded = _LADDER[_rank(tier) - 1]
        reasons.append(f"latency budget {latency_budget_ms:.0f}ms is tight (<{_TIGHT_LATENCY_BUDGET_MS:.0f}ms); downgraded '{tier}' to '{downgraded}'")
        tier = downgraded

    if allowed_tiers:
        if tier not in allowed_tiers:
            # Fall back to the highest allowed ladder rung at or below
            # the current choice, so a restrictive policy degrades
            # gracefully rather than always hard-failing.
            eligible = [t for t in allowed_tiers if t in _LADDER and _rank(t) <= _rank(tier)]
            if not eligible:
                raise NoEligibleModelTierError(
                    f"No tier in policy allowed_tiers {allowed_tiers} is eligible for the requested '{tier}'"
                )
            fallback = max(eligible, key=_rank)
            reasons.append(f"policy restricts to {allowed_tiers}; fell back from '{tier}' to '{fallback}'")
            tier = fallback
        else:
            reasons.append(f"policy allows '{tier}'")

    return tier, "; ".join(reasons)
