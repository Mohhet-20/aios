from __future__ import annotations

import pytest

from perf_platform.caching.cache_service import CacheService
from perf_platform.core.exceptions import UnsupportedCacheLayerError

TENANT = "t-cache"


@pytest.mark.asyncio
async def test_set_then_get_hits_l1_and_persists(repos):
    svc = CacheService(repos)
    await svc.set(TENANT, "response", "resp:42", "cached-payload", ttl_seconds=60)
    assert await svc.get(TENANT, "response", "resp:42") == "cached-payload"


@pytest.mark.asyncio
async def test_miss_then_set_via_get_or_compute(repos):
    svc = CacheService(repos)
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return "computed-value"

    first = await svc.get_or_compute(TENANT, "prompt", "p1", compute)
    second = await svc.get_or_compute(TENANT, "prompt", "p1", compute)
    assert first == second == "computed-value"
    assert calls["n"] == 1  # second call was a cache hit, compute() not re-invoked


@pytest.mark.asyncio
async def test_invalidate(repos):
    svc = CacheService(repos)
    await svc.set(TENANT, "embedding", "e1", "vec-blob")
    assert await svc.invalidate(TENANT, "embedding", "e1") is True
    assert await svc.get(TENANT, "embedding", "e1") is None
    assert await svc.invalidate(TENANT, "embedding", "e1") is False


@pytest.mark.asyncio
async def test_unsupported_layer_rejected(repos):
    svc = CacheService(repos)
    with pytest.raises(UnsupportedCacheLayerError):
        await svc.get(TENANT, "not-a-real-layer", "k")


@pytest.mark.asyncio
async def test_stats_tracks_hits_and_misses(repos):
    svc = CacheService(repos)
    await svc.get(TENANT, "api", "missing-key")  # miss
    await svc.set(TENANT, "api", "k1", "v1")
    await svc.get(TENANT, "api", "k1")  # hit
    stats = await svc.stats(TENANT)
    api_stat = next(s for s in stats if s.layer == "api")
    assert api_stat.misses >= 1
    assert api_stat.hits >= 1


@pytest.mark.asyncio
async def test_sweep_expired_removes_expired_rows(repos):
    svc = CacheService(repos)
    await svc.set(TENANT, "disk", "expiring", "v", ttl_seconds=-1)
    removed = await svc.sweep_expired(TENANT)
    assert removed >= 1
    assert await svc.get(TENANT, "disk", "expiring") is None
