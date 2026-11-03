"""Activity feed: record + per-scope query."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.activity.activity_service import ActivityService
from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import get_activity_service
from collaboration_platform.domain.enums import ActivityEventType

router = APIRouter(prefix="/activity", tags=["activity"])


class RecordActivityRequest(BaseModel):
    actor_id: str
    event_type: ActivityEventType
    summary: str
    workspace_id: str | None = None
    project_id: str | None = None
    asset_id: str | None = None
    organization_id: str | None = None
    event_metadata: dict | None = None


@router.post("", status_code=201)
async def record_activity(body: RecordActivityRequest, service: ActivityService = Depends(get_activity_service)):
    return to_dict(await service.record(
        actor_id=body.actor_id, event_type=body.event_type, summary=body.summary, workspace_id=body.workspace_id,
        project_id=body.project_id, asset_id=body.asset_id, organization_id=body.organization_id, event_metadata=body.event_metadata,
    ))


@router.get("/workspace/{workspace_id}")
async def feed_for_workspace(workspace_id: str, limit: int = 100, service: ActivityService = Depends(get_activity_service)):
    return to_dict_list(await service.feed_for_workspace(workspace_id, limit=limit))


@router.get("/project/{project_id}")
async def feed_for_project(project_id: str, limit: int = 100, service: ActivityService = Depends(get_activity_service)):
    return to_dict_list(await service.feed_for_project(project_id, limit=limit))


@router.get("/asset/{asset_id}")
async def feed_for_asset(asset_id: str, limit: int = 100, service: ActivityService = Depends(get_activity_service)):
    return to_dict_list(await service.feed_for_asset(asset_id, limit=limit))


@router.get("/user/{actor_id}")
async def feed_for_user(actor_id: str, limit: int = 100, service: ActivityService = Depends(get_activity_service)):
    return to_dict_list(await service.feed_for_user(actor_id, limit=limit))


@router.get("/organization/{organization_id}")
async def feed_for_organization(organization_id: str, limit: int = 100, service: ActivityService = Depends(get_activity_service)):
    return to_dict_list(await service.feed_for_organization(organization_id, limit=limit))
