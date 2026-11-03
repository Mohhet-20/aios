from __future__ import annotations

from perf_platform.caching.lru import LRUTTLCache


def test_basic_get_set():
    c = LRUTTLCache(max_entries=10)
    assert c.get("missing") is None
    c.set("a", "1")
    assert c.get("a") == "1"
    assert c.hits == 1
    assert c.misses == 1


def test_lru_eviction_order():
    c = LRUTTLCache(max_entries=2)
    c.set("a", 1)
    c.set("b", 2)
    c.get("a")  # touch 'a' so 'b' becomes least-recently-used
    c.set("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3
    assert c.evictions >= 1


def test_ttl_expiry():
    c = LRUTTLCache(max_entries=10)
    c.set("x", "v", ttl_seconds=10, now=0.0)
    assert c.get("x", now=5.0) == "v"
    assert c.get("x", now=11.0) is None


def test_sweep_expired():
    c = LRUTTLCache(max_entries=10)
    c.set("x", "v", ttl_seconds=1, now=0.0)
    c.set("y", "v", ttl_seconds=None, now=0.0)
    removed = c.sweep_expired(now=5.0)
    assert removed == 1
    assert len(c) == 1


def test_invalidate():
    c = LRUTTLCache(max_entries=10)
    c.set("a", 1)
    assert c.invalidate("a") is True
    assert c.invalidate("a") is False
    assert c.get("a") is None


def test_stats_hit_rate():
    c = LRUTTLCache(max_entries=10)
    c.set("a", 1)
    c.get("a")
    c.get("a")
    c.get("missing")
    stats = c.stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate_pct"] == round(100 * 2 / 3, 2)
