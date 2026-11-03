"""Memory Integration: the MemoryService choke point, gated by each
agent's own `memory_access` config. Per the Phase 6 scope boundary this
is backed by the one minimal in-process implementation the platform
ships — real persistence/semantic recall is future scope."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_memory_service
from agent_platform.agent_memory.memory_service import MemoryService

router = APIRouter(prefix="/agents/{agent_id}/memory", tags=["memory"])


class RememberRequest(BaseModel):
    key: str
    value: Any
    kind: str = "short_term"


@router.put("")
async def remember(agent_id: str, body: RememberRequest, svc: MemoryService = Depends(get_memory_service)):
    await svc.remember(agent_id, body.key, body.value, kind=body.kind)
    return {"status": "ok"}


@router.get("/{key}")
async def recall(agent_id: str, key: str, kind: str = "short_term", svc: MemoryService = Depends(get_memory_service)):
    return {"key": key, "value": await svc.recall(agent_id, key, kind=kind)}


@router.get("")
async def recent(agent_id: str, kind: str = "short_term", limit: int = 20, svc: MemoryService = Depends(get_memory_service)):
    return await svc.recent(agent_id, kind=kind, limit=limit)


@router.get("/search/{query}")
async def search(agent_id: str, query: str, kind: str = "semantic", top_k: int = 5, svc: MemoryService = Depends(get_memory_service)):
    return await svc.search(agent_id, query, kind=kind, top_k=top_k)


@router.delete("/{key}", status_code=204)
async def forget(agent_id: str, key: str, kind: str = "short_term", svc: MemoryService = Depends(get_memory_service)):
    await svc.forget(agent_id, key, kind=kind)
