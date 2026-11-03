import pytest

from ai_core.embeddings.cache import InMemoryEmbeddingCache
from ai_core.embeddings.embedding_engine import EmbeddingEngine
from ai_core.embeddings.similarity_search import SimilaritySearchService
from ai_core.embeddings.vector_store import InMemoryVectorStore
from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.providers.base import ModelProviderAdapter
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability
from ai_core.schemas.requests import EmbeddingRequest
from ai_core.schemas.responses import EmbeddingResponse
import httpx


class CountingEmbedProvider(ModelProviderAdapter):
    provider_name = "test"

    def __init__(self):
        super().__init__(http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        self.embed_calls = 0
        self.last_inputs: list[str] = []

    async def generate(self, request, *, model):
        raise NotImplementedError

    async def stream(self, request, *, model):
        raise NotImplementedError
        yield  # pragma: no cover

    async def embed(self, request, *, model):
        self.embed_calls += 1
        self.last_inputs = request.as_list()
        vectors = [[float(len(t)), float(sum(map(ord, t)) % 100)] for t in request.as_list()]
        return EmbeddingResponse(
            request_id=request.request_id, embeddings=vectors, model=model, provider="test", dimensions=2
        )


def _engine_and_router():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="embed-1", priority=1, capabilities={Capability.EMBEDDING}))
    provider = CountingEmbedProvider()
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    exec_engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})
    return exec_engine, router, provider


@pytest.mark.asyncio
async def test_embedding_engine_cache_miss_then_hit():
    exec_engine, router, provider = _engine_and_router()
    engine = EmbeddingEngine(exec_engine, router, cache=InMemoryEmbeddingCache())

    first = await engine.embed(EmbeddingRequest(input=["hello world"]))
    assert first.cached == [False]
    assert provider.embed_calls == 1

    second = await engine.embed(EmbeddingRequest(input=["hello world"]))
    assert second.cached == [True]
    assert provider.embed_calls == 1  # no new provider call — served from cache
    assert second.embeddings == first.embeddings


@pytest.mark.asyncio
async def test_embedding_engine_partial_cache_hit_only_calls_provider_for_misses():
    exec_engine, router, provider = _engine_and_router()
    engine = EmbeddingEngine(exec_engine, router, cache=InMemoryEmbeddingCache())

    await engine.embed(EmbeddingRequest(input=["alpha"]))
    assert provider.embed_calls == 1

    response = await engine.embed(EmbeddingRequest(input=["alpha", "beta"]))
    assert response.cached == [True, False]
    assert provider.last_inputs == ["beta"]
    assert provider.embed_calls == 2


@pytest.mark.asyncio
async def test_embedding_engine_use_cache_false_always_calls_provider():
    exec_engine, router, provider = _engine_and_router()
    engine = EmbeddingEngine(exec_engine, router, cache=InMemoryEmbeddingCache())

    await engine.embed(EmbeddingRequest(input=["x"], use_cache=False))
    await engine.embed(EmbeddingRequest(input=["x"], use_cache=False))
    assert provider.embed_calls == 2


@pytest.mark.asyncio
async def test_in_memory_vector_store_upsert_and_query_ranks_by_similarity():
    store = InMemoryVectorStore()
    from ai_core.embeddings.vector_store import VectorRecord

    await store.upsert(
        [
            VectorRecord(id="a", vector=[1.0, 0.0], metadata={"topic": "cats"}),
            VectorRecord(id="b", vector=[0.0, 1.0], metadata={"topic": "dogs"}),
        ]
    )
    results = await store.query([1.0, 0.0], top_k=2)
    assert results[0].id == "a"
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_similarity_search_service_indexes_and_searches():
    exec_engine, router, provider = _engine_and_router()
    embedding_engine = EmbeddingEngine(exec_engine, router)
    store = InMemoryVectorStore()
    service = SimilaritySearchService(embedding_engine, store)

    await service.index([("doc1", "hello world", {"kind": "greeting"}), ("doc2", "goodbye world", {"kind": "farewell"})])
    results = await service.search("hello world", top_k=1)
    assert results[0].id == "doc1"
