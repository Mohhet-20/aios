"""Artifact Management API: generic artifact + version store with
checksum verification."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.artifacts.artifact_service import ArtifactService, ArtifactVersionService
from infra_platform.dependencies.dependencies import get_artifact_service, get_artifact_version_service, get_current_tenant_id
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


class CreateArtifactRequest(BaseModel):
    name: str
    artifact_type: str
    description: str | None = None


@router.post("", status_code=201)
async def create_artifact(body: CreateArtifactRequest, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactService = Depends(get_artifact_service)):
    return to_dict(await service.create_artifact(tenant_id, **body.model_dump()))


@router.get("")
async def list_artifacts(artifact_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactService = Depends(get_artifact_service)):
    if artifact_type:
        return to_dict_list(await service.list_by_type(tenant_id, artifact_type))
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.get("/{artifact_id}")
async def get_artifact(artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactService = Depends(get_artifact_service)):
    return to_dict(await service.get(tenant_id, artifact_id))


class AddVersionRequest(BaseModel):
    storage_uri: str
    size_bytes: int | None = None
    checksum: str | None = None
    artifact_metadata: dict | None = None


@router.post("/{artifact_id}/versions", status_code=201)
async def add_version(
    artifact_id: str, body: AddVersionRequest, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactVersionService = Depends(get_artifact_version_service)
):
    return to_dict(await service.add_version(tenant_id, artifact_id, **body.model_dump()))


@router.get("/{artifact_id}/versions")
async def list_versions(artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactVersionService = Depends(get_artifact_version_service)):
    return to_dict_list(await service.list_for_artifact(tenant_id, artifact_id))


@router.get("/{artifact_id}/versions/latest")
async def get_latest_version(artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactVersionService = Depends(get_artifact_version_service)):
    return to_dict(await service.get_latest(tenant_id, artifact_id))


class VerifyChecksumRequest(BaseModel):
    expected_checksum: str


@router.post("/versions/{version_id}/verify")
async def verify_checksum(
    version_id: str, body: VerifyChecksumRequest, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactVersionService = Depends(get_artifact_version_service)
):
    return {"verified": await service.verify_checksum(tenant_id, version_id, **body.model_dump())}
