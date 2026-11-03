"""Real, in-process L1 cache: a pure-Python TTL + LRU cache with O(1)
get/set/evict, no DB round trip. This is the actual hot-path
implementation a service would call for memoization within a single
process (prompt cache, embedding cache, response cache, etc. all reuse
this before ever touching the DB-backed L2 layer in cache_service.py).

No I/O, no async — safe to call from anywhere. Deliberately dependency-
free so it has zero import cost and can be unit-benchmarked in
isolation (see tests/performance/test_cache_benchmark.py)."""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float | None


class LRUTTLCache(Generic[K, V]):
    """Fixed-capacity LRU cache with optional per-entry TTL.

    - O(1) get/set/evict via `OrderedDict.move_to_end` / `popitem`.
    - Expired entries are evicted lazily on access (checked before any
      LRU touch), not via a background sweep — this keeps the cache
      dependency-free and correct under test without a real clock
      thread. `sweep_expired()` is provided for callers that want an
      explicit periodic cleanup pass instead (e.g. a scheduled task).
    """

    def __init__(self, max_entries: int = 5000, default_ttl_seconds: float | None = None):
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self._store: OrderedDict[K, _Entry[V]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _is_expired(self, entry: _Entry[V], *, now: float) -> bool:
        return entry.expires_at is not None and entry.expires_at <= now

    def get(self, key: K, *, now: float | None = None) -> V | None:
        now = now if now is not None else time.monotonic()
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        if self._is_expired(entry, now=now):
            del self._store[key]
            self.misses += 1
            self.evictions += 1
            return None
        self._store.move_to_end(key)
        self.hits += 1
        return entry.value

    def set(self, key: K, value: V, *, ttl_seconds: float | None = None, now: float | None = None) -> None:
        now = now if now is not None else time.monotonic()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = now + ttl if ttl is not None else None
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self.max_entries:
            self._store.popitem(last=False)  # evict least-recently-used
            self.evictions += 1
        self._store[key] = _Entry(value=value, expires_at=expires_at)

    def invalidate(self, key: K) -> bool:
        return self._store.pop(key, None) is not None

    def sweep_expired(self, *, now: float | None = None) -> int:
        now = now if now is not None else time.monotonic()
        expired_keys = [k for k, e in self._store.items() if self._is_expired(e, now=now)]
        for k in expired_keys:
            del self._store[k]
        self.evictions += len(expired_keys)
        return len(expired_keys)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    @property
    def hit_rate_pct(self) -> float:
        total = self.hits + self.misses
        return round(100.0 * self.hits / total, 2) if total else 0.0

    def stats(self) -> dict[str, Any]:
        return {
            "size": len(self._store),
            "max_entries": self.max_entries,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate_pct": self.hit_rate_pct,
        }
