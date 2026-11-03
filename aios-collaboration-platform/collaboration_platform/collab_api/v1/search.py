"""Global/tag/metadata search, recent items, and saved searches."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import get_recent_items_service, get_saved_search_service, get_search_service
from collaboration_platform.search.recent_items_service import RecentItemsService
from collaboration_platform.search.saved_search_service import SavedSearchService
from collaboration_platform.search.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(q: str, workspace_id: str | None = None, asset_type: str | None = None, limit: int = 50, semantic: bool = False, service: SearchService = Depends(get_search_service)):
    return to_dict_list(await service.search(q, workspace_id=workspace_id, asset_type=asset_type, limit=limit, semantic=semantic))


@router.get("/tag/{workspace_id}/{tag_name}")
async def search_by_tag(workspace_id: str, tag_name: str, service: SearchService = Depends(get_search_service)):
    return to_dict_list(await service.search_by_tag(workspace_id, tag_name))


class MetadataSearchRequest(BaseModel):
    filters: dict


@router.post("/metadata/{workspace_id}")
async def search_by_metadata(workspace_id: str, body: MetadataSearchRequest, service: SearchService = Depends(get_search_service)):
    return to_dict_list(await service.search_by_metadata(workspace_id, body.filters))


@router.post("/recent/{user_id}/{asset_id}")
async def track_recent(user_id: str, asset_id: str, service: RecentItemsService = Depends(get_recent_items_service)):
    return to_dict(await service.track_view(user_id, asset_id))


@router.get("/recent/{user_id}")
async def list_recent(user_id: str, service: RecentItemsService = Depends(get_recent_items_service)):
    return to_dict_list(await service.list_recent(user_id))


class SavedSearchRequest(BaseModel):
    name: str
    query: dict


@router.post("/saved/{user_id}", status_code=201)
async def create_saved_search(user_id: str, body: SavedSearchRequest, service: SavedSearchService = Depends(get_saved_search_service)):
    return to_dict(await service.create(user_id, name=body.name, query=body.query))


@router.get("/saved/{user_id}")
async def list_saved_searches(user_id: str, service: SavedSearchService = Depends(get_saved_search_service)):
    return to_dict_list(await service.list_for_user(user_id))


@router.delete("/saved/{saved_search_id}", status_code=204)
async def delete_saved_search(saved_search_id: str, service: SavedSearchService = Depends(get_saved_search_service)):
    await service.delete(saved_search_id)
