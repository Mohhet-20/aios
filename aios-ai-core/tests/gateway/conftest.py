import httpx
import pytest_asyncio

from ai_core.bootstrap import AICoreContext
from ai_core.cost.cost_calculator import CostCalculator
from ai_core.cost.usage_tracker import UsageTracker
from ai_core.embeddings.cache import InMemoryEmbeddingCache
from ai_core.embeddings.embedding_engine import EmbeddingEngine
from ai_core.embeddings.vector_store import InMemoryVectorStore
from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.gateway.app import create_app
from ai_core.providers.base import ModelProviderAdapter
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability
from ai_core.schemas.responses import EmbeddingResponse
from ai_core.tool_calling.executor import ToolExecutor
from ai_core.tool_calling.registry import ToolRegistry

from tests.execution.conftest import make_response


class GatewayScriptedProvider(ModelProviderAdapter):
    """Like tests/execution/conftest.py's ScriptedProvider but with
    independent per-method queues — gateway tests exercise generate/
    stream/embed somewhat interchangeably across different endpoints
    hitting the same provider instance, so a single shared queue (the
    right model for testing ExecutionEngine's own call sequencing) would
    cause cross-method contamination here."""

    provider_name = "test"

    def __init__(self, *, generate_responses=None, stream_responses=None, embed_responses=None):
        super().__init__(http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        self._generate = list(generate_responses or [])
        self._stream = list(stream_responses or [])
        self._embed = list(embed_responses or [])

    async def generate(self, request, *, model):
        return self._generate.pop(0)

    async def stream(self, request, *, model):
        for chunk in self._stream.pop(0):
            yield chunk

    async def embed(self, request, *, model):
        return self._embed.pop(0)


def build_test_context() -> AICoreContext:
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1, capabilities={Capability.STREAMING}))
    registry.register(ModelMetadata(provider="test", name="embed-1", priority=1, capabilities={Capability.EMBEDDING}))

    provider = GatewayScriptedProvider(
        generate_responses=[
            make_response("r1", "test", "m1", content="hello from gateway"),
            make_response("r2", "test", "m1", content="hello again"),
        ],
        stream_responses=[
            [__import__("ai_core.schemas.responses", fromlist=["StreamChunk"]).StreamChunk(request_id="r1", delta="hi", is_final=True)]
        ],
        embed_responses=[
            EmbeddingResponse(request_id="r1", embeddings=[[0.1, 0.2]], model="embed-1", provider="test", dimensions=2)
        ],
    )
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    cost_calculator = CostCalculator()
    usage_tracker = UsageTracker(registry=registry, cost_calculator=cost_calculator)
    execution_engine = ExecutionEngine(
        registry=registry, router=router, providers={"test": provider},
        cost_calculator=cost_calculator, usage_tracker=usage_tracker,
    )
    embedding_engine = EmbeddingEngine(execution_engine, router, cache=InMemoryEmbeddingCache())
    tool_registry = ToolRegistry()
    return AICoreContext(
        settings=execution_engine.settings,
        registry=registry,
        router=router,
        execution_engine=execution_engine,
        embedding_engine=embedding_engine,
        usage_tracker=usage_tracker,
        cost_calculator=cost_calculator,
        tool_registry=tool_registry,
        tool_executor=ToolExecutor(tool_registry),
        vector_store=InMemoryVectorStore(),
    )


@pytest_asyncio.fixture
async def gateway_client():
    context = build_test_context()
    app = create_app(context=context)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
