"""Performance / load tests. These run against the same real SQLite-
backed session every other test uses (not a mocked timing harness), and
assert on generous wall-clock ceilings — the goal is catching a genuine
pathological regression (e.g. an accidental O(n^2) scan introduced
later), not micro-benchmarking. Note on "load": SQLAlchemy's AsyncSession
is not safe for concurrent use from multiple coroutines against one
connection, so these are sequential bulk-volume tests, not parallel
request simulations — a real concurrent-load test belongs at the ASGI
layer with one session per request, which is what production traffic
actually looks like.
"""
from __future__ import annotations

import time

import pytest

from memory_platform.domain.enums import MemoryType
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel
from memory_platform.retrieval.retrieval_service import RetrievalService
from memory_platform.vector_store.vector_platform_service import VectorPlatformService

BULK_N = 300


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_bulk_memory_creation_and_keyword_search(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)

    started = time.perf_counter()
    for i in range(BULK_N):
        await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content=f"bulk fact number {i} about deployments")
    create_elapsed = time.perf_counter() - started
    assert create_elapsed < 15.0, f"bulk creation of {BULK_N} entries took {create_elapsed:.2f}s — investigate for a regression"

    started = time.perf_counter()
    results = await mem.search_keyword("ws-1", "deployments", limit=1000)
    search_elapsed = time.perf_counter() - started
    assert len(results) == BULK_N
    assert search_elapsed < 5.0, f"keyword search over {BULK_N} entries took {search_elapsed:.2f}s — investigate for a regression"


@pytest.mark.asyncio
async def test_bulk_retrieval_multi_stage_respects_top_k_at_scale(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    for i in range(BULK_N):
        await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content=f"scale test entry {i} about retrieval performance")

    retrieval = RetrievalService(repos)
    started = time.perf_counter()
    results = await retrieval.multi_stage_retrieve("ws-1", "retrieval performance", top_k=10)
    elapsed = time.perf_counter() - started
    assert len(results) == 10
    assert elapsed < 5.0, f"multi_stage_retrieve over {BULK_N} candidates took {elapsed:.2f}s — investigate for a regression"


@pytest.mark.asyncio
async def test_bulk_embedding_indexing_batches_correctly_at_scale(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    await _workspace(repos)
    vp = VectorPlatformService(repos, ai_core)
    items = [(f"chunk-{i}", f"bulk content number {i}", {}) for i in range(250)]

    started = time.perf_counter()
    records = await vp.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=items, batch_size=50)
    elapsed = time.perf_counter() - started

    assert len(records) == 250
    assert provider.calls == 5  # 250 / 50 = 5 batched embed calls, not 250 individual ones
    assert elapsed < 10.0, f"bulk embedding of 250 items took {elapsed:.2f}s — investigate for a regression"


@pytest.mark.asyncio
async def test_retention_sweep_at_scale(repos):
    import datetime as dt

    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    for i in range(BULK_N):
        await mem.create(workspace_id="ws-1", memory_type=MemoryType.SHORT_TERM, scope_type="user", scope_id="u-1", content=f"short-lived fact {i}")

    far_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
    started = time.perf_counter()
    result = await mem.apply_retention_policies("ws-1", as_of=far_future)
    elapsed = time.perf_counter() - started

    assert result["expired_count"] == BULK_N
    assert elapsed < 10.0, f"retention sweep over {BULK_N} entries took {elapsed:.2f}s — investigate for a regression"
