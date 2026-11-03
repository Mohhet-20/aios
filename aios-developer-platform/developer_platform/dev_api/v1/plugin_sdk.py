"""Plugin SDK: registration, guarded version lifecycle, packaging,
dependency tracking, marketplace listing."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_plugin_dependency_service,
    get_plugin_lifecycle_service,
    get_plugin_marketplace_service,
    get_plugin_packaging_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list
from developer_platform.plugin_sdk.dependency_service import PluginDependencyService
from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.plugin_sdk.marketplace_service import PluginMarketplaceService
from developer_platform.plugin_sdk.packaging_service import PluginPackagingService

router = APIRouter(prefix="/plugins", tags=["plugin-sdk"])


class RegisterPluginRequest(BaseModel):
    name: str
    category: str
    owner_id: str | None = None
    description: str | None = None
    homepage_url: str | None = None


@router.post("", status_code=201)
async def register_plugin(
    body: RegisterPluginRequest, tenant_id: str = Depends(get_current_tenant_id), service: PluginLifecycleService = Depends(get_plugin_lifecycle_service),
):
    return to_dict(await service.register_plugin(tenant_id, **body.model_dump()))


class CreateVersionRequest(BaseModel):
    version: str
    manifest: dict


@router.post("/{plugin_id}/versions", status_code=201)
async def create_plugin_version(
    plugin_id: str, body: CreateVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PluginLifecycleService = Depends(get_plugin_lifecycle_service),
):
    return to_dict(await service.create_version(tenant_id, plugin_id, **body.model_dump()))


@router.post("/versions/{plugin_version_id}/validate")
async def validate_plugin_version(
    plugin_version_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PluginLifecycleService = Depends(get_plugin_lifecycle_service),
):
    return to_dict(await service.validate_version(tenant_id, plugin_version_id))


class SignVersionRequest(BaseModel):
    signed_by: str


@router.post("/versions/{plugin_version_id}/sign")
async def sign_plugin_version(
    plugin_version_id: str, body: SignVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PluginLifecycleService = Depends(get_plugin_lifecycle_service),
):
    return to_dict(await service.sign_version(tenant_id, plugin_version_id, **body.model_dump()))


@router.post("/versions/{plugin_version_id}/publish")
async def publish_plugin_version(
    plugin_version_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PluginLifecycleService = Depends(get_plugin_lifecycle_service),
):
    return to_dict(await service.publish_version(tenant_id, plugin_version_id))


@router.post("/versions/{plugin_version_id}/deprecate")
async def deprecate_plugin_version(
    plugin_version_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PluginLifecycleService = Depends(get_plugin_lifecycle_service),
):
    return to_dict(await service.deprecate_version(tenant_id, plugin_version_id))


class PackageVersionRequest(BaseModel):
    files: dict[str, str]
    storage_uri: str | None = None


@router.post("/versions/{plugin_version_id}/package")
async def package_plugin_version(
    plugin_version_id: str, body: PackageVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PluginPackagingService = Depends(get_plugin_packaging_service),
):
    files = {path: content.encode() for path, content in body.files.items()}
    return to_dict(await service.package_version(tenant_id, plugin_version_id, files=files, storage_uri=body.storage_uri))


class AddDependencyRequest(BaseModel):
    depends_on_plugin_id: str
    version_constraint: str = "*"


@router.post("/versions/{plugin_version_id}/dependencies", status_code=201)
async def add_plugin_dependency(
    plugin_version_id: str, body: AddDependencyRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PluginDependencyService = Depends(get_plugin_dependency_service),
):
    return to_dict(await service.add_dependency(tenant_id, plugin_version_id, **body.model_dump()))


@router.get("/versions/{plugin_version_id}/dependencies/resolve")
async def resolve_plugin_dependencies(
    plugin_version_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PluginDependencyService = Depends(get_plugin_dependency_service),
):
    return {"resolved_version_ids": await service.resolve_chain(tenant_id, plugin_version_id)}


marketplace_router = APIRouter(prefix="/plugins/marketplace", tags=["plugin-sdk"])


@marketplace_router.post("/{plugin_id}/submit")
async def submit_plugin_for_review(
    plugin_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PluginMarketplaceService = Depends(get_plugin_marketplace_service),
):
    return to_dict(await service.submit_for_review(tenant_id, plugin_id))


class ReviewDecisionRequest(BaseModel):
    reviewer_id: str


@marketplace_router.post("/{plugin_id}/approve")
async def approve_plugin_listing(
    plugin_id: str, body: ReviewDecisionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PluginMarketplaceService = Depends(get_plugin_marketplace_service),
):
    return to_dict(await service.approve(tenant_id, plugin_id, **body.model_dump()))


@marketplace_router.post("/{plugin_id}/reject")
async def reject_plugin_listing(
    plugin_id: str, body: ReviewDecisionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PluginMarketplaceService = Depends(get_plugin_marketplace_service),
):
    return to_dict(await service.reject(tenant_id, plugin_id, **body.model_dump()))


@marketplace_router.post("/{plugin_id}/install")
async def record_plugin_install(
    plugin_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PluginMarketplaceService = Depends(get_plugin_marketplace_service),
):
    return to_dict(await service.record_install(tenant_id, plugin_id))


class RateRequest(BaseModel):
    rating_avg: float


@marketplace_router.post("/{plugin_id}/rate")
async def rate_plugin(
    plugin_id: str, body: RateRequest, tenant_id: str = Depends(get_current_tenant_id), service: PluginMarketplaceService = Depends(get_plugin_marketplace_service),
):
    return to_dict(await service.set_rating(tenant_id, plugin_id, **body.model_dump()))


@marketplace_router.get("")
async def list_public_plugins(tenant_id: str = Depends(get_current_tenant_id), service: PluginMarketplaceService = Depends(get_plugin_marketplace_service)):
    return to_dict_list(await service.list_public(tenant_id))
