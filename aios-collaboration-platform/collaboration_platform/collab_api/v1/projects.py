"""Projects, folders, collections, tags, and favorites."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import (
    get_collection_service,
    get_favorite_service,
    get_folder_service,
    get_project_service,
    get_tag_service,
)
from collaboration_platform.projects.collection_service import CollectionService
from collaboration_platform.projects.favorite_service import FavoriteService
from collaboration_platform.projects.folder_service import FolderService
from collaboration_platform.projects.project_service import ProjectService
from collaboration_platform.projects.tag_service import TagService

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    workspace_id: str
    name: str
    slug: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest, service: ProjectService = Depends(get_project_service)):
    return to_dict(await service.create_project(body.workspace_id, name=body.name, slug=body.slug, description=body.description))


@router.get("/workspace/{workspace_id}")
async def list_projects(workspace_id: str, status: str | None = None, service: ProjectService = Depends(get_project_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id, status=status))


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None


@router.put("/{project_id}")
async def update_project(project_id: str, body: UpdateProjectRequest, service: ProjectService = Depends(get_project_service)):
    return to_dict(await service.update(project_id, name=body.name, description=body.description))


@router.post("/{project_id}/archive")
async def archive_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    return to_dict(await service.archive(project_id))


@router.post("/{project_id}/restore")
async def restore_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    return to_dict(await service.restore(project_id))


folders_router = APIRouter(prefix="/folders", tags=["projects"])


class CreateFolderRequest(BaseModel):
    workspace_id: str
    name: str
    project_id: str | None = None
    parent_folder_id: str | None = None


@folders_router.post("", status_code=201)
async def create_folder(body: CreateFolderRequest, service: FolderService = Depends(get_folder_service)):
    return to_dict(await service.create_folder(body.workspace_id, name=body.name, project_id=body.project_id, parent_folder_id=body.parent_folder_id))


@folders_router.get("/workspace/{workspace_id}")
async def list_folders(workspace_id: str, service: FolderService = Depends(get_folder_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id))


class MoveFolderRequest(BaseModel):
    new_parent_folder_id: str | None = None


@folders_router.put("/{folder_id}/move")
async def move_folder(folder_id: str, body: MoveFolderRequest, service: FolderService = Depends(get_folder_service)):
    return to_dict(await service.move(folder_id, new_parent_folder_id=body.new_parent_folder_id))


collections_router = APIRouter(prefix="/collections", tags=["projects"])


class CreateCollectionRequest(BaseModel):
    workspace_id: str
    name: str
    owner_id: str
    description: str | None = None
    is_public: bool = False


@collections_router.post("", status_code=201)
async def create_collection(body: CreateCollectionRequest, service: CollectionService = Depends(get_collection_service)):
    return to_dict(await service.create_collection(body.workspace_id, name=body.name, owner_id=body.owner_id, description=body.description, is_public=body.is_public))


class AddCollectionItemRequest(BaseModel):
    asset_id: str
    added_by: str


@collections_router.post("/{collection_id}/items", status_code=201)
async def add_collection_item(collection_id: str, body: AddCollectionItemRequest, service: CollectionService = Depends(get_collection_service)):
    return to_dict(await service.add_item(collection_id, body.asset_id, added_by=body.added_by))


@collections_router.get("/{collection_id}/items")
async def list_collection_items(collection_id: str, service: CollectionService = Depends(get_collection_service)):
    return to_dict_list(await service.list_items(collection_id))


@collections_router.delete("/{collection_id}/items/{asset_id}", status_code=204)
async def remove_collection_item(collection_id: str, asset_id: str, service: CollectionService = Depends(get_collection_service)):
    await service.remove_item(collection_id, asset_id)


tags_router = APIRouter(prefix="/tags", tags=["projects"])


class CreateTagRequest(BaseModel):
    workspace_id: str
    name: str
    color: str | None = None


@tags_router.post("", status_code=201)
async def create_tag(body: CreateTagRequest, service: TagService = Depends(get_tag_service)):
    return to_dict(await service.create_tag(body.workspace_id, name=body.name, color=body.color))


@tags_router.post("/{tag_id}/assets/{asset_id}", status_code=201)
async def tag_asset(tag_id: str, asset_id: str, service: TagService = Depends(get_tag_service)):
    return to_dict(await service.tag_asset(asset_id, tag_id))


@tags_router.delete("/{tag_id}/assets/{asset_id}", status_code=204)
async def untag_asset(tag_id: str, asset_id: str, service: TagService = Depends(get_tag_service)):
    await service.untag_asset(asset_id, tag_id)


@tags_router.get("/assets/{asset_id}")
async def list_tags_for_asset(asset_id: str, service: TagService = Depends(get_tag_service)):
    return to_dict_list(await service.list_tags_for_asset(asset_id))


favorites_router = APIRouter(prefix="/favorites", tags=["projects"])


@favorites_router.post("/{user_id}/{asset_id}", status_code=201)
async def add_favorite(user_id: str, asset_id: str, service: FavoriteService = Depends(get_favorite_service)):
    return to_dict(await service.add_favorite(user_id, asset_id))


@favorites_router.delete("/{user_id}/{asset_id}", status_code=204)
async def remove_favorite(user_id: str, asset_id: str, service: FavoriteService = Depends(get_favorite_service)):
    await service.remove_favorite(user_id, asset_id)


@favorites_router.get("/{user_id}")
async def list_favorites(user_id: str, service: FavoriteService = Depends(get_favorite_service)):
    return to_dict_list(await service.list_for_user(user_id))
