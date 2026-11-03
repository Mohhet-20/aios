import random

from ai_core.registry.model_metadata import ModelMetadata, ModelPricing
from ai_core.router.strategies import (
    ABTestStrategy,
    CanaryStrategy,
    CapabilityFilterStrategy,
    CostAwareStrategy,
    LatencyAwareStrategy,
    LoadBalancingStrategy,
    PriorityStrategy,
    RegionalStrategy,
    RuleBasedStrategy,
    TaskBasedStrategy,
)
from ai_core.schemas.enums import Capability
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.enums import Role
from ai_core.schemas.requests import GenerationRequest, RoutingHints


def _req(**hints) -> GenerationRequest:
    return GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], routing_hints=RoutingHints(**hints))


def _model(name, **kw):
    return ModelMetadata(provider="openai", name=name, **kw)


def test_capability_filter_requires_all_capabilities():
    a = _model("a", capabilities={Capability.STREAMING})
    b = _model("b", capabilities={Capability.STREAMING, Capability.TOOL_CALLING})
    result = CapabilityFilterStrategy().apply([a, b], _req(), required_capabilities={Capability.TOOL_CALLING})
    assert result == [b]


def test_task_based_promotes_matching_tags_without_dropping_others():
    a = _model("a", tags=["general"])
    b = _model("b", tags=["coding"])
    result = TaskBasedStrategy().apply([a, b], _req(task="coding"), required_capabilities=set())
    assert result[0].name == "b"
    assert len(result) == 2


def test_cost_aware_filters_above_ceiling_and_sorts_ascending():
    cheap = _model("cheap", pricing=ModelPricing(input_cost_per_1m=1, output_cost_per_1m=1))
    expensive = _model("expensive", pricing=ModelPricing(input_cost_per_1m=100, output_cost_per_1m=100))
    result = CostAwareStrategy(estimated_tokens_per_request=1000).apply(
        [expensive, cheap], _req(max_cost_usd=0.01), required_capabilities=set()
    )
    assert [m.name for m in result] == ["cheap"]


def test_latency_aware_sorts_ascending_and_untested_models_first():
    fast = _model("fast")
    fast.average_latency_ms = 100
    slow = _model("slow")
    slow.average_latency_ms = 900
    untested = _model("untested")
    result = LatencyAwareStrategy().apply([slow, fast, untested], _req(), required_capabilities=set())
    assert [m.name for m in result] == ["untested", "fast", "slow"]


def test_regional_prefers_matching_region_without_excluding_others():
    us = _model("us-model", region="us-east")
    global_ = _model("global-model", region=None)
    result = RegionalStrategy().apply([global_, us], _req(region="us-east"), required_capabilities=set())
    assert result[0].name == "us-model"
    assert len(result) == 2


def test_priority_sorts_ascending():
    low_pri = _model("low", priority=100)
    high_pri = _model("high", priority=1)
    result = PriorityStrategy().apply([low_pri, high_pri], _req(), required_capabilities=set())
    assert [m.name for m in result] == ["high", "low"]


def test_load_balancing_round_robins_top_window():
    a, b, c = _model("a"), _model("b"), _model("c")
    strat = LoadBalancingStrategy(window=3)
    first = strat.apply([a, b, c], _req(), required_capabilities=set())
    second = strat.apply([a, b, c], _req(), required_capabilities=set())
    assert [m.name for m in first] != [m.name for m in second]


def test_canary_routes_percentage_deterministically_with_seeded_rng():
    a, canary = _model("a"), _model("canary-model")
    strat = CanaryStrategy(canary_model_key="openai:canary-model", traffic_percent=100.0, rng=random.Random(1))
    result = strat.apply([a, canary], _req(), required_capabilities=set())
    assert result[0].name == "canary-model"

    strat_zero = CanaryStrategy(canary_model_key="openai:canary-model", traffic_percent=0.0)
    result_zero = strat_zero.apply([a, canary], _req(), required_capabilities=set())
    assert result_zero[0].name == "a"


def test_ab_test_selects_bucket_model():
    a, b = _model("variant-a"), _model("variant-b")
    strat = ABTestStrategy({"B": "openai:variant-b"})
    result = strat.apply([a, b], _req(experiment_bucket="B"), required_capabilities=set())
    assert result[0].name == "variant-b"


def test_rule_based_first_matching_rule_wins():
    a, b = _model("a"), _model("b")
    rules = [lambda req: None, lambda req: "openai:b"]
    strat = RuleBasedStrategy(rules)
    result = strat.apply([a, b], _req(), required_capabilities=set())
    assert result[0].name == "b"
