import asyncio

import pytest

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability, Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.responses import EmbeddingResponse, StreamChunk
from ai_core.utils.exceptions import AllProvidersFailedError, ProviderAuthenticationError, ProviderError

from tests.execution.conftest import ScriptedProvider, make_response


def _req(**kw) -> GenerationRequest:
    kw.setdefault("messages", [ChatMessage(role=Role.USER, content="hi")])
    return GenerationRequest(**kw)


def _engine(registry, providers, policy=None):
    router = ModelRouter(registry, policy=policy or RoutingPolicy(name="test", strategies=[], max_candidates=5))
    return ExecutionEngine(registry=registry, router=router, providers=providers)


@pytest.mark.asyncio
async def test_generate_success_no_retry_no_fallback():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider("test", [make_response("r1", "test", "m1")])
    engine = _engine(registry, {"test": provider})

    resp = await engine.generate(_req())
    assert resp.content == "ok"
    assert resp.execution.retries == 0
    assert resp.execution.fallback_used is False
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_generate_retries_transient_error_then_succeeds():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider(
        "test", [ProviderError("timeout-ish", provider="test", retryable=True), make_response("r1", "test", "m1")]
    )
    engine = _engine(registry, {"test": provider})

    resp = await engine.generate(_req(max_retries=3))
    assert resp.content == "ok"
    assert resp.execution.retries == 1
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_generate_fails_over_to_second_provider_on_nonretryable_error():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test-a", name="m1", priority=1))
    registry.register(ModelMetadata(provider="test-b", name="m2", priority=2))
    provider_a = ScriptedProvider("test-a", [ProviderAuthenticationError("bad key", provider="test-a")])
    provider_b = ScriptedProvider("test-b", [make_response("r1", "test-b", "m2")])
    engine = _engine(registry, {"test-a": provider_a, "test-b": provider_b})

    resp = await engine.generate(_req())
    assert resp.content == "ok"
    assert resp.execution.fallback_used is True
    assert resp.execution.attempted_models == ["test-a:m1", "test-b:m2"]
    assert provider_a.calls == 1  # no retries — auth errors aren't retryable
    assert provider_b.calls == 1


@pytest.mark.asyncio
async def test_all_candidates_failing_raises_all_providers_failed():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider("test", [ProviderAuthenticationError("bad key", provider="test")])
    engine = _engine(registry, {"test": provider})

    with pytest.raises(AllProvidersFailedError) as excinfo:
        await engine.generate(_req())
    assert excinfo.value.attempts == ["test:m1"]


@pytest.mark.asyncio
async def test_engine_level_timeout_fails_over_to_next_candidate():
    async def _slow_generate(request, *, model):
        await asyncio.sleep(5)
        return make_response("r1", "test-a", "m1")

    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test-a", name="m1", priority=1))
    registry.register(ModelMetadata(provider="test-b", name="m2", priority=2))
    slow_provider = ScriptedProvider("test-a", [])
    slow_provider.generate = _slow_generate
    fast_provider = ScriptedProvider("test-b", [make_response("r1", "test-b", "m2")])
    engine = _engine(registry, {"test-a": slow_provider, "test-b": fast_provider})

    resp = await engine.generate(_req(timeout_seconds=0.05))
    assert resp.execution.model == "m2"
    assert resp.execution.fallback_used is True


@pytest.mark.asyncio
async def test_cancellation_token_prevents_execution():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider("test", [make_response("r1", "test", "m1")])
    engine = _engine(registry, {"test": provider})
    token = asyncio.Event()
    token.set()

    with pytest.raises(asyncio.CancelledError):
        await engine.generate(_req(), cancellation_token=token)
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_cost_and_usage_tracker_are_invoked():
    class FakeCostCalculator:
        def calculate(self, model, usage):
            from ai_core.schemas.usage import CostBreakdown

            return CostBreakdown(total_cost_usd=1.23, is_estimate=False)

    class FakeUsageTracker:
        def __init__(self):
            self.recorded = []

        def record_generation(self, request, response):
            self.recorded.append(response)

        def record_embedding(self, request, response):
            pass

        def check_limits(self, request):
            pass

    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider("test", [make_response("r1", "test", "m1")])
    tracker = FakeUsageTracker()
    router = ModelRouter(registry, policy=RoutingPolicy(name="test", strategies=[], max_candidates=5))
    engine = ExecutionEngine(
        registry=registry, router=router, providers={"test": provider},
        cost_calculator=FakeCostCalculator(), usage_tracker=tracker,
    )

    resp = await engine.generate(_req())
    assert resp.cost.total_cost_usd == 1.23
    assert len(tracker.recorded) == 1


@pytest.mark.asyncio
async def test_streaming_success_yields_all_chunks():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1, capabilities={Capability.STREAMING}))
    chunks = [StreamChunk(request_id="r1", delta="Hel"), StreamChunk(request_id="r1", delta="lo", is_final=True)]
    provider = ScriptedProvider("test", [chunks])
    engine = _engine(registry, {"test": provider})

    collected = [c async for c in engine.stream(_req(stream=True))]
    assert "".join(c.delta for c in collected) == "Hello"


@pytest.mark.asyncio
async def test_streaming_fails_over_before_first_chunk():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test-a", name="m1", priority=1, capabilities={Capability.STREAMING}))
    registry.register(ModelMetadata(provider="test-b", name="m2", priority=2, capabilities={Capability.STREAMING}))
    provider_a = ScriptedProvider("test-a", [ProviderError("boom", provider="test-a", retryable=False)])
    provider_b = ScriptedProvider("test-b", [[StreamChunk(request_id="r1", delta="hi", is_final=True)]])
    engine = _engine(registry, {"test-a": provider_a, "test-b": provider_b})

    collected = [c async for c in engine.stream(_req(stream=True))]
    assert collected[0].delta == "hi"


@pytest.mark.asyncio
async def test_generate_batch_bounded_concurrency_returns_exceptions_inline():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider(
        "test", [make_response("r1", "test", "m1"), ProviderAuthenticationError("bad", provider="test")]
    )
    engine = _engine(registry, {"test": provider})

    results = await engine.generate_batch([_req(), _req()], max_concurrency=2)
    assert len(results) == 2
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], AllProvidersFailedError)


@pytest.mark.asyncio
async def test_embed_fails_over_across_embedding_candidates():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test-a", name="e1", priority=1, capabilities={Capability.EMBEDDING}))
    registry.register(ModelMetadata(provider="test-b", name="e2", priority=2, capabilities={Capability.EMBEDDING}))
    provider_a = ScriptedProvider("test-a", [ProviderError("down", provider="test-a", retryable=False)])
    provider_b = ScriptedProvider(
        "test-b", [EmbeddingResponse(request_id="r1", embeddings=[[0.1, 0.2]], model="e2", provider="test-b", dimensions=2)]
    )
    engine = _engine(registry, {"test-a": provider_a, "test-b": provider_b})

    resp = await engine.embed(EmbeddingRequest(input="hello"))
    assert resp.model == "e2"
