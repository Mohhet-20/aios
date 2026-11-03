import pytest

from ai_core.config.settings import AICoreSettings
from ai_core.embeddings.cache import InMemoryEmbeddingCache
from ai_core.embeddings.embedding_engine import EmbeddingEngine
from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability, Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.tools import ToolDefinition
from ai_core.utils.exceptions import RequestValidationError

from tests.execution.conftest import ScriptedProvider, make_response


def _engine(settings=None):
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1, capabilities={Capability.TOOL_CALLING, Capability.STREAMING}))
    provider = ScriptedProvider("test", [make_response("r1", "test", "m1")])
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    return ExecutionEngine(registry=registry, router=router, providers={"test": provider}, settings=settings)


@pytest.mark.asyncio
async def test_tool_calling_disabled_by_settings_raises():
    settings = AICoreSettings(enable_tool_calling=False)
    engine = _engine(settings)
    req = GenerationRequest(
        messages=[ChatMessage(role=Role.USER, content="hi")],
        tools=[ToolDefinition(name="x", description="x")],
    )
    with pytest.raises(RequestValidationError):
        await engine.generate(req)


@pytest.mark.asyncio
async def test_streaming_disabled_by_settings_raises():
    settings = AICoreSettings(enable_streaming=False)
    engine = _engine(settings)
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], stream=True)
    with pytest.raises(RequestValidationError):
        async for _ in engine.stream(req):
            pass


@pytest.mark.asyncio
async def test_embedding_cache_disabled_by_settings_forces_provider_call_every_time():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="e1", priority=1, capabilities={Capability.EMBEDDING}))

    class CountingProvider(ScriptedProvider):
        pass

    from ai_core.schemas.responses import EmbeddingResponse

    provider = ScriptedProvider(
        "test",
        [
            EmbeddingResponse(request_id="r1", embeddings=[[0.1]], model="e1", provider="test", dimensions=1),
            EmbeddingResponse(request_id="r2", embeddings=[[0.1]], model="e1", provider="test", dimensions=1),
        ],
    )
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    exec_engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})
    settings = AICoreSettings(enable_embedding_cache=False)
    engine = EmbeddingEngine(exec_engine, router, cache=InMemoryEmbeddingCache(), settings=settings)

    await engine.embed(EmbeddingRequest(input="x"))
    await engine.embed(EmbeddingRequest(input="x"))
    assert provider.calls == 2
