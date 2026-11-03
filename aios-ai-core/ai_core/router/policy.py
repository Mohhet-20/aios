"""A RoutingPolicy is an ordered, named pipeline of RoutingStrategy stages.
Operators compose policies declaratively instead of subclassing the
router — the default policy is a sensible general-purpose pipeline; a
policy for a latency-sensitive product surface, or one that pins
PII-tagged traffic to an on-prem model, is just a different list.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.router.strategies import (
    CapabilityFilterStrategy,
    CostAwareStrategy,
    LatencyAwareStrategy,
    LoadBalancingStrategy,
    PriorityStrategy,
    RegionalStrategy,
    RoutingStrategy,
    TaskBasedStrategy,
)


@dataclass
class RoutingPolicy:
    name: str
    strategies: list[RoutingStrategy] = field(default_factory=list)
    max_candidates: int = 3

    @classmethod
    def default(cls) -> "RoutingPolicy":
        return cls(
            name="default",
            strategies=[
                CapabilityFilterStrategy(),
                TaskBasedStrategy(),
                RegionalStrategy(),
                CostAwareStrategy(),
                LatencyAwareStrategy(),
                PriorityStrategy(),
                LoadBalancingStrategy(),
            ],
        )

    @classmethod
    def cost_optimized(cls) -> "RoutingPolicy":
        """Prioritizes cost above all else — for background/batch jobs
        where latency and load spread don't matter. CostAwareStrategy's
        ascending sort is deliberately the *last* stage: unlike the default
        policy, nothing here should be allowed to re-sort cost away."""
        return cls(
            name="cost_optimized",
            strategies=[CapabilityFilterStrategy(), CostAwareStrategy()],
        )

    @classmethod
    def latency_optimized(cls) -> "RoutingPolicy":
        """For interactive/streaming surfaces where p99 latency matters
        more than saving a fraction of a cent per request. Same reasoning
        as cost_optimized: LatencyAwareStrategy's sort must be the final
        word on ordering."""
        return cls(
            name="latency_optimized",
            strategies=[CapabilityFilterStrategy(), LatencyAwareStrategy()],
        )
