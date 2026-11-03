"""Release & Version Management: the release lifecycle, version
history, and the compatibility matrix."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_release_service, get_version_service
from release_platform.release_api.serialization import to_dict, to_dict_list
from release_platform.release_engineering.release_service import ReleaseService
from release_platform.release_engineering.version_service import VersionService

router = APIRouter(prefix="/releases", tags=["release-engineering"])
compatibility_router = APIRouter(prefix="/compatibility", tags=["release-engineering"])


class CreateReleaseRequest(BaseModel):
    version: str
    channel: str
    release_branch: str | None = None
    build_metadata: str | None = None
    changelog: str = ""


@router.post("", status_code=201)
async def create_release(
    body: CreateReleaseRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.create_release(tenant_id, **body.model_dump()))


@router.get("")
async def list_releases(
    channel: str | None = None, status: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict_list(await service.list_releases(tenant_id, channel=channel, status=status))


@router.get("/{release_id}")
async def get_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.get_or_404(tenant_id, release_id))


@router.post("/{release_id}/submit-for-candidate")
async def submit_for_candidate(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.submit_for_candidate(tenant_id, release_id))


@router.post("/{release_id}/approve")
async def approve_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.approve(tenant_id, release_id))


@router.post("/{release_id}/reject")
async def reject_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.reject(tenant_id, release_id))


@router.post("/{release_id}/revoke-approval")
async def revoke_approval(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.revoke_approval(tenant_id, release_id))


@router.post("/{release_id}/release")
async def release_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.release(tenant_id, release_id))


@router.post("/{release_id}/deprecate")
async def deprecate_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.deprecate(tenant_id, release_id))


@router.post("/{release_id}/yank")
async def yank_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseService = Depends(get_release_service),
):
    return to_dict(await service.yank(tenant_id, release_id))


@router.get("/{release_id}/history")
async def get_history(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: VersionService = Depends(get_version_service),
):
    return to_dict_list(await service.list_history(tenant_id, release_id))


class AddCompatibilityEntryRequest(BaseModel):
    version: str
    component_ref: str
    compatible_from: str
    compatible_to: str | None = None


@compatibility_router.post("", status_code=201)
async def add_compatibility_entry(
    body: AddCompatibilityEntryRequest, tenant_id: str = Depends(get_current_tenant_id), service: VersionService = Depends(get_version_service),
):
    return to_dict(await service.add_compatibility_entry(tenant_id, **body.model_dump()))


@compatibility_router.get("/{version}")
async def list_compatibility(
    version: str, tenant_id: str = Depends(get_current_tenant_id), service: VersionService = Depends(get_version_service),
):
    return to_dict_list(await service.list_compatibility(tenant_id, version))


@compatibility_router.get("/{version}/check")
async def check_compatible(
    version: str, component_ref: str, candidate_version: str,
    tenant_id: str = Depends(get_current_tenant_id), service: VersionService = Depends(get_version_service),
):
    compatible = await service.check_compatible(tenant_id, version, component_ref, candidate_version)
    return {"compatible": compatible}
