"""Pure signal-to-recommendation rules — zero DB/service imports. Each
function takes already-computed signals (a cache hit rate, a p99
latency, a routing decision) and returns a recommendation candidate
dict, or `None` if nothing is worth flagging. `RecommendationService`
(optimization_service.py) is the only caller — it gathers the signals
from the repositories, calls these, and persists whatever comes back.

Splitting it this way means the actual "is this worth recommending"
judgment call is unit-testable with plain numbers, no DB and no
async, the same testing shape as every other AIOS platform's
`*_rules.py` modules."""
from __future__ import annotations

from typing import Any

_LADDER = ["small", "medium", "large", "reasoning"]
_COMPLEXITY_BASELINE_TIER = {
    "trivial": "small",
    "simple": "small",
    "moderate": "medium",
    "complex": "large",
    "expert": "reasoning",
}


def low_cache_hit_rate_recommendation(*, layer: str, hit_rate_pct: float, threshold_pct: float) -> dict[str, Any] | None:
    if hit_rate_pct >= threshold_pct:
        return None
    return {
        "category": "caching",
        "title": f"Low hit rate on '{layer}' cache layer",
        "description": (
            f"The '{layer}' cache layer's hit rate is {hit_rate_pct:.1f}%, below the "
            f"{threshold_pct:.1f}% target. Consider raising the TTL, warming the cache "
            f"for predictable keys, or checking whether keys are being generated with "
            f"unnecessary entropy (timestamps, request ids) that prevents reuse."
        ),
        "target_ref": layer,
        "estimated_savings_usd": 0.0,
    }


def high_latency_recommendation(*, operation: str, p99_ms: float, threshold_ms: float) -> dict[str, Any] | None:
    if p99_ms <= threshold_ms:
        return None
    return {
        "category": "database" if "query" in operation.lower() or "db" in operation.lower() else "workflow",
        "title": f"P99 latency on '{operation}' exceeds target",
        "description": (
            f"P99 latency for '{operation}' is {p99_ms:.0f}ms, above the {threshold_ms:.0f}ms "
            f"SLO. Investigate the slowest traces for this operation — common causes are a "
            f"missing index, an N+1 query pattern, or a synchronous call that should be "
            f"parallelized or cached."
        ),
        "target_ref": operation,
        "estimated_savings_usd": 0.0,
    }


def model_tier_overprovisioning_recommendation(
    *, task_complexity: str, chosen_tier: str, occurrences: int, cost_delta_usd_per_request: float,
) -> dict[str, Any] | None:
    """Flags a systematic mismatch: many requests of a given complexity
    are being routed to a tier above what the complexity ladder would
    pick on its own (a policy override, a caller ignoring the router,
    or a stale default). One occurrence isn't a pattern; this only
    fires once the mismatch has repeated."""
    baseline = _COMPLEXITY_BASELINE_TIER.get(task_complexity)
    if baseline is None or chosen_tier not in _LADDER or baseline not in _LADDER:
        return None
    if _LADDER.index(chosen_tier) <= _LADDER.index(baseline):
        return None
    if occurrences < 5:
        return None
    total_savings = round(cost_delta_usd_per_request * occurrences, 4)
    return {
        "category": "model_downgrade",
        "title": f"'{task_complexity}' tasks routinely over-routed to '{chosen_tier}'",
        "description": (
            f"{occurrences} recent '{task_complexity}'-complexity requests were routed to the "
            f"'{chosen_tier}' tier, above the '{baseline}' tier the complexity ladder would "
            f"normally pick. If this is not an intentional accuracy override, downgrading "
            f"would save an estimated ${total_savings:.2f} across these requests without a "
            f"change in the tasks' actual complexity."
        ),
        "target_ref": f"{task_complexity}->{chosen_tier}",
        "estimated_savings_usd": total_savings,
    }


def budget_near_exhaustion_recommendation(*, entity_type: str, entity_id: str, utilization_pct: float) -> dict[str, Any] | None:
    if utilization_pct < 90.0:
        return None
    return {
        "category": "scaling" if entity_type in {"workflow", "agent"} else "infrastructure",
        "title": f"{entity_type.title()} '{entity_id}' is near its budget limit",
        "description": (
            f"{entity_type} '{entity_id}' has used {utilization_pct:.1f}% of its configured "
            f"budget. Review recent cost records for the largest contributing category, and "
            f"consider either raising the budget or applying a caching/model-downgrade "
            f"recommendation to reduce spend before the limit is reached."
        ),
        "target_ref": f"{entity_type}:{entity_id}",
        "estimated_savings_usd": 0.0,
    }
