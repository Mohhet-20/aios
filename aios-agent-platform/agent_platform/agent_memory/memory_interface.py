"""Memory Integration: a clean interface every memory backend (short-term,
long-term, semantic) satisfies. Per the agent platform scope boundary ("do NOT
build the Memory Platform"), this project ships exactly one minimal,
honest, in-process implementation — not a persistence layer, not
semantic/embedding-backed recall — so callers (agents, AgentExecutor,
future orchestration strategies) can depend on the interface today and
swap in a real Memory Platform later without changing a call site.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryBackend(ABC):
    @abstractmethod
    async def remember(self, agent_id: str, key: str, value: Any) -> None: ...

    @abstractmethod
    async def recall(self, agent_id: str, key: str) -> Any | None: ...

    @abstractmethod
    async def search(self, agent_id: str, query: str, *, top_k: int = 5) -> list[dict]: ...

    @abstractmethod
    async def recent(self, agent_id: str, *, limit: int = 20) -> list[dict]: ...

    @abstractmethod
    async def forget(self, agent_id: str, key: str | None = None) -> None: ...
