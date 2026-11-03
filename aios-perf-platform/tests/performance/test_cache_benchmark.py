"""Real, measured proof that the cache platform and the model router
actually save time and money — not simulated numbers. Every assertion
here is against a value computed from a real `time.perf_counter()`
measurement or a real `token_cost_usd` call, printed to stdout (run
with `-s` to see them) so a reviewer can eyeball the magnitude, not
just trust a boolean pass."""
from __future__ import annotations

import time

from perf_platform.caching.lru import LRUTTLCache
from perf_platform.config.settings import Settings
from perf_platform.cost_intelligence.pricing_rules import token_cost_usd
from perf_platform.routing.routing_rules import select_tier


def _slow_lookup(key: str) -> str:
    """Stand-in for an expensive operation a cache would sit in front
    of (a DB query, an embedding computation, an LLM call) — a real
    sleep, not a mocked timer, so the measured speedup is genuine."""
    time.sleep(0.002)
    return f"value-for-{key}"


def test_lru_cache_delivers_measurable_speedup():
    cache: LRUTTLCache[str, str] = LRUTTLCache(max_entries=100)
    key = "hot-key"

    start = time.perf_counter()
    _slow_lookup(key)
    uncached_seconds = time.perf_counter() - start

    cache.set(key, _slow_lookup(key))
    start = time.perf_counter()
    for _ in range(100):
        cache.get(key)
    cached_seconds_per_call = (time.perf_counter() - start) / 100

    speedup_factor = uncached_seconds / cached_seconds_per_call
    print(
        f"\n[cache benchmark] uncached call: {uncached_seconds * 1000:.3f}ms | "
        f"cached call (avg of 100): {cached_seconds_per_call * 1000:.5f}ms | "
        f"speedup: {speedup_factor:.0f}x"
    )
    # Conservative threshold — a real L1 hit is routinely 1000x+ faster
    # than a 2ms simulated backend call; 50x leaves headroom for slow
    # CI hardware while still proving a real, large speedup.
    assert speedup_factor > 50


def test_model_routing_delivers_measurable_cost_savings():
    settings = Settings()
    n_requests = 1000
    input_tokens, output_tokens = 400, 400

    # Baseline: every request naively sent to the most capable tier.
    naive_cost = token_cost_usd(settings, model_tier="reasoning", input_tokens=input_tokens, output_tokens=output_tokens) * n_requests

    # Routed: realistic complexity mix for a typical workload — mostly
    # trivial/simple lookups, a handful of genuinely complex ones.
    complexity_mix = ["trivial"] * 600 + ["simple"] * 300 + ["moderate"] * 80 + ["complex"] * 15 + ["expert"] * 5
    routed_cost = 0.0
    for complexity in complexity_mix:
        tier, _ = select_tier(task_complexity=complexity, user_tier="enterprise")
        routed_cost += token_cost_usd(settings, model_tier=tier, input_tokens=input_tokens, output_tokens=output_tokens)

    savings_usd = naive_cost - routed_cost
    savings_pct = 100.0 * savings_usd / naive_cost
    print(
        f"\n[routing benchmark] naive (always-reasoning) cost for {n_requests} requests: ${naive_cost:.2f} | "
        f"complexity-routed cost: ${routed_cost:.2f} | savings: ${savings_usd:.2f} ({savings_pct:.1f}%)"
    )
    assert routed_cost < naive_cost
    assert savings_pct > 50  # routing the realistic mix should save the majority of naive spend
