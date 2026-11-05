"""Real concurrency stress test: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. This platform has exactly one commit-spanning-lock
check-then-act sequence: `CacheService.set` (get-or-create by
tenant_id+layer+key). This test proves the per-key `asyncio.Lock`
actually prevents the duplicate-row race a naive "check then write"
sequence would produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from perf_platform.caching.cache_service import CacheService
from perf_platform.database.session import session_scope
from perf_platform.repositories.registry import RepositoryRegistry

TENANT = "stress-tenant"


async def _set_once(i: int) -> str:
    entry_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = CacheService(repos)
        entry = await service.set(TENANT, "response", "stress-key", f"value-from-caller-{i}")
        entry_id = entry.id
    return entry_id


@pytest.mark.asyncio
async def test_concurrent_cache_set_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_set_once(i) for i in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # cache entry row (same id) — whichever caller's write landed last
    # wins the value, but there is exactly one row.
    assert len(set(results)) == 1

    async for session in session_scope():
        repos = RepositoryRegistry(session)
        rows = await repos.cache_entries.list_for_layer(TENANT, "response", limit=100)
    assert sum(1 for r in rows if r.key == "stress-key") == 1
