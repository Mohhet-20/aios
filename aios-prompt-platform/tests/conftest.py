import contextlib
import os
import tempfile
import uuid

# Must be set before any prompt_platform module is imported.
_TMP_DB = os.path.join(tempfile.gettempdir(), f"prompt_platform_test_{uuid.uuid4().hex}.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP_DB}"
os.environ["SECRET_KEY"] = "x" * 32
os.environ["APP_ENV"] = "test"

import httpx
import pytest
import pytest_asyncio

from ai_core.bootstrap import AICoreContext
from ai_core.cost.cost_calculator import CostCalculator
from ai_core.cost.usage_tracker import UsageTracker
from ai_core.embeddings.cache import InMemoryEmbeddingCache
from ai_core.embeddings.embedding_engine import EmbeddingEngine
from ai_core.embeddings.vector_store import InMemoryVectorStore
from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.providers.base import ModelProviderAdapter
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability
from ai_core.schemas.enums import FinishReason
from ai_core.schemas.responses import ExecutionMetadata, GenerationResponse
from ai_core.schemas.usage import TokenUsage
from ai_core.tool_calling.executor import ToolExecutor
from ai_core.tool_calling.registry import ToolRegistry

from prompt_platform.database.session import async_session_factory, dispose_engine, init_models
from prompt_platform.repositories.registry import RepositoryRegistry
import prompt_platform.models  # noqa: F401 — populate Base.metadata


def make_response(content: str = "This is a scripted test response.", *, provider: str = "test", model: str = "m1") -> GenerationResponse:
    return GenerationResponse(
        content=content,
        finish_reason=FinishReason.STOP,
        usage=TokenUsage(input_tokens=20, output_tokens=10),
        execution=ExecutionMetadata(request_id="r", provider=provider, model=model, latency_ms=5.0),
    )


class ScriptedProvider(ModelProviderAdapter):
    """Reusable scripted double, same shape as ai_core's own test doubles
    but living here so this platform's test suite has zero dependency on
    ai_core's `tests/` package (not part of its installed surface)."""

    def __init__(self, provider_name: str, script: list | None = None):
        super().__init__(http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        self.provider_name = provider_name
        self._script = list(script or [])
        self.calls = 0

    def push(self, item) -> None:
        self._script.append(item)

    async def generate(self, request, *, model):
        self.calls += 1
        if not self._script:
            return make_response(provider=self.provider_name, model=model)
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def stream(self, request, *, model):
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        for chunk in item:
            yield chunk

    async def embed(self, request, *, model):
        self.calls += 1
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def build_scripted_ai_core(*, extra_models: list[ModelMetadata] | None = None, script: list | None = None) -> tuple[AICoreContext, ScriptedProvider]:
    """A ready-to-use AICoreContext backed entirely by a ScriptedProvider —
    no network access, deterministic responses, used by every test module
    in this platform that needs to "execute" a prompt."""
    registry = ModelRegistry()
    registry.register(
        ModelMetadata(
            provider="test", name="m1", priority=1,
            capabilities={Capability.STREAMING, Capability.TOOL_CALLING, Capability.JSON_OUTPUT},
            context_window=128_000,
        )
    )
    registry.register(ModelMetadata(provider="test", name="embed-1", priority=1, capabilities={Capability.EMBEDDING}))
    for m in extra_models or []:
        registry.register(m)

    provider = ScriptedProvider("test", script)
    router = ModelRouter(registry, policy=RoutingPolicy.default())
    cost_calculator = CostCalculator()
    usage_tracker = UsageTracker(registry=registry, cost_calculator=cost_calculator)
    execution_engine = ExecutionEngine(
        registry=registry, router=router, providers={"test": provider},
        cost_calculator=cost_calculator, usage_tracker=usage_tracker,
    )
    embedding_engine = EmbeddingEngine(execution_engine, router, cache=InMemoryEmbeddingCache())
    tool_registry = ToolRegistry()
    context = AICoreContext(
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
    return context, provider


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema():
    await init_models()
    yield
    await dispose_engine()
    # Windows refuses to delete a file another handle still has open; it is a scratch file in the temp dir.
    with contextlib.suppress(PermissionError, FileNotFoundError):
        os.remove(_TMP_DB)


@pytest_asyncio.fixture
async def db_session():
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def repos(db_session) -> RepositoryRegistry:
    return RepositoryRegistry(db_session)


@pytest.fixture
def scripted_ai_core():
    context, provider = build_scripted_ai_core()
    return context, provider
