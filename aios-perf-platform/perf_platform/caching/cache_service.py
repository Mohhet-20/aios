"""Multi-level cache platform. Two tiers, composed rather than
conflated:

L1 — `LRUTTLCache` (lru.py): in-process, sub-microsecond, no I/O. Used
transparently for every layer as the first lookup.

L2 — `CacheService`: DB-backed (`CacheEntryModel`), durable and shared
across processes/replicas — the honest implementation of what a real
Redis/disk/CDN-backed layer's *contract* looks like (get/set/invalidate
with TTL and hit/miss accounting) without this platform actually
shipping a Redis or CDN client. `CacheLayer` is a label on the row, not
a different code path — "redis", "disk", "cdn" etc. all go through the
same DB-backed store here; wiring an actual Redis/CDN client behind the
same interface is a swap-in, not a redesign (see README's disclosed
scope boundaries).

`get_or_compute` is the method every consumer (prompt cache, embedding
cache, response cache, ...) actually calls: L1 hit avoids the DB
entirely; L1 miss + L2 hit repopulates L1; miss on both calls the
supplied (sync) compute function, and writes through both levels.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import timedelta
from typing import Any, Callable

from perf_platform.caching.lru import LRUTTLCache
from perf_platform.config.settings import get_settings
from perf_platform.core.exceptions import UnsupportedCacheLayerError
from perf_platform.models.cache import CacheEntryModel, CacheStatModel
from perf_platform.repositories.registry import RepositoryRegistry
from perf_platform.clock import utc_now

# One process-wide L1 cache per layer — shared across tenants (keys are
# namespaced by tenant below) since the whole point of L1 is to avoid
# per-tenant setup cost; capacity is what actually bounds memory use.
_L1_CACHES: dict[str, LRUTTLCache[str, str]] = {}

# Commit-spanning get-or-create lock, keyed per (tenant, layer, key) —
# the same pattern established across every other AIOS platform for a
# check-then-act sequence that spans multiple statements: two
# concurrent `set()` calls for the same key would otherwise both see
# "no existing row" and both INSERT, producing a duplicate row (or a
# unique-constraint race, depending on the backend). Held until the
# commit actually lands, not just until the row is flushed.
_write_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def _l1_for_layer(layer: str) -> LRUTTLCache[str, str]:
    settings = get_settings()
    if layer not in _L1_CACHES:
        _L1_CACHES[layer] = LRUTTLCache(max_entries=settings.memory_cache_max_entries)
    return _L1_CACHES[layer]


def _l1_key(tenant_id: str, key: str) -> str:
    return f"{tenant_id}:{key}"


class CacheService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    def _check_layer(self, layer: str) -> None:
        if layer not in self.settings.cache_layers:
            raise UnsupportedCacheLayerError(f"Unsupported cache layer '{layer}'")

    async def get(self, tenant_id: str, layer: str, key: str) -> str | None:
        self._check_layer(layer)
        l1 = _l1_for_layer(layer)
        hit = l1.get(_l1_key(tenant_id, key))
        if hit is not None:
            await self._record(tenant_id, layer, hit=True)
            return hit

        row = await self.repos.cache_entries.get_by_key(tenant_id, layer, key)
        if row is None or (row.ttl_expires_at is not None and row.ttl_expires_at <= utc_now()):
            await self._record(tenant_id, layer, hit=False)
            return None
        row.hit_count += 1
        l1.set(_l1_key(tenant_id, key), row.value, ttl_seconds=self.settings.cache_default_ttl_seconds)
        await self._record(tenant_id, layer, hit=True)
        return row.value

    async def set(self, tenant_id: str, layer: str, key: str, value: str, *, ttl_seconds: int | None = None) -> CacheEntryModel:
        self._check_layer(layer)
        ttl = ttl_seconds if ttl_seconds is not None else self.settings.cache_default_ttl_seconds
        expires_at = utc_now() + timedelta(seconds=ttl) if ttl else None

        lock_key = f"{tenant_id}:{layer}:{key}"
        async with _write_locks[lock_key]:
            existing = await self.repos.cache_entries.get_by_key(tenant_id, layer, key)
            if existing is not None:
                existing.value = value
                existing.ttl_expires_at = expires_at
                existing.size_bytes = len(value.encode("utf-8"))
                row = existing
            else:
                row = await self.repos.cache_entries.add(
                    CacheEntryModel(tenant_id=tenant_id, layer=layer, key=key, value=value, ttl_expires_at=expires_at, size_bytes=len(value.encode("utf-8")))
                )
            await self.repos.session.commit()
        _l1_for_layer(layer).set(_l1_key(tenant_id, key), value, ttl_seconds=ttl)
        return row

    async def invalidate(self, tenant_id: str, layer: str, key: str) -> bool:
        self._check_layer(layer)
        _l1_for_layer(layer).invalidate(_l1_key(tenant_id, key))
        row = await self.repos.cache_entries.get_by_key(tenant_id, layer, key)
        if row is None:
            return False
        await self.repos.cache_entries.delete(row, hard=True)
        await self.repos.session.commit()
        return True

    async def get_or_compute(self, tenant_id: str, layer: str, key: str, compute: Callable[[], Any], *, ttl_seconds: int | None = None) -> Any:
        """The one method most callers should use: cache-aside with
        both levels handled transparently. `compute` must be a plain
        sync callable returning a JSON-serializable-as-string value —
        callers needing structured data serialize before calling this
        and deserialize the result themselves, keeping this method
        agnostic of the payload shape."""
        cached = await self.get(tenant_id, layer, key)
        if cached is not None:
            return cached
        value = compute()
        await self.set(tenant_id, layer, key, value, ttl_seconds=ttl_seconds)
        return value

    async def _record(self, tenant_id: str, layer: str, *, hit: bool) -> None:
        stat = await self.repos.cache_stats.get_for_layer(tenant_id, layer)
        if stat is None:
            stat = await self.repos.cache_stats.add(CacheStatModel(tenant_id=tenant_id, layer=layer))
        if hit:
            stat.hits += 1
        else:
            stat.misses += 1
        total = stat.hits + stat.misses
        stat.hit_rate_pct = round(100.0 * stat.hits / total, 2) if total else 0.0
        await self.repos.session.commit()

    async def stats(self, tenant_id: str) -> list[CacheStatModel]:
        return await self.repos.cache_stats.list_for_tenant(tenant_id)

    async def sweep_expired(self, tenant_id: str) -> int:
        """Explicit cleanup pass for the DB-backed L2 layer — expired
        rows are already treated as misses on read (see `get`), so this
        is purely about reclaiming storage, not correctness."""
        expired = await self.repos.cache_entries.list_expired(tenant_id)
        for row in expired:
            await self.repos.cache_entries.delete(row, hard=True)
        await self.repos.session.commit()
        return len(expired)
