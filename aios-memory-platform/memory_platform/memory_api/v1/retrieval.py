"""Retrieval Engine: semantic/keyword/hybrid search, agent/user/project/
time-aware filtering, and multi-stage retrieval with re-ranking, query
expansion, and top-K selection — the primary query surface every AI
subsystem in the AIOS reads memory/knowledge through."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends

from memory_platform.domain.enums import SearchMode
from memory_platform.memory_api.dependencies import get_current_actor_id, get_retrieval_service
from memory_platform.retrieval.retrieval_service import RetrievalService

router = APIRouter(prefix="/workspaces/{workspace_id}/retrieval", tags=["retrieval"])


def _serialize_results(results: list) -> list[dict]:
    return [asdict(r) for r in results]


@router.get("/keyword")
async def keyword_search(workspace_id: str, query: str, memory_type: str | None = None, limit: int = 50, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.keyword_search(workspace_id, query, memory_type=memory_type, limit=limit))


@router.get("/semantic")
async def semantic_search(workspace_id: str, query: str, source_type: str = "memory_entry", top_k: int = 10, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.semantic_search(workspace_id, query, source_type=source_type, top_k=top_k))


@router.get("/hybrid")
async def hybrid_search(workspace_id: str, query: str, memory_type: str | None = None, top_k: int = 10, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.hybrid_search(workspace_id, query, memory_type=memory_type, top_k=top_k))


@router.get("/agent-aware/{agent_id}")
async def agent_aware_search(workspace_id: str, agent_id: str, query: str, mode: SearchMode = SearchMode.HYBRID, top_k: int = 10, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.agent_aware_search(workspace_id, agent_id, query, mode=mode, top_k=top_k))


@router.get("/user-aware/{user_id}")
async def user_aware_search(workspace_id: str, user_id: str, query: str, mode: SearchMode = SearchMode.HYBRID, top_k: int = 10, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.user_aware_search(workspace_id, user_id, query, mode=mode, top_k=top_k))


@router.get("/project-aware/{project_id}")
async def project_aware_search(workspace_id: str, project_id: str, query: str, mode: SearchMode = SearchMode.HYBRID, top_k: int = 10, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.project_aware_search(workspace_id, project_id, query, mode=mode, top_k=top_k))


@router.get("/time-aware")
async def time_aware_search(workspace_id: str, query: str, start: datetime, end: datetime, mode: SearchMode = SearchMode.HYBRID, top_k: int = 10, svc: RetrievalService = Depends(get_retrieval_service)):
    return _serialize_results(await svc.time_aware_search(workspace_id, query, start=start, end=end, mode=mode, top_k=top_k))


@router.get("/multi-stage")
async def multi_stage_retrieve(
    workspace_id: str, query: str, scope_type: str | None = None, scope_id: str | None = None, memory_type: str | None = None,
    top_k: int = 10, use_query_expansion: bool = False, apply_reranking: bool = True,
    actor_id: str = Depends(get_current_actor_id), svc: RetrievalService = Depends(get_retrieval_service),
):
    return _serialize_results(await svc.multi_stage_retrieve(
        workspace_id, query, scope_type=scope_type, scope_id=scope_id, memory_type=memory_type, top_k=top_k,
        use_query_expansion=use_query_expansion, apply_reranking=apply_reranking, requested_by=actor_id,
    ))
