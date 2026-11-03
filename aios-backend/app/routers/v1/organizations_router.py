from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_organization_service, get_team_service
from app.schemas.organization import (
    MembershipCreate,
    OrganizationCreate,
    OrganizationRead,
    TeamCreate,
    TeamRead,
)
from app.security.permissions import Permission
from app.services.organization_service import OrganizationService, TeamService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate, service: OrganizationService = Depends(get_organization_service)
):
    from app.models.organization import OrganizationModel

    org = OrganizationModel(name=payload.name, plan=payload.plan, logo_initials=payload.name[:2].upper())
    return await service.create(org)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(service: OrganizationService = Depends(get_organization_service)):
    return await service.list()


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: str, service: OrganizationService = Depends(get_organization_service)
):
    return await service.get(organization_id)


@router.post("/{organization_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    organization_id: str,
    payload: MembershipCreate,
    service: OrganizationService = Depends(get_organization_service),
    _principal=Depends(require_permission(Permission.ORG_MANAGE)),
):
    membership = await service.add_member(organization_id, payload.user_id, payload.role)
    return {
        "organization_id": membership.organization_id,
        "user_id": membership.user_id,
        "role": membership.role,
    }


@router.get("/{organization_id}/teams", response_model=list[TeamRead])
async def list_teams(organization_id: str, service: TeamService = Depends(get_team_service)):
    return await service.list(organization_id=organization_id)


@router.post("/{organization_id}/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    organization_id: str,
    payload: TeamCreate,
    service: TeamService = Depends(get_team_service),
    _principal=Depends(require_permission(Permission.TEAM_MANAGE)),
):
    from app.models.organization import TeamModel

    team = TeamModel(organization_id=organization_id, name=payload.name)
    return await service.create(team)
