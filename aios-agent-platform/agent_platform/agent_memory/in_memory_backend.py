"""The one memory backend this platform ships: a process-local dict, with
naive substring "search" standing in for real semantic recall. This is
intentionally not durable and not semantic — swapping in a real backend
(persisted, embedding-indexed via the AI Core's own EmbeddingEngine +
vector_store, which already exist and are ready to be reused here) is
future scope, not something MemoryService or any caller needs to change
for.
"""
from __future__ import annotations

from typing import Any

from agent_platform.agent_memory.memory_interface import MemoryBackend


class InMemoryMemoryBackend(MemoryBackend):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._order: dict[str, list[str]] = {}

    async def remember(self, agent_id: str, key: str, value: Any) -> None:
        bucket = self._store.setdefault(agent_id, {})
        bucket[key] = value
        order = self._order.setdefault(agent_id, [])
        if key in order:
            order.remove(key)
        order.append(key)

    async def recall(self, agent_id: str, key: str) -> Any | None:
        return self._store.get(agent_id, {}).get(key)

    async def search(self, agent_id: str, query: str, *, top_k: int = 5) -> list[dict]:
        bucket = self._store.get(agent_id, {})
        needle = query.lower()
        matches = [{"key": k, "value": v} for k, v in bucket.items() if needle in k.lower() or needle in str(v).lower()]
        return matches[:top_k]

    async def recent(self, agent_id: str, *, limit: int = 20) -> list[dict]:
        order = self._order.get(agent_id, [])
        bucket = self._store.get(agent_id, {})
        return [{"key": k, "value": bucket[k]} for k in reversed(order[-limit:])]

    async def forget(self, agent_id: str, key: str | None = None) -> None:
        if key is None:
            self._store.pop(agent_id, None)
            self._order.pop(agent_id, None)
            return
        self._store.get(agent_id, {}).pop(key, None)
        order = self._order.get(agent_id)
        if order and key in order:
            order.remove(key)
