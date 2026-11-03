"""Team CRUD — org-wide or scoped to one workspace."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_team_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


class CreateTeamRequest(BaseModel):
    organization_id: str
    name: str
    slug: str | None = None
    workspace_id: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def create_team(body: CreateTeamRequest, service: TeamService = Depends(get_team_service)):
    team = await service.create_team(
        body.organization_id, name=body.name, slug=body.slug, workspace_id=body.workspace_id, description=body.description,
    )
    return to_dict(team)


@router.get("/{team_id}")
async def get_team(team_id: str, service: TeamService = Depends(get_team_service)):
    return to_dict(await service.repos.teams.get_or_404(team_id))


@router.post("/{team_id}/archive")
async def archive_team(team_id: str, service: TeamService = Depends(get_team_service)):
    return to_dict(await service.archive(team_id))


@router.get("")
async def list_teams(organization_id: str, service: TeamService = Depends(get_team_service)):
    return to_dict_list(await service.list_for_organization(organization_id))
