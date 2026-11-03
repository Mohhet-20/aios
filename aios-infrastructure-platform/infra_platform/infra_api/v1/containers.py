"""Container Image Registry API: build -> scan -> sign -> publish
lifecycle plus version retention pruning."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.containers.image_service import ImageRegistryService
from infra_platform.dependencies.dependencies import get_current_actor_id, get_current_tenant_id, get_image_registry_service
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/images", tags=["containers"])


class CreateImageRequest(BaseModel):
    repository: str
    tag: str
    built_from_commit: str | None = None


@router.post("", status_code=201)
async def create_image(
    body: CreateImageRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: ImageRegistryService = Depends(get_image_registry_service),
):
    return to_dict(await service.create_image(tenant_id, **body.model_dump(), created_by=actor_id))


@router.post("/{image_id}/scan/start")
async def start_scan(image_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return to_dict(await service.start_scan(tenant_id, image_id))


class RecordScanResultRequest(BaseModel):
    severity: str
    finding_count: int
    summary: str = ""


@router.post("/{image_id}/scan/result")
async def record_scan_result(
    image_id: str, body: RecordScanResultRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ImageRegistryService = Depends(get_image_registry_service),
):
    return to_dict(await service.record_scan_result(tenant_id, image_id, **body.model_dump()))


class SignImageRequest(BaseModel):
    signer: str
    signature: str


@router.post("/{image_id}/sign")
async def sign_image(
    image_id: str, body: SignImageRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ImageRegistryService = Depends(get_image_registry_service),
):
    return to_dict(await service.sign_image(tenant_id, image_id, **body.model_dump()))


@router.post("/{image_id}/publish")
async def publish_image(image_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return to_dict(await service.publish_image(tenant_id, image_id))


@router.post("/{image_id}/deprecate")
async def deprecate_image(image_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return to_dict(await service.deprecate_image(tenant_id, image_id))


@router.post("/{image_id}/quarantine")
async def quarantine_image(image_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return to_dict(await service.quarantine_image(tenant_id, image_id))


@router.post("/{image_id}/retry")
async def retry_build(image_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return to_dict(await service.retry_build(tenant_id, image_id))


@router.get("")
async def list_versions(repository: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return to_dict_list(await service.list_versions(tenant_id, repository))


@router.post("/prune")
async def prune_old_versions(repository: str, tenant_id: str = Depends(get_current_tenant_id), service: ImageRegistryService = Depends(get_image_registry_service)):
    return {"pruned": await service.prune_old_versions(tenant_id, repository)}
