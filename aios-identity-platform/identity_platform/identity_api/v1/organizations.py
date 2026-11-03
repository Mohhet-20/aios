"""Organization CRUD, settings/branding, ownership transfer, and
departments."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_organization_service
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.organizations.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


class CreateOrganizationRequest(BaseModel):
    name: str
    owner_user_id: str
    slug: str | None = None


@router.post("", status_code=201)
async def create_organization(body: CreateOrganizationRequest, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.create_organization(name=body.name, owner_user_id=body.owner_user_id, slug=body.slug))


@router.get("/{organization_id}")
async def get_organization(organization_id: str, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.repos.organizations.get_or_404(organization_id))


class UpdateSettingsRequest(BaseModel):
    settings: dict


@router.put("/{organization_id}/settings")
async def update_settings(organization_id: str, body: UpdateSettingsRequest, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.update_settings(organization_id, settings=body.settings))


class UpdateBrandingRequest(BaseModel):
    branding: dict


@router.put("/{organization_id}/branding")
async def update_branding(organization_id: str, body: UpdateBrandingRequest, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.update_branding(organization_id, branding=body.branding))


@router.post("/{organization_id}/archive")
async def archive_organization(organization_id: str, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.archive(organization_id))


@router.post("/{organization_id}/suspend")
async def suspend_organization(organization_id: str, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.suspend(organization_id))


@router.post("/{organization_id}/reinstate")
async def reinstate_organization(organization_id: str, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.reinstate(organization_id))


class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: str


@router.post("/{organization_id}/transfer-ownership")
async def transfer_ownership(organization_id: str, body: TransferOwnershipRequest, service: OrganizationService = Depends(get_organization_service)):
    return to_dict(await service.transfer_ownership(organization_id, new_owner_user_id=body.new_owner_user_id))


class CreateDepartmentRequest(BaseModel):
    name: str
    unit_type: str = "department"
    description: str | None = None
    parent_department_id: str | None = None


@router.post("/{organization_id}/departments", status_code=201)
async def create_department(organization_id: str, body: CreateDepartmentRequest, service: OrganizationService = Depends(get_organization_service)):
    dept = await service.create_department(
        organization_id, name=body.name, unit_type=body.unit_type, description=body.description,
        parent_department_id=body.parent_department_id,
    )
    return to_dict(dept)


@router.get("/{organization_id}/departments")
async def list_departments(organization_id: str, service: OrganizationService = Depends(get_organization_service)):
    return to_dict_list(await service.list_departments(organization_id))
