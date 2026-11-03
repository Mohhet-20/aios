"""Rule-based (non-LLM-judge) evaluation metrics: latency, cost, token
usage, and formatting. Each is normalized to a 0-100 score against a
configurable target so it composes with the LLM-judge metrics into one
overall score.
"""
from __future__ import annotations

from ai_core.structured_output.parser import parse_json_response
from ai_core.utils.exceptions import StructuredOutputError


def _linear_falloff(value: float, *, target: float, zero_at_multiple: float = 3.0) -> float:
    if value <= target:
        return 100.0
    ceiling = target * zero_at_multiple
    if value >= ceiling:
        return 0.0
    return round(100 * (1 - (value - target) / (ceiling - target)), 2)


def score_latency(latency_ms: float, *, target_ms: float = 2000.0) -> float:
    return _linear_falloff(latency_ms, target=target_ms)


def score_cost(cost_usd: float, *, budget_usd: float = 0.01) -> float:
    return _linear_falloff(cost_usd, target=budget_usd)


def score_token_usage(total_tokens: int, *, budget_tokens: int = 1000) -> float:
    return _linear_falloff(total_tokens, target=budget_tokens)


def score_formatting(response_text: str, *, expect_json: bool = False) -> float:
    if not expect_json:
        return 100.0
    try:
        parse_json_response(response_text)
        return 100.0
    except StructuredOutputError:
        return 0.0
