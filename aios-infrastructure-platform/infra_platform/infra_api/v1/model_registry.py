"""Model Lifecycle Management API: registry entries, versions,
approval-gated promotion, lineage, and retention pruning."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import (
    get_current_actor_id,
    get_current_tenant_id,
    get_model_lineage_service,
    get_model_registry_service,
    get_model_version_service,
)
from infra_platform.infra_api.serialization import to_dict, to_dict_list
from infra_platform.model_registry.registry_service import ModelLineageService, ModelRegistryService, ModelVersionService

router = APIRouter(prefix="/models", tags=["model-registry"])


class RegisterModelRequest(BaseModel):
    name: str
    description: str | None = None


@router.post("", status_code=201)
async def register_model(
    body: RegisterModelRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: ModelRegistryService = Depends(get_model_registry_service),
):
    return to_dict(await service.register_model(tenant_id, **body.model_dump(), owner_id=actor_id))


@router.get("")
async def list_models(tenant_id: str = Depends(get_current_tenant_id), service: ModelRegistryService = Depends(get_model_registry_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.get("/{model_id}")
async def get_model(model_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ModelRegistryService = Depends(get_model_registry_service)):
    return to_dict(await service.get(tenant_id, model_id))


class CreateVersionRequest(BaseModel):
    source_run_id: str | None = None
    artifact_id: str | None = None
    metrics: dict | None = None
    version_metadata: dict | None = None


@router.post("/{model_id}/versions", status_code=201)
async def create_version(
    model_id: str, body: CreateVersionRequest, tenant_id: str = Depends(get_current_tenant_id), service: ModelVersionService = Depends(get_model_version_service)
):
    return to_dict(await service.create_version(tenant_id, model_id, **body.model_dump()))


@router.get("/{model_id}/versions")
async def list_versions(model_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ModelVersionService = Depends(get_model_version_service)):
    return to_dict_list(await service.list_for_model(tenant_id, model_id))


class RequestPromotionRequest(BaseModel):
    requested_stage: str


@router.post("/versions/{version_id}/promote", status_code=201)
async def request_promotion(
    version_id: str, body: RequestPromotionRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: ModelVersionService = Depends(get_model_version_service),
):
    return to_dict(await service.request_promotion(tenant_id, version_id, requested_stage=body.requested_stage, reviewer_id=actor_id))


class DecideApprovalRequest(BaseModel):
    approved: bool
    comments: str | None = None


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: str, body: DecideApprovalRequest, tenant_id: str = Depends(get_current_tenant_id), actor_id: str | None = Depends(get_current_actor_id),
    service: ModelVersionService = Depends(get_model_version_service),
):
    return to_dict(await service.decide_approval(tenant_id, approval_id, approved=body.approved, reviewer_id=actor_id, comments=body.comments))


@router.post("/versions/{version_id}/archive")
async def archive_version(version_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ModelVersionService = Depends(get_model_version_service)):
    return to_dict(await service.archive_version(tenant_id, version_id))


@router.post("/{model_id}/versions/prune")
async def prune_versions(model_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ModelVersionService = Depends(get_model_version_service)):
    return {"pruned": await service.prune_old_versions(tenant_id, model_id)}


class RecordLineageRequest(BaseModel):
    parent_type: str
    parent_ref_id: str


@router.post("/versions/{version_id}/lineage", status_code=201)
async def record_lineage(
    version_id: str, body: RecordLineageRequest, tenant_id: str = Depends(get_current_tenant_id), service: ModelLineageService = Depends(get_model_lineage_service)
):
    return to_dict(await service.record_lineage(tenant_id, version_id, **body.model_dump()))


@router.get("/versions/{version_id}/lineage")
async def list_lineage(version_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ModelLineageService = Depends(get_model_lineage_service)):
    return to_dict_list(await service.list_for_version(tenant_id, version_id))
