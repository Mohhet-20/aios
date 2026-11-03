
import pytest

from ai_core.config.settings import AICoreSettings
from ai_core.cost.cost_calculator import CostCalculator, calculate_cost
from ai_core.cost.usage_tracker import UsageTracker
from ai_core.registry.model_metadata import ModelMetadata, ModelPricing
from ai_core.registry.model_registry import ModelRegistry
from ai_core.schemas.enums import FinishReason
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest, UsageContext
from ai_core.schemas.responses import EmbeddingResponse, ExecutionMetadata, GenerationResponse
from ai_core.schemas.usage import CostBreakdown, TokenUsage
from ai_core.utils.exceptions import CostLimitExceededError, RateLimitExceededError
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage


def _model(**kw) -> ModelMetadata:
    kw.setdefault("provider", "openai")
    kw.setdefault("name", "gpt-4o")
    return ModelMetadata(**kw)


def test_calculate_cost_basic_math():
    model = _model(pricing=ModelPricing(input_cost_per_1m=2.0, output_cost_per_1m=4.0))
    cost = calculate_cost(model, TokenUsage(input_tokens=1_000_000, output_tokens=500_000))
    assert cost.input_cost_usd == 2.0
    assert cost.output_cost_usd == 2.0
    assert cost.total_cost_usd == 4.0
    assert cost.is_estimate is False


def test_calculate_cost_accounts_for_cached_tokens_at_discount_rate():
    model = _model(pricing=ModelPricing(input_cost_per_1m=10.0, cached_input_cost_per_1m=1.0, output_cost_per_1m=0))
    cost = calculate_cost(model, TokenUsage(input_tokens=1_000_000, cached_tokens=500_000))
    # 500k non-cached at $10/1M + 500k cached at $1/1M
    assert cost.input_cost_usd == pytest.approx(5.0 + 0.5)


def test_cost_calculator_class_matches_function():
    model = _model(pricing=ModelPricing(input_cost_per_1m=1.0, output_cost_per_1m=1.0))
    usage = TokenUsage(input_tokens=100, output_tokens=100)
    assert CostCalculator().calculate(model, usage) == calculate_cost(model, usage)


def _gen_response(cost_usd: float, ctx: UsageContext) -> tuple[GenerationRequest, GenerationResponse]:
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], usage_context=ctx)
    resp = GenerationResponse(
        content="ok", finish_reason=FinishReason.STOP, usage=TokenUsage(input_tokens=10, output_tokens=5),
        cost=CostBreakdown(total_cost_usd=cost_usd), execution=ExecutionMetadata(request_id=req.request_id, provider="openai", model="gpt-4o"),
    )
    return req, resp


def test_usage_tracker_aggregates_by_scope_and_period():
    tracker = UsageTracker()
    ctx = UsageContext(organization_id="acme", user_id="u1", project_id="p1")
    req, resp = _gen_response(0.05, ctx)
    tracker.record_generation(req, resp)

    for scope in ("global", "org:acme", "user:u1", "project:p1"):
        summary = tracker.get_usage(scope=scope, period="day")
        assert summary is not None
        assert summary.request_count == 1
        assert summary.total_cost_usd == pytest.approx(0.05)
        assert summary.input_tokens == 10


def test_usage_tracker_daily_cost_limit_raises():
    settings = AICoreSettings(daily_cost_limit_usd=0.10, monthly_cost_limit_usd=1000.0, rate_limit_requests_per_minute=1000)
    tracker = UsageTracker(settings=settings)
    req, resp = _gen_response(0.15, UsageContext())
    tracker.record_generation(req, resp)

    with pytest.raises(CostLimitExceededError):
        tracker.check_limits(GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")]))


def test_usage_tracker_rate_limit_raises():
    settings = AICoreSettings(rate_limit_requests_per_minute=2, daily_cost_limit_usd=1000, monthly_cost_limit_usd=10000)
    tracker = UsageTracker(settings=settings)
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], usage_context=UsageContext(user_id="u1"))
    tracker.check_limits(req)
    tracker.check_limits(req)
    with pytest.raises(RateLimitExceededError):
        tracker.check_limits(req)


def test_usage_tracker_record_embedding_computes_cost_via_registry():
    registry = ModelRegistry()
    registry.register(_model(name="text-embedding-3-small", pricing=ModelPricing(input_cost_per_1m=1.0)))
    tracker = UsageTracker(registry=registry, cost_calculator=CostCalculator())
    embed_req = EmbeddingRequest(input="hello")
    embed_resp = EmbeddingResponse(
        request_id=embed_req.request_id, embeddings=[[0.1]], model="text-embedding-3-small", provider="openai",
        dimensions=1, usage=TokenUsage(input_tokens=1_000_000),
    )
    tracker.record_embedding(embed_req, embed_resp)
    summary = tracker.get_usage(scope="global", period="day")
    assert summary.total_cost_usd == pytest.approx(1.0)


def test_usage_tracker_record_embedding_unknown_model_defaults_to_zero_cost():
    tracker = UsageTracker()  # no registry wired
    embed_req = EmbeddingRequest(input="hello")
    embed_resp = EmbeddingResponse(request_id=embed_req.request_id, embeddings=[[0.1]], model="unknown", provider="openai", dimensions=1)
    tracker.record_embedding(embed_req, embed_resp)
    summary = tracker.get_usage(scope="global", period="day")
    assert summary.total_cost_usd == 0.0
