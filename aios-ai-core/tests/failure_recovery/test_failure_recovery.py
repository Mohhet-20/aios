"""Dedicated failure-recovery scenarios distinct from the execution engine's
own unit tests: a provider that's flaky-then-recovers, a fully-dead
provider chain surfacing a diagnosable error, and batch-level fault
isolation (one bad request never takes down the others).
"""
import pytest

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.providers.base import ModelProviderAdapter
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.utils.exceptions import AllProvidersFailedError, ProviderAuthenticationError, ProviderError

from tests.execution.conftest import ScriptedProvider, make_response

import httpx


class FlakyThenRecoversProvider(ModelProviderAdapter):
    """Fails the first N calls with a retryable transient error, then
    succeeds — simulates a provider having a brief outage that resolves
    without any operator intervention."""

    provider_name = "test"

    def __init__(self, fail_count: int):
        super().__init__(http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        self._remaining_failures = fail_count
        self.calls = 0

    async def generate(self, request, *, model):
        self.calls += 1
        if self._remaining_failures > 0:
            self._remaining_failures -= 1
            raise ProviderError("transient upstream 503", provider="test", retryable=True)
        return make_response("r-recovered", "test", model, content="recovered")

    async def stream(self, request, *, model):
        raise NotImplementedError
        yield  # pragma: no cover


def _req():
    return GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], max_retries=5)


@pytest.mark.asyncio
async def test_engine_recovers_after_transient_provider_outage():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = FlakyThenRecoversProvider(fail_count=3)
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})

    response = await engine.generate(_req())
    assert response.content == "recovered"
    assert response.execution.retries == 3
    assert provider.calls == 4


@pytest.mark.asyncio
async def test_full_outage_across_all_candidates_surfaces_diagnosable_error():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test-a", name="m1", priority=1))
    registry.register(ModelMetadata(provider="test-b", name="m2", priority=2))
    provider_a = ScriptedProvider("test-a", [ProviderAuthenticationError("down", provider="test-a")])
    provider_b = ScriptedProvider("test-b", [ProviderAuthenticationError("also down", provider="test-b")])
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=2))
    engine = ExecutionEngine(registry=registry, router=router, providers={"test-a": provider_a, "test-b": provider_b})

    with pytest.raises(AllProvidersFailedError) as excinfo:
        await engine.generate(_req())
    assert excinfo.value.attempts == ["test-a:m1", "test-b:m2"]
    assert excinfo.value.__cause__ is not None  # original error preserved for debugging


@pytest.mark.asyncio
async def test_batch_execution_isolates_faults_between_requests():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    # 10 requests: every 3rd one fails permanently, the rest succeed.
    script = []
    for i in range(10):
        if i % 3 == 0:
            script.append(ProviderAuthenticationError(f"bad request {i}", provider="test"))
        else:
            script.append(make_response(f"r{i}", "test", "m1"))
    provider = ScriptedProvider("test", script)
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})

    requests = [GenerationRequest(messages=[ChatMessage(role=Role.USER, content=f"r{i}")]) for i in range(10)]
    results = await engine.generate_batch(requests, max_concurrency=3)

    failures = [r for r in results if isinstance(r, Exception)]
    successes = [r for r in results if not isinstance(r, Exception)]
    assert len(failures) == 4  # indices 0, 3, 6, 9
    assert len(successes) == 6
    assert all(isinstance(f, AllProvidersFailedError) for f in failures)
