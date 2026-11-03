"""Plugin Marketplace: browse published plugins — search/most-installed/
listing detail. The "Tool Marketplace" frontend surface."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from tool_platform.dependencies.dependencies import get_marketplace_service
from tool_platform.marketplace.marketplace_service import MarketplaceService
from tool_platform.tool_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/search")
async def search(
    category: str | None = None, tag: str | None = None, query: str | None = None,
    svc: MarketplaceService = Depends(get_marketplace_service),
):
    return to_dict_list(await svc.search(category=category, tag=tag, query=query))


@router.get("/most-installed")
async def most_installed(limit: int = 10, svc: MarketplaceService = Depends(get_marketplace_service)):
    return to_dict_list(await svc.most_installed(limit=limit))


@router.get("/{plugin_id}")
async def get_listing(plugin_id: str, svc: MarketplaceService = Depends(get_marketplace_service)):
    return to_dict(await svc.get_listing(plugin_id))
