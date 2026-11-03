"""Artifact Management & Enterprise Distribution: artifacts,
distribution channels, and publish records."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.artifacts.artifact_service import ArtifactService
from release_platform.dependencies.dependencies import (
    get_artifact_service,
    get_current_tenant_id,
    get_distribution_channel_service,
    get_distribution_entry_service,
)
from release_platform.distribution.distribution_service import DistributionChannelService, DistributionEntryService
from release_platform.release_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
channels_router = APIRouter(prefix="/distribution-channels", tags=["distribution"])
entries_router = APIRouter(prefix="/distribution-entries", tags=["distribution"])


class RegisterArtifactRequest(BaseModel):
    release_id: str
    artifact_type: str
    name: str
    version: str
    checksum: str | None = None
    storage_uri: str = ""
    size_bytes: int = 0


@router.post("", status_code=201)
async def register_artifact(
    body: RegisterArtifactRequest, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactService = Depends(get_artifact_service),
):
    return to_dict(await service.register_artifact(tenant_id, **body.model_dump()))


@router.get("/{artifact_id}")
async def get_artifact(
    artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactService = Depends(get_artifact_service),
):
    return to_dict(await service.get_or_404(tenant_id, artifact_id))


@router.get("/by-release/{release_id}")
async def list_for_release(
    release_id: str, artifact_type: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: ArtifactService = Depends(get_artifact_service),
):
    return to_dict_list(await service.list_for_release(tenant_id, release_id, artifact_type=artifact_type))


class RegisterChannelRequest(BaseModel):
    channel_type: str
    name: str
    endpoint_uri: str = ""


@channels_router.post("", status_code=201)
async def register_channel(
    body: RegisterChannelRequest, tenant_id: str = Depends(get_current_tenant_id), service: DistributionChannelService = Depends(get_distribution_channel_service),
):
    return to_dict(await service.register_channel(tenant_id, **body.model_dump()))


@channels_router.get("")
async def list_channels(
    channel_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: DistributionChannelService = Depends(get_distribution_channel_service),
):
    return to_dict_list(await service.list_channels(tenant_id, channel_type=channel_type))


class PublishArtifactRequest(BaseModel):
    artifact_id: str
    channel_id: str


@entries_router.post("", status_code=201)
async def publish_artifact(
    body: PublishArtifactRequest, tenant_id: str = Depends(get_current_tenant_id), service: DistributionEntryService = Depends(get_distribution_entry_service),
):
    return to_dict(await service.publish_artifact(tenant_id, **body.model_dump()))


@entries_router.get("/by-artifact/{artifact_id}")
async def list_for_artifact(
    artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DistributionEntryService = Depends(get_distribution_entry_service),
):
    return to_dict_list(await service.list_for_artifact(tenant_id, artifact_id))
