"""Tool version CRUD (the versioned contract: schemas, capabilities,
config, auth requirement, sensitivity, connector_key) + publish/
deprecate — the "Tool Builder" configuration-editor surface."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_version_service
from tool_platform.tool_api.serialization import to_dict, to_dict_list
from tool_platform.tool_core.version_service import ToolVersionService

router = APIRouter(prefix="/tools/{tool_id}/versions", tags=["tool_versions"])


class UpdateDraftRequest(BaseModel):
    fields: dict


@router.post("/draft", status_code=201)
async def get_or_create_draft(tool_id: str, created_by: str, svc: ToolVersionService = Depends(get_version_service)):
    return to_dict(await svc.get_or_create_draft(tool_id, created_by=created_by))


@router.get("")
async def list_versions(tool_id: str, svc: ToolVersionService = Depends(get_version_service)):
    return to_dict_list(await svc.list_versions(tool_id))


@router.get("/{version_id}")
async def get_version(tool_id: str, version_id: str, svc: ToolVersionService = Depends(get_version_service)):
    return to_dict(await svc.get_version(version_id))


@router.patch("/{version_id}")
async def update_draft(tool_id: str, version_id: str, body: UpdateDraftRequest, svc: ToolVersionService = Depends(get_version_service)):
    return to_dict(await svc.update_draft(version_id, **body.fields))


@router.post("/{version_id}/publish")
async def publish_version(tool_id: str, version_id: str, activate_tool: bool = True, svc: ToolVersionService = Depends(get_version_service)):
    return to_dict(await svc.publish_version(version_id, activate_tool=activate_tool))


@router.post("/{version_id}/deprecate")
async def deprecate_version(tool_id: str, version_id: str, svc: ToolVersionService = Depends(get_version_service)):
    return to_dict(await svc.deprecate_version(version_id))
