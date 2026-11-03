"""Shared libraries: publish/unpublish, visibility, install tracking,
and favorites."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import get_library_service
from collaboration_platform.domain.enums import LibraryVisibility
from collaboration_platform.libraries.library_service import LibraryService

router = APIRouter(prefix="/libraries", tags=["libraries"])


class PublishRequest(BaseModel):
    asset_id: str
    library_type: str
    published_by: str
    visibility: LibraryVisibility = LibraryVisibility.PRIVATE


@router.post("/publish", status_code=201)
async def publish(body: PublishRequest, service: LibraryService = Depends(get_library_service)):
    return to_dict(await service.publish(body.asset_id, library_type=body.library_type, published_by=body.published_by, visibility=body.visibility))


@router.post("/{library_asset_id}/unpublish")
async def unpublish(library_asset_id: str, service: LibraryService = Depends(get_library_service)):
    return to_dict(await service.unpublish(library_asset_id))


class VisibilityRequest(BaseModel):
    visibility: LibraryVisibility


@router.put("/{library_asset_id}/visibility")
async def update_visibility(library_asset_id: str, body: VisibilityRequest, service: LibraryService = Depends(get_library_service)):
    return to_dict(await service.update_visibility(library_asset_id, body.visibility))


@router.post("/{library_asset_id}/install")
async def record_install(library_asset_id: str, service: LibraryService = Depends(get_library_service)):
    return to_dict(await service.record_install(library_asset_id))


@router.get("")
async def list_published(visibility: LibraryVisibility | None = None, library_type: str | None = None, service: LibraryService = Depends(get_library_service)):
    return to_dict_list(await service.list_published(visibility=visibility, library_type=library_type))


@router.post("/{library_asset_id}/favorite/{user_id}", status_code=201)
async def favorite(library_asset_id: str, user_id: str, service: LibraryService = Depends(get_library_service)):
    return to_dict(await service.favorite(user_id, library_asset_id))


@router.delete("/{library_asset_id}/favorite/{user_id}", status_code=204)
async def unfavorite(library_asset_id: str, user_id: str, service: LibraryService = Depends(get_library_service)):
    await service.unfavorite(user_id, library_asset_id)


@router.get("/favorites/{user_id}")
async def list_favorites(user_id: str, service: LibraryService = Depends(get_library_service)):
    return to_dict_list(await service.list_favorites_for_user(user_id))
