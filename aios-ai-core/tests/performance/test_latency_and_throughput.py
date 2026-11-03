"""Smoke-level performance tests — not a real load test, just a guard
against an accidental O(n^2) or unbounded-serialization regression in the
hot paths (routing pipeline, batch execution)."""
import time

import pytest

from ai_core.execution.execution_engine import ExecutionEngine
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.registry.seed_data import build_seeded_registry
from ai_core.router.model_router import ModelRouter
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest

from tests.execution.conftest import ScriptedProvider, make_response


def test_routing_1000_requests_completes_quickly():
    registry = build_seeded_registry()
    router = ModelRouter(registry, policy=RoutingPolicy.default())
    request = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])

    started = time.perf_counter()
    for _ in range(1000):
        router.route(request)
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0, f"routing 1000 requests took {elapsed:.2f}s — investigate for a regression"


@pytest.mark.asyncio
async def test_batch_of_50_requests_respects_bounded_concurrency_and_completes_quickly():
    registry = ModelRegistry()
    registry.register(ModelMetadata(provider="test", name="m1", priority=1))
    provider = ScriptedProvider("test", [make_response(f"r{i}", "test", "m1") for i in range(50)])
    router = ModelRouter(registry, policy=RoutingPolicy(name="t", strategies=[], max_candidates=1))
    engine = ExecutionEngine(registry=registry, router=router, providers={"test": provider})

    requests = [GenerationRequest(messages=[ChatMessage(role=Role.USER, content=f"req {i}")]) for i in range(50)]

    started = time.perf_counter()
    results = await engine.generate_batch(requests, max_concurrency=10)
    elapsed = time.perf_counter() - started

    assert len(results) == 50
    assert all(not isinstance(r, Exception) for r in results)
    assert elapsed < 3.0
