"""SDK Platform: version compatibility matrix + SDK package registry."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_sdk_compatibility_service,
    get_sdk_package_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list
from developer_platform.sdk_platform.compatibility_service import SdkCompatibilityService
from developer_platform.sdk_platform.package_service import SdkPackageService

router = APIRouter(prefix="/sdk/compatibility", tags=["sdk-platform"])


class RegisterCompatibilityRequest(BaseModel):
    language: str
    sdk_major_version: int
    min_api_version: str
    max_api_version: str | None = None
    is_supported: bool = True


@router.post("", status_code=201)
async def register_compatibility_entry(
    body: RegisterCompatibilityRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SdkCompatibilityService = Depends(get_sdk_compatibility_service),
):
    return to_dict(await service.register_entry(tenant_id, **body.model_dump()))


@router.get("/{language}")
async def list_compatibility_for_language(
    language: str, tenant_id: str = Depends(get_current_tenant_id),
    service: SdkCompatibilityService = Depends(get_sdk_compatibility_service),
):
    return to_dict_list(await service.list_for_language(tenant_id, language))


class CheckCompatibilityRequest(BaseModel):
    language: str
    sdk_major_version: int
    api_version: str


@router.post("/check")
async def check_compatibility(
    body: CheckCompatibilityRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SdkCompatibilityService = Depends(get_sdk_compatibility_service),
):
    return {"compatible": await service.check_compatible(tenant_id, **body.model_dump())}


packages_router = APIRouter(prefix="/sdk/packages", tags=["sdk-platform"])


class PublishSdkVersionRequest(BaseModel):
    language: str
    version: str
    storage_uri: str | None = None
    checksum: str | None = None
    dependencies: list[str] | None = None


@packages_router.post("", status_code=201)
async def publish_sdk_version(
    body: PublishSdkVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SdkPackageService = Depends(get_sdk_package_service),
):
    return to_dict(await service.publish_version(tenant_id, **body.model_dump()))


@packages_router.get("/{language}")
async def list_sdk_versions(
    language: str, tenant_id: str = Depends(get_current_tenant_id), service: SdkPackageService = Depends(get_sdk_package_service),
):
    return to_dict_list(await service.list_versions(tenant_id, language))


class DeprecateSdkVersionRequest(BaseModel):
    language: str
    version: str


@packages_router.post("/deprecate")
async def deprecate_sdk_version(
    body: DeprecateSdkVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: SdkPackageService = Depends(get_sdk_package_service),
):
    return to_dict(await service.deprecate_version(tenant_id, **body.model_dump()))
