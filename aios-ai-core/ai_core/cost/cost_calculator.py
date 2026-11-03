"""Canonical cost calculation logic — the single source of truth for
"how much did this request cost," used by both the execution engine's
lightweight default and the UsageTracker's aggregation."""
from __future__ import annotations

from ai_core.registry.model_metadata import ModelMetadata
from ai_core.schemas.usage import CostBreakdown, TokenUsage


def calculate_cost(model: ModelMetadata, usage: TokenUsage) -> CostBreakdown:
    non_cached_input = max(usage.input_tokens - usage.cached_tokens, 0)
    input_cost = non_cached_input * model.pricing.input_cost_per_1m / 1_000_000
    cached_cost = usage.cached_tokens * model.pricing.cached_input_cost_per_1m / 1_000_000
    output_cost = usage.output_tokens * model.pricing.output_cost_per_1m / 1_000_000
    return CostBreakdown(
        input_cost_usd=round(input_cost + cached_cost, 8),
        output_cost_usd=round(output_cost, 8),
        total_cost_usd=round(input_cost + cached_cost + output_cost, 8),
        currency=model.pricing.currency,
        is_estimate=False,
    )


class CostCalculator:
    """Satisfies `CostCalculatorProtocol`. A class (not just the bare
    function) so it's easy to extend later — e.g. a calculator that
    applies negotiated enterprise discount rates on top of list pricing —
    without changing the engine's constructor signature."""

    def calculate(self, model: ModelMetadata, usage: TokenUsage) -> CostBreakdown:
        return calculate_cost(model, usage)
