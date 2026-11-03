"""Extension Framework: extension point registry + guarded
registration lifecycle across all 11 categories."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_extension_point_service,
    get_extension_registration_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list
from developer_platform.extension_framework.point_service import ExtensionPointService
from developer_platform.extension_framework.registration_service import ExtensionRegistrationService

router = APIRouter(prefix="/extension-points", tags=["extension-framework"])


class RegisterPointRequest(BaseModel):
    category: str
    name: str
    description: str | None = None
    contract_schema: dict | None = None


@router.post("", status_code=201)
async def register_extension_point(
    body: RegisterPointRequest, tenant_id: str = Depends(get_current_tenant_id), service: ExtensionPointService = Depends(get_extension_point_service),
):
    return to_dict(await service.register_point(tenant_id, **body.model_dump()))


@router.get("")
async def list_extension_points(tenant_id: str = Depends(get_current_tenant_id), service: ExtensionPointService = Depends(get_extension_point_service)):
    return to_dict_list(await service.list_all(tenant_id))


@router.get("/{category}")
async def list_extension_points_by_category(
    category: str, tenant_id: str = Depends(get_current_tenant_id), service: ExtensionPointService = Depends(get_extension_point_service),
):
    return to_dict_list(await service.list_by_category(tenant_id, category))


registrations_router = APIRouter(prefix="/extension-registrations", tags=["extension-framework"])


class RegisterRequest(BaseModel):
    extension_point_id: str
    name: str
    plugin_id: str | None = None
    config: dict | None = None


@registrations_router.post("", status_code=201)
async def register_extension(
    body: RegisterRequest, tenant_id: str = Depends(get_current_tenant_id), service: ExtensionRegistrationService = Depends(get_extension_registration_service),
):
    return to_dict(await service.register(tenant_id, **body.model_dump()))


@registrations_router.post("/{registration_id}/activate")
async def activate_extension_registration(registration_id: str, service: ExtensionRegistrationService = Depends(get_extension_registration_service)):
    return to_dict(await service.activate(registration_id))


@registrations_router.post("/{registration_id}/disable")
async def disable_extension_registration(registration_id: str, service: ExtensionRegistrationService = Depends(get_extension_registration_service)):
    return to_dict(await service.disable(registration_id))


@registrations_router.get("/for-point/{extension_point_id}")
async def list_registrations_for_point(
    extension_point_id: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ExtensionRegistrationService = Depends(get_extension_registration_service),
):
    return to_dict_list(await service.list_for_point(tenant_id, extension_point_id))
