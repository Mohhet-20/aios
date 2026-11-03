"""Tool Registry / Discovery surface: category catalog + capability/tag/
semantic search + recently-used/favorites/recommendations — the "Tool
Registry" and "Tool Marketplace" browse experience for both a human
building a workflow and an AI agent planning a tool call."""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from tool_platform.dependencies.dependencies import get_current_actor_id, get_discovery_service
from tool_platform.discovery.discovery_service import ToolDiscoveryService
from tool_platform.tool_api.serialization import to_dict, to_dict_list
from tool_platform.tool_registry.registry import CATEGORY_SPECS, get_category_spec

router = APIRouter(prefix="/registry", tags=["registry"])


@router.get("/categories")
async def list_categories():
    return [asdict(spec) for spec in CATEGORY_SPECS]


@router.get("/categories/{category}")
async def get_category(category: str):
    return asdict(get_category_spec(category))


@router.get("/search/category")
async def search_by_category(workspace_id: str, category: str, svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.search_by_category(workspace_id, category))


@router.get("/search/tag")
async def search_by_tag(workspace_id: str, tag: str, svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.search_by_tag(workspace_id, tag))


@router.get("/search/capability")
async def search_by_capability(workspace_id: str, capability: str, svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.search_by_capability(workspace_id, capability))


@router.get("/search/semantic")
async def semantic_search(workspace_id: str, q: str, top_k: int = 10, svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.semantic_search(workspace_id, q, top_k=top_k))


@router.get("/recently-used")
async def recently_used(limit: int = 10, actor_id: str = Depends(get_current_actor_id), svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.recently_used(actor_id, limit=limit))


@router.get("/favorites")
async def list_favorites(actor_id: str = Depends(get_current_actor_id), svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.list_favorites(actor_id))


@router.post("/favorites/{tool_id}", status_code=201)
async def add_favorite(tool_id: str, actor_id: str = Depends(get_current_actor_id), svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict(await svc.add_favorite(tool_id, actor_id))


@router.delete("/favorites/{tool_id}", status_code=204)
async def remove_favorite(tool_id: str, actor_id: str = Depends(get_current_actor_id), svc: ToolDiscoveryService = Depends(get_discovery_service)):
    await svc.remove_favorite(tool_id, actor_id)


@router.get("/recommendations")
async def recommend(workspace_id: str, limit: int = 5, actor_id: str = Depends(get_current_actor_id), svc: ToolDiscoveryService = Depends(get_discovery_service)):
    return to_dict_list(await svc.recommend(workspace_id, actor_id, limit=limit))
