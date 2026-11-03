"""Multi-Cloud API: cloud accounts and tracked cloud resources."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.cloud.cloud_service import CloudAccountService, CloudResourceService
from infra_platform.dependencies.dependencies import get_cloud_account_service, get_cloud_resource_service, get_current_tenant_id
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/cloud", tags=["cloud"])


class RegisterAccountRequest(BaseModel):
    provider: str
    account_ref: str
    display_name: str


@router.post("/accounts", status_code=201)
async def register_account(body: RegisterAccountRequest, tenant_id: str = Depends(get_current_tenant_id), service: CloudAccountService = Depends(get_cloud_account_service)):
    return to_dict(await service.register_account(tenant_id, **body.model_dump()))


@router.get("/accounts")
async def list_accounts(tenant_id: str = Depends(get_current_tenant_id), service: CloudAccountService = Depends(get_cloud_account_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/accounts/{account_id}/deactivate")
async def deactivate_account(account_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CloudAccountService = Depends(get_cloud_account_service)):
    return to_dict(await service.deactivate(tenant_id, account_id))


@router.post("/accounts/{account_id}/reactivate")
async def reactivate_account(account_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CloudAccountService = Depends(get_cloud_account_service)):
    return to_dict(await service.reactivate(tenant_id, account_id))


class TrackResourceRequest(BaseModel):
    region: str
    resource_type: str
    external_id: str
    tags: dict | None = None


@router.post("/accounts/{account_id}/resources", status_code=201)
async def track_resource(account_id: str, body: TrackResourceRequest, tenant_id: str = Depends(get_current_tenant_id), service: CloudResourceService = Depends(get_cloud_resource_service)):
    return to_dict(await service.track_resource(tenant_id, account_id, **body.model_dump()))


@router.get("/accounts/{account_id}/resources")
async def list_resources_for_account(account_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CloudResourceService = Depends(get_cloud_resource_service)):
    return to_dict_list(await service.list_for_account(tenant_id, account_id))


class UpdateResourceStatusRequest(BaseModel):
    status: str


@router.patch("/resources/{resource_id}/status")
async def update_resource_status(resource_id: str, body: UpdateResourceStatusRequest, tenant_id: str = Depends(get_current_tenant_id), service: CloudResourceService = Depends(get_cloud_resource_service)):
    return to_dict(await service.update_status(tenant_id, resource_id, **body.model_dump()))
