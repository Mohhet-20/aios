"""One-call wiring of the entire AI Core stack from settings: registry (with
seed data), router, provider adapters, cost calculator, usage tracker,
observability logger, execution engine, embedding engine, and tool
registry. The HTTP gateway uses this; any standalone Python caller
(a script, a notebook, a test) can use it too instead of hand-assembling
every layer.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_core.config.settings import AICoreSettings, get_settings
from ai_core.cost.cost_calculator import CostCalculator
from ai_core.cost.usage_tracker import UsageTracker
from ai_core.embeddings.cache import InMemoryEmbeddingCache
from ai_core.embeddings.embedding_engine import EmbeddingEngine
from ai_core.embeddings.vector_store import InMemoryVectorStore
from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.observability.logger import StructlogObservabilityLogger
from ai_core.observability.metrics import CompositeObservabilityLogger, PrometheusObservabilityLogger
from ai_core.providers.registry_bootstrap import build_default_providers
from ai_core.registry.model_registry import ModelRegistry
from ai_core.registry.seed_data import build_seeded_registry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.tool_calling.executor import ToolExecutor
from ai_core.tool_calling.registry import ToolRegistry


@dataclass
class AICoreContext:
    settings: AICoreSettings
    registry: ModelRegistry
    router: ModelRouter
    execution_engine: ExecutionEngine
    embedding_engine: EmbeddingEngine
    usage_tracker: UsageTracker
    cost_calculator: CostCalculator
    tool_registry: ToolRegistry
    tool_executor: ToolExecutor
    vector_store: InMemoryVectorStore


def build_ai_core(settings: AICoreSettings | None = None) -> AICoreContext:
    settings = settings or get_settings()
    registry = build_seeded_registry()
    providers = build_default_providers(settings)
    router = ModelRouter(registry, policy=RoutingPolicy.default())

    cost_calculator = CostCalculator()
    usage_tracker = UsageTracker(settings=settings, registry=registry, cost_calculator=cost_calculator)
    logger = CompositeObservabilityLogger([StructlogObservabilityLogger(), PrometheusObservabilityLogger()])

    execution_engine = ExecutionEngine(
        registry=registry, router=router, providers=providers, settings=settings,
        cost_calculator=cost_calculator, usage_tracker=usage_tracker, logger=logger,
    )
    embedding_engine = EmbeddingEngine(execution_engine, router, cache=InMemoryEmbeddingCache(), settings=settings)

    tool_registry = ToolRegistry()
    tool_executor = ToolExecutor(tool_registry)

    return AICoreContext(
        settings=settings,
        registry=registry,
        router=router,
        execution_engine=execution_engine,
        embedding_engine=embedding_engine,
        usage_tracker=usage_tracker,
        cost_calculator=cost_calculator,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        vector_store=InMemoryVectorStore(),
    )


async def aclose_ai_core(context: AICoreContext) -> None:
    """Closes every provider adapter's owned HTTP client. Wired into the
    gateway's lifespan shutdown (see `ai_core.gateway.app`) so outbound
    connections to OpenAI/Anthropic/Gemini/etc. are released cleanly on
    SIGTERM instead of leaking until the process exits."""
    for provider in context.execution_engine.providers.values():
        await provider.aclose()
