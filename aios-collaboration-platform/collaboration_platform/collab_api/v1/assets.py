"""Collaboration asset registration and management — the pointer every
other module (comments, versions, reviews, activity, sharing) attaches
to."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.dependencies.dependencies import get_asset_service
from collaboration_platform.domain.enums import AssetType, AssetVisibility

router = APIRouter(prefix="/assets", tags=["assets"])


class RegisterAssetRequest(BaseModel):
    workspace_id: str
    asset_type: AssetType
    external_ref_id: str
    name: str
    owner_id: str
    project_id: str | None = None
    folder_id: str | None = None
    description: str | None = None
    visibility: AssetVisibility = AssetVisibility.WORKSPACE


@router.post("", status_code=201)
async def register_asset(body: RegisterAssetRequest, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.register_asset(
        workspace_id=body.workspace_id, asset_type=body.asset_type, external_ref_id=body.external_ref_id, name=body.name,
        owner_id=body.owner_id, project_id=body.project_id, folder_id=body.folder_id, description=body.description,
        visibility=body.visibility,
    ))


@router.get("/{asset_id}")
async def get_asset(asset_id: str, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.get(asset_id))


@router.get("/workspace/{workspace_id}")
async def list_assets(workspace_id: str, asset_type: AssetType | None = None, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id, asset_type=asset_type))


class RenameAssetRequest(BaseModel):
    name: str


@router.put("/{asset_id}/rename")
async def rename_asset(asset_id: str, body: RenameAssetRequest, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.rename(asset_id, name=body.name))


class MoveAssetRequest(BaseModel):
    project_id: str | None = None
    folder_id: str | None = None


@router.put("/{asset_id}/move")
async def move_asset(asset_id: str, body: MoveAssetRequest, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.move(asset_id, project_id=body.project_id, folder_id=body.folder_id))


class SetVisibilityRequest(BaseModel):
    visibility: AssetVisibility


@router.put("/{asset_id}/visibility")
async def set_visibility(asset_id: str, body: SetVisibilityRequest, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.set_visibility(asset_id, body.visibility))


@router.post("/{asset_id}/archive")
async def archive_asset(asset_id: str, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.archive(asset_id))


@router.post("/{asset_id}/restore")
async def restore_asset(asset_id: str, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.restore(asset_id))


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str, service: CollaborationAssetService = Depends(get_asset_service)):
    return to_dict(await service.delete(asset_id))
