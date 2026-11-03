"""MemoryService: the choke point every memory read/write goes through —
gates each operation against the calling agent's own `memory_access`
config ({short_term, long_term, semantic} booleans already modeled on
AgentModel) before touching the backend, so an agent that wasn't granted
a given kind of memory access can't read or write it regardless of what
the backend itself would technically allow.
"""
from __future__ import annotations

from typing import Any

from agent_platform.agent_memory.in_memory_backend import InMemoryMemoryBackend
from agent_platform.agent_memory.memory_interface import MemoryBackend
from agent_platform.core.exceptions import AuthorizationError
from agent_platform.repositories.registry import RepositoryRegistry


class MemoryService:
    def __init__(self, repos: RepositoryRegistry, backend: MemoryBackend | None = None):
        self.repos = repos
        self.backend = backend or InMemoryMemoryBackend()

    async def _require_access(self, agent_id: str, kind: str) -> None:
        agent = await self.repos.agents.get_or_404(agent_id)
        if not (agent.memory_access or {}).get(kind, False):
            raise AuthorizationError(f"agent '{agent_id}' does not have '{kind}' memory access enabled")

    async def remember(self, agent_id: str, key: str, value: Any, *, kind: str = "short_term") -> None:
        await self._require_access(agent_id, kind)
        await self.backend.remember(agent_id, key, value)

    async def recall(self, agent_id: str, key: str, *, kind: str = "short_term") -> Any | None:
        await self._require_access(agent_id, kind)
        return await self.backend.recall(agent_id, key)

    async def search(self, agent_id: str, query: str, *, kind: str = "semantic", top_k: int = 5) -> list[dict]:
        await self._require_access(agent_id, kind)
        return await self.backend.search(agent_id, query, top_k=top_k)

    async def recent(self, agent_id: str, *, kind: str = "short_term", limit: int = 20) -> list[dict]:
        await self._require_access(agent_id, kind)
        return await self.backend.recent(agent_id, limit=limit)

    async def forget(self, agent_id: str, key: str | None = None, *, kind: str = "short_term") -> None:
        await self._require_access(agent_id, kind)
        await self.backend.forget(agent_id, key)
