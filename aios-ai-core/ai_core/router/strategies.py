"""Routing strategies. Each strategy is a pipeline stage: it receives the
candidate list produced by the previous stage and returns a (possibly
filtered, possibly reordered) candidate list. `ModelRouter` runs the full
pipeline in order; the first surviving candidate is the primary pick, the
rest form the fallback chain the execution engine walks on failure.

This is deliberately NOT one big scoring function — composing small single-
purpose stages is what makes "add a new routing dimension" a one-class
change instead of a rewrite of a monolithic scorer.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from itertools import count

from ai_core.registry.model_metadata import ModelMetadata
from ai_core.schemas.enums import Capability
from ai_core.schemas.requests import GenerationRequest


class RoutingStrategy(ABC):
    name: str = "unnamed"

    @abstractmethod
    def apply(
        self, candidates: list[ModelMetadata], request: GenerationRequest, *, required_capabilities: set[Capability]
    ) -> list[ModelMetadata]:
        """Return the next candidate list. Strategies should be tolerant of
        an already-empty input and just return it unchanged — only the
        router decides that empty-after-pipeline is an error."""


class CapabilityFilterStrategy(RoutingStrategy):
    """Hard filter: a model that can't stream/call tools/emit JSON when the
    request needs it is never a valid candidate, full stop."""

    name = "capability"

    def apply(self, candidates, request, *, required_capabilities):
        if not required_capabilities:
            return candidates
        return [m for m in candidates if required_capabilities.issubset(m.capabilities)]


class TaskBasedStrategy(RoutingStrategy):
    """Soft preference: if the caller tagged the request with a task (e.g.
    'coding', 'reasoning') via routing_hints.task, models whose `tags`
    include it are moved to the front. Never filters — an untagged model
    might still be the right (or only) choice."""

    name = "task_based"

    def apply(self, candidates, request, *, required_capabilities):
        task = request.routing_hints.task
        if not task:
            return candidates
        matched = [m for m in candidates if task in m.tags]
        unmatched = [m for m in candidates if task not in m.tags]
        return matched + unmatched if matched else candidates


class CostAwareStrategy(RoutingStrategy):
    """Filters out models whose blended per-1M-token price exceeds
    `routing_hints.max_cost_usd` (interpreted as a per-request cost ceiling
    against a rough fixed-size estimate), then sorts survivors cheapest
    first as a general cost-consciousness default."""

    name = "cost_aware"

    def __init__(self, *, estimated_tokens_per_request: int = 1500):
        self._estimated_tokens = estimated_tokens_per_request

    def _estimated_cost(self, model: ModelMetadata) -> float:
        blended_per_token = (model.pricing.input_cost_per_1m + model.pricing.output_cost_per_1m) / 2 / 1_000_000
        return blended_per_token * self._estimated_tokens

    def apply(self, candidates, request, *, required_capabilities):
        max_cost = request.routing_hints.max_cost_usd
        pool = candidates
        if max_cost is not None:
            pool = [m for m in candidates if self._estimated_cost(m) <= max_cost] or candidates
        return sorted(pool, key=self._estimated_cost)


class LatencyAwareStrategy(RoutingStrategy):
    """Sorts by observed rolling-average latency (from ModelRegistry.
    update_latency). Models with no observations yet sort as if they were
    the fastest option seen so far, so new/rarely-used models aren't
    permanently penalized versus stale data — they just need one real
    request to get a real number."""

    name = "latency_aware"

    def apply(self, candidates, request, *, required_capabilities):
        max_latency = request.routing_hints.max_latency_ms
        pool = candidates
        if max_latency is not None:
            pool = [m for m in candidates if m.average_latency_ms is None or m.average_latency_ms <= max_latency] or candidates
        return sorted(pool, key=lambda m: m.average_latency_ms if m.average_latency_ms is not None else -1.0)


class RegionalStrategy(RoutingStrategy):
    """Prefers models tagged with the requested region; models with no
    region set are treated as globally available and kept in the pool
    (deprioritized, not excluded) so a regional preference never produces
    zero candidates."""

    name = "regional"

    def apply(self, candidates, request, *, required_capabilities):
        region = request.routing_hints.region
        if not region:
            return candidates
        matched = [m for m in candidates if m.region == region]
        rest = [m for m in candidates if m.region != region]
        return matched + rest if matched else candidates


class PriorityStrategy(RoutingStrategy):
    """Final tiebreaker: stable-sort by the registry's operator-assigned
    `priority` (lower = preferred). Runs last so it only breaks ties left
    by every cost/latency/task preference above."""

    name = "priority"

    def apply(self, candidates, request, *, required_capabilities):
        return sorted(candidates, key=lambda m: m.priority)


class LoadBalancingStrategy(RoutingStrategy):
    """Round-robins among the top `window` equally-ranked candidates
    instead of always picking the same #1, spreading load across
    functionally-equivalent models/deployments. Stateful by design (a
    per-router instance counter) — this is the one strategy that isn't a
    pure function of its input, which is why it's the last stage."""

    name = "load_balancing"

    def __init__(self, *, window: int = 3):
        self._window = window
        self._counter = count()

    def apply(self, candidates, request, *, required_capabilities):
        if len(candidates) <= 1:
            return candidates
        top = candidates[: self._window]
        rest = candidates[self._window :]
        # Simple round robin: rotate `top` by the call counter.
        n = next(self._counter) % len(top)
        rotated = top[n:] + top[:n]
        return rotated + rest


class CanaryStrategy(RoutingStrategy):
    """Sends `traffic_percent`% of requests to `canary_model_key` instead
    of the pipeline's current top pick, if the canary is among the
    candidates. Used to validate a new model/provider on a small slice of
    real traffic before promoting it via PriorityStrategy instead."""

    name = "canary"

    def __init__(self, *, canary_model_key: str | None = None, traffic_percent: float = 0.0, rng: random.Random | None = None):
        self.canary_model_key = canary_model_key
        self.traffic_percent = traffic_percent
        self._rng = rng or random.Random()

    def apply(self, candidates, request, *, required_capabilities):
        if not self.canary_model_key or self.traffic_percent <= 0:
            return candidates
        canary = next((m for m in candidates if m.key == self.canary_model_key), None)
        if canary is None:
            return candidates
        if self._rng.random() * 100 < self.traffic_percent:
            rest = [m for m in candidates if m.key != canary.key]
            return [canary] + rest
        return candidates


class ABTestStrategy(RoutingStrategy):
    """Deterministic (not probabilistic) variant selection: maps a caller-
    supplied `routing_hints.experiment_bucket` (e.g. "A"/"B", or a user-hash
    bucket computed upstream) to a specific model, for reproducible
    experiment assignment rather than per-request randomness."""

    name = "ab_test"

    def __init__(self, bucket_to_model_key: dict[str, str] | None = None):
        self.bucket_to_model_key = bucket_to_model_key or {}

    def apply(self, candidates, request, *, required_capabilities):
        bucket = request.routing_hints.experiment_bucket
        if not bucket or bucket not in self.bucket_to_model_key:
            return candidates
        target_key = self.bucket_to_model_key[bucket]
        target = next((m for m in candidates if m.key == target_key), None)
        if target is None:
            return candidates
        rest = [m for m in candidates if m.key != target_key]
        return [target] + rest


RuleFn = Callable[[GenerationRequest], str | None]


class RuleBasedStrategy(RoutingStrategy):
    """Runs operator-supplied rule callables in order; the first rule that
    returns a model key wins and is promoted to the front, letting
    operators encode business logic ("always route PII-tagged requests to
    the on-prem vLLM deployment") without touching the router itself."""

    name = "rule_based"

    def __init__(self, rules: list[RuleFn] | None = None):
        self.rules = rules or []

    def apply(self, candidates, request, *, required_capabilities):
        for rule in self.rules:
            target_key = rule(request)
            if not target_key:
                continue
            target = next((m for m in candidates if m.key == target_key), None)
            if target is not None:
                rest = [m for m in candidates if m.key != target_key]
                return [target] + rest
        return candidates


class MLBasedStrategy(RoutingStrategy):
    """Future seam for a learned routing policy (e.g. a small classifier
    predicting best model per request embedding). Currently a documented
    passthrough — wiring a real model in means implementing `apply()` here
    and inserting this stage into the pipeline; no other router code
    changes."""

    name = "ml_based"

    def apply(self, candidates, request, *, required_capabilities):
        return candidates
